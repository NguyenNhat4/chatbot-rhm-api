import os
import re
import time
from typing import List, Dict, Optional, Tuple


class APIOverloadException(Exception):
    """Exception raised when all API keys are overloaded or unavailable"""
    pass


class APIKeyManager:
    """
    Quản lý pool API key với:
    - Cooldown theo RetryInfo/Retry-After (khi dính 429/quota).
    - Đánh dấu lỗi tạm thời (5xx) và lỗi vĩnh viễn (key invalid).
    - Chọn key khả dụng tiếp theo (bỏ qua key đang cooldown/failed).

    ENV hỗ trợ:
      GEMINI_API_KEY           = "sk-..."                 # 1 key
      GEMINI_DEFAULT_COOLDOWN  = "60"                     # (tuỳ) giây khi không có RetryInfo
      GEMINI_TRANSIENT_COOLDOWN= "10"                     # (tuỳ) giây cho lỗi tạm thời (5xx)
    """

    _RETRY_DELAY_PATTERNS = [
        re.compile(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)s", re.I),
        re.compile(r"retry in ([0-9.]+)s", re.I),
        re.compile(r"Retry-After:\s*([0-9]+)", re.I),  # header dạng giây
    ]

    def __init__(self) -> None:
        self.api_keys: List[str] = []
        self.failed_keys: set[int] = set()        # lỗi vĩnh viễn (invalid key)
        self.cooldown_until: Dict[int, float] = {}  # idx -> unix_ts
        self.current_idx: Optional[int] = None
        self.default_cooldown = int(os.getenv("GEMINI_DEFAULT_COOLDOWN", "60"))
        self.transient_cooldown = int(os.getenv("GEMINI_TRANSIENT_COOLDOWN", "10"))
        self._load_api_keys()

    # ---------- Loaders ----------

    def _load_api_keys(self) -> None:
        single = os.getenv("GEMINI_API_KEY", "").strip()
        if not single:
            raise RuntimeError("No Gemini API keys configured. Please set GEMINI_API_KEY environment variable.")
        self.api_keys = [single]

    # ---------- Core Utils ----------

    def _now(self) -> float:
        return time.time()

    def is_available(self, idx: int) -> bool:
        if idx in self.failed_keys:
            return False
        until = self.cooldown_until.get(idx, 0.0)
        return self._now() >= until

    def set_cooldown(self, idx: int, seconds: int) -> None:
        seconds = max(1, int(seconds))
        self.cooldown_until[idx] = self._now() + seconds

    def clear_cooldown(self, idx: int) -> None:
        self.cooldown_until.pop(idx, None)

    def reset_failed_keys(self) -> None:
        self.failed_keys.clear()

    def parse_retry_delay(self, err_msg: str) -> int:
        if not err_msg:
            return self.default_cooldown
        for pat in self._RETRY_DELAY_PATTERNS:
            m = pat.search(err_msg)
            if m:
                try:
                    return max(1, int(float(m.group(1))))
                except Exception:
                    continue
        return self.default_cooldown

    # ---------- Markers ----------

    def mark_quota_exhausted(self, idx: int, err_msg: Optional[str] = None) -> None:
        """429/RESOURCE_EXHAUSTED → cooldown theo RetryInfo/Retry-After."""
        delay = self.parse_retry_delay(err_msg or "")
        self.set_cooldown(idx, delay)

    def mark_transient_error(self, idx: int) -> None:
        """5xx/overload → cooldown ngắn để tránh dội cùng key."""
        self.set_cooldown(idx, self.transient_cooldown)

    def mark_permanent_fail(self, idx: int) -> None:
        """Key invalid (401/403/404 NOT_FOUND model, v.v.) → loại khỏi pool."""
        self.failed_keys.add(idx)
        self.clear_cooldown(idx)

    # ---------- Picking ----------

    def pick_key(self) -> Tuple[str, int]:
        """
        Trả về (api_key, idx).
        """
        # Since we only have one key, check if it is available.
        # If it is available, return it.
        # If it is not available (cooldown), we return it anyway because we have no other choice.
        # The caller might retry or fail, but this manager's job is just to give the key.
        # However, looking at the original logic:
        # "If all cooling down -> choose key with shortest cooldown".
        # So for 1 key, we just return it.

        idx = 0
        self.current_idx = idx
        return self.api_keys[idx], idx

    # ---------- Introspection ----------

    def status(self) -> Dict:
        return {
            "total": len(self.api_keys),
            "failed": sorted(list(self.failed_keys)),
            "cooldowns": {i: max(0, int(self.cooldown_until.get(i, 0) - self._now()))
                          for i in range(len(self.api_keys))
                          if self.cooldown_until.get(i, 0) > self._now()},
            "current_idx": self.current_idx,
        }
api_manager = APIKeyManager()
