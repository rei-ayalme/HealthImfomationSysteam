# DeepAnalyze (DA) 使用报告

> 生成日期: 2026-04-18  
> 版本: v1.0  
> 路径: `deepanalyze/`

---

## 1. 项目概述

DeepAnalyze (DA) 是健康数据洞察平台的大模型分析组件，提供基于 OpenAI 兼容 API 的智能数据分析能力。支持流式对话、文件上传、代码执行和可视化生成等功能。

### 1.1 核心功能

- **流式对话**: 实时显示 AI 响应内容
- **文件分析**: 支持 CSV、TXT、JSON、Excel、PDF 等多种格式
- **代码执行**: 自动执行 Python 代码进行数据分析
- **可视化生成**: 自动生成图表和报告
- **OpenAI 兼容**: 标准 API 格式，易于集成

### 1.2 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| Gateway | Node.js + Express | >=18.18.0 |
| API Server | Python + FastAPI | 3.7+ |
| Model | DeepAnalyze-8B | HeyWhale 平台 |
| Client | OpenAI SDK | >=1.0.0 |

---

## 2. 架构说明

### 2.1 双层架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    客户端层                              │
│  (Web UI / Python SDK / Node.js SDK / cURL)            │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Node Gateway Layer                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Port: 3000                                       │  │
│  │  - /health (健康检查)                              │  │
│  │  - /api/analyze (分析接口)                         │  │
│  └────────────────────────┬──────────────────────────┘  │
└───────────────────────────┼─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│            Python API Server Layer                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Port: 8200                                       │  │
│  │  - /v1/models (模型列表)                           │  │
│  │  - /v1/files (文件管理)                            │  │
│  │  - /v1/chat/completions (对话补全)                 │  │
│  └────────────────────────┬──────────────────────────┘  │
└───────────────────────────┼─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│          External Model Service                          │
│     HeyWhale Platform - deepanalyze-8b                   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
deepanalyze/
├── index.js              # Node Gateway 入口
├── app.js                # Express 应用创建
├── quick_start.py        # Python 交互式测试脚本
├── main.py               # FastAPI 服务器入口
├── config.py             # 全局配置
├── models.py             # Pydantic 数据模型
├── storage.py            # 内存存储管理
├── utils.py              # 工具函数
├── chat_api.py           # 对话补全 API
├── file_api.py           # 文件管理 API
├── models_api.py         # 模型列表 API
├── admin_api.py          # 管理 API
├── requirements.txt      # Python 依赖
└── README.md             # 使用说明
```

---

## 3. 安装和配置

### 3.1 环境要求

- **Node.js**: >= 18.18.0
- **Python**: >= 3.7
- **内存**: 建议 4GB+
- **磁盘**: 建议 20GB+

### 3.2 安装依赖

**Node.js 依赖:**
```bash
cd "d:\python_HIS\pythonProject\多源健康数据驱动的疾病谱系与资源适配分析\Health_Imformation_Systeam"
npm install
```

**Python 依赖:**
```bash
cd deepanalyze
pip install -r requirements.txt
```

### 3.3 环境变量配置

创建 `.env` 文件在项目根目录:

```bash
# === Node Gateway 配置 ===
DA_HOST=0.0.0.0
DA_PORT=3000
DA_LOG_LEVEL=info

# === Python API Server 配置 ===
DA_API_HOST=0.0.0.0
DA_API_PORT=8200
DA_HTTP_SERVER_PORT=8100
DA_WORKSPACE_BASE_DIR=workspace

# === 模型配置 ===
DA_API_BASE=https://www.heywhale.com/api/model/services/69b7c9d028cbfe8349df5924/app/v1
DA_MODEL_PATH=deepanalyze-8b
DA_DEFAULT_TEMPERATURE=0.4
DA_MAX_NEW_TOKENS=32768

# === 运行时配置 ===
DA_CLEANUP_TIMEOUT_HOURS=12
DA_CLEANUP_INTERVAL_MINUTES=30
DA_CODE_EXECUTION_TIMEOUT=120
```

---

## 4. 使用方法

### 4.1 启动服务

**方式一: 使用 npm (推荐)**
```bash
# 启动完整服务 (Gateway + Python API)
npm start
```

**方式二: 分别启动**
```bash
# 终端 1: 启动 Python API Server
cd deepanalyze
python main.py

# 终端 2: 启动 Node Gateway
node deepanalyze/index.js
```

**方式三: 开发模式**
```bash
# 使用 nodemon 自动重启
npm run dev
```

### 4.2 健康检查

```bash
# 检查 Node Gateway
curl http://localhost:3000/health

# 检查 Python API Server
curl http://localhost:8200/health
```

### 4.3 使用 quick_start.py 交互式测试

```bash
cd deepanalyze
python quick_start.py
```

**交互流程:**
1. 输入 API Key (可选)
2. 选择对话类型 (1-无文件 / 2-带文件)
3. 输入文件路径 (如选择带文件)
4. 输入分析指令
5. 查看流式输出结果

### 4.4 API 调用示例

**Node Gateway 层 - 简单分析:**
```bash
curl -X POST http://localhost:3000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "分析这段健康数据",
    "data": {"key": "value"}
  }'
```

**Python API Server 层 - 对话补全:**
```bash
curl -X POST http://localhost:8200/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepanalyze-8b",
    "messages": [
      {"role": "user", "content": "分析CSV数据的统计特征"}
    ],
    "file_ids": ["file-xxx"],
    "temperature": 0.4,
    "stream": false
  }'
```

**使用 Python SDK:**
```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8200/v1",
    api_key="your-api-key"  # 可选
)

response = client.chat.completions.create(
    model="deepanalyze-8b",
    messages=[
        {"role": "user", "content": "分析这份数据的趋势"}
    ],
    file_ids=["file-xxx"],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

---

## 5. API 接口文档

### 5.1 Node Gateway 接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/analyze` | POST | 简单分析接口 |

**POST /api/analyze 请求体:**
```json
{
  "text": "分析文本内容",  // 可选
  "data": {"key": "value"}  // 可选
}
```

**响应:**
```json
{
  "summary": "已完成分析，输入长度 12",
  "score": 12,
  "details": {
    "model": "deepanalyze-8b",
    "timestamp": 1704067200000,
    "inputType": "text"
  }
}
```

### 5.2 Python API Server 接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/models` | GET | 列出可用模型 |
| `/v1/files` | GET/POST | 文件列表/上传 |
| `/v1/files/{id}` | GET/DELETE | 获取/删除文件 |
| `/v1/files/{id}/content` | GET | 下载文件 |
| `/v1/chat/completions` | POST | 对话补全 |
| `/health` | GET | 健康检查 |

**POST /v1/chat/completions 参数:**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| model | string | 是 | 模型名称 |
| messages | array | 是 | 对话消息列表 |
| file_ids | array | 否 | 关联文件ID列表 |
| temperature | float | 否 | 采样温度 (0.0-1.0) |
| stream | boolean | 否 | 是否流式响应 |
| api_key | string | 否 | 自定义API密钥 |

---

## 6. 测试方法

### 6.1 运行集成测试

```bash
# 运行 DeepAnalyze 集成测试
npm run test:deepanalyze
```

**测试覆盖:**
- `/api/analyze` 接口测试
- 错误处理测试
- 初始化测试

### 6.2 手动测试

```bash
# 测试文件上传
curl -X POST http://localhost:8200/v1/files \
  -F "file=@test.csv" \
  -F "purpose=file-extract"

# 测试对话 (带文件)
curl -X POST http://localhost:8200/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepanalyze-8b",
    "messages": [{"role": "user", "content": "分析数据"}],
    "file_ids": ["file-xxx"]
  }'
```

---

## 7. 常见问题与故障排查

### 7.1 端口冲突

**问题**: `EADDRINUSE: address already in use :::3000`

**解决**:
```bash
# 修改 .env 文件
DA_PORT=3001
DA_API_PORT=8201
DA_HTTP_SERVER_PORT=8101
```

### 7.2 Python API 连接失败

**问题**: Node Gateway 无法连接 Python API

**排查**:
```bash
# 检查 Python API 是否运行
curl http://localhost:8200/health

# 检查环境变量
echo $DA_API_BASE
```

### 7.3 文件上传失败

**问题**: 上传文件返回 500 错误

**排查**:
- 检查 `workspace/` 目录权限
- 检查文件大小 (建议 < 100MB)
- 检查文件类型是否在支持列表

### 7.4 模型调用失败

**问题**: 调用模型返回错误

**排查**:
- 检查 `DA_API_BASE` 配置
- 检查 HeyWhale API 可访问性
- 检查 API Key 是否有效

---

## 8. 性能优化建议

### 8.1 资源限制

- **代码执行超时**: 120 秒 (可配置)
- **最大生成 Token**: 32768
- **文件大小限制**: 建议 < 100MB

### 8.2 清理策略

- **线程超时**: 12 小时自动清理
- **清理间隔**: 每 30 分钟检查一次
- **手动清理**: `POST /v1/admin/cleanup`

### 8.3 性能监控

```bash
# 查看工作区磁盘使用
du -sh workspace/

# 查看运行中的线程数
ls workspace/ | wc -l
```

---

## 9. 安全注意事项

### 9.1 代码执行安全

- 代码在子进程中隔离执行
- 120 秒执行超时限制
- 工作目录隔离
- 环境变量清理 (DISPLAY 移除)

### 9.2 文件上传安全

- 文件名净化处理
- 文件类型白名单验证
- 文件大小限制
- 存储路径隔离

### 9.3 网络安全

- 生产环境应配置 CORS 白名单
- API Key 通过 HTTPS 传输
- 敏感信息使用环境变量

---

## 10. 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-04-18 | v1.0 | 初始版本，完成迁移文档 |

---

## 附录 A: 支持的文件类型

```python
SUPPORTED_EXTENSIONS = [
    '.csv', '.txt', '.json', '.xlsx', '.xls',
    '.pdf', '.doc', '.docx', '.py', '.js', '.html',
    '.xml', '.yaml', '.yml', '.md', '.log'
]
```

## 附录 B: 环境变量完整列表

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| DA_HOST | 0.0.0.0 | Node 服务监听地址 |
| DA_PORT | 3000 | Node 服务监听端口 |
| DA_LOG_LEVEL | info | 日志级别 |
| DA_MODEL | deepanalyze-8b | 模型名称 |
| DA_API_HOST | 0.0.0.0 | Python API 监听地址 |
| DA_API_PORT | 8200 | Python API 监听端口 |
| DA_HTTP_SERVER_PORT | 8100 | 文件服务器端口 |
| DA_WORKSPACE_BASE_DIR | workspace | 工作区目录 |
| DA_API_BASE | HeyWhale URL | 外部模型服务地址 |
| DA_DEFAULT_TEMPERATURE | 0.4 | 默认采样温度 |
| DA_MAX_NEW_TOKENS | 32768 | 最大生成 Token |
| DA_CLEANUP_TIMEOUT_HOURS | 12 | 线程清理超时 |
| DA_CLEANUP_INTERVAL_MINUTES | 30 | 清理检查间隔 |
| DA_CODE_EXECUTION_TIMEOUT | 120 | 代码执行超时 |

---

> **注意**: 本文档基于 DeepAnalyze 迁移版本编写，如有更新请参考最新代码。
