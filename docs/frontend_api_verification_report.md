# 前端应用数据获取方式验证报告

## 执行摘要

**验证日期**: 2026-04-14  
**验证范围**: Health_Imformation_Systeam/frontend 目录下所有前端代码文件  
**验证目标**: 确认前端是否通过真实API调用获取后端数据，而非使用硬编码或模拟数据

---

## 1. 验证方法论

### 1.1 代码审查方法
- 静态代码分析：检查所有JavaScript和HTML文件中的数据获取逻辑
- 模式匹配：搜索mock、模拟数据、硬编码数据等关键词
- 依赖分析：检查是否存在Mock Service Worker (MSW)、json-server等模拟工具
- API调用追踪：识别所有fetch、axios、XMLHttpRequest调用

### 1.2 检查的文件范围
- `frontend/assets/js/api.js` - 中台API封装模块
- `frontend/assets/js/data-service.js` - 数据服务模块
- `frontend/use/macro-analysis.html` - 宏观分析页面
- `frontend/use/meso-analysis.html` - 中观分析页面
- `frontend/use/micro-analysis.html` - 微观分析页面
- `frontend/use/prediction.html` - 预测分析页面
- `frontend/use/index.html` - 首页
- `frontend/admin/logs.html` - 日志页面

---

## 2. API基础设施分析

### 2.1 核心API模块 (api.js)

**位置**: `frontend/assets/js/api.js`

**架构设计**:
- 使用Axios创建专用实例 `middlePlatform`
- 基础URL配置: `http://127.0.0.1:8000/api`
- 超时设置: 15秒
- 实现了请求/响应拦截器

**暴露的API方法**:
```javascript
window.API = {
    getDiseasePrediction(region, years)     // GET /disease_simulation
    getSpatialAnalysis(region, radius, level) // GET /spatial_analysis
    getHealthMetric(metric, region)         // GET /health_metrics
    getGlobalHealthData(region)             // GET /global_health
    get(endpoint, params)                   // 通用GET
    post(endpoint, data)                    // 通用POST
}
```

**验证结果**: ✅ 所有方法均配置为向真实后端服务发起HTTP请求

### 2.2 数据服务模块 (data-service.js)

**位置**: `frontend/assets/js/data-service.js`

**架构设计**:
- 使用原生fetch API
- 动态检测环境设置baseURL
- 实现了5分钟数据缓存机制
- 支持缓存过期自动清理

**API端点映射**:
```javascript
// 数据集API
/api/dataset                    - 获取数据集列表
/api/dataset/{id}/detail        - 获取数据集详情

// 分析指标API
/api/analysis/metrics           - 获取分析指标
/api/chart/trend                - 获取趋势数据

// 地图数据API
/api/map/world-metrics          - 获取世界地图指标
/api/geojson/{world|china|chengdu|hospitals|continents} - 地理数据

// 预测分析API
/api/disease_simulation         - 疾病传播SDE预测
/api/spatial_analysis           - 空间可及性分析

// 新闻API
/api/news                       - 获取健康新闻

// 微观仿真API
/api/simulation/data            - 微观人群仿真数据
```

**验证结果**: ✅ 所有端点均指向真实后端API

---

## 3. 模拟数据实现分析

### 3.1 降级策略概述

系统在以下情况使用模拟数据作为**降级方案**:
1. 后端API服务不可用
2. 网络连接失败
3. 数据库为空或返回错误
4. 开发/测试环境

### 3.2 模拟数据位置与实现

#### 3.2.1 硬编码模拟数据 (分析页面)

**影响文件**:
- `macro-analysis.html` (第1074-1134行)
- `meso-analysis.html` (第2303-2361行)
- `micro-analysis.html` (第2386-2444行)
- `prediction.html` (第1961行起)

**实现方式**:
```javascript
// 前端兜底逻辑，当数据库为空或API失败时展示模拟数据
const mockData = {
    dalys: { value: 31542, trend: -1.2, sparkline: [32000, 31800, 31542, 31200, 31000] },
    top_disease: { name: "心血管疾病", ratio: 35.2 },
    dea: { value: 0.82, trend: 2.1, sparkline: [0.75, 0.78, 0.82, 0.84, 0.85] },
    prediction: { growth_rate: 2.3, target: "2030年控烟目标" }
};
```

**触发条件**:
```javascript
try {
    const data = await API.getHealthMetric('dalys');
    // 使用真实数据渲染
} catch (error) {
    // 错误已被api.js中的SweetAlert处理，这里只需调用兜底逻辑
    console.warn("中台指标加载失败，使用模拟数据", error);
    handleMetricsError(cardIds); // 使用mockData
}
```

#### 3.2.2 本地JSON模拟数据

**文件位置**: `frontend/assets/data/simulation_data.json`

**用途**: 微观人群仿真数据降级方案

**加载逻辑** (data-service.js 第254-267行):
```javascript
async _getLocalSimulationData(year) {
    try {
        const response = await fetch('/assets/data/simulation_data.json');
        const data = await response.json();
        return data[year] || data['2024'] || [];
    } catch (error) {
        console.error('[DataService] 加载本地模拟数据失败:', error);
        return [];
    }
}
```

**数据内容**: 包含2024年成都市人群仿真坐标数据，格式为 `[经度, 纬度, 状态]`

#### 3.2.3 中观分析页面随机数据

**位置**: `meso-analysis.html` (第1310行)

**实现**:
```javascript
// 模拟数据：如果是疾病负担，数值越大颜色越深（红）
let val = Math.floor(Math.random() * 60) + 40;
```

**用途**: 当GeoJSON加载成功但后端指标数据不可用时，生成随机颜色深度用于地图可视化

### 3.3 默认/兜底数据 (data-service.js)

**KPI数据兜底** (第305-314行):
```javascript
return {
    status: 'fallback',
    data: {
        totalRecords: 2847392,
        dataSources: 12,
        regions: 196,
        updateTime: new Date().toLocaleDateString('zh-CN')
    }
};
```

**仪表盘统计兜底** (第339-347行):
```javascript
return {
    status: 'fallback',
    stats: {
        totalData: 2847392,
        growthRate: 12.5,
        activeUsers: 1234,
        systemStatus: 'normal'
    }
};
```

---

## 4. 真实API调用验证

### 4.1 确认的API端点

| 端点 | 方法 | 用途 | 状态 |
|------|------|------|------|
| /api/disease_simulation | GET | 疾病预测 | ✅ 真实API |
| /api/spatial_analysis | GET | 空间分析 | ✅ 真实API |
| /api/health_metrics | GET | 健康指标 | ✅ 真实API |
| /api/global_health | GET | 全球健康数据 | ✅ 真实API |
| /api/dataset | GET | 数据集列表 | ✅ 真实API |
| /api/analysis/metrics | GET | 分析指标 | ✅ 真实API |
| /api/chart/trend | GET | 趋势数据 | ✅ 真实API |
| /api/map/world-metrics | GET | 世界地图指标 | ✅ 真实API |
| /api/geojson/* | GET | 地理JSON数据 | ✅ 真实API |
| /api/news | GET | 健康新闻 | ✅ 真实API |
| /api/simulation/data | GET | 仿真数据 | ✅ 真实API |

### 4.2 请求配置验证

**api.js请求配置**:
```javascript
const middlePlatform = axios.create({
    baseURL: 'http://127.0.0.1:8000/api',  // 指向真实后端服务
    timeout: 15000,
    headers: {
        'Content-Type': 'application/json'
    }
});
```

**data-service.js请求配置**:
```javascript
baseURL: 'http://localhost:8000'  // 开发环境
```

### 4.3 错误处理机制

**api.js错误处理**:
- HTTP 400: 请求参数错误
- HTTP 401: 身份验证失败
- HTTP 403: 权限不足
- HTTP 404: 接口不存在
- HTTP 408: 请求超时
- HTTP 500: 服务器内部错误
- HTTP 502: 网关错误
- HTTP 503: 服务不可用

**用户提示**: 使用SweetAlert2显示中文错误信息

---

## 5. 数据流分析

### 5.1 正常数据流

```
用户操作 → 页面JS → API.js/DataService → HTTP请求 → 后端服务
                                              ↓
页面渲染 ← 数据处理 ← 响应拦截器 ← HTTP响应 ← 后端数据库
```

### 5.2 降级数据流

```
用户操作 → 页面JS → API.js/DataService → HTTP请求 → 后端服务(失败)
                                              ↓
页面渲染 ← mockData/本地JSON ← catch错误处理 ← 网络/服务错误
```

---

## 6. 发现的问题与建议

### 6.1 问题清单

| 问题 | 严重程度 | 位置 | 描述 |
|------|----------|------|------|
| 硬编码模拟数据 | 中 | 4个分析页面 | API失败时显示固定模拟数据 |
| 随机数据生成 | 低 | meso-analysis.html | 地图颜色使用随机数 |
| 本地JSON依赖 | 低 | data-service.js | 仿真数据有本地JSON兜底 |
| 状态标识不清 | 中 | data-service.js | fallback状态可能误导用户 |

### 6.2 改进建议

#### 建议1: 明确标识模拟数据

**当前代码**:
```javascript
console.warn("中台指标加载失败，使用模拟数据", error);
```

**改进方案**:
```javascript
console.warn("[MOCK MODE] 后端API不可用，显示演示数据", error);
// UI添加明显标识
showMockDataIndicator(true);
```

#### 建议2: 添加模拟数据开关

**建议实现**:
```javascript
const CONFIG = {
    USE_MOCK_DATA: false,  // 生产环境设为false
    MOCK_DATA_TIMEOUT: 5000  // API超时时间
};
```

#### 建议3: 移除生产环境模拟数据

**建议步骤**:
1. 构建生产版本时删除/注释所有mockData代码块
2. 使用webpack/vite的条件编译
3. API失败时显示友好错误页面而非模拟数据

#### 建议4: 数据一致性验证

**建议实现**:
```javascript
// 添加数据校验中间件
function validateDataIntegrity(data, schema) {
    // 验证数据结构和来源
    if (!data._source || data._source !== 'api') {
        console.warn('数据可能来自非API源');
    }
}
```

---

## 7. 测试验证步骤

### 7.1 网络请求验证

1. 打开浏览器开发者工具 (F12)
2. 切换到 Network 标签
3. 刷新页面，观察以下请求:
   - `http://127.0.0.1:8000/api/*`
   - 请求方法: GET/POST
   - 响应状态: 200 OK
   - 响应内容: JSON格式数据

### 7.2 模拟数据触发验证

1. 停止后端服务
2. 刷新前端页面
3. 观察:
   - 控制台警告: "中台指标加载失败，使用模拟数据"
   - SweetAlert错误弹窗
   - 页面仍显示数据(来自mockData)

### 7.3 真实数据验证

1. 启动后端服务
2. 刷新前端页面
3. 检查:
   - Network标签显示成功请求
   - 响应数据与数据库一致
   - 无mock相关控制台日志

---

## 8. 结论

### 8.1 总体评估

**前端与后端集成状态**: ⚠️ **部分集成，存在降级机制**

### 8.2 关键发现

1. **真实API调用**: ✅ 已实现
   - 所有核心功能均配置真实API端点
   - 使用Axios和fetch发起实际HTTP请求
   - 完整的错误处理和用户提示

2. **模拟数据存在**: ⚠️ 作为降级方案
   - 4个分析页面包含硬编码mockData
   - 1个本地JSON文件用于仿真数据兜底
   - 部分统计指标有默认值

3. **数据流向**: 
   - 首选: 后端API → 真实数据
   - 降级: 本地mock → 模拟数据

### 8.3 生产环境建议

**短期措施**:
- 确保后端服务高可用性，减少触发降级
- 添加监控告警，检测API失败率

**长期措施**:
- 构建流程中移除/禁用所有模拟数据代码
- 实现数据一致性校验机制
- 添加数据来源标识（API vs Mock）

---

## 9. 附录

### 9.1 模拟数据详细清单

| 文件 | 行号 | 数据类型 | 用途 |
|------|------|----------|------|
| macro-analysis.html | 1075 | mockData对象 | 指标卡片兜底 |
| meso-analysis.html | 2305 | mockData对象 | 侧边栏指标 |
| micro-analysis.html | 2388 | mockData对象 | 侧边栏指标 |
| prediction.html | 1963 | fallbackData对象 | 预测基准数据 |
| data-service.js | 251 | _getLocalSimulationData | 仿真数据降级 |
| simulation_data.json | 全部 | 坐标数据 | 微观仿真兜底 |

### 9.2 API端点清单

完整API端点列表参见第4.1节

### 9.3 依赖检查

**未检测到以下模拟工具**:
- Mock Service Worker (MSW)
- json-server
- axios-mock-adapter
- 其他mock库

---

**报告生成时间**: 2026-04-14  
**验证人员**: AI Assistant  
**下次验证建议**: 后端服务更新后
