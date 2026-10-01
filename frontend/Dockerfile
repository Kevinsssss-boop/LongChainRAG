# 前端镜像：构建出静态文件，交给 nginx 托管，并把 /api 反代到后端。
#
# ⚠️ 未在本机实测（写这份文件时这台机器上没有 Docker）。
#    首次构建时确认两件事：
#      1) npm ci 能过 —— 它严格按 package-lock.json 装，lock 和 package.json
#         不一致会直接失败（这是故意的）
#      2) 浏览器里发一条消息，回答是**逐字**出现的。如果整段一次性蹦出来，
#         说明 nginx 的 proxy_buffering 没关掉（见 nginx.conf）。
#    跑通了就把上面这段删掉。

FROM node:22-slim AS builder

WORKDIR /build

# 只拷依赖清单再装，业务代码改动不会触发重装 node_modules
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


FROM nginx:1.27-alpine

COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
