# 首页/宏观分析/数据集联动修复计划

## 1) Summary
- 以 **GitHub main 版** 作为首页行为基线，只修复指定问题，不做额外页面改造。
- 修复三类问题：  
  1. 宏观分析左侧指标卡片空白；  
  2. 数据集页面卡片“全是艾滋梅毒”与六个分类按钮无效；  
  3. 首页左侧筛选无实质联动（要求联动全部模块）。

## 2) Current State Analysis
- 首页筛选交互入口存在：`apply()` 会触发 KPI/趋势/饼图/摘要/地图渲染，但地图当前使用随机值、区域筛选映射弱，导致“看起来没反应”。  
  - `frontend/use/index.html`：`apply`、`renderKPI`、`renderTrend`、`renderPie`、`renderReport`、`renderMap`
- 宏观分析左栏卡片依赖 `/api/analysis/metrics`，前端有 skeleton 与错误兜底；空白多来自后端返回结构与区域匹配不稳定。  
  - `frontend/use/macro-analysis.html`：`updateSidebarMetrics`  
  - `main.py`：`/api/analysis/metrics`
- 数据集页同时存在静态旧渲染与动态新渲染；分类按钮未绑定有效筛选行为；还存在接口路径不一致（`/api/datasets/...` vs `/api/dataset/...`）。  
  - `frontend/use/datasets.html`：`searchDatasets`、两个 `viewDataset`、`downloadDataset`  
  - `main.py`：`/api/dataset`、`/api/dataset/{dataset_id}/detail`

## 3) Proposed Changes

### A. 首页（仅按 main 基线修复联动，不改视觉结构）
- 文件：`frontend/use/index.html`
- 变更点：
  - 统一左侧筛选状态对象（region/year/granularity/metric），确保 `apply` 每次触发都驱动全部模块刷新。
  - KPI：使用 `/api/dataset` 返回后按 `type` 与 `country/region` 做稳定映射；无命中时使用“同类型回退 + 非空占位”，避免空白。
  - 趋势图：保持真实接口优先；当 `region` 为预定义大区时做后端可识别映射，避免请求成功但无数据。
  - 地图：去除纯随机强依赖，改为“按筛选稳定可复现的数据映射”（同筛选结果保持一致），确保用户切换筛选后可见变化。
  - 左侧按钮反馈：`应用/重置`增加明确加载与完成反馈（不新增样式体系，仅轻量状态提示）。

### B. 宏观分析左侧指标卡片空白修复
- 文件：`main.py`、`frontend/use/macro-analysis.html`
- 变更点：
  - 后端 `/api/analysis/metrics`：强化区域别名与年份回退策略（当年无数据则向近年回溯）；保证字段完整返回。
  - 返回结构稳定化：无论是否命中真实记录，始终返回 `dalys/top_disease/dea/prediction` 的完整对象与数值。
  - 前端卡片渲染容错：对 `null/undefined/NaN` 做统一处理，sparkline 空数组时回退为最小可视序列，避免卡片只显示骨架或空值。

### C. 数据集页面卡片与六个按钮修复
- 文件：`frontend/use/datasets.html`、`main.py`
- 变更点：
  - 以“按数据类型聚合”为主：将 `/api/dataset` 返回项按 `type/typeName` 分组，优先展示“全球健康/疾病负担/风险因素/干预措施/人口统计/全部数据集”六类入口。
  - 为六个按钮绑定实际行为：
    - 点击后更新当前筛选类型；
    - 重新渲染卡片列表（非空提示、分页/数量限制）；
    - 同步详情区（首条可用数据自动展示或给出无数据提示）。
  - 清理冲突逻辑：
    - 合并重复 `viewDataset`，仅保留一个实现；
    - 修正 `downloadDataset` 调用路径到 `/api/dataset/{id}/detail`；
    - 保留已有视觉布局，不改页面整体结构。
  - 后端补充：若某类型数据源为空，提供可识别的类型化回退项，确保六类按钮均有可展示内容。

## 4) Assumptions & Decisions
- 已确认：回归基线为 **GitHub main** 行为基线。
- 已确认：数据集卡片按 **数据类型聚合** 展示，不再按单一疾病名堆叠。
- 已确认：首页左侧筛选需要 **联动全部模块**（KPI/趋势图/饼图/摘要/地图）。
- 约束：除上述问题外，不改动其他页面功能与风格。

## 5) Verification Steps
- 首页验证（`/use/index.html`）：
  - 切换 region/year/metric/granularity 后，KPI、趋势图、饼图、摘要、地图都发生可见变化；
  - `应用` 和 `重置` 均有反馈，且重置后恢复默认状态。
- 宏观分析验证（`/use/macro-analysis.html`）：
  - 左侧四张指标卡片不空白，数值/趋势/微图可渲染；
  - 切换区域与年份时卡片能更新，接口失败时展示非空兜底。
- 数据集页验证（`/use/datasets.html`）：
  - 六个按钮均可点击并触发筛选结果变化；
  - 卡片不再集中为“艾滋梅毒”，而是按类型分布；
  - 详情查看与下载路径可用，且与后端路由一致。
- 接口验证：
  - `/api/dataset`、`/api/dataset/{dataset_id}/detail`、`/api/analysis/metrics` 返回结构符合前端消费约定。
