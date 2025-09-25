import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Optional dependencies
try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None  # type: ignore

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore


OQA_CSV_PATH = os.path.join("medical_knowledge_base", "oqa_v1_dataset.csv")


def _ensure_str(x: Any) -> str:
    if x is None:
        return ""
    s = str(x)
    return " ".join(s.replace("\n", " ").replace("\r", " ").split())


class OQAVectorIndex:
    """In-memory vector index for OQA English dataset.

    - Builds sentence-transformer embeddings if available; otherwise falls back to TF-IDF-like mean hashing.
    - Uses FAISS inner-product index if available; otherwise performs numpy cosine search.
    """

    def __init__(self, csv_path: str = OQA_CSV_PATH) -> None:
        if not os.path.isfile(csv_path):
            raise FileNotFoundError(f"OQA dataset not found: {csv_path}")

        # Load
        df = None
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                df = pd.read_csv(csv_path, encoding=enc)
                break
            except Exception:
                continue
        if df is None:
            raise ValueError(f"Failed to read OQA CSV: {csv_path}")

        # Normalize and keep only needed columns
        expected_cols = [
            "question",
            "context",
            "answers",
            "answer_sentence",
            "topic",
            "reference",
            "id",
        ]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""

        df = df[expected_cols].copy()
        for col in expected_cols:
            df[col] = df[col].apply(_ensure_str)

        # Compose text to embed
        texts: List[str] = []
        for _, row in df.iterrows():
            q = row.get("question", "")
            ctx = row.get("context", "")
            ans = row.get("answers", "") or row.get("answer_sentence", "")
            composed = f"Question: {q}\nContext: {ctx}\nAnswer: {ans}"
            texts.append(composed)

        # Build embeddings
        self._embeddings: np.ndarray
        self._dim: int
        self._use_faiss = False

        emb_model: Optional[SentenceTransformer] = None
        if SentenceTransformer is not None:
            try:
                emb_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            except Exception:
                emb_model = None

        if emb_model is not None:
            emb = emb_model.encode(texts, normalize_embeddings=True, convert_to_numpy=True, batch_size=64)
            self._embeddings = emb.astype(np.float32)
        else:
            # Very light-weight fallback: simple hashing-based bag embedding
            # Not ideal, but avoids heavy deps if environment lacks models
            rng = np.random.default_rng(42)
            dim = 384
            vocab: Dict[str, np.ndarray] = {}

            def word_vec(w: str) -> np.ndarray:
                v = vocab.get(w)
                if v is None:
                    # deterministic pseudo-vector for word
                    seed = abs(hash(w)) % (2**32)
                    rng_local = np.random.default_rng(seed)
                    v = rng_local.standard_normal(dim).astype(np.float32)
                    vocab[w] = v
                return v

            embeds: List[np.ndarray] = []
            for t in texts:
                words = [w for w in _ensure_str(t).lower().split() if w]
                if not words:
                    embeds.append(np.zeros((dim,), dtype=np.float32))
                    continue
                mat = np.stack([word_vec(w) for w in words], axis=0)
                v = mat.mean(axis=0)
                # L2 normalize
                n = np.linalg.norm(v) + 1e-8
                v = (v / n).astype(np.float32)
                embeds.append(v)
            self._embeddings = np.stack(embeds, axis=0)

        self._dim = int(self._embeddings.shape[1])

        # FAISS index
        self._faiss_index = None
        if faiss is not None and self._embeddings.shape[0] > 0:
            try:
                index = faiss.IndexFlatIP(self._dim)
                index.add(self._embeddings)
                self._faiss_index = index
                self._use_faiss = True
            except Exception:
                self._faiss_index = None
                self._use_faiss = False

        # Store rows for result mapping
        self._df = df.reset_index(drop=True)

    def _embed_query(self, query: str) -> np.ndarray:
        if SentenceTransformer is not None:
            try:
                model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                v = model.encode([_ensure_str(query)], normalize_embeddings=True, convert_to_numpy=True)
                return v.astype(np.float32)[0]
            except Exception:
                pass
        # fallback: same hashing approach as above
        dim = int(self._embeddings.shape[1])
        rng = np.random.default_rng(43)

        def word_vec(w: str) -> np.ndarray:
            seed = abs(hash(w)) % (2**32)
            rng_local = np.random.default_rng(seed)
            return rng_local.standard_normal(dim).astype(np.float32)

        words = [w for w in _ensure_str(query).lower().split() if w]
        if not words:
            return np.zeros((dim,), dtype=np.float32)
        mat = np.stack([word_vec(w) for w in words], axis=0)
        v = mat.mean(axis=0)
        n = np.linalg.norm(v) + 1e-8
        return (v / n).astype(np.float32)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not query or self._embeddings.shape[0] == 0:
            return []
        q = self._embed_query(query)
        if self._use_faiss and self._faiss_index is not None:
            D, I = self._faiss_index.search(q.reshape(1, -1), int(min(top_k, self._embeddings.shape[0])))
            idxs = I[0].tolist()
            sims = D[0].tolist()
        else:
            sims = (self._embeddings @ q.reshape(-1, 1)).ravel()  # cosine if normalized
            k = int(min(top_k, sims.shape[0]))
            part = np.argpartition(sims, -k)[-k:]
            idxs = part[np.argsort(sims[part])[::-1]].tolist()
            sims = [float(sims[i]) for i in idxs]

        results: List[Dict[str, Any]] = []
        for idx, sc in zip(idxs, sims):
            row = self._df.iloc[int(idx)]
            results.append(
                {
                    "score": float(sc),
                    "question": _ensure_str(row.get("question", "")),
                    "context": _ensure_str(row.get("context", "")),
                    "answer": _ensure_str(row.get("answers", "")) or _ensure_str(row.get("answer_sentence", "")),
                    "reference": _ensure_str(row.get("reference", "")),
                    "id": _ensure_str(row.get("id", "")),
                }
            )
        return results

    def get_random(self, amount: int = 5) -> List[Dict[str, Any]]:
        if len(self._df) == 0:
            return []
        n = min(amount, len(self._df))
        sampled = self._df.sample(n=n, random_state=123)
        out: List[Dict[str, Any]] = []
        for _, row in sampled.iterrows():
            out.append(
                {
                    "score": 1.0,
                    "question": _ensure_str(row.get("question", "")),
                    "context": _ensure_str(row.get("context", "")),
                    "answer": _ensure_str(row.get("answers", "")) or _ensure_str(row.get("answer_sentence", "")),
                    "reference": _ensure_str(row.get("reference", "")),
                    "id": _ensure_str(row.get("id", "")),
                }
            )
        return out


_OQA_INDEX: Optional[OQAVectorIndex] = None


def get_oqa_index() -> OQAVectorIndex:
    global _OQA_INDEX
    if _OQA_INDEX is None:
        _OQA_INDEX = OQAVectorIndex()
    return _OQA_INDEX


def preload_oqa_index() -> None:
    """Preload OQA index into memory during server startup."""
    global _OQA_INDEX
    if _OQA_INDEX is None:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(" Loading OQA vector index into memory...")
        try:
            _OQA_INDEX = OQAVectorIndex()
            logger.info(f" OQA index loaded successfully: {_OQA_INDEX._embeddings.shape[0]} items, {_OQA_INDEX._dim}D embeddings")
        except Exception as e:
            logger.error(f" Failed to load OQA index: {e}")
            raise


def is_oqa_index_loaded() -> bool:
    """Check if OQA index is already loaded in memory."""
    return _OQA_INDEX is not None


def retrieve_oqa(query: str, top_k: int = 5) -> Tuple[List[Dict[str, Any]], float]:
    idx = get_oqa_index()
    res = idx.search(query, top_k=top_k)
    score = float(res[0]["score"]) if res else 0.0
    return res, score


def retrieve_random_oqa(amount: int = 5) -> List[Dict[str, Any]]:
    idx = get_oqa_index()
    return idx.get_random(amount)


