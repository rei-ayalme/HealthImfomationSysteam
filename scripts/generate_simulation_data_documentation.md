# PopulationSimulator 代码说明文档

## 概述

`generate_simulation_data.py` 是一个基于智能体（Agent-Based）的流行病学模拟系统，用于生成成都市人口健康状态演化的可视化数据。该系统通过结合地理信息系统（GIS）、马尔可夫链状态机模型和空间行为模拟，实现了对疾病传播、医疗资源利用和人口动态变化的综合仿真。

---

## 核心原理解析

### 1. 多边形拒绝采样（Geofencing）机制

#### 功能描述

多边形拒绝采样机制用于实现模拟人口坐标的空间约束，确保生成的智能体（模拟人口）坐标严格位于成都市行政区域边界内部，而非简单的矩形区域内。这一机制保证了模拟结果的空间真实性和可视化效果的地理准确性。

#### 技术实现细节

**1.1 边界数据加载**

```python
geojson_path = os.path.join(base_dir, "data", "geojson", "chengdu_boundary.geojson")
gdf = gpd.read_file(geojson_path)
gdf.geometry = gdf.geometry.make_valid()
self.city_polygon = gdf.geometry.union_all()
```

- 使用 `geopandas` 库读取成都市边界 GeoJSON 文件
- `make_valid()` 修复几何图形的拓扑错误，避免 `TopologyException`
- `union_all()` 将多个区县边界合并为统一的成都市多边形

**1.2 外包框计算**

```python
self.minx, self.miny, self.maxx, self.maxy = self.city_polygon.bounds
```

获取多边形的经纬度外包框（Bounding Box），作为随机点生成的初始范围。

**1.3 拒绝采样算法**

```python
def _generate_points_in_polygon(self, num_points):
    """核心算法：拒绝采样法生成多边形内部随机点"""
    lons, lats = [], []
    while len(lons) < num_points:
        # 批量在外包框生成点
        x_rand = np.random.uniform(self.minx, self.maxx, 2000)
        y_rand = np.random.uniform(self.miny, self.maxy, 2000)
        
        for x, y in zip(x_rand, y_rand):
            if len(lons) >= num_points:
                break
            # 校验点是否在成都市边界内部
            if self.city_polygon.contains(Point(x, y)):
                lons.append(x)
                lats.append(y)
    
    return np.array(lons), np.array(lats)
```

**算法流程：**

1. **批量生成**：在 Bounding Box 内批量生成 2000 个随机坐标点
2. **空间判断**：使用 `shapely.geometry.Point` 和 `contains()` 方法判断点是否在多边形内部
3. **迭代采样**：持续迭代直至收集到足够数量的有效点（默认 5000 个）
4. **性能优化**：批量生成减少循环次数，提高采样效率

**数学原理：**

拒绝采样法基于蒙特卡洛方法，采样接受概率为：

$$P_{accept} = \frac{A_{polygon}}{A_{bbox}}$$

其中 $A_{polygon}$ 是多边形面积，$A_{bbox}$ 是外包框面积。对于复杂形状的多边形，该方法能有效保证采样点的空间分布真实性。

---

### 2. 马尔可夫状态机（Markov Chain）模型

#### 功能描述

马尔可夫状态机模型用于实现疾病状态的动态转移模拟。该模型基于流行病学自然史，定义了健康人群在不同疾病状态之间的转移概率，模拟疾病在人群中的自然演进过程。

#### 技术实现细节

**2.1 状态定义**

系统定义了四种健康状态：

| 状态码 | 状态名称 | 描述 |
|--------|----------|------|
| 0 | 健康 | 无疾病或疾病已康复 |
| 1 | 慢病 | 患有慢性疾病（如高血压、糖尿病） |
| 2 | 重症 | 患有严重疾病或急性发作 |
| 3 | 死亡 | 疾病导致死亡（吸收态） |

**2.2 转移矩阵定义**

```python
self.transition_matrix = np.array([
    [0.95, 0.04, 0.01, 0.00],  # 健康 -> 维持, 慢病, 重症, 死亡
    [0.05, 0.85, 0.08, 0.02],  # 慢病 -> 康复, 维持, 重症, 死亡
    [0.00, 0.10, 0.70, 0.20],  # 重症 -> 康复, 慢病, 维持, 死亡
    [0.00, 0.00, 0.00, 1.00]   # 死亡 -> 吸收态
])
```

**转移概率解读：**

- **健康状态（第0行）**：
  - 95% 概率维持健康
  - 4% 概率转为慢病（符合人群慢性病年发病率）
  - 1% 概率直接转为重症（急性疾病或意外）
  - 0% 概率直接死亡

- **慢病状态（第1行）**：
  - 5% 概率康复（健康生活方式干预效果）
  - 85% 概率维持慢病状态
  - 8% 概率恶化为重症（疾病进展）
  - 2% 概率导致死亡（严重并发症）

- **重症状态（第2行）**：
  - 0% 概率直接康复（需经过慢病阶段）
  - 10% 概率转为慢病（治疗有效，病情缓解）
  - 70% 概率维持重症（持续治疗中）
  - 20% 概率导致死亡（重症死亡率）

- **死亡状态（第3行）**：
  - 吸收态，100% 保持死亡状态

**2.3 状态转移执行**

```python
def step(self):
    """执行一年的时间步推演"""
    new_states = np.zeros(self.num_agents, dtype=int)
    for i in range(self.num_agents):
        curr_state = self.states[i]
        # 根据转移矩阵概率，计算下一年的状态
        new_states[i] = np.random.choice([0, 1, 2, 3], p=self.transition_matrix[curr_state])
        # ... 后续处理
    self.states = new_states
    return self.get_frame_data()
```

**马尔可夫性质：**

该模型满足马尔可夫性质（Markov Property），即下一时刻的状态仅依赖于当前状态，与历史状态无关：

$$P(X_{t+1} = j | X_t = i, X_{t-1}, ..., X_0) = P(X_{t+1} = j | X_t = i) = p_{ij}$$

这种无记忆性简化了计算，同时符合疾病自然史的实际情况。

---

### 3. 医疗资源虹吸效应（Spatial Clustering）实现

#### 功能描述

医疗资源虹吸效应模拟重症患者向医疗资源聚集的空间行为。当患者病情恶化至重症状态时，会主动寻求最近的医疗资源（如三甲医院），产生空间上的聚集效应。这一机制在可视化中表现为红色粒子（重症患者）向医院位置（华西医院、省医院等）移动的动画效果。

#### 技术实现细节

**3.1 医疗资源数据加载**

```python
hospitals_geojson_path = os.path.join(base_dir, "data", "geojson", "chengdu_hospitals.geojson")
self.pois = []
if os.path.exists(hospitals_geojson_path):
    with open(hospitals_geojson_path, 'r', encoding='utf-8') as f:
        hospital_data = json.load(f)
        for feature in hospital_data.get('features', []):
            coords = feature.get('geometry', {}).get('coordinates')
            if coords and len(coords) >= 2:
                self.pois.append((coords[0], coords[1]))

# 保底医院坐标（华西医院和省医院）
if not self.pois:
    hx_lon, hx_lat = gcj2wgs(104.063228, 30.64098)
    sy_lon, sy_lat = gcj2wgs(104.041648, 30.665792)
    self.pois = [(hx_lon, hx_lat), (sy_lon, sy_lat)]
```

- 从 GeoJSON 文件读取真实医院坐标
- 使用 `coord_convert` 库将 GCJ-02 坐标（火星坐标）转换为 WGS-84 坐标
- 提供保底医院坐标确保系统可用性

**3.2 虹吸效应算法**

```python
# 如果变成重症(2)，则坐标向最近的医院 POI 移动
if new_states[i] == 2:
    # 寻找最近医院（简化的贪心移动逻辑）
    closest_poi = self.pois[i % len(self.pois)]
    self.lon[i] = self.lon[i] + (closest_poi[0] - self.lon[i]) * 0.5
    self.lat[i] = self.lat[i] + (closest_poi[1] - self.lat[i]) * 0.5
```

**算法原理：**

虹吸效应使用线性插值算法实现粒子向目标点的移动：

$$P_{new} = P_{current} + (P_{target} - P_{current}) \times \alpha$$

其中：
- $P_{new}$ 是新位置
- $P_{current}$ 是当前位置
- $P_{target}$ 是目标医院位置
- $\alpha = 0.5$ 是移动系数（控制移动速度）

**空间行为解释：**

- $\alpha = 0.5$ 表示每次移动距离为剩余距离的 50%
- 这种衰减移动模拟了患者逐步前往医院的过程
- 视觉上形成粒子向医院聚集的"虹吸"效果
- 重症患者（红色粒子）在地图上形成围绕医院的聚集簇

**3.3 可视化效果**

在 ECharts 等可视化库中，重症状态（state=2）的粒子通常渲染为红色，健康状态（state=0）为绿色，慢病状态（state=1）为黄色。随着时间推移，红色粒子会逐渐向医院位置聚集，形成明显的空间聚类模式。

---

### 4. 人口守恒定律（Respawn）机制

#### 功能描述

人口守恒定律机制用于维持模拟系统的人口数量稳定。当粒子因疾病死亡（状态变为3）时，系统触发重生机制，在地图随机位置生成新的健康粒子，确保系统中始终保持固定数量的活跃粒子（默认5000个）。

#### 技术实现细节

**4.1 死亡检测与重生触发**

```python
# 死去的粒子复活成健康状态并在随机位置重生，维持人口总量
if new_states[i] == 3:
    new_states[i] = 0  # 状态重置为健康
    if self.use_polygon:
        # 在多边形内随机位置重生
        new_lon, new_lat = self._generate_points_in_polygon(1)
        self.lon[i] = new_lon[0]
        self.lat[i] = new_lat[0]
    else:
        # 矩形区域内随机重生（保底方案）
        self.lon[i] = np.random.uniform(103.5, 104.9)
        self.lat[i] = np.random.uniform(30.1, 31.4)
```

**4.2 重生位置生成**

- 优先使用多边形拒绝采样，确保重生位置在成都市边界内
- 若边界数据不可用，则在经纬度矩形范围内随机生成
- 新粒子初始状态设为健康（0），模拟新生儿或迁入人口

**4.3 人口守恒的数学表达**

设系统总人口为 $N$，各状态人口数为 $N_0, N_1, N_2, N_3$，则：

$$N = N_0 + N_1 + N_2 + N_3 = \text{const}$$

当 $N_3$ 个粒子死亡并重置为状态0时：

$$\Delta N_3 = -N_3, \quad \Delta N_0 = +N_3$$

$$N_{new} = (N_0 + N_3) + N_1 + N_2 + 0 = N_0 + N_1 + N_2 + N_3 = N$$

**4.4 生物学意义**

- **出生补偿**：模拟新生儿出生，维持人口规模
- **迁入迁出平衡**：模拟人口流动，死亡人口被新迁入人口替代
- **系统稳态**：确保长期模拟中人口基数不变，便于比较不同时期的疾病负担

---

## 系统运行机制

### 整体流程

```
初始化阶段
    │
    ├── 加载成都市边界数据
    ├── 生成5000个边界内随机坐标（拒绝采样）
    ├── 初始化健康状态（90%健康，10%慢病）
    ├── 加载医院坐标数据
    │
    ▼
时间步推演（2024-2044年）
    │
    ├── 对每个智能体：
    │   ├── 执行马尔可夫状态转移
    │   ├── 若转为重症：执行虹吸移动
    │   ├── 若死亡：触发重生机制
    │   └── 更新坐标和状态
    │
    ├── 打包帧数据
    └── 保存到JSON文件
```

### 数据输出格式

```python
def get_frame_data(self):
    """打包一帧的数据供前端渲染"""
    return np.column_stack((self.lon, self.lat, self.states)).tolist()
```

输出数据格式为 `[[lon, lat, state], ...]` 的列表，可直接用于 ECharts GL 等可视化库的散点图或尾迹图渲染。

### 主程序执行流程

```python
if __name__ == "__main__":
    # 1. 创建模拟器实例
    simulator = PopulationSimulator(num_agents=5000)
    frames = {}
    
    # 2. 执行21年时间推演
    for year in range(2024, 2045):
        frames[str(year)] = simulator.step()
        print(f"Processed year {year}")
    
    # 3. 保存结果
    output_file = os.path.join(output_dir, "simulation_data.json")
    with open(output_file, "w") as f:
        json.dump(frames, f)
```

---

## 关键技术依赖

| 库名称 | 用途 |
|--------|------|
| `geopandas` | 地理数据处理（GeoJSON读取、多边形操作） |
| `shapely` | 几何图形计算（点包含判断） |
| `numpy` | 数值计算（随机数生成、矩阵运算） |
| `coord_convert` | 坐标系转换（GCJ-02 转 WGS-84） |

---

## 应用场景

1. **疾病传播模拟**：预测慢性病在人群中的长期演进趋势
2. **医疗资源规划**：评估医院分布对重症患者可及性的影响
3. **公共卫生政策评估**：模拟不同干预措施对健康指标的影响
4. **数据可视化**：生成高质量的时空动态可视化数据

---

## 扩展建议

1. **引入传染病模型**：在马尔可夫链中加入 SIR/SEIR 传染病传播机制
2. **年龄分层**：按年龄段设置不同的转移概率矩阵
3. **社会网络**：引入个体间的社交关系，实现接触传播
4. **真实数据校准**：使用历史发病率和死亡率数据校准模型参数
