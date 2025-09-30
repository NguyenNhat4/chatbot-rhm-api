import os
import logging
import re
import random
from dotenv import load_dotenv
from google import genai
from google.genai import types
load_dotenv()
logger = logging.getLogger(__name__)

class APIOverloadException(Exception):
    pass

class APIKeyManager:
    def __init__(self):
        self.api_keys = []
        self.current_key_index = 0
        self.failed_keys = set()
        self._load_api_keys()
        random.shuffle(self.api_keys)
        logger.info(f"🔀 Shuffled {len(self.api_keys)} API keys")

    def _load_api_keys(self):
        multi = os.getenv("GEMINI_API_KEYS", "")
        if multi:
            self.api_keys = [k.strip() for k in multi.split(",") if k.strip()]
            logger.info(f"🔑 Loaded {len(self.api_keys)} keys (GEMINI_API_KEYS)")
        else:
            single = os.getenv("GEMINI_API_KEY", "")
            if not single:
                raise RuntimeError("No Gemini API keys configured")
            self.api_keys = [single]
            logger.info("🔑 Loaded 1 key (GEMINI_API_KEY)")

    def get_current_key(self):
        available = [i for i in range(len(self.api_keys)) if i not in self.failed_keys]
        if not available:
            logger.warning("⚠️ All keys failed recently; resetting")
            self.failed_keys.clear()
            available = list(range(len(self.api_keys)))
        if self.current_key_index in available:
            return self.api_keys[self.current_key_index], self.current_key_index
        self.current_key_index = available[0]
        return self.api_keys[self.current_key_index], self.current_key_index

    def mark_key_failed(self, idx: int):
        self.failed_keys.add(idx)
        logger.warning(f"🚫 Marked key {idx} as failed")

    def switch_to_next_key(self) -> bool:
        available = [i for i in range(len(self.api_keys)) if i not in self.failed_keys]
        if len(available) <= 1:
            logger.warning("⚠️ No alternate keys available")
            return False
        if self.current_key_index in available:
            available.remove(self.current_key_index)
        old = self.current_key_index
        self.current_key_index = available[0]
        logger.info(f"🔄 Switched key {old} -> {self.current_key_index}")
        return True

api_manager = APIKeyManager()

def reset_failed_keys():
    api_manager.failed_keys.clear()
    logger.info("🔄 Reset failed keys")


def get_api_key_status():
    total = len(api_manager.api_keys)
    failed = len(api_manager.failed_keys)
    return {
        "total_keys": total,
        "active_keys": total - failed,
        "failed_keys": failed,
        "current_key_index": api_manager.current_key_index,
        "failed_key_indices": list(api_manager.failed_keys),
    }

def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    vn_chars = len(re.findall(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđĐ]', text))
    total = len(text)
    return max(1, int(total / (3.2 if vn_chars > total * 0.1 else 3.8)))



def call_llm(prompt: str, fast_mode: bool = False) -> str:
    model_id =  os.getenv("GEMINI_MODEL")
    logger.info(f"🎯 model: {model_id}")

    max_retries = len(api_manager.api_keys)
    retry = 0
    last_err = None

    while retry < max_retries:
        api_key, key_idx = api_manager.get_current_key()
        try:
            client = genai.Client(api_key=api_key)

            response = client.models.generate_content(
            model=model_id,
            contents=prompt
          
        )

            text = getattr(response, "text", None)
            if not text:
                # fallback lấy từ candidates nếu cần
                cands = getattr(response, "candidates", None)
                if cands and getattr(cands[0], "content", None) and cands[0].content.parts:
                    text = getattr(cands[0].content.parts[0], "text", None)
            if not text:
                logger.error("Không lấy được text trong response")
                return "Xin lỗi, không thể tạo response."

            logger.info(f"✅ key {key_idx} OK, out len={len(text)}, est tokens={estimate_tokens(text)}")
            logger.info(f"📤 preview: {text[:200]}…")
            return text

        except Exception as e:
            es = str(e)
            last_err = es
            logger.error(f"❌ key {key_idx} error: {es}")

            # quota / quá tải
            if any(s in es for s in ["429", "RESOURCE_EXHAUSTED", "quota"]):
                api_manager.mark_key_failed(key_idx)
                if api_manager.switch_to_next_key():
                    retry += 1
                    logger.info(f"🔄 retry {retry}/{max_retries}")
                    continue
                raise APIOverloadException("All API keys quota exceeded")

            if any(s in es.lower() for s in ["overload", "temporarily unavailable", "503", "500"]):
                api_manager.mark_key_failed(key_idx)
                if api_manager.switch_to_next_key():
                    retry += 1
                    logger.info(f"🔄 retry {retry}/{max_retries}")
                    continue
                raise APIOverloadException("All API servers overloaded")

            # Lỗi “model không tồn tại” khi lỡ để -002 / models/
            if "NOT_FOUND" in es or "404" in es:
                return ("Model không hợp lệ. Dùng 'gemini-1.5-flash' hoặc 'gemini-1.5-flash-8b' "
                        "(không prefix 'models/', không hậu tố '-002').")

            return "Xin lỗi, hiện chưa xử lý được yêu cầu."
    return "Xin lỗi, hiện chưa xử lý được yêu cầu."

if __name__ == "__main__":
    print(call_llm("Hello, how are you?", fast_mode=True))
