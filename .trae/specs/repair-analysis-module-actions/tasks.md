# Tasks
- [x] Task 1: 审计四类分析页面按钮并建立动作映射表
  - [x] SubTask 1.1: 盘点 `macro/meso/micro/prediction` 页面所有专业分析按钮与目标动作
  - [x] SubTask 1.2: 标记无实现、弱实现、重复实现的按钮事件
  - [x] SubTask 1.3: 为每个按钮定义唯一动作与失败反馈策略

- [x] Task 2: 修复首页趋势图全球/东亚单点问题
  - [x] SubTask 2.1: 校正 `main.py` 趋势接口区域映射与候选回退
  - [x] SubTask 2.2: 保证时间序列返回最小点数并与前端参数一致
  - [x] SubTask 2.3: 调整首页趋势渲染逻辑，避免被单点数据降级为静态异常

- [x] Task 3: 修复中观“卫生资源配置效率分析”视图不变问题
  - [x] SubTask 3.1: 检查中观页面效率模块筛选状态是否传递到图表数据层
  - [x] SubTask 3.2: 使效率相关按钮触发真实数据刷新与视图更新
  - [x] SubTask 3.3: 增加模块级反馈（加载/完成/失败）

- [x] Task 4: 修复宏观/微观/预测页面同类按钮无作业问题
  - [x] SubTask 4.1: 为无效按钮补齐事件处理函数
  - [x] SubTask 4.2: 清理重复函数与无效入口，统一调用路径
  - [x] SubTask 4.3: 统一详情弹窗、导出、重算等动作的回执行为

- [x] Task 5: 补全首页全球地图指标并实现高亮交互
  - [x] SubTask 5.1: 定义国际数据优先的指标融合算法（含缺失值回退）
  - [x] SubTask 5.2: 在地图渲染中接入计算指标、tooltip字段与视觉映射
  - [x] SubTask 5.3: 对齐中观中国地图的悬浮高亮交互体验

- [x] Task 6: 联调与回归验证
  - [x] SubTask 6.1: 验证四类页面按钮均可触发预期结果
  - [x] SubTask 6.2: 验证首页趋势在全球/东亚为多点曲线
  - [x] SubTask 6.3: 验证中观效率模块切换后视图变化
  - [x] SubTask 6.4: 验证首页全球地图信息完整与悬浮高亮

- [x] Task 7: 修复微观分析页面未实现的按钮动作并补齐反馈
  - [x] SubTask 7.1: 为 `switchPAFView`、`switchPopulationView`、`playTrendAnimation`、`exportInterventionTable` 补齐函数实现并绑定到现有图表实例
  - [x] SubTask 7.2: 为上述动作统一增加成功/失败反馈（通知或弹窗），避免点击后静默无响应
  - [x] SubTask 7.3: 回归验证微观页面“切换/重算/详情/导出”按钮链路，确保不再触发 `is not defined` 前端运行时错误

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 1
- Task 4 depends on Task 1
- Task 5 depends on Task 1
- Task 6 depends on Task 2, Task 3, Task 4, Task 5
