# 2SFCA / aceso 项目分析算法提取与流程还原

## 1. 仓库与核心模块定位

本次分析使用本地镜像目录：
- `external_repos/oss_research/2SFCA`
- `external_repos/oss_research/aceso`

### 1.1 2SFCA 仓库核心入口
- 主算法脚本入口：[两步移动搜索法.py](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/2SFCA/两步移动搜索法.py)
- OD 计算入口：[get_od.py](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/2SFCA/get_od.py)
  - 距离函数：`distance()` [get_od.py:L7-L17](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/2SFCA/get_od.py#L7-L17)
  - OD 计算：`get_od()` [get_od.py:L20-L41](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/2SFCA/get_od.py#L20-L41)
- 供给分级与阈值逻辑：[两步移动搜索法.py:L12-L22](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/2SFCA/两步移动搜索法.py#L12-L22)

### 1.2 aceso 仓库核心入口
- 包导出入口：[aceso/__init__.py](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/aceso/aceso/__init__.py)
- 引力与 2SFCA/3SFCA 模型：[gravity.py](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/aceso/aceso/gravity.py)
  - 通用模型：`GravityModel` [gravity.py:L32-L205](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/aceso/aceso/gravity.py#L32-L205)
  - 2SFCA：`TwoStepFCA` [gravity.py:L206-L219](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/aceso/aceso/gravity.py#L206-L219)
  - 3SFCA：`ThreeStepFCA` [gravity.py:L222-L258](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/aceso/aceso/gravity.py#L222-L258)
- 衰减函数：`uniform/negative_exp/inverse_power/get_decay_function` [decay.py](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/aceso/aceso/decay.py)

## 2. 数据结构提取

### 2.1 2SFCA（脚本型）
- `communities`: 社区需求点 DataFrame（含人口、坐标）
- `hospitals`: 医疗供给点 DataFrame（含床位、坐标、类型）
- `od_pd`: 需求点到供给点 OD 距离矩阵（DataFrame）
- `Threshold`: 不同医院级别对应阈值（namedtuple）

### 2.2 aceso（库型）
- `distance_matrix`: shape=(n_demand, n_supply) 的 NumPy 矩阵
- `demand_array`: shape=(n_demand,)
- `supply_array`: shape=(n_supply,)
- `decay_function`: 距离衰减函数

## 3. 算法流程（伪代码）

```text
Input: D[n,m], demand[n], supply[m], catchment, decay()

Step-1（供给端）
for each supply j:
    weighted_demand_j = sum_i demand[i] * decay(D[i,j]) if D[i,j] <= catchment else 0
    ratio[j] = supply[j] / weighted_demand_j  (if denominator>0 else 0)

Step-2（需求端）
for each demand i:
    accessibility[i] = sum_j ratio[j] * decay(D[i,j]) if D[i,j] <= catchment else 0

Output: accessibility[n], ratio[m]
```

## 4. 复杂度分析

设需求点数量为 `n`，供给点数量为 `m`：
- 时间复杂度：`O(n*m)`（两步都扫描矩阵）
- 空间复杂度：
  - 朴素实现：`O(n*m)`（显式权重矩阵） + `O(n+m)`
  - 分块向量化：`O(n*B)` + `O(n+m)`，`B` 为 block 大小，通常 `B << m`

## 5. 性能瓶颈（静态审查）

1) `2SFCA/get_od.py` 双层 `iterrows` 逐行计算，CPU 密集  
   - 位置：[get_od.py:L31-L34](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/2SFCA/get_od.py#L31-L34)

2) `2SFCA/两步移动搜索法.py` 使用脚本串行流程与逐元素更新，且出现 `.ix` 旧接口  
   - 位置：[两步移动搜索法.py:L96-L104](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/2SFCA/两步移动搜索法.py#L96-L104)

3) aceso 中衰减函数分发无缓存/无批量复用，重复构造中间矩阵  
   - 位置：[gravity.py:L172-L205](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/aceso/aceso/gravity.py#L172-L205)

4) aceso 0 距离处理采用“硬替换大数”策略，可读性与数值稳定性欠佳  
   - 位置：[gravity.py:L198-L203](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/external_repos/oss_research/aceso/aceso/gravity.py#L198-L203)
