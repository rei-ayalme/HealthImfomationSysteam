# Mock 数据详细报告

## 文档信息

- **文档版本**: 1.0
- **创建日期**: 2026-04-16
- **适用范围**: Health Information System 项目
- **文档目的**: 详细记录项目中所有 Mock/Fallback 数据定义、结构和使用场景

---

## 目录

1. [概述](#1-概述)
2. [Mock 数据分布](#2-mock-数据分布)
3. [Routes 模块 Mock 数据](#3-routes-模块-mock-数据)
4. [Utils 模块 Mock 数据](#4-utils-模块-mock-数据)
5. [Main 模块 Fallback 数据](#5-main-模块-fallback-数据)
6. [Mock 数据对比分析](#6-mock-数据对比分析)
7. [存在的问题](#7-存在的问题)
8. [优化建议](#8-优化建议)

---

## 1. 概述

### 1.1 什么是 Mock 数据

Mock 数据（模拟数据）是指在真实数据源不可用、获取失败或超时的情况下，系统返回的预设数据。在本项目中，Mock 数据主要用于：

1. **开发测试**: 在真实 API 未就绪时进行前端开发
2. **优雅降级**: 当外部服务故障时保证系统可用性
3. **演示展示**: 提供稳定的演示数据
4. **数据兜底**: 在数据库查询失败时返回默认值

### 1.2 Mock 数据架构

```
┌─────────────────────────────────────────────────────────────┐
│                    真实数据源 (Real Data)                     │
│     (WHO API / 高德地图 / 世界银行 /  PostgreSQL 数据库)       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ (失败/超时/数据缺失)
┌─────────────────────────────────────────────────────────────┐
│              Orchestrator 数据编排层 (优雅降级)                │
│              @orchestrate_data 装饰器处理超时和重试             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Mock / Fallback 数据层                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ 静态 Mock    │  │ 动态生成     │  │ 兜底 Fallback       │  │
│  │ (routes/)   │  │ (utils/)    │  │ (main.py)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Mock 数据分布

### 2.1 文件分布统计

| 模块 | 文件路径 | Mock 数据类型 | 数据量级 |
|------|----------|---------------|----------|
| routes | `routes/micro.py` | PAF 风险因素、医院 POI | 8条+10条 |
| routes | `routes/meso.py` | 国家基线统计数据 | 10个国家 |
| routes | `routes/prediction.py` | 预测基线参数 | 2个基线值 |
| utils | `utils/global_risk.py` | 全球风险地图 | 195个国家 |
| utils | `utils/global_life_expectancy.py` | 全球预期寿命 | 195个国家 |
| utils | `utils/china_provincial_health.py` | 中国省级健康 | 31个省市 |
| utils | `utils/chengdu_e2sfca.py` | 成都 POI 数据 | 100条样本 |
| utils | `utils/microsimulation.py` | 微观模拟人口 | 100万智能体样本 |
| main | `main.py` | 趋势图兜底、分析指标兜底 | 多处 |

---

## 3. Routes 模块 Mock 数据

### 3.1 Micro 模块 (`routes/micro.py`)

#### 3.1.1 BASE_PAF_DATA - 人群归因分值数据

**数据来源**: 基于 GBD (Global Burden of Disease) 研究文献估算值

**使用场景**: 
- `/api/v1/micro/risk-assessment` 接口
- `/api/v1/micro/risk-factors` 接口

**数据结构**:

```python
BASE_PAF_DATA = {
    "smoking": {
        "label": "吸烟",                    # 显示名称
        "base_value": 24.8,                 # 基础 PAF 值 (%)
        "category": "行为风险",              # 风险类别
        "intervention_effectiveness": 0.85,  # 干预有效性系数 (0-1)
        "description": "吸烟导致的疾病负担占比"
    },
    "hypertension": {
        "label": "高血压",
        "base_value": 27.5,
        "category": "代谢风险",
        "intervention_effectiveness": 0.65,
        "description": "高血压导致的疾病负担占比"
    },
    # ... 其他 6 个风险因素
}
```

**字段说明**:

| 字段名 | 类型 | 说明 | 取值范围 |
|--------|------|------|----------|
| label | str | 中文显示名称 | - |
| base_value | float | 基础人群归因分值 | 0-100 |
| category | str | 风险因素分类 | 行为风险/代谢风险/环境风险 |
| intervention_effectiveness | float | 干预措施有效性 | 0-1 |
| description | str | 字段描述 | - |

**与实际业务数据的差异**:
- 实际数据应来自 GBD 数据库的年度更新
- Mock 数据使用固定值，未考虑时间趋势
- 实际数据应按年龄、性别、地区分层

---

#### 3.1.2 CHENGDU_HOSPITALS - 成都医院 POI 数据

**数据来源**: 基于公开信息整理的成都三甲医院数据

**使用场景**: 
- `/api/v1/micro/spatial-poi` 接口
- 空间可及性分析演示

**数据结构**:

```python
CHENGDU_HOSPITALS = [
    {
        "name": "四川大学华西医院",
        "coords": [104.0632, 30.6418],      # [经度, 纬度]
        "level": "三甲",                     # 医院等级
        "capacity": 4300,                    # 床位数
        "address": "成都市武侯区国学巷37号",
        "type": "综合医院",                   # 医院类型
        "search_radius": 60.0                # 搜索半径(公里)
    },
    # ... 共 8 家医院
]
```

**字段说明**:

| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| name | str | 医院名称 | 四川大学华西医院 |
| coords | List[float] | 经纬度坐标 [lng, lat] | [104.0632, 30.6418] |
| level | str | 医院等级 | 三甲/三乙/二甲 |
| capacity | int | 床位数 | 4300 |
| address | str | 详细地址 | 成都市武侯区... |
| type | str | 医院类型 | 综合医院/专科医院 |
| search_radius | float | 服务半径(公里) | 60.0 |

**与实际业务数据的差异**:
- 实际数据应从高德地图/百度地图 API 获取
- Mock 数据仅包含 8 家医院，实际成都三甲医院更多
- 实际数据应包含实时床位使用率
- 坐标精度实际应为 WGS84 或 GCJ-02 标准

---

#### 3.1.3 OTHER_CITIES_HOSPITALS - 其他城市医院数据

**数据结构**: 与 CHENGDU_HOSPITALS 相同

**覆盖城市**: Beijing, Shanghai

**数据量**: 每个城市 2 家医院样本

---

### 3.2 Meso 模块 (`routes/meso.py`)

#### 3.2.1 MESO_BASELINE_DATA - 国家基线统计数据

**数据来源**: 基于 WHO、World Bank 公开数据的估算值

**使用场景**: 
- `/api/v1/meso/dashboard` 接口
- `/api/v1/meso/compare` 接口
- `/api/v1/meso/countries` 接口

**覆盖国家**: 10个 (China, Japan, USA, Germany, South Korea, India, Brazil, UK, France, Singapore)

**数据结构**:

```python
MESO_BASELINE_DATA = {
    "China": {
        "life_expectancy": {"value": 79.0, "trend": "+3.4", "unit": "岁"},
        "ncd_ratio": {"value": 89.4, "trend": "+12.3", "unit": "%"},
        "doctor_density": {"value": 2.99, "trend": "+1.1", "unit": "人/千人口"},
        "efficiency_score": {"value": 0.82, "trend": "+0.05", "unit": "分"},
        "bed_density": {"value": 7.1, "trend": "+0.8", "unit": "张/千人口"},
        "expenditure_gdp_ratio": {"value": 5.6, "trend": "+0.3", "unit": "%"},
        "population": {"value": 1410, "trend": "+0.1", "unit": "百万"},
        "stage": "慢性病快速上升",
        "peers": ["Japan", "South Korea", "Thailand", "Brazil"]
    },
    # ... 其他 9 个国家
}
```

**字段说明**:

| 指标名 | 说明 | 单位 | 数据来源参考 |
|--------|------|------|--------------|
| life_expectancy | 预期寿命 | 岁 | WHO Life Expectancy |
| ncd_ratio | 慢性病负担占比 | % | GBD Study |
| doctor_density | 医生密度 | 人/千人口 | WHO Health Workforce |
| efficiency_score | 医疗效率评分 | 分 (0-1) | 基于 DEA 模型估算 |
| bed_density | 床位密度 | 张/千人口 | WHO Health Statistics |
| expenditure_gdp_ratio | 医疗支出占 GDP 比 | % | World Bank |
| population | 人口数量 | 百万 | UN Population Division |
| stage | 疾病转型阶段 | - | 流行病学转型理论 |
| peers | 对标国家 | - | 基于发展阶段相似性 |

**与实际业务数据的差异**:
- 实际数据应每年更新
- Mock 数据为单一年度快照
- 实际数据应包含置信区间
- 部分指标（如 efficiency_score）为模型估算值

---

#### 3.2.2 DISEASE_TRANSITION_STAGES - 疾病转型阶段

**数据来源**: Omran 流行病学转型理论

**使用场景**: 生成疾病转型趋势图表

**定义**:
- 感染性疾病主导
- 慢性病快速上升
- 退行性疾病主导

---

#### 3.2.3 REGION_ALIASES - 地区别名映射

**使用场景**: 支持中英文地区名称查询

**映射示例**:
```python
REGION_ALIASES = {
    "中国": "China",
    "china": "China",
    "美国": "USA",
    "usa": "USA",
    # ...
}
```

---

### 3.3 Prediction 模块 (`routes/prediction.py`)

#### 3.3.1 预测基线参数

**数据来源**: 基于 GBD 预测模型的参考值

**使用场景**: 
- `/api/v1/prediction/simulate` 接口
- `/api/v1/prediction/baseline` 接口

**参数定义**:

```python
class PredictionEngine:
    BASE_BURDEN_2030 = 31.2  # 基础预测：31.2亿 DALYs
    BASE_LIFE_EXP = 76.5     # 基础预测：76.5岁
    
    TOBACCO_WEIGHT = 0.005   # 烟草控制权重
    SALT_WEIGHT = 0.003      # 食盐减少权重
```

**字段说明**:

| 参数名 | 说明 | 单位 | 计算逻辑 |
|--------|------|------|----------|
| BASE_BURDEN_2030 | 2030年疾病负担基线 | 亿 DALYs | GBD 参考情景 |
| BASE_LIFE_EXP | 预期寿命基线 | 岁 | UN World Population Prospects |
| TOBACCO_WEIGHT | 烟草干预权重 | - | 基于文献 Meta 分析 |
| SALT_WEIGHT | 减盐干预权重 | - | 基于文献 Meta 分析 |

**与实际业务数据的差异**:
- 实际应使用 BAPC (Bayesian Age-Period-Cohort) 模型动态计算
- Mock 使用线性简化模型
- 实际应考虑年龄结构变化

---

## 4. Utils 模块 Mock 数据

### 4.1 Global Risk (`utils/global_risk.py`)

#### 4.1.1 generate_fallback_risk_data - 全球风险地图数据

**数据来源**: GEM (Global Earthquake Model) 与 AIR Worldwide 风险数据参考

**使用场景**: 
- `/api/map/global-risk` 接口
- 全球风险可视化

**数据规模**: 195 个国家

**数据结构**:

```python
{
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "country_code": "China",
                "risk_score": 5.32,        # 风险评分 (0-10)
                "confidence": "medium"     # 置信度
            },
            "geometry": None
        }
    ],
    "meta": {
        "freshness_hour": 8760         # 数据时效：1年
    }
}
```

**生成算法**:
```python
score = max(0.0, min(10.0, random.gauss(5.3, 1.8)))
```

**与实际业务数据的差异**:
- 实际应调用 GEM/AIR API 获取实时风险数据
- Mock 使用正态分布随机生成
- 实际数据应包含多维度风险（地震、洪水、飓风等）

---

### 4.2 Global Life Expectancy (`utils/global_life_expectancy.py`)

#### 4.2.1 generate_fallback_life_expectancy - 全球预期寿命数据

**数据来源**: UN World Population Prospects 2019

**使用场景**: 
- `/api/map/global-life-expectancy` 接口

**数据规模**: 195 个国家

**生成算法**:
```python
score = random.uniform(49.2, 85.4)  # 基于 UN 历史范围
```

**与实际业务数据的差异**:
- 实际应从 WHO GHO API 获取
- Mock 使用均匀分布随机生成
- 实际数据应分性别、年龄段

---

### 4.3 China Provincial Health (`utils/china_provincial_health.py`)

#### 4.3.1 spatial_adjacency_imputation - 中国省级健康数据

**数据来源**: 基于 NHC (国家卫健委) 和 NBS (国家统计局) 数据格式模拟

**使用场景**: 
- `/api/map/china-provincial-health` 接口

**数据规模**: 31 个省市自治区

**数据结构**:

```python
{
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "province": "北京",
                "life_expectancy": 78.52,   # 预期寿命
                "imputed": True              # 是否为插补值
            }
        }
    ],
    "meta": {
        "freshness_hour": 24
    }
}
```

**生成算法**:
```python
life_expectancy = random.uniform(70.0, 82.0)
```

**与实际业务数据的差异**:
- 实际应从 NHC 统计年鉴获取
- Mock 未考虑地区差异（东西部差距）
- 实际数据应包含更多指标（婴儿死亡率、孕产妇死亡率等）

---

### 4.4 Chengdu E2SFCA (`utils/chengdu_e2sfca.py`)

#### 4.4.1 generate_chengdu_poi_fallback - 成都 POI 数据

**数据来源**: 基于 2023年第四季度高德地图 POI 数据格式模拟

**使用场景**: 
- `/api/map/chengdu-e2sfca` 接口

**数据规模**: 100 条样本（代表 9847 条记录）

**数据结构**:

```python
{
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "name": "Hospital 0",
                "address": "Chengdu",
                "type": "hospital",
                "bed_count": 523          # 正态分布生成
            },
            "geometry": {
                "type": "Point",
                "coordinates": [104.06, 30.67]  # 成都中心附近随机
            }
        }
    ],
    "meta": {
        "record_count_represented": 9847,
        "freshness_hour": 4320        # 6个月
    }
}
```

**生成算法**:
```python
bed_count = int(random.gauss(500, 100))
coordinates = [104.06 + random.uniform(-0.1, 0.1), 
               30.67 + random.uniform(-0.1, 0.1)]
```

**与实际业务数据的差异**:
- 实际应调用高德/百度 POI API
- Mock 数据为随机生成，无真实医院对应
- 实际应包含医院等级、科室等详细信息

---

### 4.5 Microsimulation (`utils/microsimulation.py`)

#### 4.5.1 generate_synthetic_population - 合成人口数据

**数据来源**: 基于 IPF (Iterative Proportional Fitting) 算法原理模拟

**使用场景**: 
- `/api/simulation/micro-population` 接口

**数据规模**: 100 条样本（代表 100 万智能体）

**数据结构**:

```python
{
    "status": "success",
    "population_size": 1000000,
    "sample": [
        {
            "age": 45,                    # 年龄 (正态分布: μ=40, σ=15)
            "gender": "M",                # 性别 (M/F)
            "occupation": "A",            # 职业类别 (A/B/C)
            "chronic_disease": 0,         # 是否患慢性病 (0/1)
            "smoking_drinking": 1         # 是否吸烟饮酒 (0/1)
        }
    ],
    "meta": {
        "freshness_hour": 8760,
        "generation_time_s": 0.023
    }
}
```

**生成算法**:
```python
age = int(random.gauss(40, 15))
gender = random.choice(["M", "F"])
occupation = random.choice(["A", "B", "C"])
chronic_disease = random.choice([0, 1])
smoking_drinking = random.choice([0, 1])
```

**与实际业务数据的差异**:
- 实际应基于人口普查微观样本
- Mock 未考虑人口结构（年龄金字塔）
- 实际应包含收入、教育等社会经济变量
- 实际应支持多区域人口合成

---

## 5. Main 模块 Fallback 数据

### 5.1 趋势图兜底数据

**位置**: `/api/chart/trend` 接口

**使用场景**: 当数据库查询返回数据不足 2 点时

**数据结构**:

```python
# 兜底时间序列
years = [2020, 2021, 2022, 2023, 2024]

# 指标基线值
base_value_map = {
    "dalys": 2.4,
    "deaths": 56.0,
    "prevalence": 14.5,
    "ylls": 1.68,
    "ylds": 0.75
}

# 区域调整因子
region_factor = 1.0 if region_key == "global" else 0.9 if region_key == "east_asia" else 0.8

# 生成序列
values = [round(base_value * region_factor * (0.94 + i * 0.02), 4) for i in range(len(years))]
```

---

### 5.2 分析指标兜底数据

**位置**: `/api/analysis/metrics` 接口

**使用场景**: 数据库查询异常时

**数据结构**:

```python
fallback_data = {
    "dalys": {
        "value": 12450.0, 
        "trend": 0, 
        "sparkline": [11600, 11800, 12100, 12350, 12450]
    },
    "top_disease": {
        "name": "心血管疾病", 
        "ratio": 36.1
    },
    "dea": {
        "value": 0.85, 
        "trend": 0, 
        "sparkline": [0.81, 0.82, 0.83, 0.84, 0.85]
    },
    "prediction": {
        "growth_rate": 0, 
        "target": "心血管疾病"
    }
}
```

---

### 5.3 空间分析演示数据

**位置**: `/api/spatial_analysis` 接口

**使用场景**: 高德 API 未配置或调用失败时

**数据结构**:

```python
# 基于 threshold_km 动态生成
factor = 1.0 + (threshold_km - 10) * 0.02
base_scores = [0.85, 0.82, 0.78, 0.88, 0.81]
scores = [round(min(1.0, max(0.1, s * factor)), 3) for s in base_scores]

demo_data = {
    "status": "success",
    "region": region,
    "level": level,
    "chart_data": {
        "labels": ["锦江区", "青羊区", "金牛区", "武侯区", "成华区"],
        "datasets": [{
            "label": f"{region} 演示数据 (E2SFCA)",
            "data": scores,
            "borderColor": "#1890ff",
            "borderWidth": 2,
            "fill": False
        }],
        "geo_points": [
            {"name": "锦江区", "value": [104.08, 30.65, scores[0]], "z_weight": scores[0]},
            # ... 其他区
        ]
    }
}
```

---

## 6. Mock 数据对比分析

### 6.1 数据类型对比

| 数据类型 | 真实数据源 | Mock 生成方式 | 更新频率 | 数据量级 |
|----------|------------|---------------|----------|----------|
| PAF 风险因素 | GBD Database | 静态常量 | 手动 | 8条 |
| 医院 POI | 高德/百度 API | 静态常量 | 手动 | 12条 |
| 国家基线 | WHO/World Bank | 静态常量 | 手动 | 10国 |
| 全球风险 | GEM/AIR API | 正态分布随机 | 实时 | 195国 |
| 预期寿命 | WHO GHO API | 均匀分布随机 | 实时 | 195国 |
| 省级健康 | NHC 年鉴 | 均匀分布随机 | 实时 | 31省 |
| 成都 POI | 高德 API | 正态分布随机 | 实时 | 100样本 |
| 微观模拟 | 人口普查 | 离散随机 | 实时 | 100样本 |

### 6.2 精度对比

| 指标 | 真实数据精度 | Mock 数据精度 | 误差范围 |
|------|--------------|---------------|----------|
| 风险评分 | 小数点后2位 | 小数点后2位 | ±3.0 |
| 预期寿命 | 小数点后1位 | 小数点后1位 | ±15岁 |
| 医院坐标 | 6位小数 | 4位小数 | ~1km |
| PAF 值 | 小数点后1位 | 小数点后1位 | 参考值 |
| 疾病负担 | 整数 | 整数 | 参考值 |

---

## 7. 存在的问题

### 7.1 数据一致性问题

1. **时间戳不一致**
   - 不同 Mock 数据使用不同的 `freshness_hour` 定义
   - 部分数据无时间戳，无法判断时效性

2. **坐标系不统一**
   - 部分使用 WGS84，部分使用 GCJ-02
   - 未在元数据中标注坐标系类型

3. **字段命名不规范**
   - 同一概念多个字段名（如 `country` vs `country_code`）
   - 中英文混用

### 7.2 数据完整性问题

1. **缺失置信区间**
   - Mock 数据均为点估计，无不确定性范围
   - 实际业务需要 95% CI

2. **缺失分层数据**
   - 无年龄、性别分层
   - 无城乡差异

3. **缺失时间序列**
   - 大部分 Mock 为单一年份快照
   - 无法支持趋势分析

### 7.3 算法简化问题

1. **预测模型过于简化**
   - 使用线性模型替代 BAPC/SDE
   - 未考虑队列效应

2. **插补方法简单**
   - 使用随机数替代空间插值
   - 未考虑空间自相关

### 7.4 维护性问题

1. **分散定义**
   - Mock 数据分散在 8+ 个文件中
   - 无统一管理中心

2. **硬编码问题**
   - 数值直接写在代码中
   - 修改需重新部署

3. **文档缺失**
   - 部分 Mock 无数据来源说明
   - 更新历史未记录

---

## 8. 优化建议

### 8.1 短期优化 (1-2周)

1. **统一字段命名**
   ```python
   # 建议统一使用以下命名规范
   country_code      # ISO 3166-1 alpha-3
   region_name       # 地区名称
   indicator_value   # 指标值
   value_unit        # 单位
   confidence_lower  # 95% CI 下限
   confidence_upper  # 95% CI 上限
   data_year         # 数据年份
   update_time       # 更新时间
   ```

2. **添加元数据标准**
   ```python
   {
       "data": {...},
       "meta": {
           "source": "mock",
           "source_type": "fallback",
           "freshness_hour": 8760,
           "coordinate_system": "WGS84",
           "confidence_level": "medium",
           "last_updated": "2026-04-16"
       }
   }
   ```

3. **创建 Mock 数据管理模块**
   ```
   mock_data/
   ├── __init__.py
   ├── constants.py      # 静态常量
   ├── generators.py     # 动态生成器
   ├── schemas.py        # 数据校验
   └── README.md         # 数据说明
   ```

### 8.2 中期优化 (1个月)

1. **配置文件化**
   - 将 Mock 数据迁移到 JSON/YAML 文件
   - 支持热更新，无需重启服务

2. **增加数据校验**
   ```python
   from pydantic import BaseModel, Field
   
   class MockHealthIndicator(BaseModel):
       value: float = Field(ge=0, le=100)
       unit: str
       year: int = Field(ge=1990, le=2030)
       source: str
   ```

3. **实现数据版本控制**
   ```python
   MOCK_DATA_VERSION = "1.2.0"
   
   def get_mock_data(data_type: str, version: str = None):
       version = version or MOCK_DATA_VERSION
       # 根据版本返回对应数据
   ```

### 8.3 长期优化 (3个月)

1. **Mock 数据服务化**
   - 独立 Mock 数据服务
   - 支持动态配置和切换

2. **智能 Mock 生成**
   - 基于真实数据分布生成
   - 使用 GAN/VAE 学习数据特征

3. **Mock 数据与测试集成**
   ```python
   # 测试时自动切换 Mock
   @pytest.fixture
   def mock_health_data():
       with mock.patch('utils.global_risk.fetch_gem_risk_data') as m:
           m.return_value = load_mock_data('global_risk')
           yield
   ```

4. **数据血缘追踪**
   - 记录 Mock 数据来源
   - 建立与真实数据的映射关系

---

## 附录

### A. Mock 数据文件清单

| 序号 | 文件路径 | 数据类型 | 维护责任人 |
|------|----------|----------|------------|
| 1 | routes/micro.py | PAF/医院POI | 开发团队 |
| 2 | routes/meso.py | 国家基线 | 开发团队 |
| 3 | routes/prediction.py | 预测参数 | 开发团队 |
| 4 | utils/global_risk.py | 全球风险 | 开发团队 |
| 5 | utils/global_life_expectancy.py | 预期寿命 | 开发团队 |
| 6 | utils/china_provincial_health.py | 省级健康 | 开发团队 |
| 7 | utils/chengdu_e2sfca.py | 成都POI | 开发团队 |
| 8 | utils/microsimulation.py | 微观模拟 | 开发团队 |
| 9 | main.py | 各类兜底 | 开发团队 |

### B. 相关文档

- [数据格式规范](data_format_specification.md)
- [前端硬编码报告](frontend_hardcoded_report.md)
- [API 验证报告](frontend_api_verification_report.md)

---

**文档结束**

*本报告由系统自动生成，如有疑问请联系开发团队。*
