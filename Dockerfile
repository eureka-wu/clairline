# =========================================================================
# 阶段 1: 前端构建 (Node.js 编译 Vue3 + Vite)
# 使用 --platform=$BUILDPLATFORM 强制在宿主机原生架构上执行前端编译 (仅耗时3~5秒，
# 彻底消除在 QEMU ARM64 模拟器下死锁与卡顿数小时的恶性问题)
# =========================================================================
FROM --platform=$BUILDPLATFORM node:20-alpine AS frontend-builder
WORKDIR /build/frontend

# 优先缓存依赖层
COPY frontend/package*.json ./
RUN npm install

# 编译生成前端静态产物
COPY frontend/ ./
RUN npm run build

# =========================================================================
# 阶段 2: 极轻量 Python 运行镜像 (前后端一体化伺服)
# =========================================================================
FROM python:3.12-slim AS runner

WORKDIR /app

# 设置无缓冲与 UTF-8 字符编码
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Docker 容器纯粹作为无头 (Headless) Web API 与 MCP 智能服务运行
# 仅需 requests, bottle, Pillow，彻底剔除桌面端专用的 pyinstaller 与 pywebview (GUI)
# 避免在 ARM64 QEMU 下触发漫长的 C 语言源码编译
RUN pip install --no-cache-dir requests>=2.31.0 bottle>=0.12.25 Pillow>=10.0.0 pymysql>=1.1.0 cryptography>=42.0.0

# 复制后端核心逻辑
COPY backend/ /app/backend/

# 将阶段 1 编译的前端静态产物复制至容器目录
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# 挂载数据卷目录，持久化 SQLite 数据库与用户配置
VOLUME ["/app/backend/data"]

# 暴露 Web 与 API 服务端口
EXPOSE 3000

# 启动一体化服务
CMD ["python", "backend/server.py"]
