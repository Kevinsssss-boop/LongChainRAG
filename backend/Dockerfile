# 后端镜像。构建上下文是 backend/（见仓库根的 docker-compose.yml）。
#
# ⚠️ 未在本机实测。写这份文件时这台机器上没装 Docker（`docker` 命令不存在），
#    所以它没有经过任何一次真实构建。首次使用前请先构建一次并确认：
#      1) chromadb / bcrypt 在 linux 上有对应的 wheel（没有就会去编译，
#         那需要 build-essential，第一阶段已经装了）
#      2) /api/health 能返回 200（HEALTHCHECK 依赖它）
#      3) 上传文件确实落在挂载出来的 /app/data 卷里，容器重建后还在
#    跑通了就把上面这段删掉。
#
# 分阶段构建：第一阶段装依赖（要编译工具链，很大），
# 第二阶段只拷贝装好的 venv 和源码，不带编译器、不带 pip 缓存。

FROM python:3.13-slim AS builder

# 少数包没有 wheel 时需要现场编译；装完即弃，不进最终镜像
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# 先只拷依赖声明再装。只要这两个文件没变，这一层就走缓存 ——
# 改业务代码不会触发重装那 122 个包。
COPY requirements.lock requirements.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.lock


FROM python:3.13-slim AS runtime

# PYTHONDONTWRITEBYTECODE：不写 .pyc，容器里没意义
# PYTHONUNBUFFERED  ：日志实时输出，否则 docker logs 要等缓冲区满
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# 非 root 运行：应用被攻破时，攻击者拿到的不是 root shell
RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=appuser:appuser . /app/

# SQLite / Chroma / 上传文件都写在 /app/data 下，compose 里挂成卷
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

USER appuser

EXPOSE 8000

# 用标准库 urllib 做健康检查，不为了 curl 再往镜像里装东西
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
