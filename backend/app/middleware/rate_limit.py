import time
from collections import defaultdict
from fastapi import Request, HTTPException, status
from app.config import settings


class RateLimiter:
    """Token bucket rate limiter per user."""

    def __init__(self):
        self.buckets: dict[str, list[float]] = defaultdict(list)

    def check(self, user_id: str) -> bool:
        """Check if the request is allowed. Returns True if allowed."""
        now = time.time()
        window_start = now - 60  # 1 minute window

        # Clean old entries
        self.buckets[user_id] = [t for t in self.buckets[user_id] if t > window_start]

        if len(self.buckets[user_id]) >= settings.RATE_LIMIT_PER_MINUTE:
            return False

        self.buckets[user_id].append(now)
        return True


rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """Rate limit middleware for FastAPI."""
    # Bypass rate limiting in stress test mode
    if settings.STRESS_TEST_MODE:
        return await call_next(request)

    # Skip rate limiting for non-API routes
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    # Skip rate limiting for auth endpoints
    if request.url.path.startswith("/api/auth/"):
        return await call_next(request)

    # Get user from token
    auth_header = request.headers.get("Authorization")
    if auth_header:
        user_id = auth_header  # Use token as identifier
        if not rate_limiter.check(user_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试",
            )

    return await call_next(request)