import time

from fastapi import HTTPException

_limiters: list["RateLimiter"] = []


class RateLimiter:
    # shortcut: per-process fixed window, swap for Redis when running >1 worker
    def __init__(self, limit: int, window_s: int):
        self.limit, self.window_s = limit, window_s
        self._hits: dict[str, tuple[float, int]] = {}
        _limiters.append(self)

    def check(self, key: str) -> None:
        now = time.monotonic()
        start, n = self._hits.get(key, (now, 0))
        if now - start >= self.window_s:
            start, n = now, 0
        if n >= self.limit:
            raise HTTPException(429, {"code": "rate_limited", "message_key": "errors.rate_limited"})
        self._hits[key] = (start, n + 1)

    def reset(self) -> None:
        self._hits.clear()


def reset_all() -> None:
    for lim in _limiters:
        lim.reset()
