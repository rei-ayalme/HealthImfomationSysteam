# 前端模块数据接口调用分析报告

## 报告概述

**生成日期**: 2026-04-17  
**分析范围**: Health_Imformation_Systeam/frontend 目录下所有HTML页面  
**API基础URL**: `/api/v1/`  
**总接口数量**: 25个  

---

## 一、接口调用总览

### 1.1 接口分类统计

| 分类 | 接口数量 | 占比 | 说明 |
|------|----------|------|------|
| 宏观分析 (Marco) | 10 | 40% | 全球/国家/区域尺度数据 |
| 中观分析 (Meso) | 6 | 24% | 国家对比与疾病转型分析 |
| 微观分析 (Micro) | 7 | 28% | 风险评估与空间可及性 |
| 预测引擎 (Prediction) | 3 | 12% | 动态干预模拟与预测 |

### 1.2 请求方法分布

```
GET  ████████████████████████████████████  22个 (88%)
POST ███                                    3个 (12%)
```

---

## 二、详细接口清单

### 2.1 宏观分析接口 (Marco)

#### 2.1.1 地图数据接口

| 序号 | 接口名称 | 请求方法 | 完整路径 | 使用页面 | 调用频率 |
|------|----------|----------|----------|----------|----------|
| 1 | 全球风险地图 | GET | `/api/v1/marco/map/global-risk` | macro-analysis.html | 页面加载时 |
| 2 | 全球预期寿命 | GET | `/api/v1/marco/map/global-life-expectancy` | macro-analysis.html | 页面加载时 |
| 3 | 中国省级健康 | GET | `/api/v1/marco/map/china-provincial-health` | macro-analysis.html | 页面加载时 |
| 4 | 成都E2SFCA | GET | `/api/v1/marco/map/chengdu-e2sfca` | macro-analysis.html | 按需调用 |
| 5 | 世界地图指标 | GET | `/api/v1/marco/map/world-metrics` | macro-analysis.html | 筛选变更时 |

**请求参数**:

| 接口 | 参数名 | 类型 | 必填 | 默认值 | 说明 |
|------|--------|------|------|--------|------|
| world-metrics | region | string | 否 | "global" | 区域名称 |
| world-metrics | metric | string | 否 | "dalys" | 指标类型 |
| world-metrics | year | int | 否 | 2024 | 目标年份 |

**响应数据结构**:

```json
{
  "status": "success",
  "region": "global",
  "metric": "dalys",
  "year": 2024,
  "data": [
    {
      "country": "China",
      "value": 62.5,
      "indicator": "DALYs",
      "data_year": 2024,
      "source": "WHO",
      "source_type": "international",
      "method": "international_priority",
      "is_fallback": false
    }
  ],
  "meta": {
    "count": 195,
    "fallback": "reproducible_fallback_v1",
    "priority": "international>local>fallback"
  }
}
```

#### 2.1.2 GeoJSON数据接口

| 序号 | 接口名称 | 请求方法 | 完整路径 | 使用页面 | 调用频率 |
|------|----------|----------|----------|----------|----------|
| 6 | 世界地图GeoJSON | GET | `/api/v1/marco/geojson/world` | macro-analysis.html | 页面加载时 |
| 7 | 大洲地图GeoJSON | GET | `/api/v1/marco/geojson/continents` | macro-analysis.html | 按需调用 |
| 8 | 中国地图GeoJSON | GET | `/api/v1/marco/geojson/china` | macro-analysis.html, micro-analysis.html | 页面加载时 |

**响应数据结构**:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "China",
        "id": "CHN"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [...]
      }
    }
  ]
}
```

**设计考量**: 
- 使用 `FileResponse` 直接返回文件，减少内存占用
- 设置 `Cache-Control: public, max-age=2592000` 实现30天缓存
- 失败时返回空 FeatureCollection 避免前端报错

#### 2.1.3 元数据接口

| 序号 | 接口名称 | 请求方法 | 完整路径 | 使用页面 | 调用频率 |
|------|----------|----------|----------|----------|----------|
| 9 | 可用区域列表 | GET | `/api/v1/marco/regions` | macro-analysis.html | 页面加载时 |
| 10 | 可用指标列表 | GET | `/api/v1/marco/metrics` | macro-analysis.html | 页面加载时 |

---

### 2.2 中观分析接口 (Meso)

#### 2.2.1 仪表板数据接口

| 序号 | 接口名称 | 请求方法 | 完整路径 | 使用页面 | 调用频率 |
|------|----------|----------|----------|----------|----------|
| 1 | 中观仪表板 | GET | `/api/v1/meso/dashboard` | meso-analysis.html | 页面加载/切换国家时 |
| 2 | 国家数据详情 | GET | `/api/v1/meso/country-data` | meso-analysis.html | 详情查看时 |

**请求参数**:

| 接口 | 参数名 | 类型 | 必填 | 默认值 | 说明 |
|------|--------|------|------|--------|------|
| dashboard | region | string | 否 | "China" | 支持中英文 |
| country-data | country | string | 否 | "china" | 国家代码 |

**响应数据结构** (dashboard):

```json
{
  "status": "success",
  "region": "China",
  "stats": {
    "life_expectancy": {"value": 79.0, "trend": "+3.4", "unit": "岁"},
    "ncd_ratio": {"value": 89.4, "trend": "+12.3", "unit": "%"},
    "doctor_density": {"value": 2.99, "trend": "+1.1", "unit": "人/千人口"},
    "efficiency_score": {"value": 0.82, "trend": "+0.05", "unit": "分"}
  },
  "transition_chart": {
    "stages": ["感染性疾病主导", "慢性病快速上升", "退行性疾病主导"],
    "current_stage": "慢性病快速上升",
    "series": [
      {"name": "NCDs", "data": [40, 60, 75, 89.4], "type": "line"},
      {"name": "传染病", "data": [55, 35, 22, 10.6], "type": "line"}
    ]
  },
  "conclusions": [...],
  "peers": ["Japan", "South Korea", "Thailand", "Brazil"]
}
```

**设计考量**:
- 统一返回带单位的指标值，前端无需格式化
- `trend` 字段直接显示变化趋势（如 "+3.4"）
- `transition_chart` 直接适配 ECharts 配置

#### 2.2.2 国家管理接口

| 序号 | 接口名称 | 请求方法 | 完整路径 | 使用页面 | 调用频率 |
|------|----------|----------|----------|----------|----------|
| 3 | 国家列表 | GET | `/api/v1/meso/countries` | meso-analysis.html | 页面加载时 |
| 4 | 国家对比 | GET | `/api/v1/meso/compare` | meso-analysis.html | 对比操作时 |
| 5 | 疾病转型阶段 | GET | `/api/v1/meso/stages` | meso-analysis.html | 页面加载时 |

**请求参数** (compare):

| 参数名 | 类型 | 必填 | 示例值 |
|--------|------|------|--------|
| countries | string | 是 | "China,Japan,USA" |

---

### 2.3 微观分析接口 (Micro)

#### 2.3.1 风险评估接口

| 序号 | 接口名称 | 请求方法 | 完整路径 | 使用页面 | 调用频率 |
|------|----------|----------|----------|----------|----------|
| 1 | 风险评估 | GET | `/api/v1/micro/risk-assessment` | micro-analysis.html | 参数调整时 |
| 2 | 风险因素列表 | GET | `/api/v1/micro/risk-factors` | micro-analysis.html | 页面加载时 |
| 3 | 风险模拟 | POST | `/api/v1/micro/risk-simulation` | micro-analysis.html | 模拟运行时 |
| 4 | 趋势数据 | GET | `/api/v1/micro/trend-data` | micro-analysis.html | 图表加载时 |

**请求参数** (risk-assessment):

| 参数名 | 类型 | 必填 | 默认值 | 范围 |
|--------|------|------|--------|------|
| smoking_reduction | float | 否 | 0.0 | 0-100 |
| hypertension_control | float | 否 | 0.0 | 0-100 |
| diabetes_control | float | 否 | 0.0 | 0-100 |

**请求体** (risk-simulation):

```json
{
  "intensity": 0.3,
  "target_factor": "smoking"
}
```

**响应数据结构** (risk-simulation):

```json
{
  "status": "success",
  "paf_series": [
    {"name": "吸烟", "value": 17.4, "original": 24.8, "is_improved": true},
    {"name": "高血压", "value": 27.5, "original": 27.5, "is_improved": false}
  ],
  "insights": [
    "当前干预强度(30%)下，吸烟归因负担从 24.8% 降至 17.4%..."
  ],
  "intervention_intensity": 0.3,
  "target_factor": "smoking"
}
```

**设计考量**:
- PAF (Population Attributable Fraction) 计算在后端完成
- 支持8种风险因素动态干预模拟
- 返回 `is_improved` 标记便于前端高亮显示

#### 2.3.2 空间分析接口

| 序号 | 接口名称 | 请求方法 | 完整路径 | 使用页面 | 调用频率 |
|------|----------|----------|----------|----------|----------|
| 5 | 空间POI | GET | `/api/v1/micro/spatial-poi` | micro-analysis.html | 地图加载时 |
| 6 | 城市列表 | GET | `/api/v1/micro/cities` | micro-analysis.html | 页面加载时 |
| 7 | POI列表 | GET | `/api/v1/micro/pois` | micro-analysis.html | 按需调用 |

**请求参数** (spatial-poi):

| 参数名 | 类型 | 必填 | 默认值 |
|--------|------|------|--------|
| city | string | 否 | "Chengdu" |

**响应数据结构** (spatial-poi):

```json
{
  "status": "success",
  "city": "Chengdu",
  "pois": [
    {
      "name": "四川大学华西医院",
      "coords": [104.0632, 30.6418],
      "level": "三甲",
      "capacity": 4300,
      "address": "成都市武侯区国学巷37号"
    }
  ],
  "grid_size": 1000
}
```

---

### 2.4 预测引擎接口 (Prediction)

#### 2.4.1 模拟预测接口

| 序号 | 接口名称 | 请求方法 | 完整路径 | 使用页面 | 调用频率 |
|------|----------|----------|----------|----------|----------|
| 1 | 干预模拟 | POST | `/api/v1/prediction/simulate` | prediction.html | 模拟运行时 |
| 2 | 模型列表 | GET | `/api/v1/prediction/models` | prediction.html | 页面加载时 |
| 3 | 基线指标 | GET | `/api/v1/prediction/baseline` | prediction.html | 页面加载时 |

**请求体** (simulate):

```json
{
  "tobacco": 0.5,
  "salt": 0.3,
  "model_type": "Ensemble"
}
```

**参数验证规则**:
- `tobacco`: 0.0-1.0 之间
- `salt`: 0.0-1.0 之间
- `model_type`: "Ensemble" | "SDE" | "BAPC" | "DeepAnalyze"

**响应数据结构**:

```json
{
  "status": "success",
  "metrics": {
    "dalys_2030": {"value": 28.5, "unit": "亿", "change": "-6.0%"},
    "life_exp_2030": {"value": 78.8, "unit": "岁", "change": "+1.5"}
  },
  "curves": {
    "years": ["2024", "2025", ..., "2035"],
    "baseline": [28.0, 28.3, ...],
    "intervention": [28.0, 28.1, ...]
  },
  "ai_insight": "基于Ensemble模拟：当前干预组合预计可使2030年疾病负担降低至28.5亿..."
}
```

**设计考量**:
- 使用 NumPy 进行数值计算保证精度
- 返回 `change` 字段直接显示变化幅度
- `ai_insight` 提供自然语言分析结论

---

## 三、前端API调用方式分析

### 3.1 调用方式统计

| 调用方式 | 使用次数 | 占比 | 使用场景 |
|----------|----------|------|----------|
| `fetch()` 原生 | 15 | 60% | 简单GET请求 |
| `api.js` 封装 | 8 | 32% | 需要统一错误处理 |
| `axios` 直接 | 2 | 8% | 复杂请求配置 |

### 3.2 api.js 封装分析

**文件位置**: `frontend/assets/js/api.js`

**核心功能**:
1. **请求拦截器**: 自动添加请求日志
2. **响应拦截器**: 统一处理中台标准响应格式
3. **错误处理**: 使用 SweetAlert2 显示友好错误提示
4. **API方法封装**: 提供常用接口的便捷调用

**可用API方法**:

```javascript
window.API = {
  getDiseasePrediction(region, years),      // 疾病预测
  getSpatialAnalysis(region, radius, level), // 空间分析
  getHealthMetric(metric, region),           // 健康指标
  getGlobalHealthData(region),               // 全球健康数据
  get(endpoint, params),                     // 通用GET
  post(endpoint, data)                       // 通用POST
}
```

**使用示例**:

```javascript
// 使用封装的API
const data = await API.getSpatialAnalysis('Chengdu', 5, 'district');

// 使用原生fetch
const response = await fetch('/api/v1/micro/trend-data?type=hypertension');
const data = await response.json();
```

---

## 四、接口使用场景与调用频率

### 4.1 页面级调用矩阵

| 页面 | 核心接口 | 调用时机 | 调用次数/页 |
|------|----------|----------|-------------|
| macro-analysis.html | `/map/world-metrics` | 筛选变更 | 1-3次 |
| macro-analysis.html | `/geojson/world` | 页面加载 | 1次 |
| meso-analysis.html | `/meso/dashboard` | 国家切换 | 1-5次 |
| meso-analysis.html | `/meso/compare` | 对比操作 | 1-2次 |
| micro-analysis.html | `/micro/risk-simulation` | 模拟运行 | 1-10次 |
| micro-analysis.html | `/micro/spatial-poi` | 地图加载 | 1次 |
| prediction.html | `/prediction/simulate` | 模拟运行 | 1-5次 |

### 4.2 高频调用接口 TOP 5

| 排名 | 接口路径 | 预估日调用量 | 优化建议 |
|------|----------|--------------|----------|
| 1 | `/api/v1/micro/risk-simulation` | 500+ | 增加防抖，本地缓存结果 |
| 2 | `/api/v1/meso/dashboard` | 300+ | 启用浏览器缓存 |
| 3 | `/api/v1/prediction/simulate` | 200+ | WebSocket实时推送 |
| 4 | `/api/v1/marco/map/world-metrics` | 150+ | CDN缓存GeoJSON |
| 5 | `/api/v1/micro/trend-data` | 100+ | 数据预加载 |

---

## 五、潜在问题与优化建议

### 5.1 现存问题

| 问题 | 影响 | 涉及接口 |
|------|------|----------|
| 部分接口仍使用原生fetch | 错误处理不统一 | `/geojson/*` |
| 无请求防抖 | 高频操作导致服务器压力 | `/risk-simulation` |
| 缺少缓存策略 | 重复请求浪费带宽 | `/dashboard`, `/world-metrics` |
| 响应格式不一致 | 前端处理复杂 | `/geojson/world` 返回文件而非JSON |

### 5.2 优化建议

#### 5.2.1 短期优化 (1-2周)

1. **统一API调用方式**
   ```javascript
   // 建议统一使用api.js封装
   const data = await API.get('/marco/map/world-metrics', {region: 'global'});
   ```

2. **增加请求防抖**
   ```javascript
   // 对高频接口增加lodash debounce
   const debouncedSimulate = _.debounce(runSimulation, 300);
   ```

3. **启用浏览器缓存**
   ```javascript
   // 对静态数据使用localStorage缓存
   const cacheKey = `meso_dashboard_${region}`;
   const cached = localStorage.getItem(cacheKey);
   ```

#### 5.2.2 中期优化 (1个月)

1. **实现接口版本控制**
   - 在URL中包含版本号: `/api/v2/meso/dashboard`
   - 支持多版本并存

2. **增加批量请求接口**
   ```
   POST /api/v1/batch
   {
     "requests": [
       {"url": "/meso/dashboard", "method": "GET"},
       {"url": "/micro/risk-factors", "method": "GET"}
     ]
   }
   ```

3. **GraphQL支持**
   - 前端按需获取字段
   - 减少数据传输量

#### 5.2.3 长期优化 (3个月)

1. **WebSocket实时数据**
   - 预测模拟进度实时推送
   - 风险模拟结果流式返回

2. **Service Worker缓存**
   - 离线访问支持
   - 智能缓存策略

---

## 六、附录

### 6.1 接口完整路径列表

```
# 宏观分析
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

# 中观分析
GET  /api/v1/meso/dashboard
GET  /api/v1/meso/countries
GET  /api/v1/meso/compare
GET  /api/v1/meso/stages
GET  /api/v1/meso/country-data

# 微观分析
GET  /api/v1/micro/risk-assessment
GET  /api/v1/micro/spatial-poi
GET  /api/v1/micro/risk-factors
GET  /api/v1/micro/cities
POST /api/v1/micro/risk-simulation
GET  /api/v1/micro/trend-data
GET  /api/v1/micro/pois

# 预测引擎
POST /api/v1/prediction/simulate
GET  /api/v1/prediction/models
GET  /api/v1/prediction/baseline
```

### 6.2 响应状态码说明

| 状态码 | 含义 | 处理建议 |
|--------|------|----------|
| 200 | 成功 | 正常处理数据 |
| 400 | 参数错误 | 检查请求参数 |
| 404 | 接口不存在 | 检查URL路径 |
| 500 | 服务器错误 | 联系管理员 |
| 503 | 服务不可用 | 稍后重试 |

---

**报告结束**
