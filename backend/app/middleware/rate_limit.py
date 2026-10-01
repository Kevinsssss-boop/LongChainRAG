"""滑动窗口限流。

原来的实现有四个问题，每一个都能单独把限流变成摆设、或者把正常错误报成 500：

1. **在中间件里 raise HTTPException → 客户端收到 500。**
   这是 Starlette 的 BaseHTTPMiddleware，从它里面抛 HTTPException 不会经过
   FastAPI 的异常处理器，只会变成未处理异常。用户看到的是「服务器内部错误」，
   而不是 429「请求过于频繁」。
2. **缺 CORS 头。** 限流中间件注册得比 CORSMiddleware 更靠外，它直接返回的
   响应根本不经过 CORS 层。浏览器因此只会报「网络错误」，看不到状态码和文案。
   修法是把注册顺序倒过来，见 app/main.py。
3. **可以绕过。** 原逻辑是 `if auth_header:` 才检查 —— 只要不带 Authorization
   头就完全不受限；而 `/api/auth/` 整个前缀被跳过，登录接口可以无限撞密码。
   现在：有 token 按用户计，没 token 按客户端 IP 计，登录/注册单独用更严的配额。
4. **字典无限增长。** 每个 token 一个 key，且从不清理，跑久了内存只涨不降。

（顺带说明为什么没直接用 requirements 里的 slowapi：它要求每个端点显式声明
`request: Request` 参数并挂装饰器，等于把所有路由改一遍。中间件方案修好这四条
就够了。）
"""

import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.security import decode_access_token

# 登录/注册可以被拿来撞密码，单独用更严的配额
_STRICT_PATHS = ("/api/auth/login", "/api/auth/register")
_STRICT_LIMIT_PER_MINUTE = 10

_WINDOW_SECONDS = 60
# 每这么多次调用清一次空闲 bucket，避免字典无限增长
_PRUNE_EVERY = 1000
# 超过这个时长没有任何请求的 bucket 视为空闲
_PRUNE_IDLE_SECONDS = 300


class RateLimiter:
    """滑动窗口：记录窗口内每次请求的时间戳。"""

    def __init__(self):
        self.buckets: dict[str, list[float]] = defaultdict(list)
        self._calls = 0

    def check(self, key: str, limit: int) -> bool:
        """记一次请求。超过配额返回 False。"""
        self._calls += 1
        if self._calls % _PRUNE_EVERY == 0:
            self.prune()

        now = time.time()
        window_start = now - _WINDOW_SECONDS

        hits = [t for t in self.buckets[key] if t > window_start]
        if len(hits) >= limit:
            # 写回裁剪后的列表，否则过期时间戳会一直堆在里面
            self.buckets[key] = hits
            return False

        hits.append(now)
        self.buckets[key] = hits
        return True

    def prune(self, idle_seconds: float = _PRUNE_IDLE_SECONDS) -> int:
        """清掉长时间没动静的 bucket，返回清掉的个数。"""
        now = time.time()
        dead = [
            key for key, hits in self.buckets.items()
            if not hits or hits[-1] < now - idle_seconds
        ]
        for key in dead:
            del self.buckets[key]
        return len(dead)


rate_limiter = RateLimiter()


def _client_ip(request: Request) -> str:
    """取客户端 IP。放在反向代理后面时必须看 X-Forwarded-For，
    否则所有请求的来源都是代理本身，等于全站共用一个配额。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _identify(request: Request) -> str:
    """限流身份：带 token 按用户算，不带 token 按 IP 算。

    关键是**不带 token 也要限流**。原来写的是 `if auth_header:` ——
    只要不加 Authorization 头就完全绕过了限流。
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        payload = decode_access_token(auth_header[7:])
        if payload and payload.get("sub"):
            # 解 token 不查库，是一次 HMAC 校验，足够便宜
            return f"user:{payload['sub']}"
    return f"ip:{_client_ip(request)}"


async def rate_limit_middleware(request: Request, call_next):
    """Rate limit middleware for FastAPI."""
    # 压测模式关掉限流：压测本来就是要在短时间内打出大量请求
    if settings.STRESS_TEST_MODE:
        return await call_next(request)

    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)

    limit = (
        _STRICT_LIMIT_PER_MINUTE
        if path.startswith(_STRICT_PATHS)
        else settings.RATE_LIMIT_PER_MINUTE
    )

    if not rate_limiter.check(_identify(request), limit):
        # 返回 JSONResponse 而不是 raise HTTPException：
        # 中间件里抛的 HTTPException 不会被 FastAPI 的异常处理器接住，
        # 客户端拿到的是 500 而不是 429。
        return JSONResponse(
            status_code=429,
            content={"detail": "请求过于频繁，请稍后再试"},
            headers={"Retry-After": str(_WINDOW_SECONDS)},
        )

    return await call_next(request)
