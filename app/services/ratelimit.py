"""Per-user rolling-window rate limiting for booking creation."""
import threading
import time

from ..errors import AppError

_WINDOW_SECONDS = 60
_MAX_REQUESTS = 20

_buckets: dict[int, list[float]] = {}
_lock = threading.Lock()


def record_and_check(user_id: int) -> None:
    now = time.time()
    with _lock:
        bucket = _buckets.get(user_id, [])
        bucket = [t for t in bucket if t > now - _WINDOW_SECONDS]

        if len(bucket) >= _MAX_REQUESTS:
            _buckets[user_id] = bucket
            raise AppError(429, "RATE_LIMITED", "Too many booking requests")

        bucket.append(now)
        _buckets[user_id] = bucket


def cleanup_stale_buckets() -> None:
    """Remove buckets with no timestamps inside the current window.

    Call this periodically (e.g. a background task every few minutes) to
    stop _buckets from growing unbounded for users who stop making requests.
    """
    now = time.time()
    with _lock:
        stale = [
            uid for uid, bucket in _buckets.items()
            if not any(t > now - _WINDOW_SECONDS for t in bucket)
        ]
        for uid in stale:
            del _buckets[uid]
