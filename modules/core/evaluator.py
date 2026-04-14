# modules/core/evaluator.py
"""
DEA/2SFCA 数学引擎
包含医疗资源配置核心数学模型：
- CCR-DEA 效率评估
- E2SFCA 空间可及性计算
"""

import numpy as np
import pandas as pd
from scipy.optimize import linprog
import logging
from typing import List, Dict, Union

logger = logging.getLogger("health_system.algorithms")


class HealthMathModels:
    """
    医疗资源配置核心数学模型库
    包含 DEA 效率评估、2SFCA 空间可及性等硬核算法
    """

    @staticmethod
    def calculate_dea_efficiency(X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        """
        基于线性规划的 CCR-DEA (数据包络分析) 模型
        用于计算各地区的医疗资源投入产出综合技术效率 (综合效率)

        参数:
            X: 投入矩阵 (n_dmus x m_inputs) - 如医生数、床位数、卫生经费
            Y: 产出矩阵 (n_dmus x s_outputs) - 如健康寿命、治愈率
        返回:
            efficiencies: 包含每个 DMU (决策单元) 效率得分的数组 [0, 1]
        """
        if X.size == 0 or Y.size == 0:
            from utils.logger import log_missing_data
            log_missing_data("HealthMathModels", "DEA Efficiency", 2024, "Global", "投入或产出矩阵为空")
            return np.array([])

        n_dmus, m_inputs = X.shape
        _, s_outputs = Y.shape
        efficiencies = np.zeros(n_dmus)

        # 遍历每一个 DMU (决策单元，即每一个地区)
        for k in range(n_dmus):
            # 添加极小值 epsilon (1e-6) 避免 0 值导致的 Unbounded 或无解错误
            x_k = X[k, :] + 1e-6
            y_k = Y[k, :] + 1e-6
            X_smooth = X + 1e-6
            Y_smooth = Y + 1e-6

            # 目标函数：最大化第 k 个 DMU 的加权产出
            # 在 scipy.linprog 中求最小值，因此目标系数取负
            c = np.concatenate((np.zeros(m_inputs), -y_k))

            # 约束条件 1: \sum v_i * x_{ik} = 1 (第 k 个 DMU 的加权投入等于 1)
            A_eq = np.concatenate((x_k, np.zeros(s_outputs))).reshape(1, -1)
            b_eq = np.array([1.0])

            # 约束条件 2: \sum u_r * y_{rj} - \sum v_i * x_{ij} <= 0 (所有 DMU 的产出不能超过投入)
            A_ub = np.hstack((-X_smooth, Y_smooth))
            b_ub = np.zeros(n_dmus)

            # 变量边界: 权重 v_i, u_r >= 0
            bounds = [(0, None) for _ in range(m_inputs + s_outputs)]

            try:
                # 求解线性规划
                res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
                if res.success:
                    # 效率值为目标函数的相反数
                    efficiencies[k] = -res.fun
                else:
                    efficiencies[k] = np.nan
                    logger.warning(f"DEA求解失败 DMU {k}: {res.message}")
            except Exception as e:
                efficiencies[k] = np.nan
                logger.error(f"DEA计算异常 DMU {k}: {str(e)}")

        # 修正可能因为浮点数精度导致的微小越界 (如 1.00000000002)
        efficiencies = np.clip(efficiencies, 0, 1.0)
        return efficiencies

    @staticmethod
    def haversine_distance(lat1: Union[float, np.ndarray], lon1: Union[float, np.ndarray],
                           lat2: Union[float, np.ndarray], lon2: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """计算地球上两点间的球面距离 (单位: 公里)"""
        R = 6371.0  # 地球平均半径 (公里)

        # 转换为弧度
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return R * c

    @staticmethod
    def calculate_e2sfca(supply_df: pd.DataFrame, demand_df: pd.DataFrame,
                         radius_col: str = 'search_radius', default_radius_km: float = 60.0,
                         decay_type: str = 'piecewise_power', beta: float = 1.5,
                         use_network_distance: bool = False) -> pd.Series:
        """
        计算增强型两步移动搜索法 (E2SFCA - Enhanced Two-Step Floating Catchment Area)
        支持分段功率衰减函数，并允许用户针对不同级别的医院自定义搜寻半径

        参数:
            supply_df: 必须包含 ['lat', 'lon', 'capacity']，可选包含 radius_col (搜寻半径)
            demand_df: 必须包含 ['lat', 'lon', 'population']
            radius_col: 供给点数据中定义搜寻半径的列名 (单位：公里)
            default_radius_km: 若未提供自定义半径，则使用的默认搜寻半径
            decay_type: 衰减函数类型 ('gaussian', 'power', 'piecewise_power')
            beta: 功率衰减指数
            use_network_distance: 是否使用真实路网距离(若无则回退到球面距离)
        返回:
            与 demand_df 索引对应的空间可及性指数序列
        """
        if supply_df.empty or demand_df.empty:
            from utils.logger import log_missing_data
            log_missing_data("HealthMathModels", "E2SFCA", 2024, "Global", "供需节点数据为空")
            return pd.Series(np.zeros(len(demand_df)), index=demand_df.index)

        # 提取或设定搜寻半径 (形如 (n_supply, 1))
        if radius_col and radius_col in supply_df.columns:
            thresholds = supply_df[radius_col].values[:, np.newaxis]
        else:
            thresholds = np.full((len(supply_df), 1), default_radius_km)

        # 定义多样化衰减函数
        def apply_decay(d, d0, method='gaussian', p_beta=1.5):
            if method == 'gaussian':
                return np.where(d <= d0, np.exp(-(d ** 2) / (2 * (d0 / 2) ** 2)), 0)
            elif method == 'power':
                return np.where(d <= d0, 1.0 / (np.maximum(d, 1.0) ** p_beta), 0)
            elif method == 'piecewise_power':
                # 分段功率衰减：将搜寻半径分为3个时间带 (如 0-1/3, 1/3-2/3, 2/3-1)
                z1 = d0 / 3.0
                z2 = d0 * (2.0 / 3.0)
                
                # 计算各段的代表距离（如中点距离）以得出权重
                m1 = np.maximum(z1 / 2.0, 1.0)
                m2 = np.maximum(z1 + z1 / 2.0, 1.0)
                m3 = np.maximum(z2 + z1 / 2.0, 1.0)
                
                w1 = 1.0 / (m1 ** p_beta)
                w2 = 1.0 / (m2 ** p_beta)
                w3 = 1.0 / (m3 ** p_beta)
                
                # 归一化使得最内层权重为 1.0
                w2_norm = w2 / w1
                w3_norm = w3 / w1
                
                weights = np.zeros_like(d)
                weights = np.where(d <= z1, 1.0, weights)
                weights = np.where((d > z1) & (d <= z2), w2_norm, weights)
                weights = np.where((d > z2) & (d <= d0), w3_norm, weights)
                return weights
            else:
                return np.where(d <= d0, 1.0, 0)

        # 提取坐标数组
        supply_coords = supply_df[['lat', 'lon']].values
        demand_coords = demand_df[['lat', 'lon']].values

        # 计算距离矩阵 (行: 供给点, 列: 需求点)
        if use_network_distance:
            pass

        # 球面距离计算
        lat1 = np.radians(supply_coords[:, 0])[:, np.newaxis]
        lon1 = np.radians(supply_coords[:, 1])[:, np.newaxis]
        lat2 = np.radians(demand_coords[:, 0])[np.newaxis, :]
        lon2 = np.radians(demand_coords[:, 1])[np.newaxis, :]

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        R = 6371.0
        dist_matrix = R * c

        # 步骤 1：计算供需比 R_j
        weights_matrix = apply_decay(dist_matrix, thresholds, method=decay_type, p_beta=beta)
        demand_pop = demand_df['population'].values
        
        weighted_demand = np.sum(weights_matrix * demand_pop, axis=1)
        
        supply_capacity = supply_df['capacity'].values
        R_j = np.zeros_like(supply_capacity, dtype=float)
        valid_idx = weighted_demand > 0
        R_j[valid_idx] = supply_capacity[valid_idx] / weighted_demand[valid_idx]

        supply_df['R_j'] = R_j

        # 步骤 2：计算空间可及性指数
        access_scores = np.sum(weights_matrix * R_j[:, np.newaxis], axis=0)

        return pd.Series(access_scores, index=demand_df.index)


class SpatialEngine:
    """
    空间决策引擎 - 负责所有基于地理位置的医疗资源评估与规划

    该类整合了空间可达性分析、应急路线规划和设施布局优化三大核心功能，
    为医疗资源配置提供全面的空间决策支持。

    设计原则：
    - 高性能：使用向量化计算和缓存机制优化大规模数据处理
    - 模块化：各功能方法独立，可根据需求单独调用
    - 健壮性：完善的输入验证和错误处理

    依赖：
        - numpy/pandas: 数值计算
        - scipy: 空间算法
        - utils.spatial_utils: 基础空间计算工具

    示例:
        >>> engine = SpatialEngine(cache_size=128)
        >>> 
        >>> # 计算可达性
        >>> access = engine.calculate_accessibility(supply_df, demand_df)
        >>> 
        >>> # 应急路线规划
        >>> routes = engine.plan_emergency_routes(30.6, 104.0, hospital_df)
        >>> 
        >>> # 设施布局优化
        >>> layout = engine.optimize_facility_layout(facilities, population)
    """

    def __init__(self, cache_size: int = 128, enable_progress: bool = True):
        """
        初始化空间决策引擎

        Args:
            cache_size: LRU缓存大小，用于缓存距离矩阵等中间结果
            enable_progress: 是否启用长时操作的进度显示

        示例:
            >>> engine = SpatialEngine(cache_size=256)
        """
        from functools import lru_cache
        from typing import Callable

        self.cache_size = cache_size
        self.enable_progress = enable_progress
        self.logger = logging.getLogger("health_system.spatial_engine")

        # 创建带缓存的距离计算函数
        self._cached_distance_calc = lru_cache(maxsize=cache_size)(self._compute_distance_matrix_impl)

        # 统计信息
        self.stats = {
            'distance_calculations': 0,
            'cache_hits': 0,
            'accessibility_computations': 0,
            'emergency_plans': 0,
            'layout_optimizations': 0
        }

    def _compute_distance_matrix_impl(
        self,
        supply_coords_tuple: tuple,
        demand_coords_tuple: tuple
    ) -> np.ndarray:
        """
        计算供给点与需求点之间的距离矩阵（实现层）

        使用Haversine公式计算球面距离，支持批量计算。
        坐标以元组形式传入以便缓存。

        Args:
            supply_coords_tuple: 供给点坐标元组 ((lat1, lon1), (lat2, lon2), ...)
            demand_coords_tuple: 需求点坐标元组 ((lat1, lon1), (lat2, lon2), ...)

        Returns:
            距离矩阵 (n_supply x n_demand)，单位：公里
        """
        supply_coords = np.array(supply_coords_tuple)
        demand_coords = np.array(demand_coords_tuple)

        # 使用向量化Haversine计算
        from utils.spatial_utils import SpatialUtils

        n_supply = len(supply_coords)
        n_demand = len(demand_coords)

        # 扩展维度以便广播计算
        lat1 = supply_coords[:, 0][:, np.newaxis]  # (n_supply, 1)
        lon1 = supply_coords[:, 1][:, np.newaxis]
        lat2 = demand_coords[:, 0][np.newaxis, :]  # (1, n_demand)
        lon2 = demand_coords[:, 1][np.newaxis, :]

        # 使用SpatialUtils批量计算
        dist_matrix = SpatialUtils.haversine_distance(lat1, lon1, lat2, lon2)

        return dist_matrix

    def _compute_distance_matrix(
        self,
        supply_df: pd.DataFrame,
        demand_df: pd.DataFrame,
        lat_col: str = 'lat',
        lon_col: str = 'lon'
    ) -> np.ndarray:
        """
        计算供给点与需求点之间的距离矩阵（带缓存）

        Args:
            supply_df: 供给点DataFrame，需包含 lat/lon 列
            demand_df: 需求点DataFrame，需包含 lat/lon 列
            lat_col: 纬度列名
            lon_col: 经度列名

        Returns:
            距离矩阵 (n_supply x n_demand)，单位：公里

        Raises:
            ValueError: 输入数据缺少必要的坐标列
        """
        # 验证输入
        for df, name in [(supply_df, 'supply_df'), (demand_df, 'demand_df')]:
            if lat_col not in df.columns:
                raise ValueError(f"{name} 缺少纬度列 '{lat_col}'")
            if lon_col not in df.columns:
                raise ValueError(f"{name} 缺少经度列 '{lon_col}'")

        # 转换为元组以便缓存
        supply_coords = tuple(map(tuple, supply_df[[lat_col, lon_col]].values))
        demand_coords = tuple(map(tuple, demand_df[[lat_col, lon_col]].values))

        # 检查缓存
        cache_key = (supply_coords, demand_coords)

        try:
            dist_matrix = self._cached_distance_calc(supply_coords, demand_coords)
            self.stats['cache_hits'] += 1
        except Exception:
            # 缓存未命中，重新计算
            dist_matrix = self._compute_distance_matrix_impl(supply_coords, demand_coords)

        self.stats['distance_calculations'] += 1
        return dist_matrix

    def calculate_accessibility(
        self,
        supply_df: pd.DataFrame,
        demand_df: pd.DataFrame,
        method: str = 'e2sfca',
        decay_type: str = 'gaussian',
        threshold_km: float = 5.0,
        beta: float = 1.5,
        capacity_col: str = 'capacity',
        pop_col: str = 'population',
        lat_col: str = 'lat',
        lon_col: str = 'lon',
        use_elderly_weight: bool = False,
        elderly_col: str = 'elderly_ratio'
    ) -> pd.DataFrame:
        """
        计算医疗资源空间可达性

        实现增强型两步移动搜索法 (E2SFCA) 和引力模型，评估各地区
        医疗资源的空间可达性水平。

        算法参考:
            - Luo & Wang (2003): Two-step floating catchment area method
            - Wan et al. (2012): Enhanced 2SFCA with flexible catchment sizes
            - 整合自: modules/spatial/urban_accessibility.py

        Args:
            supply_df: 供给端数据，需包含 lat/lon/capacity 列
            demand_df: 需求端数据，需包含 lat/lon/population 列
            method: 计算方法 ('e2sfca' 或 'gravity')
            decay_type: 距离衰减函数类型 ('gaussian', 'power', 'piecewise_power', 'binary')
            threshold_km: 搜寻半径阈值（公里）
            beta: 功率衰减指数（用于power和piecewise_power）
            capacity_col: 供给能力列名
            pop_col: 人口列名
            lat_col: 纬度列名
            lon_col: 经度列名
            use_elderly_weight: 是否对老龄化地区加权（弱势群体优先）
            elderly_col: 老龄化率列名

        Returns:
            包含可达性指数的DataFrame（基于demand_df的副本）

        Raises:
            ValueError: 输入数据验证失败或参数无效
            TypeError: 输入类型错误

        示例:
            >>> engine = SpatialEngine()
            >>> result = engine.calculate_accessibility(
            ...     supply_df=hospitals,
            ...     demand_df=communities,
            ...     method='e2sfca',
            ...     threshold_km=5.0,
            ...     use_elderly_weight=True
            ... )
            >>> print(result['accessibility_index'].describe())
        """
        import time
        start_time = time.time()

        # ========== 输入验证 ==========
        if not isinstance(supply_df, pd.DataFrame) or not isinstance(demand_df, pd.DataFrame):
            raise TypeError("supply_df 和 demand_df 必须是 pandas DataFrame")

        if supply_df.empty or demand_df.empty:
            raise ValueError("供给或需求数据不能为空")

        required_supply = [lat_col, lon_col, capacity_col]
        required_demand = [lat_col, lon_col, pop_col]

        for col in required_supply:
            if col not in supply_df.columns:
                raise ValueError(f"supply_df 缺少必要列: {col}")

        for col in required_demand:
            if col not in demand_df.columns:
                raise ValueError(f"demand_df 缺少必要列: {col}")

        if use_elderly_weight and elderly_col not in demand_df.columns:
            self.logger.warning(f"elderly_col '{elderly_col}' 不存在，忽略老龄化权重")
            use_elderly_weight = False

        # 创建结果副本
        result_df = demand_df.copy()

        # ========== 计算距离矩阵 ==========
        dist_matrix = self._compute_distance_matrix(
            supply_df, demand_df, lat_col, lon_col
        )

        # 添加小值避免除零
        dist_matrix = dist_matrix + 0.001

        # ========== 距离衰减函数 ==========
        def apply_decay(d: np.ndarray, d0: float, method: str) -> np.ndarray:
            """应用距离衰减函数"""
            if method == 'gaussian':
                # 高斯衰减: W = exp(-(d/d0)^2)
                weights = np.exp(-(d / d0) ** 2)
                weights[d > d0] = 0
                return weights
            elif method == 'power':
                # 幂函数衰减: W = 1 / d^beta
                weights = np.where(d <= d0, 1.0 / (np.maximum(d, 1.0) ** beta), 0)
                return weights
            elif method == 'piecewise_power':
                # 分段幂衰减 (E2SFCA标准)
                z1, z2 = d0 / 3.0, d0 * (2.0 / 3.0)
                m1 = np.maximum(z1 / 2.0, 1.0)
                m2 = np.maximum(z1 + z1 / 2.0, 1.0)
                m3 = np.maximum(z2 + z1 / 2.0, 1.0)
                w1, w2, w3 = 1.0, 1.0 / (m2 ** beta), 1.0 / (m3 ** beta)
                w2_norm, w3_norm = w2 / w1, w3 / w1

                weights = np.zeros_like(d)
                weights = np.where(d <= z1, 1.0, weights)
                weights = np.where((d > z1) & (d <= z2), w2_norm, weights)
                weights = np.where((d > z2) & (d <= d0), w3_norm, weights)
                return weights
            elif method == 'binary':
                # 二进制阈值
                return np.where(d <= d0, 1.0, 0.0)
            else:
                raise ValueError(f"未知的衰减函数类型: {method}")

        # ========== 提取数据 ==========
        supply_capacity = supply_df[capacity_col].values
        demand_pop = demand_df[pop_col].values

        # ========== 方法选择 ==========
        if method == 'e2sfca':
            # ===== E2SFCA 方法 =====
            weights_matrix = apply_decay(dist_matrix, threshold_km, decay_type)

            # 步骤1: 计算供需比 R_j
            weighted_demand = np.sum(weights_matrix * demand_pop, axis=1)
            R_j = np.zeros_like(supply_capacity, dtype=float)
            valid_mask = weighted_demand > 0
            R_j[valid_mask] = supply_capacity[valid_mask] / weighted_demand[valid_mask]

            # 步骤2: 计算可达性指数
            access_scores = np.sum(weights_matrix * R_j[:, np.newaxis], axis=0)

            # 应用老龄化权重（弱势群体优先）
            if use_elderly_weight:
                elderly_ratios = demand_df[elderly_col].fillna(0).values
                weights = np.where(elderly_ratios > 0.2, 1.5, 1.0)
                access_scores = access_scores / weights

            result_df['accessibility_index'] = access_scores

        elif method == 'gravity':
            # ===== 引力模型 =====
            # 衰减矩阵 (n_supply x n_demand)
            decay_matrix = dist_matrix ** -beta

            # 计算供需潜力
            # V_j: 每个供给点的需求加权和 (n_supply,)
            V_j = np.dot(decay_matrix, demand_pop)
            # A_i: 每个需求点的可达性 (n_demand,)
            # supply_capacity / V_j 得到每个供给点的供需比，然后加权求和到每个需求点
            supply_ratio = supply_capacity / np.maximum(V_j, 1e-10)
            A_i = np.dot(supply_ratio, decay_matrix)  # (n_supply,) dot (n_supply, n_demand) = (n_demand,)

            result_df['accessibility_index'] = A_i

        else:
            raise ValueError(f"未知的计算方法: {method}，支持 'e2sfca' 或 'gravity'")

        # 记录统计
        self.stats['accessibility_computations'] += 1
        elapsed = time.time() - start_time
        self.logger.info(f"可达性计算完成: {len(demand_df)} 个需求点, {len(supply_df)} 个供给点, 耗时 {elapsed:.3f}s")

        return result_df

    def plan_emergency_routes(
        self,
        incident_lat: float,
        incident_lon: float,
        hospital_df: pd.DataFrame,
        max_routes: int = 3,
        response_time_weight: float = 0.7,
        capacity_weight: float = 0.3,
        lat_col: str = 'lat',
        lon_col: str = 'lon',
        capacity_col: str = 'capacity',
        name_col: str = 'name'
    ) -> Dict:
        """
        规划应急响应路线

        根据事件发生位置，综合考虑距离、医院容量和响应优先级，
        推荐最优的应急响应医院及预计到达时间。

        算法参考:
            - 基于最短路径的贪心选择
            - 整合自: modules/spatial/emergency_planner.py
            - 考虑SIR模型推演需求

        Args:
            incident_lat: 事件发生纬度
            incident_lon: 事件发生经度
            hospital_df: 医院数据，需包含 lat/lon/capacity/name 列
            max_routes: 返回的最优路线数量
            response_time_weight: 响应时间权重 (0-1)
            capacity_weight: 医院容量权重 (0-1)
            lat_col: 纬度列名
            lon_col: 经度列名
            capacity_col: 容量列名
            name_col: 医院名称列名

        Returns:
            包含应急规划结果的字典:
            {
                'incident_location': {'lat': float, 'lon': float},
                'recommended_hospitals': [
                    {
                        'rank': int,
                        'name': str,
                        'distance_km': float,
                        'estimated_time_min': float,
                        'capacity_score': float,
                        'priority_score': float,
                        'lat': float,
                        'lon': float
                    },
                    ...
                ],
                'total_options': int,
                'planning_timestamp': str
            }

        Raises:
            ValueError: 输入参数无效或医院数据不足
            TypeError: 坐标类型错误

        示例:
            >>> engine = SpatialEngine()
            >>> routes = engine.plan_emergency_routes(
            ...     incident_lat=30.6586,
            ...     incident_lon=104.0648,
            ...     hospital_df=hospitals,
            ...     max_routes=3
            ... )
            >>> for hospital in routes['recommended_hospitals']:
            ...     print(f"{hospital['rank']}. {hospital['name']}: {hospital['estimated_time_min']:.1f}分钟")
        """
        import time
        from datetime import datetime

        start_time = time.time()

        # ========== 输入验证 ==========
        if not isinstance(incident_lat, (int, float)) or not isinstance(incident_lon, (int, float)):
            raise TypeError("事件坐标必须是数值类型")

        if not (-90 <= incident_lat <= 90):
            raise ValueError(f"纬度 {incident_lat} 超出有效范围 [-90, 90]")
        if not (-180 <= incident_lon <= 180):
            raise ValueError(f"经度 {incident_lon} 超出有效范围 [-180, 180]")

        if not isinstance(hospital_df, pd.DataFrame):
            raise TypeError("hospital_df 必须是 pandas DataFrame")

        if hospital_df.empty:
            raise ValueError("医院数据不能为空")

        required_cols = [lat_col, lon_col, capacity_col]
        for col in required_cols:
            if col not in hospital_df.columns:
                raise ValueError(f"hospital_df 缺少必要列: {col}")

        if len(hospital_df) < max_routes:
            max_routes = len(hospital_df)
            self.logger.warning(f"医院数量不足，调整 max_routes 为 {max_routes}")

        # ========== 计算到各医院的距离 ==========
        from utils.spatial_utils import SpatialUtils

        hospital_lats = hospital_df[lat_col].values
        hospital_lons = hospital_df[lon_col].values

        distances = SpatialUtils.haversine_distance(
            incident_lat, incident_lon,
            hospital_lats, hospital_lons
        )

        # ========== 计算综合评分 ==========
        # 假设平均车速 40 km/h（城市道路考虑拥堵）
        AVG_SPEED_KMH = 40.0

        # 响应时间（分钟）
        response_times = (distances / AVG_SPEED_KMH) * 60

        # 容量标准化得分 (0-1)
        capacities = hospital_df[capacity_col].values
        if capacities.max() > capacities.min():
            capacity_scores = (capacities - capacities.min()) / (capacities.max() - capacities.min())
        else:
            capacity_scores = np.ones_like(capacities)

        # 时间得分（越短越好，反转并标准化）
        if response_times.max() > response_times.min():
            time_scores = 1 - (response_times - response_times.min()) / (response_times.max() - response_times.min())
        else:
            time_scores = np.ones_like(response_times)

        # 综合优先级评分
        priority_scores = (
            response_time_weight * time_scores +
            capacity_weight * capacity_scores
        )

        # ========== 排序并选择最优路线 ==========
        # 获取排序索引
        sorted_indices = np.argsort(priority_scores)[::-1]

        recommended_hospitals = []
        for rank, idx in enumerate(sorted_indices[:max_routes], 1):
            hospital = hospital_df.iloc[idx]

            recommended_hospitals.append({
                'rank': rank,
                'name': hospital.get(name_col, f'Hospital_{idx}'),
                'distance_km': float(distances[idx]),
                'estimated_time_min': float(response_times[idx]),
                'capacity_score': float(capacity_scores[idx]),
                'priority_score': float(priority_scores[idx]),
                'lat': float(hospital[lat_col]),
                'lon': float(hospital[lon_col])
            })

        # ========== 构建返回结果 ==========
        result = {
            'incident_location': {
                'lat': float(incident_lat),
                'lon': float(incident_lon)
            },
            'recommended_hospitals': recommended_hospitals,
            'total_options': len(hospital_df),
            'planning_timestamp': datetime.now().isoformat(),
            'algorithm_params': {
                'response_time_weight': response_time_weight,
                'capacity_weight': capacity_weight,
                'avg_speed_kmh': AVG_SPEED_KMH
            }
        }

        # 记录统计
        self.stats['emergency_plans'] += 1
        elapsed = time.time() - start_time
        self.logger.info(f"应急路线规划完成: 从 ({incident_lat:.4f}, {incident_lon:.4f}) 到 {len(hospital_df)} 家医院, 耗时 {elapsed:.3f}s")

        return result

    def optimize_facility_layout(
        self,
        current_facilities: pd.DataFrame,
        population_heatmap: pd.DataFrame,
        optimization_method: str = 'coverage_gap',
        max_new_facilities: int = 2,
        coverage_radius_km: float = 5.0,
        min_population_threshold: int = 50000,
        facility_lat_col: str = 'lat',
        facility_lon_col: str = 'lon',
        pop_lat_col: str = 'lat',
        pop_lon_col: str = 'lon',
        pop_col: str = 'population'
    ) -> Dict:
        """
        优化医疗设施布局

        分析现有设施分布与人口密度的匹配程度，识别服务盲区，
        并推荐最优的新设施选址。

        算法参考:
            - 最大覆盖问题 (Maximum Coverage Problem)
            - 贪心算法逐步选择最优位置
            - 整合自: modules/spatial/layout_optimizer.py
            - 基尼系数评估不平等程度

        Args:
            current_facilities: 现有设施数据，需包含 lat/lon 列
            population_heatmap: 人口热力图数据，需包含 lat/lon/population 列
            optimization_method: 优化方法 ('coverage_gap', 'equal_access', 'min_distance')
            max_new_facilities: 推荐的新设施最大数量
            coverage_radius_km: 服务覆盖半径（公里）
            min_population_threshold: 最小人口阈值（低于此值不考虑建设施）
            facility_lat_col: 设施纬度列名
            facility_lon_col: 设施经度列名
            pop_lat_col: 人口纬度列名
            pop_lon_col: 人口经度列名
            pop_col: 人口列名

        Returns:
            包含布局优化结果的字典:
            {
                'current_coverage': {
                    'coverage_rate': float,  # 当前覆盖率 (0-1)
                    'avg_distance_km': float,
                    'gini_coefficient': float  # 不平等系数
                },
                'blind_spots': pd.DataFrame,  # 识别的服务盲区
                'recommendations': [
                    {
                        'rank': int,
                        'lat': float,
                        'lon': float,
                        'priority_population': int,
                        'expected_coverage_increase': float,
                        'justification': str
                    },
                    ...
                ],
                'projected_coverage': {
                    'coverage_rate': float,  # 建设新设施后的预期覆盖率
                    'improvement_percentage': float
                }
            }

        Raises:
            ValueError: 输入数据无效或参数错误
            TypeError: 输入类型错误

        示例:
            >>> engine = SpatialEngine()
            >>> layout = engine.optimize_facility_layout(
            ...     current_facilities=existing_hospitals,
            ...     population_heatmap=pop_density,
            ...     max_new_facilities=3,
            ...     coverage_radius_km=5.0
            ... )
            >>> print(f"当前覆盖率: {layout['current_coverage']['coverage_rate']:.1%}")
            >>> for rec in layout['recommendations']:
            ...     print(f"建议位置: ({rec['lat']:.4f}, {rec['lon']:.4f})")
        """
        import time
        from datetime import datetime

        start_time = time.time()

        # ========== 输入验证 ==========
        if not isinstance(current_facilities, pd.DataFrame) or not isinstance(population_heatmap, pd.DataFrame):
            raise TypeError("current_facilities 和 population_heatmap 必须是 pandas DataFrame")

        if current_facilities.empty:
            self.logger.warning("现有设施数据为空，将基于纯人口分布进行规划")

        if population_heatmap.empty:
            raise ValueError("人口热力图数据不能为空")

        # 验证必要列
        for df, name, lat_col, lon_col in [
            (current_facilities, 'current_facilities', facility_lat_col, facility_lon_col),
            (population_heatmap, 'population_heatmap', pop_lat_col, pop_lon_col)
        ]:
            if not df.empty:
                if lat_col not in df.columns:
                    raise ValueError(f"{name} 缺少纬度列: {lat_col}")
                if lon_col not in df.columns:
                    raise ValueError(f"{name} 缺少经度列: {lon_col}")

        if pop_col not in population_heatmap.columns:
            raise ValueError(f"population_heatmap 缺少人口列: {pop_col}")

        if optimization_method not in ['coverage_gap', 'equal_access', 'min_distance']:
            raise ValueError(f"未知的优化方法: {optimization_method}")

        # ========== 计算当前覆盖情况 ==========
        pop_coords = population_heatmap[[pop_lat_col, pop_lon_col]].values
        pop_values = population_heatmap[pop_col].values
        total_population = pop_values.sum()

        if total_population == 0:
            raise ValueError("总人口为0，无法进行布局优化")

        # 导入空间工具
        from utils.spatial_utils import SpatialUtils

        # 计算每个人口点到最近设施的距离
        if not current_facilities.empty:
            facility_coords = current_facilities[[facility_lat_col, facility_lon_col]].values

            # 扩展维度计算所有点对距离
            lat1 = facility_coords[:, 0][:, np.newaxis]
            lon1 = facility_coords[:, 1][:, np.newaxis]
            lat2 = pop_coords[:, 0][np.newaxis, :]
            lon2 = pop_coords[:, 1][np.newaxis, :]

            dist_matrix = SpatialUtils.haversine_distance(lat1, lon1, lat2, lon2)
            min_distances = dist_matrix.min(axis=0)  # 每个需求点到最近设施的距离

            # 计算覆盖率
            covered_mask = min_distances <= coverage_radius_km
            current_coverage_rate = pop_values[covered_mask].sum() / total_population
            avg_distance = np.average(min_distances, weights=pop_values)

            # 计算基尼系数（不平等程度）
            sorted_distances = np.sort(min_distances)
            n = len(sorted_distances)
            cumsum = np.cumsum(sorted_distances)
            gini = (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n if cumsum[-1] > 0 else 0
        else:
            # 无现有设施
            min_distances = np.full(len(population_heatmap), np.inf)
            current_coverage_rate = 0.0
            avg_distance = np.inf
            gini = 1.0  # 最大不平等

        # ========== 识别服务盲区 ==========
        blind_spots_mask = min_distances > coverage_radius_km
        blind_spots = population_heatmap[blind_spots_mask].copy()
        blind_spots['distance_to_nearest'] = min_distances[blind_spots_mask]

        # 过滤人口过低的区域
        if min_population_threshold > 0:
            blind_spots = blind_spots[blind_spots[pop_col] >= min_population_threshold]

        # ========== 推荐新设施位置 ==========
        recommendations = []

        if len(blind_spots) > 0 and max_new_facilities > 0:
            if optimization_method == 'coverage_gap':
                # ===== 最大覆盖缺口法 =====
                # 贪心算法：每次选择能覆盖最多未服务人口的位置

                remaining_blind = blind_spots.copy()
                selected_facilities = []

                for i in range(max_new_facilities):
                    if remaining_blind.empty:
                        break

                    # 对每个候选位置，计算其覆盖的未服务人口
                    best_coverage = 0
                    best_idx = None
                    best_coords = None

                    # 简化：从盲区中选择人口密度最高的点
                    # 实际应用中可以使用更复杂的搜索算法
                    candidate = remaining_blind.loc[remaining_blind[pop_col].idxmax()]
                    best_coords = (candidate[pop_lat_col], candidate[pop_lon_col])
                    best_population = candidate[pop_col]

                    # 计算该位置能覆盖多少人口
                    lat_c, lon_c = best_coords
                    distances_to_candidate = SpatialUtils.haversine_distance(
                        lat_c, lon_c,
                        pop_coords[:, 0], pop_coords[:, 1]
                    )

                    # 新覆盖的人口（原本未被覆盖且在半径内）
                    newly_covered = (distances_to_candidate <= coverage_radius_km) & blind_spots_mask
                    coverage_increase = pop_values[newly_covered].sum() / total_population

                    recommendations.append({
                        'rank': i + 1,
                        'lat': float(best_coords[0]),
                        'lon': float(best_coords[1]),
                        'priority_population': int(best_population),
                        'expected_coverage_increase': float(coverage_increase),
                        'justification': f'覆盖盲区，服务人口约 {int(best_population):,} 人'
                    })

                    # 更新盲区（移除已被覆盖的区域）
                    remaining_blind_mask = distances_to_candidate > coverage_radius_km
                    if remaining_blind_mask.any():
                        remaining_blind = remaining_blind[remaining_blind_mask[remaining_blind.index]]
                    else:
                        break

            elif optimization_method == 'equal_access':
                # ===== 平等可达性法 =====
                # 优先选择距离现有设施最远的区域
                blind_spots_sorted = blind_spots.sort_values('distance_to_nearest', ascending=False)

                for i, (idx, row) in enumerate(blind_spots_sorted.head(max_new_facilities).iterrows()):
                    recommendations.append({
                        'rank': i + 1,
                        'lat': float(row[pop_lat_col]),
                        'lon': float(row[pop_lon_col]),
                        'priority_population': int(row[pop_col]),
                        'expected_coverage_increase': None,  # 需要进一步计算
                        'justification': f'距离最近设施 {row["distance_to_nearest"]:.1f} km，改善空间不平等'
                    })

            elif optimization_method == 'min_distance':
                # ===== 最小距离法 =====
                # 选择使平均距离最小化的位置
                # 简化实现：选择人口加权中心
                weighted_lat = np.average(blind_spots[pop_lat_col], weights=blind_spots[pop_col])
                weighted_lon = np.average(blind_spots[pop_lon_col], weights=blind_spots[pop_col])

                recommendations.append({
                    'rank': 1,
                    'lat': float(weighted_lat),
                    'lon': float(weighted_lon),
                    'priority_population': int(blind_spots[pop_col].sum()),
                    'expected_coverage_increase': None,
                    'justification': '人口加权中心位置，最小化平均服务距离'
                })

        # ========== 计算预期覆盖率 ==========
        projected_coverage_rate = current_coverage_rate
        if recommendations:
            # 简化计算：假设每个新设施增加一定的覆盖率
            for rec in recommendations:
                if rec['expected_coverage_increase']:
                    projected_coverage_rate += rec['expected_coverage_increase']

        projected_coverage_rate = min(projected_coverage_rate, 1.0)
        improvement = projected_coverage_rate - current_coverage_rate

        # ========== 构建返回结果 ==========
        result = {
            'current_coverage': {
                'coverage_rate': float(current_coverage_rate),
                'avg_distance_km': float(avg_distance) if np.isfinite(avg_distance) else None,
                'gini_coefficient': float(gini),
                'total_population': int(total_population),
                'covered_population': int(pop_values[covered_mask].sum()) if not current_facilities.empty else 0
            },
            'blind_spots': blind_spots[[pop_lat_col, pop_lon_col, pop_col, 'distance_to_nearest']].copy() if not blind_spots.empty else pd.DataFrame(),
            'recommendations': recommendations,
            'projected_coverage': {
                'coverage_rate': float(projected_coverage_rate),
                'improvement_percentage': float(improvement * 100),
                'new_facilities_count': len(recommendations)
            },
            'optimization_params': {
                'method': optimization_method,
                'coverage_radius_km': coverage_radius_km,
                'min_population_threshold': min_population_threshold,
                'max_new_facilities': max_new_facilities
            }
        }

        # 记录统计
        self.stats['layout_optimizations'] += 1
        elapsed = time.time() - start_time
        self.logger.info(f"设施布局优化完成: {len(current_facilities)} 现有设施, {len(population_heatmap)} 人口点, 推荐 {len(recommendations)} 新位置, 耗时 {elapsed:.3f}s")

        return result

    def get_statistics(self) -> Dict:
        """
        获取引擎使用统计信息

        Returns:
            包含各类操作统计的字典

        示例:
            >>> engine = SpatialEngine()
            >>> # ... 执行一些操作 ...
            >>> stats = engine.get_statistics()
            >>> print(f"距离计算次数: {stats['distance_calculations']}")
        """
        return self.stats.copy()

    def reset_statistics(self) -> None:
        """重置统计信息"""
        self.stats = {
            'distance_calculations': 0,
            'cache_hits': 0,
            'accessibility_computations': 0,
            'emergency_plans': 0,
            'layout_optimizations': 0
        }
        self.logger.info("统计信息已重置")
