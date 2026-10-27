# ==========================================
# 阶段 1: 前端构建 (Node.js 编译 Vue3 + Vite)
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /build/frontend

# 优先缓存依赖层
COPY frontend/package*.json ./
RUN npm install

# 编译生成静态静态文件
COPY frontend/ ./
RUN npm run build

# ==========================================
# 阶段 2: 极轻量 Python 运行镜像 (一体化伺服)
# ==========================================
FROM python:3.12-slim AS runner

WORKDIR /app

# 设置无缓冲与字符编码
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# 安装运行时依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端逻辑与核心代码
COPY backend/ /app/backend/

# 将阶段 1 编译的前端产物复制到容器内
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# 挂载数据卷目录，持久化 SQLite 数据库与用户配置
VOLUME ["/app/backend/data"]

# 暴露 Web 与 API 服务端口
EXPOSE 3000

# 启动一体化服务
CMD ["python", "backend/server.py"]
