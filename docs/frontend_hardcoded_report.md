# 前端脚本硬编码问题系统性检查报告

## 检查概述
- **目标目录**: `d:\python_HIS\pythonProject\多源健康数据驱动的疾病谱系与资源适配分析\Health_Imformation_Systeam\frontend`
- **参考文件1**: `micro-analysis.html#L2008-2039` (干预措施场景数据)
- **参考文件2**: `micro-analysis.html#L2536-2551` (导出功能数据)
- **检查时间**: 2026-04-15
- **涉及文件数**: 20+ 个HTML/JS文件

---

## 参考硬编码模式特征分析

### 模式1: 场景化干预措施数据 (L2008-2039)
```javascript
// 特征: 基于scenario条件的硬编码数据数组
if (scenario === 'A') {
    data = [
        { name: '烟草税提高50%', value: [2.85, 15, 'A级'], itemStyle: { color: '#52c41a' } },
        { name: '全民减盐行动', value: [1.2, 12, 'A级'], itemStyle: { color: '#52c41a' } },
        // ... 更多硬编码对象
    ];
} else if (scenario === 'B') {
    // ... 另一组硬编码数据
} else {
    // ... 默认硬编码数据
}
```

### 模式2: 导出功能硬编码数据 (L2536-2551)
```javascript
// 特征: 硬编码的CSV表头和数据行
const rows = [
    ['group', 'risk_score', 'paf'],
    ['全人群', '0.68', '44.2%'],
    ['男性', '0.74', '48.1%'],
    ['女性', '0.62', '39.4%']
];
```

---

## 硬编码问题详细清单

### 一、硬编码API地址和URL

#### 1.1 第三方CDN资源URL
| 文件路径 | 行号 | 硬编码内容 | 功能说明 |
|---------|------|-----------|---------|
| use/micro-analysis.html | L11-13 | `https://fonts.googleapis.com`, `https://fonts.gstatic.com` | Google Fonts字体资源 |
| use/micro-analysis.html | L19-20 | `https://cdn.jsdelivr.net/npm/sweetalert2@11`, `https://cdn.jsdelivr.net/npm/axios@1.6.0` | SweetAlert2和Axios CDN |
| use/meso-analysis.html | L11-13 | `https://fonts.googleapis.com` 等 | Google Fonts字体资源 |
| use/meso-analysis.html | L19-20 | `https://cdn.jsdelivr.net/npm/axios@1.6.0`, `https://cdn.jsdelivr.net/npm/sweetalert2@11` | CDN资源 |
| use/index.html | L10-12 | `https://fonts.googleapis.com` 等 | Google Fonts字体资源 |
| use/index.html | L388 | `https://webapi.amap.com/maps?v=2.0&key=893aa291ba8fd5ceea01973a6162f182` | 高德地图API (含硬编码key) |
| use/prediction.html | L11-13 | `https://fonts.googleapis.com` 等 | Google Fonts字体资源 |
| use/prediction.html | L19-21 | `https://fastly.jsdelivr.net/npm/echarts-gl@2.0.9`, `https://cdn.jsdelivr.net/npm/axios@1.6.0`, `https://cdn.jsdelivr.net/npm/sweetalert2@11` | CDN资源 |
| use/macro-analysis.html | L11-13 | `https://fonts.googleapis.com` 等 | Google Fonts字体资源 |
| use/macro-analysis.html | L19-20 | `https://cdn.jsdelivr.net/npm/axios@1.6.0`, `https://cdn.jsdelivr.net/npm/sweetalert2@11` | CDN资源 |
| use/datasets.html | L17 | `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css` | Font Awesome CDN |
| admin/*.html | 多个文件 | `https://fonts.googleapis.com` 等 | Google Fonts字体资源 |

#### 1.2 API基础URL配置
| 文件路径 | 行号 | 硬编码内容 | 功能说明 |
|---------|------|-----------|---------|
| use/micro-analysis.html | L1193 | `const MICRO_API_BASE_URL = '/api';` | 微观分析API基础URL |
| use/meso-analysis.html | L1201 | `const MESO_API_BASE_URL = '/api';` | 中观分析API基础URL |
| use/macro-analysis.html | L783 | `const API_BASE_URL = '/api';` | 宏观分析API基础URL |
| use/prediction.html | L1330 | `const PREDICTION_API_BASE_URL = '/api';` | 预测分析API基础URL |
| use/datasets.html | L728 | `const DATASET_API_BASE = '/api';` | 数据集API基础URL |
| admin/data-management.html | L926 | `const API_BASE_URL = 'http://localhost:8000/api/v1';` | 数据管理API基础URL (含localhost) |
| assets/js/api.js | L26 | `baseURL: 'http://127.0.0.1:8000/api'` | API基础URL (含127.0.0.1) |
| assets/js/data-service.js | L28 | `this.baseURL = 'http://localhost:8000';` | 数据服务基础URL |
| test-data-service.html | L499 | `'http://localhost:8000/api/dataset?limit=1'` | 测试数据服务URL |

---

### 二、硬编码业务数据和配置

#### 2.1 干预措施场景数据 (与参考模式1相同)
**文件**: use/micro-analysis.html

| 行号 | 硬编码内容 | 功能说明 | 相似度 |
|------|-----------|---------|--------|
| L2008-2017 | Scenario A数据: 7个干预措施对象 | 乐观情景干预数据 | 100% |
| L2018-2027 | Scenario B数据: 7个干预措施对象 | 保守情景干预数据 | 100% |
| L2028-2037 | Scenario C(else)数据: 7个干预措施对象 | 基准情景干预数据 | 100% |

**硬编码详情**:
```javascript
// L2008-2017 Scenario A
{ name: '烟草税提高50%', value: [2.85, 15, 'A级'], itemStyle: { color: '#52c41a' } }
{ name: '全民减盐行动', value: [1.2, 12, 'A级'], itemStyle: { color: '#52c41a' } }
{ name: '学校体育强化', value: [3.5, 25, 'B级'], itemStyle: { color: '#52c41a' } }
{ name: '高血压规范管理', value: [4.8, 20, 'A级'], itemStyle: { color: '#52c41a' } }
{ name: '工作场所健康', value: [6.5, 18, 'C级'], itemStyle: { color: '#faad14' } }
{ name: '糖尿病筛查', value: [8.2, 30, 'B级'], itemStyle: { color: '#faad14' } }
{ name: '空气污染治理', value: [15, 22, 'A级'], itemStyle: { color: '#f5222d' } }

// L2018-2027 Scenario B (数值不同)
{ name: '烟草税提高50%', value: [3.5, 22, 'A级'], ... }
// ...

// L2028-2037 Scenario C (数值不同)
{ name: '烟草税提高50%', value: [1.5, 10, 'A级'], ... }
```

#### 2.2 导出功能硬编码数据 (与参考模式2相同)
**文件**: use/micro-analysis.html

| 行号 | 硬编码内容 | 功能说明 | 相似度 |
|------|-----------|---------|--------|
| L2538-2542 | CSV导出数据: 表头+3行数据 | 微观风险数据导出 | 100% |

**硬编码详情**:
```javascript
const rows = [
    ['group', 'risk_score', 'paf'],
    ['全人群', '0.68', '44.2%'],
    ['男性', '0.74', '48.1%'],
    ['女性', '0.62', '39.4%']
];
```

#### 2.3 Mock/Demo数据

**use/micro-analysis.html**
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L2390-2393 | Mock数据对象 | 前端兜底数据 |
| L2365 | 兜底数组 `[0, 0.5, 1, 1.2, 1.4]` | 图表默认数据 |

**硬编码详情**:
```javascript
const mockData = {
    dalys: { value: 31542, trend: -1.2, sparkline: [32000, 31800, 31542, 31200, 31000] },
    top_disease: { name: "心血管疾病", ratio: 35.2 },
    dea: { value: 0.82, trend: 2.1, sparkline: [0.75, 0.78, 0.82, 0.84, 0.85] },
    prediction: { growth_rate: 1.5, target: "2030年降低30%" }
};
```

**use/meso-analysis.html**
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L2307-2310 | Mock数据对象 | 前端兜底数据 |
| L2282 | 兜底数组 `[0, 0.5, 1, 1.2, 1.4]` | 图表默认数据 |
| L1550-1567 | 国家基础数据 | 中国/美国/其他国家的cd/ncd/injury/covid数据 |
| L2075-2091 | 地区分布数据 | 东部/中部/西部/东北地区数据 |

**use/prediction.html**
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L1965-1968 | Mock数据对象 | 前端兜底数据 |

**use/macro-analysis.html**
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L1076-1079 | Mock数据对象 | 前端兜底数据 |
| L1418-1439 | 国家预期寿命数据 | 硬编码的各国预期寿命值 |
| L1442-1450+ | 国家DALYs率数据 | 硬编码的各国DALYs率值 |

#### 2.4 地区/人群分布硬编码数据

**use/meso-analysis.html**
```javascript
// L2075-2079
data = [
    { name: '东部地区', value: 0.15, itemStyle: { color: '#52c41a' } },
    { name: '中部地区', value: 0.28, itemStyle: { color: '#1890ff' } },
    { name: '西部地区', value: 0.35, itemStyle: { color: '#faad14' } },
    { name: '东北地区', value: 0.32, itemStyle: { color: '#f5222d' } }
];

// L2082-2086
data = [
    { name: '东北部', value: 0.12, itemStyle: { color: '#52c41a' } },
    { name: '中西部', value: 0.18, itemStyle: { color: '#1890ff' } },
    { name: '南部', value: 0.25, itemStyle: { color: '#faad14' } },
    { name: '西部', value: 0.20, itemStyle: { color: '#f5222d' } }
];

// L2089-2092
data = [
    { name: '发达地区', value: 0.18, itemStyle: { color: '#52c41a' } },
    { name: '发展中地区', value: 0.32, itemStyle: { color: '#1890ff' } },
    { name: '欠发达地区', value: 0.42, itemStyle: { color: '#faad14' } }
];
```

---

### 三、硬编码文本和消息

#### 3.1 通知消息文本 (showNotification)

**use/micro-analysis.html** (18处)
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L1589 | `showNotification('切换成功', \`已切换至${label}\`)` | PAF视图切换成功 |
| L1592 | `showNotification('切换失败', 'PAF视图切换失败，请稍后重试')` | PAF视图切换失败 |
| L1610 | `showNotification('解读成功', \`已生成${title}详细解读\`)` | 解读成功 |
| L1613 | `showNotification('解读失败', '当前无法生成PAF详细解读')` | 解读失败 |
| L1704 | `showNotification('切换成功', \`已切换至${label}维度\`)` | 维度切换成功 |
| L1707 | `showNotification('切换失败', '人群分布维度切换失败')` | 维度切换失败 |
| L1822 | `showNotification('播放已停止', '趋势动画已停止并恢复全量时间轴')` | 动画停止 |
| L1839 | `showNotification('播放完成', '趋势动画已播放完成')` | 动画完成 |
| L1859 | `showNotification('开始播放', '趋势动画播放中，再次点击可停止')` | 动画开始 |
| L2155 | `showNotification('计算完成', \`E2SFCA 空间计算完成，半径: ${threshold}km\`, 'success')` | 空间计算完成 |
| L2461 | `showNotification('分析已更新', \`已更新 ${populationName} - ${genderName} 的数据\`)` | 分析更新 |
| L2529 | `showNotification('导出成功', '干预措施汇总表已导出')` | 导出成功 |
| L2550 | `showNotification('导出成功', '微观分析数据已导出')` | 导出成功 |

**use/meso-analysis.html** (10处)
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L2381 | `showNotification('分析已更新', ...)` | 分析更新通知 |
| L2386 | `showNotification('更新失败', '部分图表更新失败...')` | 更新失败通知 |
| L2398 | `showNotification('演播启动', '正在演算 1990-2024 年疾病时空演变路径...')` | 演播启动 |
| L2427 | `showNotification('演算完毕', '已为您完整展现三十年宏观健康演变轨迹')` | 演算完毕 |
| L2455 | `showNotification('导出成功', \`${type} 图表数据已导出\`)` | 导出成功 |
| L2588 | `showNotification('公平性结果', '集中指数从2010年的0.15下降至2024年的0.08...')` | 公平性结果 |

**use/macro-analysis.html** (8处)
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L1643 | `showNotification('时间已切换', '地图数据已切换至 ' + e.target.value + ' 年')` | 时间切换 |
| L2740 | `showNotification('图表更新完成', '已按当前筛选条件刷新全部宏观图表')` | 图表更新 |
| L2781 | `showNotification('导出成功', '宏观分析数据已导出')` | 导出成功 |
| L2875 | `showNotification('相关性分析', 'Pearson r=0.78, p<0.001...')` | 相关性分析 |
| L2879 | `showNotification('回归模型', '预期寿命 = 62.5 + 0.00024 × 人均GDP，R²=0.61')` | 回归模型 |

**use/prediction.html** (10处)
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L2078 | `showNotification('正在导出预测数据...', 'info')` | 导出中 |
| L2080 | `showNotification('数据导出成功！', 'success')` | 导出成功 |
| L2093 | `showNotification('图表已刷新', 'success')` | 图表刷新 |
| L2103 | `showNotification('敏感性分析功能开发中...', 'info')` | 功能开发中 |
| L2117 | `showNotification('当前为基准情景，未施加额外干预', 'info')` | 基准情景 |
| L2215 | `showNotification('干预模拟完成！', 'success')` | 模拟完成 |

**use/analysis-framework.html** (5处)
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L1316 | `showNotification('配置已保存', '当前分析配置已保存到本地')` | 配置保存 |
| L1333 | `showNotification('配置提醒', '请先选择分析维度')` | 配置提醒 |
| L1337 | `showNotification('配置提醒', '结束年份不能小于起始年份')` | 配置提醒 |
| L1350 | `showNotification('分析完成', '已根据您的配置更新分析结果')` | 分析完成 |

---

### 四、硬编码图表数据

#### 4.1 折线图数据

**use/micro-analysis.html**
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L1752 | `data: [31.0, 30.2, 29.5, 28.2, 27.5, 26.6, 25.8, 24.8]` | 高血压患病率趋势 |
| L1760 | `data: [35.2, 35.8, 36.5, 35.8, 35.2, 34.5, 33.8, 32.5]` | 另一指标趋势 |
| L1768 | `data: [18.5, 19.2, 20.5, 21.2, 22.0, 22.8, 23.5, 22.8]` | 第三指标趋势 |
| L1776 | `data: [42.5, 44.2, 46.5, 48.2, 50.5, 52.8, 54.2, 50.7]` | 第四指标趋势 |
| L1784 | `data: [23.7, 24.5, 25.2, 26.0, 26.8, 27.5, 28.2, 27.5]` | 第五指标趋势 |

#### 4.2 柱状图数据

**use/micro-analysis.html**
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L1984 | `data: [9300, 43200, 265500, 85200, 38500, 89200, 42500]` | 实际摄入数据 |
| L1990 | `data: [5500, 25300, 300500, 200500, 50250, 50250, 25250]` | 推荐摄入数据 |

#### 4.3 国家对比数据

**use/macro-analysis.html**
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L1674 | `const countries = ['中非共和国', '尼日利亚', '印度', '俄罗斯', '巴西', '美国', '中国', '德国', '英国', '韩国', '新加坡', '瑞士', '日本']` | 国家列表 |
| L1681 | `values: [54.0, 55.0, 70.4, 71.3, 75.9, 78.5, 79.0, 81.3, 81.2, 83.5, 82.9, 83.4, 84.2]` | 预期寿命值 |
| L1689 | `values: [8200, 7500, 5800, 5200, 4500, 4200, 3800, 3400, 3500, 3100, 2600, 2800, 2500]` | DALYs率值 |
| L1697 | `values: [19.8, 18.5, 13.8, 14.5, 11.2, 10.5, 9.8, 9.2, 9.3, 8.4, 7.8, 8.2, 7.5]` | 死亡率值 |

---

### 五、硬编码配置参数

#### 5.1 颜色配置

**use/micro-analysis.html**
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L1510-L1525 | 疾病颜色配置 | 高血压/糖尿病等疾病对应的颜色 |

**use/macro-analysis.html**
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L1498 | `colors: ['#d73027', '#fc8d59', '#fee08b', '#d9ef8b', '#91cf60', '#1a9850']` | 颜色方案1 |
| L1505 | `colors: ['#1a9850', '#91cf60', '#d9ef8b', '#fee08b', '#fc8d59', '#d73027']` | 颜色方案2 |
| L1682 | `colors: ['#d73027', '#d73027', '#fc8d59', '#fc8d59', ...]` (13个颜色) | 国家对比颜色 |

#### 5.2 阈值和范围配置

**use/micro-analysis.html**
| 行号 | 硬编码内容 | 功能说明 |
|------|-----------|---------|
| L1682 | `min: 50, max: 90` | 预期寿命范围 |
| L1691 | `min: 2000, max: 9000` | DALYs率范围 |
| L1699 | `min: 5, max: 20` | 死亡率范围 |

---

## 硬编码问题分类统计

### 按文件统计
| 文件名 | 硬编码实例数 | 严重程度 |
|--------|-------------|----------|
| use/micro-analysis.html | 35+ | 高 |
| use/meso-analysis.html | 25+ | 高 |
| use/macro-analysis.html | 30+ | 高 |
| use/prediction.html | 15+ | 中 |
| use/analysis-framework.html | 8+ | 中 |
| admin/data-management.html | 5+ | 中 |
| assets/js/api.js | 3+ | 高 |
| assets/js/data-service.js | 2+ | 高 |

### 按类型统计
| 硬编码类型 | 出现次数 | 风险等级 |
|-----------|---------|----------|
| API地址/URL | 15+ | 高 |
| 业务数据/指标值 | 50+ | 高 |
| 通知消息文本 | 46+ | 低 |
| 颜色配置 | 20+ | 低 |
| Mock/Demo数据 | 15+ | 中 |
| 图表数据 | 40+ | 高 |
| 导出数据 | 5+ | 中 |

---

## 主要问题分析

### 1. 数据一致性问题
- **同一指标在不同文件中数值不一致**
  - Mock数据中的dalys值在多个文件中重复定义但可能不一致
  - 各国健康指标数据硬编码，无法与后端同步

### 2. 维护困难
- 所有业务数据都硬编码在JavaScript中
- 修改数据需要修改代码并重新部署
- 无法通过配置或API动态更新

### 3. 环境依赖问题
- API基础URL硬编码为localhost/127.0.0.1
- 第三方CDN资源URL硬编码，存在单点故障风险
- 高德地图API key硬编码

### 4. 国际化困难
- 所有文本消息都是中文硬编码
- 国家名称硬编码，不支持多语言
- 无法根据用户语言偏好自动切换

---

## 改进建议

### 短期方案 (1-2周)
1. **提取配置对象**
   - 将API基础URL提取到统一的config.js文件
   - 将颜色配置提取到theme.js文件
   - 将通知消息文本提取到i18n.js文件

2. **环境配置化**
   - 使用环境变量配置API地址
   - 根据环境(dev/prod)切换CDN资源

### 中期方案 (1个月)
1. **数据API化**
   - 将干预措施数据迁移到后端API
   - 将国家对比数据迁移到后端API
   - 将Mock数据替换为真实API调用

2. **配置中心**
   - 建立前端配置中心，支持动态配置
   - 实现配置热更新机制

### 长期方案 (2-3个月)
1. **数据管理后台**
   - 提供数据管理界面
   - 支持非技术人员更新业务数据

2. **国际化支持**
   - 引入i18n框架
   - 实现多语言支持

---

## 附录: 完整硬编码实例索引

### 高优先级修复项
1. **API地址硬编码** - 15处
2. **业务数据硬编码** - 50+处
3. **高德地图API key** - 1处

### 中优先级修复项
1. **Mock数据** - 15+处
2. **导出数据硬编码** - 5+处
3. **图表数据硬编码** - 40+处

### 低优先级修复项
1. **通知消息文本** - 46+处
2. **颜色配置** - 20+处
3. **第三方CDN URL** - 30+处

---

**报告生成时间**: 2026-04-15
**检查范围**: frontend目录下所有HTML/JS文件
**参考模式**: micro-analysis.html#L2008-2039, L2536-2551
