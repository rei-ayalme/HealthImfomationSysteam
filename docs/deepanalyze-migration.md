# DeepAnalyze 迁移说明

## 1. 迁移步骤
- 将 `d:\python_HIS\pythonProject\da_quick_start` 的核心源码与文档复制到根目录 `deepanalyze/`。
- 排除非源码目录：`venv/`、`__pycache__/`、`workspace/`。
- 新增 Node 启动层：`deepanalyze/index.js`、`deepanalyze/app.js`，对外提供统一 `/health` 与 `/api/analyze`。
- 新增 agent 接入目录：`src/deepanalyze/agent/index.js`。
- 新增集成测试目录：`__tests__/integration/deepanalyze/`。
- 新增 CI 工作流：`.github/workflows/deepanalyze-ci.yml`。

## 2. 环境变量
- `DA_HOST`：服务监听地址，默认 `0.0.0.0`
- `DA_PORT`：服务监听端口，默认 `3000`
- `DA_LOG_LEVEL`：日志等级，默认 `info`
- `DA_MODEL`：分析模型名，默认 `deepanalyze-8b`
- `DA_AGENT_PROVIDER`：agent 供应商标识，默认 `openai`
- `DA_OPENAI_API_KEY`：可选，OpenAI Key
- `DA_API_BASE`：Python quick_start API 基地址
- `DA_QUICKSTART_API_BASE`：quick_start.py 使用的 API 基地址

## 3. 端口冲突解决
- 若 `3000` 被占用，修改 `.env`：
  - `DA_PORT=3001`
- 启动后检查日志是否输出：
  - `Listening on http://0.0.0.0:3001`
- 自检命令：
  - `curl http://localhost:3001/health`

## 4. 启动与测试
- 启动：`npm start`
- 开发：`yarn dev`
- 集成测试：`npm run test:deepanalyze`

## 5. 兼容性策略
- 使用 `DA_` 前缀隔离 DeepAnalyze 环境变量，避免污染原有 Python 项目配置。
- Node 侧逻辑放在新增目录，不改动原有主站页面与 FastAPI 业务入口。
