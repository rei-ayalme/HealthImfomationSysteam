# 数据分析下拉选项无法选择问题修复报告

## 1. 问题现象
- 数据分析页面中，点击按钮后出现的下拉选项框无法稳定选择，部分页面表现为下拉不可见或无法交互。
- 典型影响页：宏观分析、中观分析、预测模拟。

## 2. 根因定位
- 全局样式误伤：在 [common.css](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/frontend/assets/css/common.css) 中将 `.sidebar` 等全局隐藏，导致承载筛选下拉的侧栏容器被隐藏。
- 全局脚本误伤：在 [common.js](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/frontend/assets/js/common.js) 的 `stripLocalNavigation()` 中，存在对 `.sidebar` 与 `aside` 的剥离式隐藏，导致下拉控件交互链路被切断。
- 伴随问题：全局强制 `main-container/admin-container` 为 `display:block` 与内容区全宽覆盖，对原有分析页布局造成二次冲突。

## 3. 修复措施
- 样式层：
  - 取消对 `.sidebar` 的全局 `display:none` 规则，仅保留对明确遗留导航类的隐藏。
  - 去除全局强制全宽与 `display:block` 覆盖，恢复页面原有容器布局能力。
- 脚本层：
  - 在 `stripLocalNavigation()` 中移除 `.sidebar` 与 `aside` 剥离逻辑。
  - 删除过于宽泛的启发式隐藏（`[class*='tabs']` 等）。
- 交互层：
  - 为统一顶部“数据分析”下拉补充键盘可用性：`Enter/Space/Escape` 与 `aria-expanded` 状态同步。

## 4. 验证结果

### 4.1 鼠标选择
- 宏观分析页：年份下拉可从 `2024` 切换为 `2020`。
- 中观分析页：图层下拉可从 `burden` 切换为 `efficiency`。
- 预测模拟页：干预措施可切换为 `combined`。

### 4.2 键盘操作
- 在宏观页聚焦下拉后，`ArrowDown + Enter` 可成功变更值（验证 `Q1 -> Q2`）。

### 4.3 回归测试
- Python 静态回归测试： [test_ui_dropdown_regression.py](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/tests/test_ui_dropdown_regression.py)
  - 防止再次引入“全局隐藏 sidebar/aside”。
  - 校验导航下拉键盘支持关键逻辑存在。
- UI 兼容脚本： [dropdown_compat_check.mjs](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/tests/ui/dropdown_compat_check.mjs)
  - 入口命令：`npm run test:ui-dropdown`
  - 输出报告：`reports/ui/dropdown-compat-report.json`

## 5. 兼容性说明
- 已完成 Chromium 内核链路自动化验证（交互成功）。
- Firefox/WebKit 全自动回归脚本已提供；当前环境下载官方浏览器驱动受网络限制，可在 CI 或联网环境执行同一脚本获得完整跨浏览器报告。
