# Core framework import
from pocketflow import Node

# Standard library imports
import logging

# Configure logging for this module with Vietnam timezone
from utils.timezone_utils import setup_vietnam_logging
from config.logging_config import logging_config

if logging_config.USE_VIETNAM_TIMEZONE:
    logger = setup_vietnam_logging(__name__, 
                                 level=getattr(logging, logging_config.LOG_LEVEL.upper()),
                                 format_str=logging_config.LOG_FORMAT)
else:
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, logging_config.LOG_LEVEL.upper()))





class RetrieveFromKB(Node):
    """
    Retrieve relevant QA pairs from Qdrant vector database using hybrid search.

    ID-based architecture - no scoring needed (FilterAgent handles semantic filtering):
    - prep(): Read query and metadata from shared
    - exec(): Call Qdrant retrieval utility
    - post(): Write lightweight {id, CAUHOI} to shared

    Output: shared["retrieved_candidates"] - list of lightweight candidates
    """

    def prep(self, shared):
        logger.info("📚 [RetrieveFromKB] PREP - Đọc query và metadata từ shared")

        # Read from shared store ONLY
        query = shared.get("query", "")
        demuc = shared.get("demuc", "")
        chu_de_con = shared.get("chu_de_con", "")

        logger.info(f"📚 [RetrieveFromKB] PREP - query='{str(query)[:80]}...', demuc='{demuc}', chu_de_con='{chu_de_con}'")
        return query, demuc, chu_de_con

    def exec(self, inputs):
        query, demuc, chu_de_con = inputs
        logger.info("📚 [RetrieveFromKB] EXEC - Bắt đầu retrieve từ Qdrant")

        # Call Qdrant retrieval utility function
        from utils.knowledge_base.qdrant_retrieval import retrieve_from_qdrant

        # Retrieve with filters if available
        retrieved_results = retrieve_from_qdrant(
            query=query,
            demuc=demuc if demuc else None,
            chu_de_con=chu_de_con if chu_de_con else None,
            top_k=20
        )

        # Extract lightweight candidates: {id, CAUHOI}
        candidates = [
            {
                "id": result["id"],
                "CAUHOI": result["CAUHOI"]
            }
            for result in retrieved_results
        ]

        # Log top results
        if candidates:
            lines = ["\n📚 [RetrieveFromKB] TOP CANDIDATES:"]
            for i, candidate in enumerate(candidates[:5], 1):
                lines.append(
                    f"  {i}. id={candidate['id']} | Q: {candidate['CAUHOI'][:80]}..."
                )
            logger.info("\n".join(lines))

        logger.info(f"📚 [RetrieveFromKB] EXEC - Retrieved {len(candidates)} candidates")
        return candidates

    def post(self, shared, prep_res, exec_res):
        logger.info("📚 [RetrieveFromKB] POST - Lưu kết quả retrieve")

        candidates = exec_res

        # Save lightweight candidates to shared store
        shared["retrieved_candidates"] = candidates

        # Update RAG state
        shared["rag_state"] = "retrieved"

        logger.info(f"📚 [RetrieveFromKB] POST - Saved {len(candidates)} candidates to 'retrieved_candidates'")

        return "default" 


