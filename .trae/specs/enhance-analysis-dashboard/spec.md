# Enhance Analysis Dashboard & Multi-stage Data Cleaning Spec

## Why

目前许多分析页面的可视化图表缺乏数据，这表明数据清洗和数据绑定流程不够稳健，导致数据没有成功接入。此外，数据分析页面左侧的“健康指标”分布栏过于扁平（如简单的文本列表），缺乏视觉重点，且没有与右侧的核心图表（如地图、趋势图）形成良好的互动。我们需要通过多段式数据清洗确保可靠的数据供应，并通过重构侧边栏（采用交互式的微型数据卡片）来提供专业、动态的分析洞察。

## What Changes

* 实施多段式数据清洗（提取、校验、插值、转换等分阶段进行），确保数据正确格式化并传递给前端可视化，不丢失关键字段。

* 将分析页面（如 `use/macro-analysis.html` 等）的左侧栏重构为三大模块：核心疾病负担（模块 A）、医疗资源效能（模块 B）和风险与预测研判（模块 C）。

* 用微型数据卡片 (Data Cards) 替换简单的纯文本列表，卡片包含趋势指示器（带颜色的上下箭头）、大号粗体数字和微图表 (Sparklines)。

* 添加交互联动：点击数据卡片将更新主 ECharts/地图，切换到相应的数据层（例如，点击 DEA 切换到 DEA 效率热力图）。

* 更新后端 API，动态提供这些指标和趋势数据。

## Impact

* Affected specs: 数据预处理管线、前端分析页面、后端 API。

* Affected code: `modules/data/preprocessor.py`, `main.py`, `frontend/use/macro-analysis.html` (及其他分析页), `frontend/assets/css/common.css`, `frontend/assets/js/common.js`.

## ADDED Requirements

### Requirement: Multi-stage Data Cleaning

系统应分多个稳健的阶段执行数据清洗，以确保所有可视化组件都能接收到有效的真实数据。

### Requirement: Interactive Sidebar Data Cards

系统应将健康指标显示为交互式卡片。

#### Scenario: Interactive map update

* **WHEN** 用户点击侧边栏中的“综合效率均值 (DEA)”卡片时

* **THEN** 主地图自动切换以显示 DEA 效率热力图分布层。

## MODIFIED Requirements

### Requirement: Indicator Visualization

侧边栏中的指标应显示趋势箭头（对于疾病负担上升等负面结果显示红色，对于改善显示绿色）和微图表，而不是静态文本。\
**ADDED Requirements (新增需求)**

* **Requirement: Schema Validation & Quality Audit (强类型校验与质量审计)** 在数据转换写入数据库（或生成 JSON）之前，管线必须通过数据模式（Schema）校验异常值（如负数人口、越界的比率）。如果插值比例过高，应生成警告日志。
* **Requirement: Dynamic ECharts Configuration (动态图表配置)** 当侧边栏交互触发地图图层切换时，前端 ECharts 实例必须同步更新图例（Legend）、视觉映射器（VisualMap）的极值和颜色主题，以适配不同量级的数据指标。
* **Requirement: Graceful Degradation (优雅降级与空状态)** 如果选定区域的特定指标缺失，对应的微型数据卡片应显示为“禁用/置灰”状态，并带有没有数据的提示，而不是导致整个侧边栏渲染失败。

**ADDED Scenarios (新增测试场景)**

* **Scenario: Handling mismatched data scales during map transition**
  * **WHEN** 用户正在查看数值在 0 到 100,000 之间的“DALYs 疾病负担”地图层，
  * **AND** 点击侧边栏数值在 0.0 到 1.0 之间的“DEA 效率”卡片时，
  * **THEN** 地图无缝切换到 DEA 数据，**并且**地图左下角的图例标尺自动从 100,000 变更为 1.0 封顶，颜色从红色系（疾病预警）平滑过渡为蓝/绿色系（效率指标）。
* **Scenario: Skeleton loading for data cards**
  * **WHEN** 用户首次进入分析页面或切换分析大区时，
  * **THEN** 在后端 API 返回最新数据前的几百毫秒内，侧边栏的所有微型数据卡片显示为灰色脉冲动画（骨架屏），防止页面布局抖动

