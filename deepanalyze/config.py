"""
DeepAnalyze API 服务器配置模块
包含所有配置常量及环境设置
"""

import os

# 环境设置
os.environ.setdefault("MPLBACKEND", "Agg")

# API 配置
API_BASE = os.getenv("DA_API_BASE", "https://www.heywhale.com/api/model/services/69b7c9d028cbfe8349df5924/app/v1")
MODEL_PATH = os.getenv("DA_MODEL_PATH", "deepanalyze-8b")
WORKSPACE_BASE_DIR = os.getenv("DA_WORKSPACE_BASE_DIR", "workspace")
HTTP_SERVER_PORT = int(os.getenv("DA_HTTP_SERVER_PORT", "8100"))
HTTP_SERVER_BASE = f"http://localhost:{HTTP_SERVER_PORT}"

# API 服务器配置
API_HOST = os.getenv("DA_API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("DA_API_PORT", "8200"))
API_TITLE = os.getenv("DA_API_TITLE", "DeepAnalyze OpenAI-Compatible API")
API_VERSION = os.getenv("DA_API_VERSION", "1.0.0")

# 线程清理配置
CLEANUP_TIMEOUT_HOURS = int(os.getenv("DA_CLEANUP_TIMEOUT_HOURS", "12"))
CLEANUP_INTERVAL_MINUTES = int(os.getenv("DA_CLEANUP_INTERVAL_MINUTES", "30"))

# 代码执行配置
CODE_EXECUTION_TIMEOUT = int(os.getenv("DA_CODE_EXECUTION_TIMEOUT", "120"))
MAX_NEW_TOKENS = int(os.getenv("DA_MAX_NEW_TOKENS", "32768"))

# 文件处理配置
FILE_STORAGE_DIR = os.path.join(WORKSPACE_BASE_DIR, "_files")
VALID_FILE_PURPOSES = ["fine-tune", "answers", "file-extract", "assistants"]

# 模型配置
DEFAULT_TEMPERATURE = float(os.getenv("DA_DEFAULT_TEMPERATURE", "0.4"))
DEFAULT_MODEL = os.getenv("DA_DEFAULT_MODEL", "deepanalyze-8b")

# DeepAnalyze 模型停止令牌 ID
STOP_TOKEN_IDS = [151676, 151645]

# 支持的工具
SUPPORTED_TOOLS = ["code_interpreter"]
