# 健康信息系统（Health Information System）
基于Python + Streamlit构建的健康信息分析与可视化系统，聚焦**全球疾病负担（GBD）分析**、**医疗资源配置评估**等核心场景，提供数据查询、计算分析、可视化展示、结果导出等一站式功能。

## 一、项目简介
本系统面向医疗健康数据分析师、公共卫生研究人员，整合了GBD疾病负担测算、医疗资源配置评价（秩和比法）、DEA效率分析等核心算法，通过轻量化的Web界面实现健康数据的快速分析与可视化，支持山西省/江苏省/辽宁省等多区域医疗资源数据的批量处理与结果验证。

### 核心特性
-  可视化展示：基于Streamlit实现交互式图表（折线图、柱状图、热力图），直观呈现疾病负担/医疗资源分布；
-  精准计算：内置GBD疾病负担、秩和比法（RSR）、DEA效率分析等标准化算法，结果可与官方年鉴数据比对；
-  轻量存储：采用SQLite数据库管理健康数据，无需独立数据库服务，部署成本低；
-  数据安全：支持敏感医疗数据脱敏、SQL注入防护、页面权限控制，符合健康数据合规要求；
-  灵活导出：支持分析结果导出为CSV/Excel/PDF格式，便于报告撰写。

## 二、环境要求
- Python版本：≥3.8（推荐3.8~3.10，避免高版本语法兼容问题）
- 操作系统：Windows/Linux/macOS（跨平台兼容）

## 三、快速启动
### 1. 克隆项目（若使用Git管理）
```bash
git clone <项目仓库地址>
cd Health_Imformation_Systeam  # 进入项目根目录
```

### 2. 安装依赖
```bash
# 安装项目所需所有依赖
pip install -r requirements.txt

# 验证依赖安装（无报错则成功）
pip check
```

### 3. 配置环境变量
修改项目根目录下的`.env`文件，补充必要配置（示例）：
```env
# 数据库配置
DB_PATH=./health_system.db
# Streamlit配置
STREAMLIT_PORT=8501
STREAMLIT_DEBUG=False
# 数据目录
DATA_DIR=./data
# 敏感数据加密密钥（自定义）
ENCRYPT_KEY=your_random_key_123456
```

### 4. 启动系统
```bash
# 启动Streamlit Web应用
streamlit run streamlit_app.py
```
启动成功后，浏览器自动打开 `http://localhost:8501` 即可访问系统。

## 四、目录结构说明
```
Health_Imformation_Systeam/
├── .env                # 环境变量配置（敏感信息/可变路径）
├── .gitignore          # Git版本控制忽略规则
├── health_system.db    # SQLite数据库（存储健康数据/分析结果）
├── requirements.txt    # Python依赖清单
├── run_gbd_analysis.py # GBD分析核心脚本（批量计算/数据校验）
├── streamlit_app.py    # Streamlit主应用（Web界面入口）
├── data/               # 数据目录（原始数据/预处理数据/导出结果）
│   ├── gbd_raw.csv     # GBD原始数据集
│   ├── medical_resource.xlsx # 医疗资源配置数据
│   └── export/         # 结果导出目录
├── config/             # 配置目录（全局配置/日志配置）
├── db/                 # 数据库管理（表结构初始化/数据迁移）
├── modules/            # 业务模块（按功能拆分）
│   ├── gbd_analysis.py # GBD疾病负担计算模块
│   ├── rsr_evaluate.py # 秩和比法医疗资源评估模块
│   └── dea_analysis.py # DEA效率分析模块
├── pages/              # Streamlit子页面（功能拆分）
│   ├── data_query.py   # 数据查询页面
│   ├── visualization.py # 可视化展示页面
│   └── export_result.py # 结果导出页面
└── utils/              # 通用工具（数据清洗/加密/文件操作）
    ├── data_clean.py   # 数据清洗工具
    ├── db_operate.py   # 数据库操作工具
    └── encrypt.py      # 敏感数据加密工具
```

## 五、核心功能使用说明
### 1. GBD疾病负担分析
1. 进入系统后点击「GBD分析」页面；
2. 上传GBD原始数据（CSV格式）或选择内置示例数据；
3. 选择分析维度（如疾病类型、年份、区域）；
4. 点击「开始计算」，系统自动生成疾病负担值及趋势图；
5. 点击「导出结果」可下载分析报告（CSV/PDF）。

### 2. 医疗资源配置评估
1. 进入「医疗资源评估」页面；
2. 选择评估区域（如山西省/江苏省）及指标（床位数、医师数、医护比）；
3. 系统通过秩和比法（RSR）自动计算综合评分并生成区域对比图；
4. 支持与官方年鉴数据比对，验证结果准确性。

### 3. 数据管理
1. 进入「数据管理」页面，可手动录入/批量导入医疗数据；
2. 支持数据修改、删除、脱敏（如身份证号隐藏中间6位）；
3. 所有操作记录自动同步至`health_system.db`，可追溯。

## 六、注意事项
### 1. 数据安全
- 敏感数据（如患者身份证、手机号）会自动脱敏存储，禁止修改`utils/encrypt.py`中的加密逻辑；
- `.env`文件包含数据库密码/加密密钥，**禁止提交到Git仓库**（已在`.gitignore`中配置）；
- 非管理员用户仅可查看脱敏后的数据，无修改/导出权限。

### 2. 数据准确性
- 建议使用官方数据源（如卫生统计年鉴、GBD官方数据集），避免非标准化数据导致计算误差；
- 批量分析前先通过「数据校验」功能检查数据完整性（如无缺失字段、无异常值）。

### 3. 部署说明
- 生产环境部署时，建议修改`STREAMLIT_DEBUG=False`，关闭调试模式；
- 若部署至Linux服务器，需将`.env`中的路径改为Linux格式（如`./data`而非`C:\data`）。

## 七、常见问题
### Q1：启动Streamlit时提示“ModuleNotFoundError: No module named 'streamlit'”？
A：未安装依赖，执行`pip install -r requirements.txt`重新安装，或单独安装`pip install streamlit`。

### Q2：数据导入后计算结果为空？
A：检查数据格式是否符合要求（如字段名匹配、无空值/负数），可先用「数据清洗」功能预处理。

### Q3：页面访问缓慢/卡顿？
A：大数据分析时启用缓存（Streamlit的`@st.cache_data`装饰器）；给数据库高频查询字段建索引（如`disease_id`、`region`）。

## 八、免责声明
本系统仅用于学术研究/内部分析，不涉及临床医疗决策；所有医疗数据需符合《健康医疗大数据管理办法》，禁止用于商业用途。