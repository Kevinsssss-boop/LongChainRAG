"""Debug endpoint: test Bailian API connection directly."""
from fastapi import APIRouter
import httpx

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/health2")
def health2():
    """Simple health check without DB."""
    return {"status": "ok", "msg": "debug router working"}


@router.post("/test-llm")
async def test_llm(message: str = "你好"):
    """Direct LLM test — no auth, no RAG. Just call DashScope."""
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key = "sk-ws-H.ELYHPLR.2VlI.MEUCIFFaWf8UxibRgvJB8ejL17woar62U3hyHrFf9Z9Ia1SSAiEAk32HcBP0ez8krhVQDDt_wnPPM_uIo1ju2rOZ9fXQgKo"

    async with httpx.AsyncClient(base_url=url, timeout=60) as client:
        resp = await client.post(
            "/chat/completions",
            json={
                "model": "qwen-plus",
                "messages": [
                    {"role": "user", "content": message},
                ],
                "max_tokens": 200,
            },
            headers={"Authorization": f"Bearer {api_key}"},
        )
        return resp.json()
