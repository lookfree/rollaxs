import bcrypt
import time
from collections import defaultdict, deque


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


class RateLimiter:
    def __init__(self, max_hits: int = 5, window_sec: int = 60):
        self.max_hits, self.window = max_hits, window_sec
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        # 顺手清理整窗过期的旧 key,防止字典无限增长
        if len(self.hits) > 1000:
            for k in [k for k, dq in self.hits.items() if not dq or now - dq[-1] > self.window]:
                del self.hits[k]
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max_hits:
            return False
        q.append(now)
        return True

    def reset(self) -> None:
        """Clear all state — useful in tests."""
        self.hits.clear()
