# 空间可达性优化模块使用说明

## 1. 安装依赖
项目已有 Python 依赖环境下，确保包含 `numpy` 与 `pytest`：

```bash
pip install numpy pytest
```

## 2. 模块位置
- 优化源码：[spatial_algorithms.py](file:///d:/python_HIS/pythonProject/Health_Imformation_Systeam/modules/core/spatial_algorithms.py)

## 3. 兼容接口
与 aceso 风格保持一致的核心输入：
- `distance_matrix: np.ndarray`，shape=(n_demand, n_supply)
- `demand_array: np.ndarray`，shape=(n_demand,)
- `supply_array: np.ndarray`，shape=(n_supply,)

可选参数：
- `catchment`（阈值半径）
- `decay`（`uniform` / `inverse_power`）
- `beta`（逆幂衰减指数）

## 4. 调用示例

```python
import numpy as np
from modules.core.spatial_algorithms import optimized_2sfca

distance = np.array([[10, 40], [25, 5]], dtype=float)
demand = np.array([1000, 800], dtype=float)
supply = np.array([50, 80], dtype=float)

result = optimized_2sfca(
    distance_matrix=distance,
    demand_array=demand,
    supply_array=supply,
    catchment=30.0,
    decay="uniform"
)

print(result.accessibility)
print(result.supply_ratio)
print(result.metadata)
```

## 5. Benchmark 与回归测试

```bash
py -m pytest tests/test_spatial_access_optimized.py tests/benchmark/test_spatial_access_benchmark.py -q
```

测试将自动输出：
- 正确性一致性（误差阈值 1e-6）
- 1万/10万/100万规模性能对比
- 报告文件 `reports/deepanalyze/spatial_access_benchmark.json`

## 6. 扩展接口建议
- 可新增 `decay="gaussian"` 与自定义衰减回调
- 可新增 `chunk_size` 显式参数用于超大规模调优
- 可新增 `numba/cupy` 后端以支持 JIT/GPU 加速
