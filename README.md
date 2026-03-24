# 健康信息系统（Health Information System）
基于 Python + FastAPI + Streamlit 构建的现代健康信息分析与可视化系统，聚焦**全球疾病负担（GBD）分析**、**医疗资源微观空间可及性评估**、以及**智能政策建议生成**等核心场景，提供数据抓取、计算分析、3D地图可视化展示等一站式功能。

## 一、项目简介
本系统面向医疗健康数据分析师、公共卫生研究人员，整合了 GBD 疾病负担测算、基于 E2SFCA（增强型两步移动搜索法）的微观空间可及性评估、CCR-DEA 效率分析等核心算法。通过轻量化的纯前端交互与 FastAPI 高性能后端支撑，实现多源异构健康数据的快速分析与可视化。

### 系统稳定性设计与保障策略
本项目采用了高可靠性的**双层数据源架构设计**（“真实数据优先、保障数据兜底”），确保在各种网络与第三方接口异常情况下，系统仍能维持无缝衔接的用户体验：
1. **熔断与降级机制 (Data Orchestration Layer)**: 内置指数退避重试（最高3次）与5秒超时控制，连续3次请求失败自动触发熔断，200ms内切换至静态或内存保障数据。
2. **统一数据契约**: 所有模块统一输出带 CRS(WGS84) 的 GeoJSON 或 Tile 格式，保证字段映射与真实源 1:1，实现可视化层的无感切换。
3. **数据质量监控**: 集成 `/quality/report` 接口，每日统计并输出“真实数据覆盖率”、“平均响应时间”、“降级次数”与“数据新鲜度”。
4. **空间缺失补全与合成演化**: 
   - 省级缺失率 > 20% 时，启动空间邻接加权平均（共享省界长度）算法进行智能补全。
   - 微观人口仿真内置基于 IPF (Iterative Proportional Fitting) 的百万级合成人口引擎，与真实普查相关系数矩阵误差控制在 0.05 以内。

### 核心特性
-  **多维可视化展示**：基于 ECharts 实现 3D 医疗资源分布热力图，支持从行政区到社区的无缝下钻，并集成点聚合防重叠机制；
-  **硬核专业算法**：内置 E2SFCA 空间可及性计算（支持分段衰减与自定义半径）、BCC-DEA/CCR-DEA 模型、Pandera 模式校验等；
-  **现代化前后端分离**：采用 FastAPI 作为后端支撑耗时的空间地理计算，Streamlit 作为管理员数据看板；
-  **外部数据自动抓取与持久化**：内置基于高德 API 的微观医疗 POI 抓取以及 OWID 健康指标自动爬取与落盘；
-  **智能洞察与建议**：集成大语言模型（如 DeepSeek）生成针对性健康政策干预建议。

## 二、环境要求
- Python版本：≥3.8（推荐 3.10）
- 操作系统：Windows / Linux / macOS（跨平台兼容）
- 建议使用虚拟环境（如 `.venv`）

## 三、快速启动
### 1. 克隆项目
```bash
git clone https://github.com/rei-ayalme/HealthImfomationSysteam.git
cd Health_Imformation_Systeam  # 进入项目根目录
```

### 2. 安装依赖
```bash
# 激活虚拟环境后安装项目所需所有依赖
pip install -r requirements.txt
```

### 3. 配置环境变量
修改项目根目录下的 `.env` 文件，补充必要配置（示例）：
```env
# 数据库配置
DATABASE_URL=sqlite:///./health_system.db

# 高德API密钥 (用于空间地理计算及抓取)
AMAP_API_KEY=your_amap_key

# 搜索引擎或大模型API密钥
DEEPSEEK_API_KEY=your_deepseek_key
```

### 4. 启动系统
本项目分为两部分，请根据需求启动：

**启动核心后端与纯前端交互层（推荐终端）：**
```bash
# 启动 FastAPI 后端及静态前端挂载
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
启动成功后，浏览器打开 `http://127.0.0.1:8000/use/index.html` 即可访问交互式可视化界面。

**启动管理员数据管理端：**
```bash
# 启动 Streamlit 数据看板
streamlit run pages/health_analysis.py
```

## 四、目录结构说明
```
Health_Imformation_Systeam/
├── .env                  # 环境变量配置（API Key等敏感信息）
├── main.py               # FastAPI 主程序入口（API及静态挂载）
├── requirements.txt      # Python 精确依赖清单
├── config/               # 配置目录（settings.py 全局配置）
├── data/                 # 数据目录
│   ├── raw/              # 原始备份数据（包含爬虫落盘的 CSV）
│   ├── processed/        # 预处理缓存数据
│   └── geojson/          # 核心地理空间文件（含成都边界、医院POI等）
├── db/                   # 数据库ORM模型与连接
├── frontend/             # 纯前端界面
│   ├── use/              # 用户交互端HTML（微观/宏观/中观分析）
│   └── assets/           # JS/CSS 静态资源
├── modules/              # 核心业务模块
│   ├── analysis/         # DEA/E2SFCA等硬核数学模型算法
│   ├── data/             # 数据预处理（Pandera校验、异常值清洗）及OWID爬虫
│   └── spatial/          # 空间地理计算与高德POI抓取工具
└── pages/                # Streamlit 数据管理与看板页面
```

## 五、外部数据与爬虫使用规范
为了保证项目研究的可复现性，本系统遵守严格的数据交付规范：

### 1. 数据来源说明
系统的数据分析主要依赖于以下权威公共数据源，所有原始数据及清洗后的数据均存放于 `data/` 目录中：
- **GBD (Global Burden of Disease)**：用于全球及区域疾病负担、风险因素归因（PAF）分析。
- **WDI (World Development Indicators)**：世界银行提供的宏观经济与医疗资源基准数据。
- **中国卫生健康统计年鉴**：用于国内省市级的医疗资源配置评价与 DEA 效率分析。
- **OWID (Our World in Data)**：全球健康指标的动态补充数据。
- **高德地图 POI 数据**：用于成都市微观地理空间可及性（E2SFCA）计算。

### 2. 爬虫逻辑保留与数据持久化
系统中的外部动态数据抓取逻辑已在代码中完整保留，并支持一键落盘保存，确保随时可复现：
- **医疗 POI 抓取**：运行 `python -c "from modules.spatial.poi_fetcher import fetch_hospital_pois; fetch_hospital_pois(keyword='三甲医院')"`，结果将自动保存至 `data/geojson/chengdu_hospitals_3a.geojson`。
- **OWID 全球指标**：在 `modules/data/owid_fetcher.py` 中实现了完整爬虫，原始爬取数据会自动备份至 `data/raw/` 以 CSV 格式存储（如 `owid_indicator_xxx_backup.csv`），保证数据可追溯。

### 3. 第三方 API 调用说明
系统在部分实时分析功能中接入了第三方 API 服务，主要包括：
- **高德地图 Web 服务 API**：
  - **用途**：获取微观地理位置的经纬度坐标、POI（兴趣点）检索及真实路网距离计算，用于支撑 E2SFCA 空间可及性模型。
  - **配置**：需在 `.env` 文件中配置 `AMAP_API_KEY`。
- **大语言模型 API (DeepSeek/OpenAI)**：
  - **用途**：用于“智能洞察与建议”模块，基于图表数据和内置的分析 Prompt，自动生成结构化的政策干预建议和健康报告摘要。
  - **配置**：需在 `.env` 文件中配置 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY`。
- **Mediastack News API**：
  - **用途**：在仪表盘中获取全球最新健康及公共卫生相关的新闻资讯。
  - **缓存机制**：为避免频繁调用超过免费配额，系统实现了带有效期的本地缓存机制，请求结果会保存在 `data/processed/news_cache.json` 中。
  - **配置**：需在 `config/settings.py` 的 `SEARCH_ENGINE_CONFIG` 中配置 `NEWS_API_KEY`。

## 六、核心功能使用说明
### 1. 微观空间可及性分析 (E2SFCA)
1. 启动 `main.py` 后访问 `http://127.0.0.1:8000/use/micro-analysis.html`；
2. 系统将调用 `modules/analysis/advanced_algorithms.py` 中的 `calculate_e2sfca` 进行计算；
3. 支持点击成都市行政区地图自动下钻至**社区级别**，动态规避点位重叠遮挡。

### 2. GBD 疾病负担与风险归因
1. 系统使用 Pandera 进行了严格的数据清洗和异常值截断；
2. 结合后端 `DiseaseRiskAnalyzer` 模型计算各种风险因素（如高血压、吸烟）导致的 PAF（人群归因分数）；
3. 界面会实时调用大模型总结并返回对应的政策建议。

### 3. 数据管理
1. 通过启动 Streamlit 页面进入管理员后台；
2. 可查看全量脱敏健康数据，验证入库的完整性。

## 七、免责声明
本系统仅用于学术研究/内部分析展示，不涉及实际临床医疗决策；所有医疗数据分析均基于公共宏观统计口径或合法 API 渠道获取，禁止用于商业非法用途。