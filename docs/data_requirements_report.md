# 健康信息系统数据需求报告

## 报告概述

**报告日期**: 2026-04-19  
**报告版本**: v1.1  
**编制目的**: 明确各分析模块缺失数据，指导数据收集与补充工作  
**适用范围**: Marco/Meso/Micro/Prediction 四个层面模型

**更新说明**: v1.1版本整合了代码级数据依赖分析结果，补充了数据库表级缺失数据、API数据流分析等内容。

---

## 一、数据需求总览

| 模型/模块 | 缺失数据项数 | 最高优先级 | 预计补充周期 |
|-----------|-------------|-----------|-------------|
| Marco (宏观分析) | 4项 | 🔴 P0 | 2-4周 |
| Meso (中观分析) | 5项 | 🔴 P0 | 4-6周 |
| Micro (微观分析) | 3项 | 🟡 P1 | 2-3周 |
| Prediction (预测引擎) | 2项 | 🟡 P1 | 3-4周 |
| **数据库核心表** | **3项** | **🔴 P0** | **1-2周** |
| **总计** | **17项** | - | - |

---

## 二、关键发现：数据库核心表缺失数据（新增）

基于代码依赖分析 (`main.py`, `routes/*.py`)，发现以下数据库表存在**关键数据缺失**，直接影响API功能：

### 2.1 AdvancedDiseaseTransition 表 - 疾病谱系基线数据缺失

| 属性 | 详情 |
|------|------|
| **表名** | `adv_disease_transition` |
| **缺失数据** | China/global 地区的疾病谱系基线数据 |
| **影响API** | `/api/disease_simulation`, `/api/analysis/metrics`, `/api/chart/trend` |
| **错误日志** | `missing_report_2026-04.json`: "缺少该地区的疾病谱系数据" |
| **当前行为** | API返回400错误："未能找到 {region} 的基线数据，无法进行 SDE 预测" |
| **需要字段** | `location_name`, `cause_name`, `year`, `val` (DALYs), `source` |
| **数据量** | China: 2000-2024年 × 主要疾病类型(心血管/肿瘤/糖尿病等) |
| **补充优先级** | 🔴 **P0 - 阻塞性问题** |
| **数据来源** | GBD Study Results, IHME |

### 2.2 AdvancedResourceEfficiency 表 - DEA效率数据缺失

| 属性 | 详情 |
|------|------|
| **表名** | `adv_resource_efficiency` |
| **缺失数据** | 投入/产出矩阵为空 |
| **影响API** | `/api/analysis/metrics` |
| **错误日志** | `missing_report_2026-04.json`: "投入或产出矩阵为空" |
| **当前行为** | DEA效率指标使用硬编码兜底值 0.85 |
| **需要字段** | `location_name`, `year`, `dea_efficiency`, `input_indicators`, `output_indicators` |
| **投入指标** | 医生密度、床位密度、卫生支出占GDP比 |
| **产出指标** | 预期寿命、婴儿死亡率、DALYs |
| **补充优先级** | 🔴 **P0 - 阻塞性问题** |

### 2.3 GlobalHealthMetric 表 - 全球健康指标缺失

| 属性 | 详情 |
|------|------|
| **表名** | `global_health_metric` |
| **缺失数据** | 195国 × 5指标 × 35年时序数据 |
| **影响API** | `/api/map/world-metrics`, `/api/v1/marco/map/world-metrics` |
| **当前行为** | 使用 `_calc_reproducible_map_fallback()` 生成回退值 |
| **需要字段** | `region`, `indicator`, `year`, `value`, `source`, `is_fallback` |
| **指标类型** | DALYs, Deaths, Prevalence, YLLs, YLDs |
| **补充优先级** | 🟡 **P1 - 高优先级** |

---

## 三、Marco 宏观分析模块数据需求

### 3.1 全球预期寿命分布数据

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Marco - 全球预期寿命地图 |
| **缺失数据类型** | 全球各国预期寿命数据 |
| **具体字段** | `country_code` (ISO 3166-1 alpha-3), `life_expectancy` (岁), `data_year` (年份), `source` (数据来源), `confidence` (置信度) |
| **数据量** | 195个国家/地区 |
| **当前状态** | 使用随机生成数据 (49.2-85.4岁范围) |
| **数据来源** | WHO Global Health Observatory (GHO) - https://www.who.int/data/gho  <br>World Bank Open Data - https://data.worldbank.org/indicator/SP.DYN.LE00.IN <br>United Nations Population Division |
| **格式要求** | GeoJSON FeatureCollection，包含国家边界几何数据 |
| **质量标准** | • 数据时效性：≤2年<br>• 缺失值比例：≤5%<br>• 与国家边界数据匹配率：≥98% |
| **补充优先级** | 🔴 **P0 - 最高优先级** |
| **使用位置** | `utils/global_life_expectancy.py` - `fetch_real_life_expectancy()` |

### 3.2 全球风险地图数据

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Marco - 全球风险地图 |
| **缺失数据类型** | 全球健康风险评分数据 |
| **具体字段** | `country_code`, `risk_score` (0-10), `risk_category` (疾病负担/环境/行为), `confidence` (置信度), `last_updated` |
| **数据量** | 195个国家/地区 |
| **当前状态** | 使用随机生成数据 (均值5.3, 标准差1.8) |
| **数据来源** | Global Burden of Disease (GBD) Study - https://vizhub.healthdata.org/gbd-results/<br>IHME - Institute for Health Metrics and Evaluation |
| **格式要求** | GeoJSON FeatureCollection，与预期寿命数据几何一致 |
| **质量标准** | • 风险评分精度：小数点后2位<br>• 数据时效性：≤1年<br>• 分类覆盖率：100% |
| **补充优先级** | 🔴 **P0 - 最高优先级** |
| **使用位置** | `utils/global_risk.py` - `fetch_gem_risk_data()` |

### 3.3 中国省级健康数据

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Marco - 中国省级健康指标 |
| **缺失数据类型** | 31个省级行政区健康统计数据 |
| **具体字段** | `province_name`, `life_expectancy` (岁), `mortality_rate` (‰), `doctor_density` (人/千人口), `bed_density` (张/千人口), `health_expenditure` (元/人) |
| **数据量** | 31个省级行政区 × 多年份数据 |
| **当前状态** | 使用随机生成数据 (70.0-82.0岁) |
| **数据来源** | 中国国家统计局 - https://data.stats.gov.cn/<br>《中国卫生健康统计年鉴》<br>NHC (国家卫生健康委员会) 公开数据 |
| **格式要求** | GeoJSON，与行政区划边界匹配 |
| **质量标准** | • 省级覆盖率：100% (31/31)<br>• 数据时效性：≤1年<br>• 与国家统计局官方数据一致性：≥99% |
| **补充优先级** | 🔴 **P0 - 最高优先级** |
| **使用位置** | `utils/china_provincial_health.py` - `fetch_nhc_nbs_data()` |

### 3.4 世界地图指标时序数据

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Marco - 世界地图指标动态展示 |
| **缺失数据类型** | DALYs/Deaths/Prevalence/YLLs/YLDs 时序数据 |
| **具体字段** | `country`, `indicator` (指标类型), `year` (1990-2024), `value`, `unit`, `source`, `is_fallback` |
| **数据量** | 195国 × 5指标 × 35年 ≈ 34,000条记录 |
| **当前状态** | 依赖数据库GlobalHealthMetric表，缺失时生成回退值 |
| **数据来源** | WHO Global Health Observatory<br>GBD Study Results<br>World Bank HealthStats |
| **格式要求** | JSON数组，支持按国家和指标筛选 |
| **质量标准** | • 时间跨度：≥30年<br>• 年度完整性：≥90%<br>• 数值精度：小数点后4位 |
| **补充优先级** | 🟡 **P1 - 高优先级** |
| **使用位置** | `routes/marco.py` - `/map/world-metrics` API |

---

## 四、Meso 中观分析模块数据需求

### 4.1 国家卫生年鉴数据

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Meso - 国家医疗资源配置基线 |
| **缺失数据类型** | 10个国家卫生统计面板数据 |
| **具体字段** | `country`, `physician_density` (人/千人口), `bed_density` (张/千人口), `expenditure_gdp_ratio` (%), `population` (万人), `life_expectancy` (岁), `ncd_ratio` (%), `data_year` |
| **数据量** | 10个国家 × 2005-2024年 |
| **当前状态** | **硬编码静态数据**，未从卫生年鉴Excel读取 |
| **数据来源** | `data/raw/卫生年鉴表/` (2005-2020年Excel文件)<br>WHO Global Health Observatory<br>OECD Health Statistics<br>World Bank HealthStats |
| **格式要求** | CSV或Excel，标准化字段名，支持中英文对照 |
| **质量标准** | • 数据可追溯性：100%<br>• 单位一致性：统一使用标准单位<br>• 更新频率：年度更新 |
| **补充优先级** | 🔴 **P0 - 最高优先级** |
| **使用位置** | `routes/meso.py` - `COUNTRY_PROFILES` 字典 |

### 4.2 疾病转型动态数据

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Meso - 疾病转型阶段分析 |
| **缺失数据类型** | 10国慢性病/传染病负担历史趋势 |
| **具体字段** | `country`, `ncd_ratio` (%), `infectious_ratio` (%), `year` (2000,2010,2020,2024), `transition_stage` |
| **数据量** | 10国 × 4个时间点 |
| **当前状态** | 硬编码4个时间点数据，非真实历史数据 |
| **数据来源** | GBD Study - Disease Burden by Cause<br>WHO Global Health Estimates<br>各国卫生部官方统计 |
| **格式要求** | JSON，支持ECharts折线图渲染 |
| **质量标准** | • 时间分辨率：至少每5年一个数据点<br>• 分类准确性：与ICD-10分类一致<br>• 总和校验：NCD + 传染病 + 其他 = 100% |
| **补充优先级** | 🟡 **P1 - 高优先级** |
| **使用位置** | `routes/meso.py` - `DISEASE_TRANSITION_BASE` 字典 |

### 4.3 医疗资源对标数据

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Meso - 国家间医疗资源配置对比 |
| **缺失数据类型** | 对标国家(peers)详细指标数据 |
| **具体字段** | `country`, `peer_countries` (列表), `efficiency_score` (0-1), `bed_density`, `doctor_density`, `stage` |
| **数据量** | 10国 × 平均4个对标国 |
| **当前状态** | 硬编码对标关系，无动态计算 |
| **数据来源** | OECD Health Statistics<br>Commonwealth Fund<br>WHO Health Workforce Accounts |
| **格式要求** | JSON，支持对标矩阵查询 |
| **质量标准** | • 对标逻辑：基于地理/经济/发展阶段相似性<br>• 数据完整性：所有对标指标覆盖率≥95% |
| **补充优先级** | 🟡 **P1 - 高优先级** |
| **使用位置** | `routes/meso.py` - `MESO_BASELINE_DATA` 中的 `peers` 字段 |

### 4.4 效率评分算法参数

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Meso - 医疗资源配置效率评估 |
| **缺失数据类型** | DEA效率计算所需参数和基准数据 |
| **具体字段** | `input_indicators` (投入指标), `output_indicators` (产出指标), `reference_countries`, `efficiency_algorithm` |
| **数据量** | 多组参数配置 |
| **当前状态** | 硬编码效率评分，无DEA实际计算 |
| **数据来源** | 学术文献 (邵龙龙等, 2025; 常景双, 2019)<br>WHO Efficiency Reports |
| **格式要求** | JSON配置文件 |
| **质量标准** | • 算法可复现性：100%<br>• 参数透明度：完整记录算法权重 |
| **补充优先级** | 🟢 **P2 - 中优先级** |
| **使用位置** | `routes/meso.py` - `efficiency_score` 字段 |

### 4.5 卫生统计年鉴提取器

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Meso - 数据提取模块 |
| **缺失数据类型** | 卫生年鉴Excel自动提取模块 |
| **具体功能** | 从2005-2020年卫生年鉴Excel中提取：`physicians`, `nurses`, `hospital_beds`, `population` |
| **当前状态** | **完全缺失**，仅配置路径未实现逻辑 |
| **数据来源** | `data/raw/卫生年鉴表/*.xlsx` (16个文件) |
| **格式要求** | Python模块，输出标准化CSV |
| **质量标准** | • 提取准确率：≥98%<br>• 异常处理：支持表头变化适配<br>• 单位自动转换：统一转换为标准单位 |
| **补充优先级** | 🔴 **P0 - 最高优先级** |
| **使用位置** | 需新建 `utils/yearbook_extractor.py` |

---

## 五、Micro 微观分析模块数据需求

### 5.1 PAF风险因素实证数据

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Micro - 风险评估(CRA) |
| **缺失数据类型** | 8种风险因素的人群归因分值(PAF)实证数据 |
| **具体字段** | `risk_factor` (风险因素), `paf_value` (%), `base_value` (%), `intervention_effectiveness` (0-1), `category` (行为/代谢/环境), `confidence_interval`, `data_source`, `study_year` |
| **风险因素** | 吸烟、高血压、糖尿病、肥胖、缺乏运动、饮酒、空气污染、不健康饮食 |
| **数据量** | 8个因素 × 多国数据 |
| **当前状态** | 使用文献参考值硬编码，无实证数据支持 |
| **数据来源** | GBD Study - Risk Factor Attribution<br>WHO Global Health Risks<br>《中国居民营养与慢性病状况报告》 |
| **格式要求** | CSV，支持按国家和年份筛选 |
| **质量标准** | • 数据可溯源：引用具体研究文献<br>• 置信区间：提供95% CI<br>• 时效性：≤5年 |
| **补充优先级** | 🟡 **P1 - 高优先级** |
| **使用位置** | `routes/micro.py` - `BASE_PAF_DATA` 字典 |

### 5.2 医院POI详细数据

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Micro - 空间可及性分析(2SFCA) |
| **缺失数据类型** | 成都/北京/上海三甲医院详细POI数据 |
| **具体字段** | `name`, `coords` ([lng, lat]), `level` (医院等级), `capacity` (床位数), `address`, `type` (综合/专科), `department_count`, `specialties` (特色科室) |
| **数据量** | 成都≥50家，北京≥80家，上海≥70家 |
| **当前状态** | 仅8家成都医院硬编码数据，其他两城市仅2家样本 |
| **数据来源** | 高德地图API - https://lbs.amap.com/<br>百度地图API - https://lbsyun.baidu.com/<br>国家卫健委医疗机构查询平台 |
| **格式要求** | GeoJSON，WGS84坐标系 |
| **质量标准** | • 坐标精度：≤100米<br>• 属性完整性：≥95%<br>• 时效性：≤6个月 |
| **补充优先级** | 🟡 **P1 - 高优先级** |
| **使用位置** | `routes/micro.py` - `CHENGDU_HOSPITALS` / `OTHER_CITIES_HOSPITALS` |

### 5.3 空间可及性热力图数据

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Micro - E2SFCA空间分析 |
| **缺失数据类型** | 成都市医疗资源空间可及性网格数据 |
| **具体字段** | `grid_id`, `coordinates` (网格边界), `accessibility_score` (可及性指数), `population_density`, `distance_to_nearest_hospital` |
| **数据量** | 成都市全域500m×500m网格 |
| **当前状态** | 使用随机生成数据模拟 |
| **数据来源** | 基于OSM路网数据自计算<br>高德地图路径规划API |
| **格式要求** | GeoJSON网格，支持热力图渲染 |
| **质量标准** | • 网格覆盖率：100%<br>• 可及性指数范围：0-1<br>• 与医院POI数据关联一致性 |
| **补充优先级** | 🟢 **P2 - 中优先级** |
| **使用位置** | `utils/chengdu_e2sfca.py` - `fetch_amap_baidu_poi()` |

---

## 六、Prediction 预测引擎模块数据需求

### 6.1 历史疾病负担时序数据

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Prediction - 动态干预模拟 |
| **缺失数据类型** | DALYs历史时序数据用于模型校准 |
| **具体字段** | `year` (2000-2024), `dalys` (亿), `deaths` (万人), `ylds` (万人), `ylls` (万人), `cause_breakdown` (病因分解) |
| **数据量** | 25年 × 多指标 |
| **当前状态** | 使用基线值31.2亿，无历史数据支撑 |
| **数据来源** | GBD Study - DALYs by Cause<br>WHO Global Health Estimates<br>《中国卫生健康统计年鉴》 |
| **格式要求** | CSV，支持时间序列分析 |
| **质量标准** | • 时间连续性：无缺失年份<br>• 病因分类：与ICD-10一致<br>• 总DALYs一致性：与WHO数据误差≤2% |
| **补充优先级** | 🟡 **P1 - 高优先级** |
| **使用位置** | `routes/prediction.py` - `BASE_DALYS_2030` 校准 |

### 6.2 干预效果实证参数

| 需求项 | 详情 |
|--------|------|
| **模型名称** | Prediction - 干预效果模拟 |
| **缺失数据类型** | 烟草控制和减盐干预的效果系数 |
| **具体字段** | `intervention_type`, `baseline_paf` (%), `reduction_rate` (%/年), `lag_years` (效果延迟年数), `population_reach` (覆盖率), `evidence_source` |
| **干预类型** | 烟草控制、减盐、运动推广、饮食改善 |
| **数据量** | 4类干预 × 多国研究数据 |
| **当前状态** | 硬编码权重系数 (TOBACCO_IMPACT_WEIGHT=0.4, SALT_IMPACT_WEIGHT=0.3) |
| **数据来源** | WHO Best Buys<br>《中国慢性病防治中长期规划》<br>Cochrane系统评价 |
| **格式要求** | JSON配置文件，支持元数据追溯 |
| **质量标准** | • 循证依据：RCT或准实验研究<br>• 效果可量化：提供点估计和95%CI<br>• 人群适用性：中国人群研究优先 |
| **补充优先级** | 🟢 **P2 - 中优先级** |
| **使用位置** | `routes/prediction.py` - `PredictionEngine` 类参数 |

---

## 七、API数据流与缺失数据处理机制（新增）

### 7.1 各API数据依赖与兜底机制

| API端点 | 依赖数据表/文件 | 当前缺失处理 | 影响程度 |
|---------|----------------|-------------|----------|
| `/api/chart/trend` | `AdvancedDiseaseTransition` | 使用硬编码兜底序列 | 中 |
| `/api/analysis/metrics` | `AdvancedDiseaseTransition`, `AdvancedResourceEfficiency` | 使用fallback_data (第401行) | **高** |
| `/api/disease_simulation` | `AdvancedDiseaseTransition` | **返回400错误，无法执行** | **极高** |
| `/api/spatial_analysis` | 高德POI API | 使用演示数据 (E2SFCA模拟) | 中 |
| `/api/news` | Mediastack API | API限额(100次/月)超额使用静态数据 | 低 |
| `/api/v1/marco/map/world-metrics` | `GlobalHealthMetric` | 使用`_calc_reproducible_map_fallback` | 中 |
| `/api/v1/meso/country-data` | `COUNTRY_PROFILES` (硬编码) | 使用硬编码静态数据 | 中 |
| `/api/v1/micro/spatial-poi` | `CHENGDU_HOSPITALS` | 使用硬编码8家医院 | 高 |
| `/api/v1/prediction/simulate` | 基线参数 | 使用硬编码基线值31.2亿 | 中 |

### 7.2 前端页面数据兜底情况

| 页面 | 数据需求 | 兜底数据类型 | 位置 |
|------|---------|-------------|------|
| `macro-analysis.html` | 健康趋势/指标 | mockData (第1077行) | 硬编码JS对象 |
| `meso-analysis.html` | 国家基线/转型 | 模拟数据标识 (第1140行) | API返回is_mock标记 |
| `micro-analysis.html` | 医院POI/风险 | CHENGDU_HOSPITALS (8家) | 硬编码数组 |
| `prediction.html` | 基准指标 | fallbackData (第1958行) | 硬编码JS对象 |
| `index.html` | 趋势/地图 | fallbackValue | 可复现回退算法 |

---

## 八、数据需求汇总表

### 8.1 按优先级汇总

#### 🔴 P0 - 最高优先级（立即补充，阻塞功能）

| 序号 | 模块 | 数据需求 | 数据来源 | 预计工作量 | 阻塞功能 |
|------|------|---------|---------|-----------|----------|
| 1 | **数据库** | `AdvancedDiseaseTransition` China/global数据 | GBD Study | 3-5天 | `/api/disease_simulation` |
| 2 | **数据库** | `AdvancedResourceEfficiency` DEA投入产出矩阵 | 卫生年鉴 | 3-5天 | DEA效率指标 |
| 3 | Marco | 全球预期寿命分布 (195国) | WHO GHO | 3-5天 | 预期寿命地图 |
| 4 | Marco | 全球风险地图数据 (195国) | GBD Study | 3-5天 | 风险地图 |
| 5 | Marco | 中国省级健康数据 (31省) | 国家统计局 | 2-3天 | 省级地图 |
| 6 | Meso | 国家卫生年鉴数据 (10国×20年) | 卫生年鉴Excel | 5-7天 | 国家对比 |
| 7 | Meso | 卫生统计年鉴提取器模块 | 自研开发 | 7-10天 | 年鉴自动化 |

#### 🟡 P1 - 高优先级（4周内补充）

| 序号 | 模块 | 数据需求 | 数据来源 | 预计工作量 |
|------|------|---------|---------|-----------|
| 8 | **数据库** | `GlobalHealthMetric` 全球时序数据 | WHO, GBD | 5-7天 |
| 9 | Marco | 世界地图指标时序数据 | WHO, GBD | 5-7天 |
| 10 | Meso | 疾病转型动态数据 | GBD Study | 3-5天 |
| 11 | Meso | 医疗资源对标数据 | OECD, WHO | 2-3天 |
| 12 | Micro | PAF风险因素实证数据 | GBD, WHO | 4-6天 |
| 13 | Micro | 医院POI详细数据 (3城市×200家) | 高德/百度API | 5-7天 |
| 14 | Prediction | 历史疾病负担时序数据 | GBD, 年鉴 | 3-5天 |

#### 🟢 P2 - 中优先级（3个月内补充）

| 序号 | 模块 | 数据需求 | 数据来源 | 预计工作量 |
|------|------|---------|---------|-----------|
| 15 | Meso | 效率评分算法参数 | 学术文献 | 2-3天 |
| 16 | Micro | 空间可及性热力图数据 | OSM/API计算 | 7-10天 |
| 17 | Prediction | 干预效果实证参数 | WHO, Cochrane | 3-5天 |

### 8.2 按数据来源汇总

| 数据来源 | 涉及数据项 | API/网址 | 访问方式 |
|---------|-----------|---------|---------|
| **WHO GHO** | 全球预期寿命、风险评分、PAF | https://www.who.int/data/gho | API/GHO Access |
| **World Bank** | 预期寿命、卫生支出、人口 | https://data.worldbank.org/ | API/Data Catalog |
| **GBD Study** | 疾病负担、风险归因、转型数据 | https://vizhub.healthdata.org/ | 下载/Results Tool |
| **国家统计局** | 中国省级健康统计 | https://data.stats.gov.cn/ | 下载/API |
| **高德地图** | 医院POI、路径规划 | https://lbs.amap.com/ | API Key |
| **百度地图** | 医院POI、路径规划 | https://lbsyun.baidu.com/ | API Key |
| **本地年鉴** | 卫生年鉴Excel (2005-2020) | `data/raw/卫生年鉴表/` | 本地文件 |
| **OECD** | 医疗资源对标数据 | https://data.oecd.org/ | API/下载 |

---

## 九、数据收集任务分配建议

### 9.1 任务分工矩阵

| 数据项 | 建议负责人 | 协作方 | 交付物 | 优先级 |
|--------|-----------|--------|--------|--------|
| `AdvancedDiseaseTransition`表数据 | 数据工程师 | 业务分析师 | SQL导入脚本 | 🔴 P0 |
| `AdvancedResourceEfficiency`表数据 | 数据工程师 | 后端开发 | SQL导入脚本 | 🔴 P0 |
| 全球预期寿命/风险数据 | 数据工程师 | 业务分析师 | CSV/GeoJSON | 🔴 P0 |
| 中国省级健康数据 | 数据工程师 | 政策研究员 | CSV/GeoJSON | 🔴 P0 |
| 卫生年鉴提取模块 | 后端开发 | 数据工程师 | Python模块 | 🔴 P0 |
| `GlobalHealthMetric`表数据 | 数据工程师 | 业务分析师 | SQL导入脚本 | 🟡 P1 |
| 疾病转型/对标数据 | 业务分析师 | 外部专家 | JSON配置 | 🟡 P1 |
| PAF风险因素数据 | 业务分析师 | 流行病学专家 | CSV数据库 | 🟡 P1 |
| 医院POI数据 | 数据工程师 | GIS专员 | GeoJSON | 🟡 P1 |
| 历史DALYs数据 | 数据工程师 | 业务分析师 | CSV时序数据 | 🟡 P1 |
| 干预效果参数 | 业务分析师 | 公共卫生专家 | JSON配置 | 🟢 P2 |

### 9.2 修订里程碑计划

| 里程碑 | 日期 | 交付内容 | 关键目标 |
|--------|------|---------|----------|
| **M1** | 2026-04-23 | 完成数据库核心表数据导入 | `/api/disease_simulation`可用 |
| **M2** | 2026-04-30 | 完成P0数据收集：全球预期寿命、中国省级数据 | 宏观地图可用 |
| **M3** | 2026-05-07 | 完成P0数据收集：全球风险地图、卫生年鉴20年数据 | 中观分析可用 |
| **M4** | 2026-05-21 | 完成P1数据收集：`GlobalHealthMetric`、疾病转型、PAF风险因素 | 数据库完整性提升 |
| **M5** | 2026-06-04 | 完成P1数据收集：医院POI、历史DALYs | 微观分析/预测可用 |
| **M6** | 2026-06-25 | 完成P2数据收集：效率参数、热力图、干预参数 | 算法优化 |

---

## 十、附录

### 10.1 数据需求对照表

| 模型 | 当前状态 | 目标状态 | 差距 |
|------|---------|---------|------|
| **数据库-疾病谱系** | 表空，API返回400错误 | GBD真实数据导入 | **100%数据缺失** |
| **数据库-DEA效率** | 投入产出矩阵为空 | 卫生年鉴计算导入 | **100%数据缺失** |
| Marco-预期寿命 | 随机生成(49-85岁) | WHO真实数据 | **195国真实数据缺失** |
| Marco-风险地图 | 随机生成(均值5.3) | GBD真实风险 | **195国真实数据缺失** |
| Marco-中国省级 | 随机生成(70-82岁) | 国家统计局官方 | **31省真实数据缺失** |
| Meso-国家基线 | 硬编码静态值 | 年鉴动态提取 | **20年时序数据缺失** |
| Meso-疾病转型 | 硬编码4时间点 | GBD历史数据 | **真实历史趋势缺失** |
| Micro-PAF | 文献参考值 | 实证研究数据 | **中国人群PAF缺失** |
| Micro-医院POI | 仅8家样本 | 全市200+家 | **92%医院数据缺失** |
| Prediction-基线 | 硬编码31.2亿 | 历史DALYs校准 | **25年时序数据缺失** |

### 10.2 已存在数据清单（无需补充）

以下数据已存在于 `data/` 目录，功能正常：

| 数据类别 | 文件路径 | 状态 |
|---------|----------|------|
| 卫生年鉴原始文件 | `data/raw/卫生年鉴表/2005-2020.xlsx` | ✅ 可用 |
| GBD原始数据 | `data/raw/GBD.csv` | ✅ 可用 |
| WDI原始数据 | `data/raw/WDI.csv` | ✅ 可用 |
| 清洗后数据 | `data/processed/cleaned_*.csv` | ✅ 可用 |
| 成都GeoJSON | `data/geojson/chengdu_*.geojson` | ✅ 可用 |
| 可及性缓存 | `data/processed/chengdu_accessibility_*.geojson` | ✅ 可用 |
| 全球地图 | `data/geojson/countries/*.geo.json` | ✅ 可用 |
| 全球国家边界 | `data/geojson/ne_10m_admin_0_countries.geojson` | ✅ 可用 |

### 10.3 相关文档

- [data_call_analysis_report.md](./data_call_analysis_report.md) - 数据调用分析报告
- [mock_data_report.md](./mock_data_report.md) - Mock数据规范
- [hardcoded_data_report.md](./hardcoded_data_report.md) - 硬编码数据报告
- `data/missing_data/missing_report_2026-04.json` - 缺失数据日志

---

**报告编制**: Health Information System Team  
**审核状态**: 待审核  
**下次更新**: M1里程碑完成后更新（2026-04-23）
