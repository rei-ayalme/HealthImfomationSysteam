# 中台数据中转接口Path路径分析报告

## 报告概述

**生成日期**: 2026-04-17  
**分析范围**: Health_Imformation_Systeam/routes 目录  
**路由框架**: FastAPI APIRouter  
**总接口数量**: 25个  
**基础路径前缀**: `/api/v1`

---

## 一、中台架构概览

### 1.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端应用层                               │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │ macro-       │ meso-        │ micro-       │ prediction   │  │
│  │ analysis.html│ analysis.html│ analysis.html│ .html        │  │
│  └──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘  │
└─────────┼──────────────┼──────────────┼──────────────┼──────────┘
          │              │              │              │
          └──────────────┴──────┬───────┴──────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────┐
│                         中台服务层 (FastAPI)                     │
│  ┌────────────────────────────┼────────────────────────────┐    │
│  │      API Router 路由分发    │                            │    │
│  │  ┌─────────┬─────────┬─────┴────┬─────────┐             │    │
│  │  │ /marco  │ /meso   │ /micro   │/prediction           │    │
│  │  │ (10个)  │ (6个)   │ (7个)    │ (3个)   │             │    │
│  │  └────┬────┴────┬────┴────┬─────┴────┬────┘             │    │
│  └───────┼─────────┼─────────┼──────────┼──────────────────┘    │
└──────────┼─────────┼─────────┼──────────┼───────────────────────┘
           │         │         │          │
           ▼         ▼         ▼          ▼
┌─────────────────────────────────────────────────────────────────┐
│                         数据处理层                               │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │ DataLoader   │ DataProcessor│ Predictor    │ HealthMath   │  │
│  │ (数据加载)    │ (数据处理)    │ (预测引擎)    │ Models       │  │
│  └──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘  │
└─────────┼──────────────┼──────────────┼──────────────┼──────────┘
          │              │              │              │
          └──────────────┴──────┬───────┴──────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────┐
│                         数据存储层                               │
│  ┌──────────────┬──────────────┼──────────────┬──────────────┐  │
│  │ PostgreSQL   │ 本地文件      │   Mock数据   │ 外部API      │  │
│  │ (主数据库)    │ (GeoJSON等)  │   (降级用)   │ (WHO等)      │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 路由模块分布

| 模块文件 | 路由前缀 | 接口数量 | 功能定位 |
|----------|----------|----------|----------|
| `marco.py` | `/api/v1/marco` | 10 | 宏观分析数据总线 |
| `meso.py` | `/api/v1/meso` | 6 | 中观分析数据总线 |
| `micro.py` | `/api/v1/micro` | 7 | 微观分析计算引擎 |
| `prediction.py` | `/api/v1/prediction` | 3 | 预测引擎路由 |

---

## 二、完整Path路径分析

### 2.1 宏观分析路由 (Marco)

**文件**: [`routes/marco.py`](file:///d:/python_HIS/pythonProject/多源健康数据驱动的疾病谱系与资源适配分析/Health_Imformation_Systeam/routes/marco.py)

#### 2.1.1 路径清单

| 序号 | 完整Path | 方法 | 功能模块 | 处理函数 |
|------|----------|------|----------|----------|
| 1 | `/api/v1/marco/map/global-risk` | GET | 全球风险地图 | `get_global_risk_map()` |
| 2 | `/api/v1/marco/map/global-life-expectancy` | GET | 全球预期寿命 | `get_global_life_expectancy()` |
| 3 | `/api/v1/marco/map/china-provincial-health` | GET | 中国省级健康 | `get_china_provincial_health()` |
| 4 | `/api/v1/marco/map/chengdu-e2sfca` | GET | 成都E2SFCA | `get_chengdu_e2sfca()` |
| 5 | `/api/v1/marco/map/world-metrics` | GET | 世界地图指标 | `get_world_map_metrics()` |
| 6 | `/api/v1/marco/geojson/world` | GET | 世界GeoJSON | `get_world_geojson()` |
| 7 | `/api/v1/marco/geojson/continents` | GET | 大洲GeoJSON | `get_continents_geojson()` |
| 8 | `/api/v1/marco/geojson/china` | GET | 中国GeoJSON | `get_china_geojson()` |
| 9 | `/api/v1/marco/regions` | GET | 可用区域列表 | `get_available_regions()` |
| 10 | `/api/v1/marco/metrics` | GET | 可用指标列表 | `get_available_metrics()` |

#### 2.1.2 请求处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    /api/v1/marco/map/world-metrics              │
│                         请求处理流程                             │
└─────────────────────────────────────────────────────────────────┘

1. 请求接收
   ├─ URL: /api/v1/marco/map/world-metrics?region=global&metric=dalys&year=2024
   ├─ 方法: GET
   └─ 参数: region, metric, year

2. 参数验证与标准化
   ├─ region_key = region.strip().lower()  → "global"
   ├─ metric_key = metric.strip().lower()  → "dalys"
   └─ target_year = int(year or 2024)      → 2024

3. 数据库查询
   ├─ 构建SQL查询条件
   │   ├─ 指标匹配: indicator ILIKE '%daly%'
   │   ├─ 年份范围: year >= 2009 AND year <= 2024
   │   └─ 非空过滤: region IS NOT NULL, value IS NOT NULL
   └─ 执行查询: db.query(GlobalHealthMetric).filter(...).all()

4. 数据处理
   ├─ 标准化国家名称: _normalize_country_key()
   ├─ 数据源优先级排序: _source_priority()
   │   ├─ 国际来源: 0 (WHO/OWID/GBD等)
   │   ├─ 本地来源: 1
   │   └─ 其他: 2
   └─ 缺失数据回退: _calc_reproducible_map_fallback()

5. 响应构建
   ├─ 状态: "success" / "error"
   ├─ 数据: payload[]
   └─ 元数据: meta{count, fallback, priority}

6. 返回响应
   └─ JSONResponse
```

#### 2.1.3 权限控制策略

| 控制点 | 策略 | 实现方式 |
|--------|------|----------|
| 认证 | 暂无 | 预留 TODO |
| 授权 | 公开访问 | 无限制 |
| 限流 | 暂无 | 需添加 |
| 缓存 | 30天 | Cache-Control头 |

**设计考量**:
- 当前所有宏观接口均为公开访问，未实现认证机制
- GeoJSON文件设置长期缓存(30天)，减少磁盘IO
- 建议在请求拦截器中添加API Key认证

#### 2.1.4 上下游关联

```
上游调用方:
  └─ frontend/use/macro-analysis.html
      ├─ 页面加载时调用: /map/world-metrics, /geojson/world
      └─ 筛选变更时调用: /map/world-metrics

下游依赖:
  ├─ db/models/GlobalHealthMetric (数据库模型)
  ├─ utils/global_risk.py (全球风险计算)
  ├─ utils/global_life_expectancy.py (预期寿命计算)
  ├─ utils/china_provincial_health.py (省级健康数据)
  ├─ utils/chengdu_e2sfca.py (空间可及性)
  └─ config/settings.py (配置信息)
```

---

### 2.2 中观分析路由 (Meso)

**文件**: [`routes/meso.py`](file:///d:/python_HIS/pythonProject/多源健康数据驱动的疾病谱系与资源适配分析/Health_Imformation_Systeam/routes/meso.py)

#### 2.2.1 路径清单

| 序号 | 完整Path | 方法 | 功能模块 | 处理函数 |
|------|----------|------|----------|----------|
| 1 | `/api/v1/meso/dashboard` | GET | 中观仪表板 | `get_meso_dashboard()` |
| 2 | `/api/v1/meso/countries` | GET | 国家列表 | `get_available_countries()` |
| 3 | `/api/v1/meso/compare` | GET | 国家对比 | `compare_countries()` |
| 4 | `/api/v1/meso/stages` | GET | 疾病转型阶段 | `get_disease_transition_stages()` |
| 5 | `/api/v1/meso/country-data` | GET | 国家详细数据 | `get_country_data()` |

#### 2.2.2 请求处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    /api/v1/meso/dashboard                       │
│                         请求处理流程                             │
└─────────────────────────────────────────────────────────────────┘

1. 请求接收
   ├─ URL: /api/v1/meso/dashboard?region=China
   ├─ 方法: GET
   └─ 参数: region (支持中英文)

2. 地区名称标准化
   ├─ 输入: "中国" / "china" / "China"
   └─ 标准化: REGION_ALIASES 映射 → "China"

3. 数据获取
   ├─ MESO_BASELINE_DATA["China"] (内存数据)
   │   ├─ life_expectancy, ncd_ratio
   │   ├─ doctor_density, efficiency_score
   │   └─ bed_density, expenditure_gdp_ratio
   └─ 疾病转型数据生成: get_transition_data()
       ├─ 当前阶段: "慢性病快速上升"
       ├─ 历史趋势: ncd_series[], infectious_series[]
       └─ ECharts配置: series[]

4. 动态结论生成
   └─ generate_conclusions()
       ├─ 基于指标值生成自然语言描述
       └─ 根据效率评分添加建议

5. 响应构建
   └─ MesoDashboardResponse 模型验证
```

#### 2.2.3 权限控制策略

| 控制点 | 策略 | 实现方式 |
|--------|------|----------|
| 认证 | 暂无 | 预留 TODO |
| 授权 | 公开访问 | 无限制 |
| 数据验证 | 自动回退 | 无效参数返回默认值 |

**设计考量**:
- 使用内存数据(MESO_BASELINE_DATA)而非数据库，响应速度快
- 支持中英文地区名称，提升用户体验
- 无效参数自动回退到默认值，避免前端报错

#### 2.2.4 上下游关联

```
上游调用方:
  └─ frontend/use/meso-analysis.html
      ├─ 页面加载: /dashboard?region=China
      ├─ 国家切换: /dashboard?region={country}
      └─ 对比功能: /compare?countries=China,Japan,USA

下游依赖:
  ├─ MESO_BASELINE_DATA (内存常量数据)
  ├─ COUNTRY_PROFILES (国家配置数据)
  ├─ DISEASE_TRANSITION_BASE (疾病转型数据)
  └─ DISEASE_TRANSITION_STAGES (阶段定义)
```

---

### 2.3 微观分析路由 (Micro)

**文件**: [`routes/micro.py`](file:///d:/python_HIS/pythonProject/多源健康数据驱动的疾病谱系与资源适配分析/Health_Imformation_Systeam/routes/micro.py)

#### 2.3.1 路径清单

| 序号 | 完整Path | 方法 | 功能模块 | 处理函数 |
|------|----------|------|----------|----------|
| 1 | `/api/v1/micro/risk-assessment` | GET | 风险评估 | `get_risk_assessment()` |
| 2 | `/api/v1/micro/spatial-poi` | GET | 空间POI | `get_spatial_poi()` |
| 3 | `/api/v1/micro/risk-factors` | GET | 风险因素列表 | `get_risk_factors()` |
| 4 | `/api/v1/micro/cities` | GET | 城市列表 | `get_available_cities()` |
| 5 | `/api/v1/micro/risk-simulation` | POST | 风险模拟 | `simulate_risk()` |
| 6 | `/api/v1/micro/trend-data` | GET | 趋势数据 | `get_trend_data()` |
| 7 | `/api/v1/micro/pois` | GET | POI列表 | `get_pois()` |

#### 2.3.2 请求处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│                  /api/v1/micro/risk-simulation                  │
│                         请求处理流程                             │
└─────────────────────────────────────────────────────────────────┘

1. 请求接收
   ├─ URL: /api/v1/micro/risk-simulation
   ├─ 方法: POST
   └─ 请求体:
       {
         "intensity": 0.3,
         "target_factor": "smoking"
       }

2. 请求体验证 (Pydantic模型)
   ├─ RiskSimulationRequest 自动验证
   │   ├─ intensity: 0.0-1.0 范围
   │   └─ target_factor: 必须在 BASE_PAF_DATA 中
   └─ 验证失败返回 400 Bad Request

3. PAF计算
   ├─ 遍历 BASE_PAF_DATA (8种风险因素)
   ├─ 目标因素干预计算:
   │   reduction = intensity * effectiveness
   │   current_paf = base_paf * (1 - reduction)
   └─ 其他因素保持基线值

4. 洞察生成
   ├─ 计算降幅: original - current
   ├─ 生成自然语言描述
   └─ 识别其他高风险因素

5. 响应构建
   └─ RiskSimulationResponse 模型验证
       {
         "status": "success",
         "paf_series": [...],
         "insights": [...]
       }
```

#### 2.3.3 权限控制策略

| 控制点 | 策略 | 实现方式 |
|--------|------|----------|
| 请求体验证 | Pydantic模型 | 自动参数校验 |
| 参数范围限制 | 装饰器验证 | `@field_validator` |
| 错误处理 | HTTPException | 400/500状态码 |

**设计考量**:
- 使用 Pydantic 模型进行严格的请求体验证
- PAF计算使用科学公式，确保结果准确性
- 返回 `is_improved` 标记便于前端可视化

#### 2.3.4 上下游关联

```
上游调用方:
  └─ frontend/use/micro-analysis.html
      ├─ 风险评估: /risk-assessment?smoking_reduction=30
      ├─ 模拟运行: /risk-simulation (POST)
      └─ 空间分析: /spatial-poi?city=Chengdu

下游依赖:
  ├─ BASE_PAF_DATA (8种风险因素基线数据)
  ├─ CHENGDU_HOSPITALS (成都医院POI数据)
  ├─ OTHER_CITIES_HOSPITALS (其他城市数据)
  ├─ TREND_DATA_MAP (标准化趋势数据)
  └─ STANDARD_YEARS (标准年份数组)
```

---

### 2.4 预测引擎路由 (Prediction)

**文件**: [`routes/prediction.py`](file:///d:/python_HIS/pythonProject/多源健康数据驱动的疾病谱系与资源适配分析/Health_Imformation_Systeam/routes/prediction.py)

#### 2.4.1 路径清单

| 序号 | 完整Path | 方法 | 功能模块 | 处理函数 |
|------|----------|------|----------|----------|
| 1 | `/api/v1/prediction/simulate` | POST | 干预模拟 | `simulate_future()` |
| 2 | `/api/v1/prediction/models` | GET | 模型列表 | `get_available_models()` |
| 3 | `/api/v1/prediction/baseline` | GET | 基线指标 | `get_baseline_metrics()` |

#### 2.4.2 请求处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│                  /api/v1/prediction/simulate                    │
│                         请求处理流程                             │
└─────────────────────────────────────────────────────────────────┘

1. 请求接收
   ├─ URL: /api/v1/prediction/simulate
   ├─ 方法: POST
   └─ 请求体:
       {
         "tobacco": 0.5,
         "salt": 0.3,
         "model_type": "Ensemble"
       }

2. 请求体验证 (SimulationRequest)
   ├─ tobacco: 0.0-1.0 (ge=0.0, le=1.0)
   ├─ salt: 0.0-1.0
   └─ model_type: 枚举验证

3. 干预影响计算 (PredictionEngine)
   ├─ impact = tobacco * 0.4 + salt * 0.3
   └─ 使用 NumPy 进行数值计算

4. 核心预测计算
   ├─ simulate_dalys(): 疾病负担模拟
   │   └─ reduction_rate = impact * 0.15
   ├─ simulate_life_expectancy(): 预期寿命模拟
   │   └─ life_boost = impact * 2.5
   └─ generate_prediction_curves(): 曲线数据生成
       └─ 基线路径 vs 干预路径

5. AI洞察生成
   └─ generate_ai_insight()
       ├─ 计算降幅百分比
       ├─ 根据干预措施生成建议
       └─ 返回自然语言分析

6. 响应构建
   └─ SimulationResponse 模型验证
```

#### 2.4.3 权限控制策略

| 控制点 | 策略 | 实现方式 |
|--------|------|----------|
| 参数验证 | Field约束 | `ge=0.0, le=1.0` |
| 模型校验 | 枚举验证 | 预定义模型列表 |
| 计算异常 | try-except | 500错误返回 |

**设计考量**:
- 使用 NumPy 保证数值计算精度
- 支持4种预测模型动态切换
- 返回完整的曲线数据供ECharts渲染

#### 2.4.4 上下游关联

```
上游调用方:
  └─ frontend/use/prediction.html
      ├─ 模拟运行: /simulate (POST)
      ├─ 模型选择: /models
      └─ 基线查看: /baseline

下游依赖:
  └─ PredictionEngine 类
      ├─ BASE_DALYS_2030 (基线疾病负担)
      ├─ BASE_LIFE_EXP (基线预期寿命)
      ├─ MODEL_PARAMS (模型参数配置)
      └─ NumPy 数值计算库
```

---

## 三、Path路径设计分析

### 3.1 URL设计规范

#### 3.1.1 路径结构

```
/api/v1/{module}/{resource}/{action}

示例:
/api/v1/marco/map/world-metrics
│     │     │    └─ 具体资源
│     │     └─ 资源类别
│     └─ 功能模块
└─ API版本
```

#### 3.1.2 设计规范评估

| 规范项 | 现状 | 建议 |
|--------|------|------|
| 版本控制 | ✅ 有版本号 /v1/ | 保持 |
| 模块划分 | ✅ 清晰 (marco/meso/micro/prediction) | 保持 |
| 资源命名 | ⚠️ 部分使用驼峰 | 统一使用kebab-case |
| 复数形式 | ✅ 使用复数 (countries, metrics) | 保持 |
| 动作表达 | ✅ 使用HTTP方法 | 保持 |

### 3.2 路径层级深度

| 层级 | 路径示例 | 数量 | 评价 |
|------|----------|------|------|
| 3级 | `/api/v1/marco/regions` | 5 | ✅ 简洁清晰 |
| 4级 | `/api/v1/marco/map/world-metrics` | 12 | ✅ 结构合理 |
| 5级 | 无 | 0 | - |

### 3.3 HTTP方法使用

| 方法 | 使用次数 | 使用场景 | 评价 |
|------|----------|----------|------|
| GET | 22 | 数据查询 | ✅ 符合REST规范 |
| POST | 3 | 模拟计算 | ✅ 符合REST规范 |
| PUT | 0 | - | ⚠️ 暂无更新操作 |
| DELETE | 0 | - | ⚠️ 暂无删除操作 |

---

## 四、权限控制策略分析

### 4.1 当前权限控制现状

| 路由模块 | 认证机制 | 授权机制 | 限流策略 |
|----------|----------|----------|----------|
| marco | ❌ 无 | 公开访问 | ❌ 无 |
| meso | ❌ 无 | 公开访问 | ❌ 无 |
| micro | ❌ 无 | 公开访问 | ❌ 无 |
| prediction | ❌ 无 | 公开访问 | ❌ 无 |

### 4.2 建议权限控制方案

```python
# 建议实现方案

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证JWT令牌"""
    token = credentials.credentials
    # 验证逻辑...
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌"
        )
    return user_info

# 应用到路由
@router.get("/dashboard", dependencies=[Depends(verify_token)])
async def get_meso_dashboard():
    ...
```

### 4.3 分级权限设计

| 接口级别 | 接口示例 | 建议权限 |
|----------|----------|----------|
| 公开接口 | `/geojson/world`, `/regions` | 无需认证 |
| 用户接口 | `/dashboard`, `/risk-assessment` | 需登录 |
| 管理接口 | `/admin/*` (预留) | 需管理员权限 |
| 计算密集型 | `/simulate` | 需配额/限流 |

---

## 五、上下游服务关联分析

### 5.1 完整调用链

```
┌─────────────────────────────────────────────────────────────────┐
│                        完整数据流向图                            │
└─────────────────────────────────────────────────────────────────┘

前端请求
    │
    ▼
┌─────────────────┐
│   Nginx (可选)   │ ← 静态文件服务、反向代理、负载均衡
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI 中台    │ ← 路由分发、参数验证、响应构建
│  - marco        │
│  - meso         │
│  - micro        │
│  - prediction   │
└────────┬────────┘
         │
    ┌────┴────┬─────────────┬─────────────┐
    ▼         ▼             ▼             ▼
┌────────┐ ┌────────┐  ┌──────────┐  ┌──────────┐
│PostgreSQL│ │本地文件 │  │ 内存数据  │  │ 计算引擎  │
│- 健康指标│ │- GeoJSON│  │- PAF基线 │  │- NumPy   │
│- 区域数据│ │- 配置  │  │- 国家配置 │  │- 预测模型 │
└────────┘ └────────┘  └──────────┘  └──────────┘
```

### 5.2 依赖关系矩阵

| 路由模块 | 数据库 | 文件系统 | 内存数据 | 计算库 | 外部API |
|----------|--------|----------|----------|--------|---------|
| marco | ✅ | ✅ GeoJSON | ⚠️ 回退数据 | ❌ | ⚠️ 预留 |
| meso | ❌ | ❌ | ✅ 全部 | ❌ | ❌ |
| micro | ❌ | ❌ | ✅ 全部 | ❌ | ❌ |
| prediction | ❌ | ❌ | ✅ 参数 | ✅ NumPy | ❌ |

### 5.3 服务解耦建议

#### 5.3.1 当前耦合问题

1. **数据与路由耦合**
   - MESO_BASELINE_DATA 直接定义在路由文件中
   - 不利于数据更新和维护

2. **计算逻辑与路由耦合**
   - PredictionEngine 定义在路由文件中
   - 不利于单元测试和复用

#### 5.3.2 解耦方案

```
建议目录结构:

routes/
├── __init__.py
├── marco.py          # 仅负责路由和参数处理
├── meso.py
├── micro.py
├── prediction.py
└── dependencies.py   # 依赖注入

services/
├── __init__.py
├── marco_service.py  # 业务逻辑
├── meso_service.py
├── micro_service.py
└── prediction_service.py

repositories/
├── __init__.py
├── health_metric_repo.py  # 数据访问
├── geojson_repo.py
└── mock_data_repo.py

data/
├── meso_baseline.json      # 数据文件
├── country_profiles.json
└── disease_transition.json
```

---

## 六、潜在优化点

### 6.1 路径优化

| 当前路径 | 建议路径 | 优化理由 |
|----------|----------|----------|
| `/map/world-metrics` | `/maps/world/metrics` | 更清晰的资源层级 |
| `/geojson/world` | `/maps/world/geojson` | 统一资源命名 |
| `/risk-simulation` | `/simulations/risk` | 动作转资源 |

### 6.2 性能优化

| 优化点 | 当前状态 | 建议方案 | 预期收益 |
|--------|----------|----------|----------|
| GeoJSON缓存 | 30天HTTP缓存 | CDN + 本地缓存 | 减少90%请求 |
| 数据库查询 | 每次请求查询 | 连接池 + 查询缓存 | 减少50%延迟 |
| PAF计算 | 实时计算 | 预计算 + 缓存 | 减少80%计算时间 |
| 预测曲线 | 每次生成 | 结果缓存 | 减少70%计算时间 |

### 6.3 安全优化

| 优化点 | 风险等级 | 建议方案 | 优先级 |
|--------|----------|----------|--------|
| 缺少认证 | 🔴 高 | 实现JWT认证 | P0 |
| 参数注入 | 🟡 中 | 加强参数验证 | P1 |
| 无请求限流 | 🟡 中 | 添加Rate Limit | P1 |
| 敏感信息泄露 | 🟢 低 | 日志脱敏 | P2 |

---

## 七、附录

### 7.1 完整Path列表

```
# 宏观分析 (Marco)
GET  /api/v1/marco/map/global-risk
GET  /api/v1/marco/map/global-life-expectancy
GET  /api/v1/marco/map/china-provincial-health
GET  /api/v1/marco/map/chengdu-e2sfca
GET  /api/v1/marco/map/world-metrics
GET  /api/v1/marco/geojson/world
GET  /api/v1/marco/geojson/continents
GET  /api/v1/marco/geojson/china
GET  /api/v1/marco/regions
GET  /api/v1/marco/metrics

# 中观分析 (Meso)
GET  /api/v1/meso/dashboard
GET  /api/v1/meso/countries
GET  /api/v1/meso/compare
GET  /api/v1/meso/stages
GET  /api/v1/meso/country-data

# 微观分析 (Micro)
GET  /api/v1/micro/risk-assessment
GET  /api/v1/micro/spatial-poi
GET  /api/v1/micro/risk-factors
GET  /api/v1/micro/cities
POST /api/v1/micro/risk-simulation
GET  /api/v1/micro/trend-data
GET  /api/v1/micro/pois

# 预测引擎 (Prediction)
POST /api/v1/prediction/simulate
GET  /api/v1/prediction/models
GET  /api/v1/prediction/baseline
```

### 7.2 路由注册代码

```python
# main.py 中的路由注册

from routes import marco_router, meso_router, micro_router, prediction_router

app.include_router(marco_router)      # prefix="/api/v1/marco"
app.include_router(meso_router)       # prefix="/api/v1/meso"
app.include_router(micro_router)      # prefix="/api/v1/micro"
app.include_router(prediction_router) # prefix="/api/v1/prediction"
```

## 八、Optional 字段与 None 值使用场景分析

### 8.1 设计模式概述

在中台接口设计中，`Optional[T] = None` 模式被广泛用于表示**可选字段**，这些字段在特定条件下可能没有值。这种设计模式体现了以下原则：

1. **可选性原则**: 非核心字段设为可选，提高接口灵活性
2. **降级策略**: 当数据不可用时返回 None 而非报错
3. **渐进式响应**: 核心数据必须返回，扩展数据可选返回

### 8.2 各模块 Optional 字段场景

#### 8.2.1 宏观分析模块 (Marco)

##### GeoJSONResponse 模型

**文件位置**: [`routes/marco.py#L45-49`](file:///d:/python_HIS/pythonProject/多源健康数据驱动的疾病谱系与资源适配分析/Health_Imformation_Systeam/routes/marco.py#L45-49)

```python
class GeoJSONResponse(BaseModel):
    """GeoJSON 响应模型"""
    status: str
    path: Optional[str] = None
    msg: Optional[str] = None
```

**场景说明**:

| 场景 | 触发条件 | path 值 | msg 值 | 实际返回值 |
|------|----------|---------|--------|------------|
| **场景1: 成功返回文件** | GeoJSON文件存在 | `None` (未使用) | `None` | `FileResponse` 直接返回文件内容 |
| **场景2: 文件不存在** | 主路径和fallback路径都不存在 | `None` | `"GeoJSON file not found"` | 空 FeatureCollection 或错误JSON |

**实际接口行为分析**:

```python
# /api/v1/marco/geojson/world 实际实现
@router.get("/geojson/world")
async def get_world_geojson():
    if os.path.exists(file_path):
        return FileResponse(file_path)  # ← 直接返回文件，不使用 GeoJSONResponse 模型
    return {"type": "FeatureCollection", "features": []}  # ← 返回 dict，非模型实例
```

**关键发现**:
- `GeoJSONResponse` 模型**定义了但未实际使用**
- 实际接口返回 `FileResponse` 或 `dict`，而非模型实例
- 这是**设计文档与实现不一致**的典型例子

**改进建议**:
```python
# 方案1: 统一返回模型（推荐）
@router.get("/geojson/world", response_model=GeoJSONResponse)
async def get_world_geojson():
    if os.path.exists(file_path):
        return GeoJSONResponse(
            status="success",
            path="/static/geojson/world.json",  # 返回可访问URL
            msg=None
        )
    return GeoJSONResponse(
        status="error",
        path=None,
        msg="GeoJSON file not found"
    )

# 方案2: 删除未使用的模型
# 如果保持当前实现，应删除 GeoJSONResponse 模型避免混淆
```

---

##### MapDataResponse 模型

**文件位置**: [`routes/marco.py#L52-56`](file:///d:/python_HIS/pythonProject/多源健康数据驱动的疾病谱系与资源适配分析/Health_Imformation_Systeam/routes/marco.py#L52-56)

```python
class MapDataResponse(BaseModel):
    """地图数据响应模型"""
    status: str
    data: Any
    msg: Optional[str] = None
```

**场景说明**:

| 场景 | 触发条件 | msg 值 | 使用示例 |
|------|----------|--------|----------|
| **成功响应** | 数据正常返回 | `None` | `{"status": "success", "data": {...}, "msg": None}` |
| **降级响应** | 使用fallback数据 | `"Using fallback data"` | `{"status": "success", "data": {...}, "msg": "Using fallback data"}` |
| **错误响应** | 数据获取失败 | 错误详情 | `{"status": "error", "data": [], "msg": "Database connection failed"}` |

---

#### 8.2.2 中观分析模块 (Meso)

##### MetricValue 模型

**文件位置**: [`routes/meso.py#L22-26`](file:///d:/python_HIS/pythonProject/多源健康数据驱动的疾病谱系与资源适配分析/Health_Imformation_Systeam/routes/meso.py#L22-26)

```python
class MetricValue(BaseModel):
    """指标值模型"""
    value: float
    trend: str
    unit: Optional[str] = None
```

**场景说明**:

| 场景 | 触发条件 | unit 值 | 示例 |
|------|----------|---------|------|
| **无量纲指标** | 效率评分、百分比等 | `None` | `{"value": 0.82, "trend": "+0.05", "unit": None}` |
| **有单位指标** | 人口、床位数等 | 具体单位 | `{"value": 1410, "trend": "+0.1", "unit": "百万"}` |

**设计考量**:
- 效率评分等无量纲指标不需要单位
- 保持模型一致性，避免空字符串 `""`
- 前端可通过 `unit ? `${value}${unit}` : value` 判断

---

##### CountryBaseline 模型

**文件位置**: [`routes/meso.py#L29-38`](file:///d:/python_HIS/pythonProject/多源健康数据驱动的疾病谱系与资源适配分析/Health_Imformation_Systeam/routes/meso.py#L29-38)

```python
class CountryBaseline(BaseModel):
    """国家基础数据模型"""
    life_expectancy: MetricValue
    ncd_ratio: MetricValue
    doctor_density: MetricValue
    efficiency_score: MetricValue
    bed_density: Optional[MetricValue] = None
    expenditure_gdp_ratio: Optional[MetricValue] = None
```

**场景说明**:

| 字段 | 可选性 | 触发条件 | 说明 |
|------|--------|----------|------|
| `life_expectancy` | 必填 | - | 核心指标 |
| `ncd_ratio` | 必填 | - | 核心指标 |
| `doctor_density` | 必填 | - | 核心指标 |
| `efficiency_score` | 必填 | - | 核心指标 |
| `bed_density` | **可选** | 部分国家数据缺失 | 床位密度 |
| `expenditure_gdp_ratio` | **可选** | 部分国家数据缺失 | 医疗支出占比 |

**示例数据**:

```python
# 完整数据（中国）
{
    "life_expectancy": {"value": 79.0, "trend": "+3.4", "unit": "岁"},
    "ncd_ratio": {"value": 89.4, "trend": "+12.3", "unit": "%"},
    "doctor_density": {"value": 2.99, "trend": "+1.1", "unit": "人/千人口"},
    "efficiency_score": {"value": 0.82, "trend": "+0.05", "unit": None},
    "bed_density": {"value": 7.1, "trend": "+0.8", "unit": "张/千人口"},  # 有值
    "expenditure_gdp_ratio": {"value": 5.6, "trend": "+0.3", "unit": "%"}  # 有值
}

# 部分缺失数据（某小国）
{
    "life_expectancy": {"value": 65.0, "trend": "+2.1", "unit": "岁"},
    "ncd_ratio": {"value": 45.2, "trend": "+8.5", "unit": "%"},
    "doctor_density": {"value": 0.5, "trend": "+0.1", "unit": "人/千人口"},
    "efficiency_score": {"value": 0.55, "trend": "+0.02", "unit": None},
    "bed_density": None,  # ← 数据缺失
    "expenditure_gdp_ratio": None  # ← 数据缺失
}
```

---

#### 8.2.3 微观分析模块 (Micro)

##### RiskFactor 模型

**文件位置**: [`routes/micro.py#L32-37`](file:///d:/python_HIS/pythonProject/多源健康数据驱动的疾病谱系与资源适配分析/Health_Imformation_Systeam/routes/micro.py#L32-37)

```python
class RiskFactor(BaseModel):
    """风险因素模型"""
    name: str
    value: float
    trend: str
    category: Optional[str] = None
```

**场景说明**:

| 场景 | 触发条件 | category 值 | 说明 |
|------|----------|-------------|------|
| **标准风险因素** | 有预定义分类 | 分类名称 | `"行为风险"`, `"代谢风险"`, `"环境风险"` |
| **自定义风险因素** | 用户添加 | `None` | 未分类的风险因素 |

---

##### POI 模型

**文件位置**: [`routes/micro.py#L71-77`](file:///d:/python_HIS\pythonProject\多源健康数据驱动的疾病谱系与资源适配分析\Health_Imformation_Systeam\routes\micro.py#L71-77)

```python
class POI(BaseModel):
    """兴趣点模型"""
    name: str
    coords: List[float]
    level: str
    capacity: int
    address: Optional[str] = None
```

**场景说明**:

| 场景 | 触发条件 | address 值 | 示例 |
|------|----------|------------|------|
| **完整信息** | 地址数据可用 | 详细地址 | `"成都市武侯区国学巷37号"` |
| **地址缺失** | 数据源无地址 | `None` | `None` |

**实际数据示例**:

```python
# 完整POI数据
{
    "name": "四川大学华西医院",
    "coords": [104.0632, 30.6418],
    "level": "三甲",
    "capacity": 4300,
    "address": "成都市武侯区国学巷37号"  # 有地址
}

# 地址缺失的POI
{
    "name": "某社区诊所",
    "coords": [104.0500, 30.6500],
    "level": "社区",
    "capacity": 50,
    "address": None  # 地址未知
}
```

---

##### SpatialPOIResponse 模型

**文件位置**: [`routes/micro.py#L80-86`](file:///d:/python_HIS\pythonProject\多源健康数据驱动的疾病谱系与资源适配分析\Health_Imformation_Systeam\routes\micro.py#L80-86)

```python
class SpatialPOIResponse(BaseModel):
    """空间 POI 响应模型"""
    status: str
    city: str
    pois: List[POI]
    accessibility_heatmap: Optional[str] = None
    grid_size: Optional[int] = None
```

**场景说明**:

| 字段 | 可选性 | 触发条件 | 说明 |
|------|--------|----------|------|
| `status` | 必填 | - | 响应状态 |
| `city` | 必填 | - | 城市名称 |
| `pois` | 必填 | - | POI列表 |
| `accessibility_heatmap` | **可选** | 热力图数据未生成 | 可及性热力图URL或base64 |
| `grid_size` | **可选** | 未使用网格分析 | 网格大小（米） |

**响应示例**:

```python
# 完整响应（含热力图）
{
    "status": "success",
    "city": "Chengdu",
    "pois": [...],
    "accessibility_heatmap": "data:image/png;base64,iVBORw0KGgo...",  # 有热力图
    "grid_size": 1000
}

# 简化响应（无热力图）
{
    "status": "success",
    "city": "Chengdu",
    "pois": [...],
    "accessibility_heatmap": None,  # 未生成热力图
    "grid_size": None
}
```

---

##### 查询参数中的 None

**文件位置**: [`routes/micro.py#L382-383`](file:///d:/python_HIS\pythonProject\多源健康数据驱动的疾病谱系与资源适配分析\Health_Imformation_Systeam\routes\micro.py#L382-383)

```python
@router.get("/spatial-poi")
async def get_spatial_poi(
    city: str = "Chengdu",
    level: Optional[str] = None,        # 可选筛选条件
    min_capacity: Optional[int] = None  # 可选筛选条件
) -> Dict[str, Any]:
```

**场景说明**:

| 参数 | 默认值 | 使用场景 | 示例URL |
|------|--------|----------|---------|
| `city` | `"Chengdu"` | 指定城市 | `/spatial-poi?city=Beijing` |
| `level` | `None` | 筛选医院等级 | `/spatial-poi?level=三甲` |
| `min_capacity` | `None` | 筛选最小床位数 | `/spatial-poi?min_capacity=1000` |

**逻辑处理**:

```python
async def get_spatial_poi(city: str = "Chengdu", level: Optional[str] = None, ...):
    hospitals = get_hospitals_by_city(city)
    
    # 当 level 不为 None 时进行筛选
    if level is not None:
        hospitals = [h for h in hospitals if h["level"] == level]
    
    # 当 min_capacity 不为 None 时进行筛选
    if min_capacity is not None:
        hospitals = [h for h in hospitals if h["capacity"] >= min_capacity]
    
    return {"status": "success", "pois": hospitals}
```

---

### 8.3 None 值使用最佳实践

#### 8.3.1 使用原则

| 原则 | 说明 | 示例 |
|------|------|------|
| **区分 None 与空字符串** | None 表示"无值"，空字符串表示"空值" | `address: None` vs `address: ""` |
| **区分 None 与默认值** | None 触发不同逻辑，默认值是有效值 | `level: None` (不筛选) vs `level: "全部"` |
| **文档化可选字段** | 明确说明何时为 None | 字段注释 + 文档说明 |

#### 8.3.2 前端处理建议

```javascript
// 处理可能为 None 的字段
const displayAddress = poi.address ?? "地址未知";  // 使用空值合并运算符
const displayUnit = metric.unit ? `${metric.value}${metric.unit}` : metric.value;

// 条件渲染
{hospital.bed_density && (
    <div>床位密度: {hospital.bed_density.value} {hospital.bed_density.unit}</div>
)}
```

#### 8.3.3 后端处理建议

```python
# 使用 pydantic 的 Field 添加说明
from pydantic import Field

class POI(BaseModel):
    address: Optional[str] = Field(
        default=None,
        description="医院地址，当数据源无地址信息时为 None"
    )
```

---

### 8.4 设计问题与改进建议

#### 8.4.1 当前问题

| 问题 | 涉及模型 | 影响 |
|------|----------|------|
| 模型定义与实现不一致 | `GeoJSONResponse` | 模型未实际使用，造成混淆 |
| 缺少字段说明 | 多个模型 | 前端无法判断 None 的具体含义 |
| 错误处理不统一 | `MapDataResponse` | 部分返回 None，部分返回错误消息 |

#### 8.4.2 改进建议

1. **统一响应模型使用**
   ```python
   # 删除未使用的模型或统一使用
   @router.get("/geojson/world", response_model=GeoJSONResponse)
   async def get_world_geojson():
       ...
   ```

2. **添加字段文档**
   ```python
   class MetricValue(BaseModel):
       unit: Optional[str] = Field(
           default=None,
           description="指标单位，无量纲指标为 None"
       )
   ```

3. **标准化错误响应**
   ```python
   class ErrorResponse(BaseModel):
       status: str = "error"
       code: str  # 错误代码
       message: str  # 错误消息
       details: Optional[Dict] = None  # 详细错误信息
   ```

---

### 8.5 None 值场景汇总表

| 模块 | 模型/字段 | 场景 | None 含义 | 前端处理建议 |
|------|-----------|------|-----------|--------------|
| Marco | `GeoJSONResponse.path` | 文件直接返回 | 不适用 | 忽略此字段 |
| Marco | `GeoJSONResponse.msg` | 成功响应 | 无错误 | 不显示消息 |
| Marco | `MapDataResponse.msg` | 成功响应 | 无附加消息 | 不显示消息 |
| Meso | `MetricValue.unit` | 无量纲指标 | 无单位 | 仅显示数值 |
| Meso | `CountryBaseline.bed_density` | 数据缺失 | 该指标不可用 | 隐藏或显示"N/A" |
| Micro | `RiskFactor.category` | 未分类 | 无预定义分类 | 显示"未分类" |
| Micro | `POI.address` | 地址未知 | 数据源无地址 | 显示"地址未知" |
| Micro | `SpatialPOIResponse.accessibility_heatmap` | 未生成热力图 | 功能未启用 | 不显示热力图 |
| Micro | `SpatialPOIResponse.grid_size` | 未使用网格 | 分析粒度不适用 | 不显示网格信息 |
| Micro | 查询参数 `level` | 不筛选等级 | 返回所有等级 | 显示全部医院 |
| Micro | 查询参数 `min_capacity` | 不筛选容量 | 返回所有容量 | 显示全部医院 |

---

### 7.3 接口版本演进规划

| 版本 | 计划时间 | 主要变更 |
|------|----------|----------|
| v1 | 当前 | 基础功能 |
| v1.1 | +1个月 | 添加认证、限流 |
| v2 | +3个月 | 路径规范化、GraphQL支持 |
| v3 | +6个月 | 微服务拆分、gRPC支持 |

---

**报告结束**
