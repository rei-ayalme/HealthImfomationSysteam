# 健康信息系统（Health Information System）

基于 Python + FastAPI + Streamlit 构建的现代健康信息分析与可视化系统，聚焦**全球疾病负担（GBD）分析**、**医疗资源微观空间可及性评估**、**智能政策建议生成**以及**多智能体流行病学模拟**等核心场景，提供数据抓取、计算分析、3D地图可视化展示等一站式功能。

---

## 一、项目简介

本系统面向医疗健康数据分析师、公共卫生研究人员，整合了 GBD 疾病负担测算、基于 E2SFCA（增强型两步移动搜索法）的微观空间可及性评估、CCR-DEA 效率分析、智能体疾病传播模拟等核心算法。通过轻量化的纯前端交互与 FastAPI 高性能后端支撑，实现多源异构健康数据的快速分析与可视化。

### 系统稳定性设计与保障策略
本项目采用了高可靠性的**双层数据源架构设计**（“真实数据优先、保障数据兜底”），确保在各种网络与第三方接口异常情况下，系统仍能维持无缝衔接的用户体验：
1. **熔断与降级机制 (Data Orchestration Layer)**: 内置指数退避重试（最高3次）与5秒超时控制，连续3次请求失败自动触发熔断，200ms内切换至静态或内存保障数据。
2. **统一数据契约**: 所有模块统一输出带 CRS(WGS84) 的 GeoJSON 或 Tile 格式，保证字段映射与真实源 1:1，实现可视化层的无感切换。
3. **数据质量监控**: 集成 `/quality/report` 接口，每日统计并输出“真实数据覆盖率”、“平均响应时间”、“降级次数”与“数据新鲜度”。
4. **空间缺失补全与合成演化**: 
   - 省级缺失率 > 20% 时，启动空间邻接加权平均（共享省界长度）算法进行智能补全。
   - 微观人口仿真内置基于 IPF (Iterative Proportional Fitting) 的百万级合成人口引擎，与真实普查相关系数矩阵误差控制在 0.05 以内。

### 核心特性

- **多维可视化展示**：基于 ECharts 实现 3D 医疗资源分布热力图，支持从行政区到社区的无缝下钻，并集成点聚合防重叠机制
- **硬核专业算法**：内置 E2SFCA 空间可及性计算（支持分段衰减与自定义半径）、BCC-DEA/CCR-DEA 模型、Pandera 模式校验等
- **现代化前后端分离**：采用 FastAPI 作为后端支撑耗时的空间地理计算，Streamlit 作为管理员数据看板
- **外部数据自动抓取与持久化**：内置基于高德 API 的微观医疗 POI 抓取以及 OWID 健康指标自动爬取与落盘
- **智能洞察与建议**：集成大语言模型（如 DeepSeek）生成针对性健康政策干预建议
- **数据驱动的随机逻辑斯蒂预测模型**：摒弃传统硬编码参数，实现从历史数据自动学习增长特征，引入承载力上限约束，杜绝预测数据爆炸
- **多智能体流行病学模拟**：基于马尔可夫链和空间行为的智能体模拟系统，可视化展示疾病传播和医疗资源利用动态
- **标准化数据中台架构**：统一 API 响应格式，Axios 拦截器自动处理请求/响应，实现前后端高效通信

---

## 二、预测引擎升级：数据驱动的随机逻辑斯蒂模型

针对传统时间序列预测模型参数僵化、易出现指数级爆炸的问题，本系统的 `core/predictor.py` 摒弃了早期硬编码的几何布朗运动（GBM），重构为**数据驱动的随机逻辑斯蒂模型**。该升级主要由以下两大核心方案融合而成：

### 1. 历史数据动态校准 (Dynamic Parameter Calibration)

**痛点**：传统 SDE 模型的漂移率（Drift）和扩散率（Diffusion）通常依赖人工先验设定，缺乏对不同地区、不同指标（如床位、医生数）的自适应能力。

**重构方案**：引入历史时间序列的动态学习机制。系统通过计算历史数据的对数收益率（Log Returns），自动利用伊藤引理（Itô's Lemma）反推真实的内生增长率（$r$）和历史波动率（$\sigma$）。

**效果**：实现了"千城千面"的精准测算。只要喂给引擎历史数据，它就能自动抓取该地区医疗资源的真实扩张速度与波动特征。

### 2. 逻辑斯蒂饱和约束 (Logistic Saturation Constraint)

**痛点**：医疗资源（如千人床位数）受限于地方财政、人口基数和国家政策规划，不可能无限增长。传统的指数外推模型在预测中长期趋势时，极易产生脱离现实的"爆炸"数据。

**重构方案**：将底层的 SDE 公式升级为随机逻辑斯蒂方程，引入了"环境承载力上限"变量 $K$。

$$dX_t = r X_t \left(1 - \frac{X_t}{K}\right) dt + \sigma X_t dW_t$$

**效果**：预测曲线不再是盲目冲高的指数线，而是会随着资源密度逼近政策天花板（$K$ 值）而平滑减速，完美贴合医疗体系发展的真实客观规律。

### 💡 业务落地价值

- **极强的可解释性**：算法输出的不再是黑盒数字，而是具备明确政策意义的参数（系统内生动力 $r$、抗风险波动率 $\sigma$、政策承载力 $K$）
- **绝对的安全防爆**：通过数学约束（欧拉-丸山方法离散化求解 + 边界裁剪），彻底杜绝了前端大屏或分析报告中出现负数或突破天际的脏数据

**使用示例**：
```python
from modules.core.predictor import Predictor

historical_data = [100, 105, 112, 118, 125, 132, 140, 148, 155, 162]

result = Predictor.run_data_driven_logistic_sde(
    historical_data=historical_data,
    years_ahead=5,
    capacity_k=200  # 可选：指定承载力上限
)

print(result["parameters"])      # 校准的参数 (r, sigma, K)
print(result["future_predictions"])  # 未来5年的预测值
```

---

## 三、多智能体流行病学模拟系统

系统包含基于智能体（Agent-Based）的流行病学模拟模块，用于生成人口健康状态演化的可视化数据。

### 核心机制

1. **多边形拒绝采样（Geofencing）**：确保模拟人口坐标严格位于成都市行政区域边界内部
2. **马尔可夫状态机（Markov Chain）**：定义健康/慢病/重症/死亡四种状态的转移概率
3. **医疗资源虹吸效应（Spatial Clustering）**：模拟重症患者向医院聚集的空间行为
4. **人口守恒定律（Respawn）**：死亡粒子重生为健康粒子，维持系统人口稳定

### 运行模拟

```bash
python scripts/generate_simulation_data.py
```

生成结果保存至 `frontend/assets/data/simulation_data.json`，可直接用于前端可视化展示。

---

## 四、标准化数据中台架构

系统已实现标准化数据中台架构，统一前后端通信协议：

### 统一响应格式

```json
{
  "code": 200,
  "message": "操作成功",
  "data": { ... },
  "timestamp": "2026-04-14T10:30:00Z"
}
```

### 前端 API 模块

位于 `frontend/assets/js/api.js`，提供：
- Axios 拦截器自动处理请求/响应
- 统一的错误处理和 SweetAlert2 提示
- 封装常用 API 方法（疾病预测、空间分析、健康指标等）

### 已集成中台机制的页面

- `prediction.html` - 疾病预测可视化
- `macro-analysis.html` - 宏观健康分析
- `meso-analysis.html` - 中观地理分析
- `micro-analysis.html` - 微观空间可及性分析

---

## 五、环境要求

- **Python 版本**：≥3.9（推荐 3.11）
- **Node.js**：≥18.0（用于前端开发，可选）
- **操作系统**：Windows / Linux / macOS（跨平台兼容）
- **内存**：≥8GB RAM（推荐 16GB，用于空间计算）
- **存储**：≥5GB 可用空间

建议使用虚拟环境（如 `.venv` 或 `conda`）

---

## 六、快速启动

### 1. 克隆项目

```bash
git clone https://github.com/rei-ayalme/HealthImfomationSysteam.git
cd Health_Imformation_Systeam
```

### 2. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 到 `.env` 并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=sqlite:///./db/health_system.db

# 高德API密钥 (用于空间地理计算及抓取)
AMAP_API_KEY=your_amap_key_here

# 大模型API密钥 (用于智能洞察)
DEEPSEEK_API_KEY=your_deepseek_key_here
OPENAI_API_KEY=your_openai_key_here

# Redis 配置（可选，用于缓存）
REDIS_URL=redis://localhost:6379/0

# 新闻API密钥（可选）
NEWS_API_KEY=your_news_api_key_here
```

### 4. 初始化数据库

```bash
python -c "from db.database import init_db; init_db()"
```

### 5. 启动系统

**启动 FastAPI 后端（推荐）：**

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

访问 `http://127.0.0.1:8000/use/index.html`

**启动 Streamlit 管理员看板：**

```bash
streamlit run pages/health_analysis.py
```

---

## 七、目录结构

```
Health_Imformation_Systeam/
├── .env                          # 环境变量配置
├── .env.example                  # 环境变量模板
├── main.py                       # FastAPI 主程序入口
├── requirements.txt              # Python 依赖清单
├── README.md                     # 项目说明文档
├── config/                       # 配置目录
│   └── settings.py               # 全局配置
├── data/                         # 数据目录
│   ├── raw/                      # 原始数据
│   ├── processed/                # 处理后的数据
│   └── geojson/                  # 地理空间文件
├── db/                           # 数据库模块
│   ├── database.py               # 数据库连接
│   └── models.py                 # ORM 模型
├── frontend/                     # 前端界面
│   ├── use/                      # 用户交互页面
│   │   ├── index.html            # 首页
│   │   ├── macro-analysis.html   # 宏观分析
│   │   ├── meso-analysis.html    # 中观分析
│   │   ├── micro-analysis.html   # 微观分析
│   │   └── prediction.html       # 疾病预测
│   └── assets/                   # 静态资源
│       ├── js/                   # JavaScript 文件
│       │   └── api.js            # 中台 API 模块
│       ├── css/                  # 样式文件
│       └── data/                 # 模拟数据
├── modules/                      # 核心业务模块
│   ├── analysis/                 # 分析算法
│   ├── core/                     # 核心功能
│   ├── data/                     # 数据处理
│   └── spatial/                  # 空间计算
├── pages/                        # Streamlit 页面
├── scripts/                      # 工具脚本
│   └── generate_simulation_data.py  # 模拟数据生成
├── tests/                        # 测试文件
└── utils/                        # 工具函数
    └── response.py               # 标准响应格式
```

---

## 八、核心功能使用

### 1. 微观空间可及性分析 (E2SFCA)

1. 启动后端服务后访问 `http://127.0.0.1:8000/use/micro-analysis.html`
2. 选择分析区域和搜寻半径
3. 系统将调用 E2SFCA 算法计算医疗资源空间可及性
4. 支持行政区下钻至社区级别，动态展示资源分布热力图

### 2. GBD 疾病负担与风险归因

1. 访问 `http://127.0.0.1:8000/use/macro-analysis.html`
2. 系统使用 Pandera 进行数据清洗和异常值截断
3. 结合 `DiseaseRiskAnalyzer` 计算风险因素的人群归因分数（PAF）
4. 调用大模型生成针对性政策建议

### 3. 疾病预测与模拟

1. 访问 `http://127.0.0.1:8000/use/prediction.html`
2. 选择地区和时间范围
3. 系统使用随机逻辑斯蒂模型预测未来疾病负担
4. 可视化展示预测结果和置信区间

### 4. 多智能体模拟可视化

1. 运行 `python scripts/generate_simulation_data.py` 生成模拟数据
2. 在前端页面查看人口健康状态的时空演化
3. 观察重症患者向医院聚集的虹吸效应

---

## 九、API 文档

启动后端后访问自动生成的 API 文档：

- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

### 主要 API 端点

| 端点 | 描述 |
|------|------|
| `GET /api/disease_simulation` | 疾病预测模拟 |
| `GET /api/spatial_analysis` | 空间可及性分析 |
| `GET /api/analysis/metrics` | 健康指标数据 |
| `GET /api/geojson/china` | 中国地图 GeoJSON |

---

## 十、外部数据与爬虫

### 数据来源

- **GBD (Global Burden of Disease)**：全球疾病负担数据
- **WDI (World Development Indicators)**：世界银行宏观经济数据
- **中国卫生健康统计年鉴**：国内医疗资源配置数据
- **OWID (Our World in Data)**：全球健康指标动态数据
- **高德地图 POI 数据**：成都市微观地理空间数据

### 爬虫使用

**医疗 POI 抓取：**
```bash
python -c "from modules.spatial.poi_fetcher import fetch_hospital_pois; fetch_hospital_pois(keyword='三甲医院')"
```

**OWID 数据抓取：**
```bash
python -c "from modules.data.owid_fetcher import fetch_owid_data; fetch_owid_data()"
```

---

## 十一、测试

运行测试套件：

```bash
# 运行中台机制测试
python tests/test_middle_platform.py

# 运行数据质量测试
python tests/test_data_quality.py
```

---

## 十二、贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 十三、许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 十四、免责声明

本系统仅用于学术研究/内部分析展示，不涉及实际临床医疗决策；所有医疗数据分析均基于公共宏观统计口径或合法 API 渠道获取，禁止用于商业非法用途。

---

## 十五、联系方式

- 项目主页：[GitHub](https://github.com/rei-ayalme/HealthImfomationSysteam)
- 问题反馈：[Issues](https://github.com/rei-ayalme/HealthImfomationSysteam/issues)
- 邮箱：contact@healthinfo.example.com

---

**最后更新**：2026年4月14日
