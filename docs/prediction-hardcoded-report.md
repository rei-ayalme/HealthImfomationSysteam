# prediction.html 硬编码内容分析报告

## 执行摘要

本报告对 `prediction.html` 文件进行了全面的硬编码内容分析。该文件是健康预测与模拟模块，包含 2637 行代码，基于SDE(随机微分方程)、BAPC(贝叶斯年龄-时期-队列)和DeepAnalyze等模型实现多情景健康预测。分析发现文件中存在大量硬编码的预测参数、情景数据、模型配置和模拟数据，需要系统性地进行优化以提高预测准确性和可维护性。

---

## 一、硬编码内容详细列表

### 1. 预测统计卡片硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 950 | `<div class="stat-value">31.2亿</div>` | 业务数据 | 2030年疾病负担预测 |
| 952 | `<span>+9.5% (vs 2024)</span>` | 业务数据 | 疾病负担变化趋势 |
| 962 | `<div class="stat-value">76.5岁</div>` | 业务数据 | 预期寿命预测(2030) |
| 964 | `<span>+1.8岁 (vs 2024)</span>` | 业务数据 | 预期寿命变化 |
| 974 | `<div class="stat-value">1.5%</div>` | 业务数据 | 年均增长率 |
| 986 | `<div class="stat-value">97.2%</div>` | 业务数据 | 模型准确率 |

### 2. 情景说明数据硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 998-1028 | 三种情景卡片 | 业务数据 | 乐观/基准/悲观情景说明 |

```html
<!-- 第998-1028行 - 硬编码的情景说明 -->
<div class="scenario-card optimistic">
    <div class="scenario-header">
        <span class="scenario-icon">🌟</span>
        <span class="scenario-name">乐观情景</span>
    </div>
    <div class="scenario-desc">
        假设：全民健康覆盖实现、慢性病防控达标...<br>
        概率权重：25% | 2030年DALYs: 29.5亿
    </div>
</div>
<div class="scenario-card baseline">
    ...
    概率权重：50% | 2030年DALYs: 31.2亿
</div>
<div class="scenario-card pessimistic">
    ...
    概率权重：25% | 2030年DALYs: 33.8亿
</div>
```

### 3. 预测模型参数硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 1565-1585 | 模型基础参数 | 配置数据 | 不同预测目标的基础值、增长率、波动率 |

```javascript
// 第1565-1585行 - 硬编码的预测模型参数
if (target === 'disease_burden') {
    baseValue = 2850;
    growthRate = scenario === 'baseline' ? 0.015 : (scenario === 'optimistic' ? 0.008 : 0.025);
    volatility = scenario === 'baseline' ? 0.08 : (scenario === 'optimistic' ? 0.06 : 0.12);
} else if (target === 'life_expectancy') {
    baseValue = 73.2;
    growthRate = scenario === 'baseline' ? 0.0025 : (scenario === 'optimistic' ? 0.0035 : 0.0015);
    volatility = scenario === 'baseline' ? 0.02 : (scenario === 'optimistic' ? 0.015 : 0.03);
} else if (target === 'mortality') {
    baseValue = 7.5;
    growthRate = scenario === 'baseline' ? -0.01 : (scenario === 'optimistic' ? -0.02 : 0.005);
    volatility = scenario === 'baseline' ? 0.1 : (scenario === 'optimistic' ? 0.08 : 0.15);
} else {
    baseValue = 25.4;
    growthRate = scenario === 'baseline' ? 0.01 : (scenario === 'optimistic' ? 0.005 : 0.02);
    volatility = scenario === 'baseline' ? 0.08 : (scenario === 'optimistic' ? 0.06 : 0.12);
}
```

### 4. 模型差异参数硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 1587-1594 | 模型差异调整 | 配置数据 | BAPC/DeepAnalyze模型调整系数 |

```javascript
// 第1587-1594行 - 硬编码的模型差异参数
if (model === 'BAPC') {
    growthRate *= 0.95;
    volatility *= 1.2;
} else if (model === 'DeepAnalyze') {
    growthRate *= 1.05;
    volatility *= 0.8;
}
```

### 5. 干预参数硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 1596-1599 | 干预级别调整 | 配置数据 | 干预强度和资源水平调整系数 |

```javascript
// 第1596-1599行 - 硬编码的干预参数
if (interventionLevel === 'strong') growthRate *= 0.85;
if (interventionLevel === 'weak') growthRate *= 1.12;
if (resourceLevel === 'high') growthRate *= 0.9;
if (resourceLevel === 'low') growthRate *= 1.1;
```

### 6. 多情景对比数据硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 1739-1770 | scenarioChart数据 | 业务数据 | 三种情景的增长率参数 |

```javascript
// 第1759-1770行 - 硬编码的情景增长率
const optimisticData = years.map(year => {
    const growthRate = target === 'life_expectancy' ? 0.0035 : (target === 'mortality' ? -0.02 : 0.005);
    return (baseValue * Math.pow(1 + growthRate, parseInt(year) - 2024)).toFixed(target === 'life_expectancy' ? 1 : 0);
});
const baselineData = years.map(year => {
    const growthRate = target === 'life_expectancy' ? 0.0025 : (target === 'mortality' ? -0.01 : 0.01);
    ...
});
const pessimisticData = years.map(year => {
    const growthRate = target === 'life_expectancy' ? 0.0015 : (target === 'mortality' ? 0.005 : 0.02);
    ...
});
```

### 7. 瀑布图数据硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 1859-1931 | waterfallChart数据 | 业务数据 | SHAP值分解数据 |

```javascript
// 第1859-1931行 - 硬编码的瀑布图数据
data: [0, 2850, 4350, 4950, 4580, 4080, 0],  // 辅助数据
data: [2850, 1500, 600, 100, '-', '-', 4080], // 增量数据
data: ['-', '-', '-', '-', 370, 500, '-']     // 减量数据
```

### 8. 干预模拟参数硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 2156-2183 | 干预效果计算 | 业务数据 | 各类干预措施的避免DALYs和成本 |

```javascript
// 第2156-2183行 - 硬编码的干预模拟参数
if (interventionType === 'tobacco') {
    averted = (1.2 * factor).toFixed(1);
    cost = (34.2 * factor).toFixed(1);
    icer = Math.round(2850 / factor);
    insight = '控烟政策在早期见效慢，但在10年后产生指数级健康收益。';
} else if (interventionType === 'salt') {
    averted = (0.8 * factor).toFixed(1);
    cost = (12.5 * factor).toFixed(1);
    icer = Math.round(1560 / factor);
    insight = '减盐行动能迅速降低心血管疾病发生率...';
}
// ... 其他干预类型
```

### 9. 干预结果图表数据硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 2260-2271 | interventionResultChart数据 | 业务数据 | 累积健康收益曲线数据 |

```javascript
// 第2260-2271行 - 硬编码的干预结果数据
series: [{
    type: 'line',
    smooth: true,
    data: [0, 8, 18, 32, 48, 65],  // 累积健康收益
    ...
}]
```

### 10. Mock数据回退硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 1964-1969 | fallbackData对象 | 配置数据 | 侧边栏指标Mock数据 |

```javascript
// 第1964-1969行 - 硬编码的Mock回退数据
const fallbackData = {
    dalys: { value: 31542, trend: -1.2, sparkline: [32000, 31800, 31542, 31200, 31000] },
    top_disease: { name: "心血管疾病", ratio: 35.2 },
    dea: { value: 0.82, trend: 2.1, sparkline: [0.75, 0.78, 0.82, 0.84, 0.85] },
    prediction: { growth_rate: 1.5, target: "2030年降低30%" }
};
```

### 11. 粒子仿真系统硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 2326-2331 | 颜色映射 | 配置数据 | 健康状态颜色配置 |
| 2413-2421 | 医院POI兜底数据 | 业务数据 | 成都市医院坐标 |

```javascript
// 第2326-2331行 - 硬编码的颜色映射
const colorMap = {
    0: '#52c41a', // 健康
    1: '#faad14', // 慢病
    2: '#f5222d', // 重症
    3: '#8c8c8c'  // 死亡
};

// 第2413-2421行 - 硬编码的医院POI数据
hospitalsDataCache = [
    [104.058564, 30.643904, '四川大学华西医院'],
    [104.037064, 30.668702, '四川省人民医院'],
    ...
];
```

### 12. API端点配置硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 1330 | `PREDICTION_API_BASE_URL` | 配置数据 | API基础URL配置 |
| 1351 | report API端点 | 配置数据 | 后端报告接口路径 |

### 13. UI文本硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 849 | 页面标题 | 静态文本 | "🔮 健康预测模拟" |
| 850 | 页面副标题 | 静态文本 | 功能说明文本 |
| 1048-1056 | 预测分析解读 | 静态文本 | 趋势特征、驱动因素、不确定性分析 |
| 1173-1181 | 核心预测结论 | 静态文本 | 6条预测结论和政策建议 |

### 14. 数据来源与局限说明硬编码

| 行号 | 代码片段 | 类型 | 内容说明 |
|------|----------|------|----------|
| 1187-1215 | 数据来源卡片 | 静态文本 | GBD 2021、WHO等数据来源 |
| 1199-1205 | 模型局限列表 | 静态文本 | 5条模型局限性说明 |
| 1209-1214 | 更新计划列表 | 静态文本 | 4条更新计划 |

---

## 二、硬编码类型分类统计

| 类型 | 数量 | 占比 | 风险等级 |
|------|------|------|----------|
| 业务数据 | 38处 | 58% | 高 |
| 配置数据 | 18处 | 27% | 高 |
| 静态文本 | 10处 | 15% | 低 |

---

## 三、维护风险分析

### 高风险项

1. **预测模型参数准确性风险**
   - 基础值、增长率、波动率均为硬编码
   - 不同预测目标(疾病负担/预期寿命/死亡率/患病率)使用不同参数
   - 三情景(乐观/基准/悲观)参数差异缺乏统计学依据
   - 建议：建立模型参数校准机制，定期使用最新数据重新估计

2. **模型差异参数缺乏依据**
   - SDE/BAPC/DeepAnalyze三模型的调整系数(0.95/1.05等)为经验值
   - 缺乏模型对比验证数据
   - 建议：建立模型评估框架，动态选择最优模型

3. **干预效果数据维护困难**
   - 5类干预措施的避免DALYs、成本、ICER为硬编码
   - 干预效果随时间和人群变化，需要定期更新
   - 建议：建立干预效果数据库，对接系统综述和Meta分析结果

### 中风险项

1. **情景概率权重固定**
   - 乐观/基准/悲观三情景的概率权重固定为25%/50%/25%
   - 缺乏情景概率的动态调整机制
   - 建议：基于蒙特卡洛模拟动态计算情景概率

2. **Mock数据可能误导用户**
   - 当后端不可用时显示模拟数据
   - 用户无法区分预测结果和模拟数据
   - 建议：明确标注数据来源和置信度

### 低风险项

1. **UI文本国际化困难**
   - 中文文本硬编码，国际化需要全面替换
   - 建议：使用i18n框架管理文本

---

## 四、优化建议

### 1. 预测模型参数化 (优先级：高)

```javascript
// 建议：创建模型配置服务
class PredictionModelService {
  async getModelParams(target, scenario) {
    // 从后端获取最新模型参数
    const response = await fetch(`/api/prediction/params?target=${target}&scenario=${scenario}`);
    return response.json();
  }
  
  async calibrateModel(historicalData) {
    // 使用历史数据校准模型参数
    // 返回最优参数组合
  }
  
  async validateModel(modelType, testData) {
    // 验证模型准确性
    // 返回MAPE、RMSE等指标
  }
}
```

### 2. 多模型融合机制 (优先级：高)

```javascript
// 建议：模型融合服务
class ModelEnsembleService {
  async getEnsemblePrediction(target, region, year) {
    // 获取多个模型的预测结果
    const [sdeResult, bapcResult, deepResult] = await Promise.all([
      this.runSDE(target, region, year),
      this.runBAPC(target, region, year),
      this.runDeepAnalyze(target, region, year)
    ]);
    
    // 加权融合
    return this.weightedAverage([sdeResult, bapcResult, deepResult]);
  }
  
  async getModelWeights() {
    // 基于历史回测表现动态调整模型权重
  }
}
```

### 3. 干预效果动态计算 (优先级：高)

```javascript
// 建议：干预效果计算引擎
class InterventionEffectEngine {
  async calculateEffect(interventionType, intensity, startYear, targetPopulation) {
    // 基于微观模拟计算干预效果
    const simulation = await this.runMicrosimulation({
      intervention: interventionType,
      intensity: intensity,
      startYear: startYear,
      population: targetPopulation
    });
    
    return {
      avertedDALYs: simulation.avertedDALYs,
      cost: simulation.cost,
      ICER: simulation.cost / simulation.qalysGained,
      confidenceInterval: simulation.ci
    };
  }
}
```

### 4. 情景概率动态计算 (优先级：中)

```javascript
// 建议：情景分析服务
class ScenarioAnalysisService {
  async calculateScenarioProbabilities() {
    // 基于蒙特卡洛模拟计算各情景概率
    const simulations = await this.runMonteCarlo(10000);
    
    return {
      optimistic: this.calculateProbability(simulations, 'optimistic'),
      baseline: this.calculateProbability(simulations, 'baseline'),
      pessimistic: this.calculateProbability(simulations, 'pessimistic')
    };
  }
}
```

### 5. 数据版本与溯源 (优先级：中)

```javascript
// 建议：预测数据版本管理
const PredictionDataVersion = {
  version: '2024-Q4-v2',
  modelParams: {
    lastCalibrated: '2024-11-15',
    calibrationData: 'GBD 2021'
  },
  interventionData: {
    lastUpdated: '2024-10-01',
    source: 'Cochrane Reviews'
  }
};
```

---

## 五、改进优先级建议

| 优先级 | 改进项 | 预计工作量 | 影响范围 |
|--------|--------|------------|----------|
| P0 | 预测模型参数API化 | 4天 | 预测核心模块 |
| P0 | 多模型融合机制 | 5天 | 预测核心模块 |
| P0 | 干预效果动态计算 | 4天 | 干预模拟模块 |
| P1 | 情景概率动态计算 | 3天 | 情景分析模块 |
| P1 | 数据版本与溯源 | 2天 | 全页面 |
| P2 | 国际化框架 | 3天 | 全页面 |

---

## 六、总体评估

### 当前状态
- **硬编码密度**: 高 (约56处硬编码，其中38处业务数据+18处配置数据)
- **维护难度**: 高 (预测模型参数需要专业知识校准)
- **预测准确性**: 中 (硬编码参数难以适应数据变化)
- **可扩展性**: 低 (新增预测目标需要修改代码)

### 改进后预期
- **模型更新**: 从手动修改代码变为API自动获取最新参数
- **预测准确性**: 提升15-25% (通过模型融合和动态校准)
- **维护成本**: 降低70%以上
- **可扩展性**: 支持动态添加新的预测目标和模型

---

## 七、具体实施步骤

1. **第一阶段 (2-3周)**
   - 建立预测模型服务层
   - 实现模型参数API化
   - 建立模型校准机制

2. **第二阶段 (3-4周)**
   - 实现多模型融合框架
   - 建立模型评估和选择机制
   - 干预效果动态计算引擎

3. **第三阶段 (2-3周)**
   - 情景概率动态计算
   - 数据版本与溯源系统
   - 国际化框架集成

---

## 八、关键技术建议

### 模型技术栈
- **SDE模型**: 使用Python + StochasticDiffEq.jl
- **BAPC模型**: 使用R + BAPC包
- **DeepAnalyze**: 使用Python + PyTorch/TensorFlow
- **模型服务**: FastAPI + Celery (异步任务)

### 数据存储
- **模型参数**: PostgreSQL + JSONB
- **预测结果**: InfluxDB (时序数据)
- **干预效果**: MongoDB (文档型)

### 缓存策略
- **热点预测**: Redis (1小时TTL)
- **模型参数**: 本地缓存 (24小时TTL)

---

*报告生成时间: 2024年*
*分析文件: prediction.html (2637行)*
