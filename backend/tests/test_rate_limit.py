"""限流：返回值、CORS 头、以及能不能被绕过。"""
import pytest

from app.config import settings
from app.middleware.rate_limit import RateLimiter


class TestRateLimiterUnit:
    def test_allows_up_to_limit_then_blocks(self):
        limiter = RateLimiter()
        for _ in range(3):
            assert limiter.check("k", 3) is True
        assert limiter.check("k", 3) is False

    def test_separate_keys_have_separate_budgets(self):
        limiter = RateLimiter()
        assert limiter.check("a", 1) is True
        assert limiter.check("b", 1) is True
        assert limiter.check("a", 1) is False

    def test_prune_drops_idle_buckets(self):
        """字典不能无限增长。

        原来的实现是每个 token 一个 key、从不清理，跑久了内存只涨不降。
        """
        limiter = RateLimiter()
        limiter.check("idle", 10)
        limiter.buckets["idle"] = [0.0]  # 假装是五分钟前打的
        limiter.check("active", 10)

        removed = limiter.prune(idle_seconds=60)

        assert removed == 1
        assert "idle" not in limiter.buckets
        assert "active" in limiter.buckets


class TestRateLimitMiddleware:
    def test_returns_429_not_500(self, client, monkeypatch):
        """超限返回 429，不是 500。

        原来是在中间件里 `raise HTTPException`。这是 Starlette 的
        BaseHTTPMiddleware —— 从它里面抛的 HTTPException 不会经过 FastAPI 的
        异常处理器，只会变成未处理异常。客户端拿到 500「服务器内部错误」，
        完全不知道是自己请求太频。
        """
        monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 1)

        first = client.get("/api/health")
        second = client.get("/api/health")

        assert first.status_code == 200
        assert second.status_code == 429

    def test_429_carries_cors_headers(self, client, monkeypatch):
        """429 响应必须带 CORS 头。

        限流中间件原来注册在 CORSMiddleware 的**外层**，它直接返回的响应不经过
        CORS 层。浏览器因此只报「网络错误」，前端既读不到 429，也读不到那句
        「请求过于频繁，请稍后再试」。
        """
        monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 0)

        resp = client.get("/api/health", headers={"Origin": "http://localhost:5173"})

        assert resp.status_code == 429
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_requests_without_token_are_still_limited(self, client, monkeypatch):
        """不带 Authorization 头也必须限流。

        原逻辑是 `if auth_header:` 才做检查 —— 只要不加这个头，限流就完全
        被绕过了。而且 /api/auth/ 整个前缀被跳过，登录接口可以无限撞密码。
        """
        monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 1)

        assert client.get("/api/health").status_code == 200
        assert client.get("/api/health").status_code == 429

    def test_login_has_a_stricter_budget(self, client, monkeypatch):
        """登录接口用更严的配额（防撞库），不受 RATE_LIMIT_PER_MINUTE 影响。

        这里把常规配额调到很大，登录仍然应该在 10 次之后被拦。
        """
        monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 1000)

        codes = [
            client.post(
                "/api/auth/login",
                json={"username": "nobody", "password": "wrong-password"},
            ).status_code
            for _ in range(11)
        ]

        assert codes[:10] == [401] * 10, "前 10 次应当是正常的凭据错误"
        assert codes[10] == 429, "第 11 次应当被限流拦住"

    def test_non_api_paths_are_not_limited(self, client, monkeypatch):
        """非 /api/ 路径不限流 —— 静态页面、/docs 不该被限。"""
        monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 0)

        assert client.get("/docs").status_code == 200
        assert client.get("/api/health").status_code == 429
