"""
DeepAnalyze API 服务器主应用入口
设置 FastAPI 应用并启动服务器
"""

import time
import threading
import signal
import sys
import atexit
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import API_HOST, API_PORT, API_TITLE, API_VERSION, HTTP_SERVER_PORT, CLEANUP_INTERVAL_MINUTES
from models import HealthResponse
from utils import start_http_server
from storage import storage

# 安全常量
# MAX_CLEANUP_ERRORS = 10
# MAX_ITERATIONS = 1000
# CLEANUP_BACKOFF_SECONDS = 30


def _ensure_utf8_stdio():
    """Windows 控制台通常使用 GBK 编码；启动日志中的表情符号可能引发 UnicodeEncodeError"""
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError, AttributeError):
            pass


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    app = FastAPI(title=API_TITLE, version=API_VERSION)

    # 添加 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 引入所有路由
    from file_api import router as file_router
    from models_api import router as models_router
    from chat_api import router as chat_router
    from admin_api import router as admin_router

    app.include_router(file_router)
    app.include_router(models_router)
    app.include_router(chat_router)
    app.include_router(admin_router)

    # 健康检查端点
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """健康检查端点"""
        return HealthResponse(
            status="healthy",
            timestamp=int(time.time())
        )

    return app


def main():
    """启动 API 服务器的主入口"""
    print("🚀 Starting DeepAnalyze OpenAI-Compatible API Server...")
    print(f"   - API Server: http://{API_HOST}:{API_PORT}")
    print(f"   - File Server: http://localhost:{HTTP_SERVER_PORT}")
    print(f"   - Workspace: workspace")
    print("\n📖 API Endpoints:")
    print("   - Models API: /v1/models")
    print("   - Files API: /v1/files")
    print("   - Chat API: /v1/chat/completions")
    print("   - Admin API: /v1/admin")

    # Start HTTP file server in a separate thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    # Create and start the FastAPI application
    app = create_app()

    print("Starting API server...")
    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    _ensure_utf8_stdio()
    main()