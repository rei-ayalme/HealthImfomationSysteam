# Tasks
- [x] Task 1: 重构数据清洗管线为多阶段模式
  - [x] SubTask 1.1: 拆分 `preprocessor.py` 和 `cleaner.py` 的数据清洗流程为明确的阶段（如 Schema 验证、缺失值处理、异常值处理、最终格式化入库），并确保可视化必需字段均不缺失。
  - [x] SubTask 1.2: 执行清洗管线并确认数据能正确写入 SQLite 供前端调用。
- [x] Task 2: 后端 API 增强
  - [x] SubTask 2.1: 在 `main.py` 中创建或更新 API（如 `/api/analysis/metrics`），使其能动态提供聚合数据、DALYs、DEA 及同比趋势供侧边栏卡片使用。
- [x] Task 3: 更新 CSS 和 JS 支持侧边栏数据卡片
  - [x] SubTask 3.1: 在 `common.css` 中添加 `.indicator-card`, `.metric-value`, `.trend` 等样式，加入悬浮效果与颜色区分。
  - [x] SubTask 3.2: 在 `common.js` 中实现 `updateSidebarMetrics` 逻辑，用于获取数据并动态更新卡片。
- [x] Task 4: 前端 HTML 重构
  - [x] SubTask 4.1: 修改 `macro-analysis.html` 及其他相关页面的左侧边栏，使用新的微型数据卡片 HTML 结构（分为核心疾病负担、医疗资源效能、风险与预测三大模块）。
- [x] Task 5: 实现交互联动
  - [x] SubTask 5.1: 为数据卡片添加点击事件监听器，触发 ECharts 实例的 `setOption` 更新（实现在 DALYs、DEA 等数据层之间切换）。点击卡片不仅要换数据，**必须重置 ECharts 的 VisualMap（视觉映射）**，否则 DEA（0~1）和 DALYs（几万）的颜色标尺会冲突

