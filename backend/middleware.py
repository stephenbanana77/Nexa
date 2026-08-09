"""Simple in-memory rate limiter middleware."""
import os
import time
from collections import defaultdict
from fastapi import Request, HTTPException


class RateLimiter:
    """Token-bucket style rate limiter. Per-user, per-endpoint categories."""

    def __init__(self):
        # {user_id: [(timestamp,)]
        self._chat_requests: dict[str, list[float]] = defaultdict(list)
        self._upload_requests: dict[str, list[float]] = defaultdict(list)
        self._general_requests: dict[str, list[float]] = defaultdict(list)
        self._login_requests: dict[str, list[float]] = defaultdict(list)

        # Limits
        self.chat_per_minute = 20    # chat/analysis calls
        self.upload_per_minute = 5   # file uploads
        self.login_per_minute = 5    # login attempts
        self.general_per_minute = 60 # everything else

    def _check(self, bucket: dict[str, list[float]], key: str, limit: int, window: float = 60) -> bool:
        now = time.time()
        # Remove old entries
        bucket[key] = [t for t in bucket[key] if now - t < window]
        if len(bucket[key]) >= limit:
            return False
        bucket[key].append(now)
        return True

    def check_chat(self, user_id: str) -> bool:
        return self._check(self._chat_requests, user_id, self.chat_per_minute)

    def check_upload(self, user_id: str) -> bool:
        return self._check(self._upload_requests, user_id, self.upload_per_minute)

    def check_general(self, user_id: str) -> bool:
        return self._check(self._general_requests, user_id, self.general_per_minute)

    def check_login(self, user_id: str) -> bool:
        return self._check(self._login_requests, user_id, self.login_per_minute)


# Singleton
_rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware to enforce rate limits."""
    # Allow bypass in test/dev environments
    if os.environ.get("ENABLE_RATE_LIMIT", "true").lower() == "false":
        return await call_next(request)

    # Use client IP only (NOT x-user-id header — trivially forgeable)
    forwarded = request.headers.get("X-Forwarded-For")
    user_id = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")

    path = request.url.path
    method = request.method

    # Chat/analysis endpoints
    if "/api/chat" in path and method == "POST":
        if not _rate_limiter.check_chat(user_id):
            raise HTTPException(status_code=429, detail="Too many analysis requests. Please wait a moment.", headers={"Retry-After": "30"})

    # Login endpoint (brute force protection)
    if "/api/auth/login" in path and method == "POST":
        if not _rate_limiter.check_login(user_id):
            raise HTTPException(status_code=429, detail="Too many login attempts. Please wait a moment.", headers={"Retry-After": "60"})

    # Upload endpoints
    elif "/api/datasets/upload" in path and method == "POST":
        if not _rate_limiter.check_upload(user_id):
            raise HTTPException(status_code=429, detail="Too many uploads. Please wait a moment.", headers={"Retry-After": "30"})

    # General endpoints
    elif not _rate_limiter.check_general(user_id):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.", headers={"Retry-After": "10"})

    response = await call_next(request)
    return response
