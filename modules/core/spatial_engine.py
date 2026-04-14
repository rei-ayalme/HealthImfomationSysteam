# modules/core/spatial_engine.py
"""
空间决策引擎 - 负责所有基于地理位置的医疗资源评估与规划

该类整合了空间可达性分析、应急路线规划和设施布局优化三大核心功能，
为医疗资源配置提供全面的空间决策支持。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Literal, Optional, Tuple, List, Union

import numpy as np
import pandas as pd

from utils.spatial_utils import SpatialUtils

logger = logging.getLogger("health_system.spatial_engine")

DecayType = Literal["uniform", "inverse_power", "gaussian"]


@dataclass
class AccessibilityResult:
    """可达性计算结果"""
    accessibility: np.ndarray
    supply_ratio: np.ndarray
    metadata: Dict[str, float]


class SpatialEngine:
    """
    空间决策引擎 - 负责所有基于地理位置的医疗资源评估与规划
    
    该类整合了空间可达性分析、应急路线规划和设施布局优化三大核心功能，
    为医疗资源配置提供全面的空间决策支持。
    """

    def __init__(self, cache_size: int = 128, enable_progress: bool = True):
        """
        初始化空间决策引擎
        
        Args:
            cache_size: 缓存大小，用于缓存距离计算结果
            enable_progress: 是否启用进度跟踪
        """
        from functools import lru_cache
        
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
        """计算供给点与需求点之间的距离矩阵（实现层）"""
        supply_coords = np.array(supply_coords_tuple)
        demand_coords = np.array(demand_coords_tuple)
        
        n_supply = len(supply_coords)
        n_demand = len(demand_coords)
        
        # 使用向量化计算
        dist_matrix = np.zeros((n_demand, n_supply))
        for i in range(n_demand):
            dist_matrix[i, :] = SpatialUtils.haversine_distance(
                demand_coords[i][0], demand_coords[i][1],
                supply_coords[:, 0], supply_coords[:, 1]
            )
        
        return dist_matrix

    def _compute_distance_matrix(
        self,
        supply_coords: np.ndarray,
        demand_coords: np.ndarray
    ) -> np.ndarray:
        """计算距离矩阵（带缓存）"""
        supply_tuple = tuple(map(tuple, supply_coords))
        demand_tuple = tuple(map(tuple, demand_coords))
        
        self.stats['distance_calculations'] += 1
        return self._cached_distance_calc(supply_tuple, demand_tuple)

    def _build_weight_matrix(
        self,
        distance_matrix: np.ndarray,
        catchment: float,
        decay: DecayType,
        beta: float,
    ) -> np.ndarray:
        """构建权重矩阵"""
        if decay == "uniform":
            return (distance_matrix <= catchment).astype(np.float64)
        if decay == "inverse_power":
            mask = distance_matrix <= catchment
            safe_d = np.where(distance_matrix <= 0, 1e-9, distance_matrix)
            w = np.where(mask, np.power(safe_d, -beta), 0.0)
            return w.astype(np.float64)
        if decay == "gaussian":
            mask = distance_matrix <= catchment
            w = np.where(mask, np.exp(-0.5 * (distance_matrix / catchment) ** 2), 0.0)
            return w.astype(np.float64)
        raise ValueError(f"Unsupported decay: {decay}")

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
        
        使用增强型两步移动搜索法 (E2SFCA) 或重力模型计算空间可达性
        
        Args:
            supply_df: 供给点数据 (医院等)
            demand_df: 需求点数据 (人口分布等)
            method: 计算方法 ('e2sfca' 或 'gravity')
            decay_type: 距离衰减类型 ('gaussian', 'uniform', 'inverse_power')
            threshold_km: 搜索半径 (公里)
            beta: 距离衰减系数
            capacity_col: 供给能力列名
            pop_col: 人口列名
            lat_col: 纬度列名
            lon_col: 经度列名
            use_elderly_weight: 是否使用老年人口加权
            elderly_col: 老年人口比例列名
            
        Returns:
            包含可达性指标的 DataFrame
        """
        self.stats['accessibility_computations'] += 1
        
        # 提取坐标
        supply_coords = supply_df[[lat_col, lon_col]].values
        demand_coords = demand_df[[lat_col, lon_col]].values
        
        # 计算距离矩阵
        dist_matrix = self._compute_distance_matrix(supply_coords, demand_coords)
        
        # 提取供给和需求
        supply = supply_df[capacity_col].values
        demand = demand_df[pop_col].values
        
        # 老年人口加权
        if use_elderly_weight and elderly_col in demand_df.columns:
            elderly_weights = 1.0 + demand_df[elderly_col].fillna(0).values
            demand = demand * elderly_weights
        
        if method == 'e2sfca':
            return self._calculate_e2sfca(demand_df, dist_matrix, supply, demand, 
                                          threshold_km, decay_type, beta)
        elif method == 'gravity':
            return self._calculate_gravity(demand_df, dist_matrix, supply, demand, beta)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _calculate_e2sfca(
        self,
        demand_df: pd.DataFrame,
        dist_matrix: np.ndarray,
        supply: np.ndarray,
        demand: np.ndarray,
        threshold_km: float,
        decay_type: str,
        beta: float
    ) -> pd.DataFrame:
        """增强型两步移动搜索法 (E2SFCA)"""
        n_demand, n_supply = dist_matrix.shape
        
        # 第一步：计算每个供给点的供需比
        weight_matrix = self._build_weight_matrix(dist_matrix, threshold_km, decay_type, beta)
        weighted_demand = weight_matrix.T @ demand  # (n_supply,)
        
        # 避免除零
        supply_ratio = np.divide(
            supply, weighted_demand,
            out=np.zeros_like(supply, dtype=np.float64),
            where=weighted_demand > 0
        )
        
        # 第二步：计算每个需求点的可达性
        accessibility = weight_matrix @ supply_ratio  # (n_demand,)
        
        result_df = demand_df.copy()
        result_df['accessibility'] = accessibility
        result_df['supply_ratio'] = np.nan
        result_df.loc[result_df.index[:len(supply_ratio)], 'supply_ratio'] = supply_ratio
        
        return result_df

    def _calculate_gravity(
        self,
        demand_df: pd.DataFrame,
        dist_matrix: np.ndarray,
        supply: np.ndarray,
        demand: np.ndarray,
        beta: float
    ) -> pd.DataFrame:
        """重力模型可达性计算"""
        # 重力模型：A_i = sum_j (S_j * f(d_ij))
        # f(d) = d^(-beta)
        with np.errstate(divide='ignore', invalid='ignore'):
            friction = np.power(dist_matrix, -beta)
            friction[np.isinf(friction)] = 0
        
        accessibility = friction @ supply  # (n_demand,)
        
        result_df = demand_df.copy()
        result_df['accessibility'] = accessibility
        
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
        
        根据事故地点和医院分布，规划最优应急响应路线
        
        Args:
            incident_lat: 事故地点纬度
            incident_lon: 事故地点经度
            hospital_df: 医院数据
            max_routes: 最大返回路线数量
            response_time_weight: 响应时间权重
            capacity_weight: 医院容量权重
            lat_col: 纬度列名
            lon_col: 经度列名
            capacity_col: 容量列名
            name_col: 名称列名
            
        Returns:
            包含推荐路线和医院信息的字典
        """
        self.stats['emergency_plans'] += 1
        
        if hospital_df.empty:
            return {
                'status': 'error',
                'message': 'No hospitals available',
                'routes': []
            }
        
        # 计算到每个医院的距离
        hospital_coords = hospital_df[[lat_col, lon_col]].values
        distances = SpatialUtils.haversine_distance(
            incident_lat, incident_lon,
            hospital_coords[:, 0], hospital_coords[:, 1]
        )
        
        # 估算响应时间 (假设平均速度 60 km/h)
        response_times = distances / 60.0 * 60  # 转换为分钟
        
        # 计算综合评分 (越低越好)
        # 归一化
        norm_time = (response_times - response_times.min()) / (response_times.max() - response_times.min() + 1e-9)
        norm_capacity = 1.0 - (hospital_df[capacity_col].values - hospital_df[capacity_col].min()) / \
                             (hospital_df[capacity_col].max() - hospital_df[capacity_col].min() + 1e-9)
        
        scores = response_time_weight * norm_time + capacity_weight * norm_capacity
        
        # 选择最优路线
        best_indices = np.argsort(scores)[:max_routes]
        
        routes = []
        for idx in best_indices:
            hospital = hospital_df.iloc[idx]
            routes.append({
                'hospital_name': hospital[name_col],
                'distance_km': round(float(distances[idx]), 2),
                'estimated_time_min': round(float(response_times[idx]), 1),
                'capacity': int(hospital[capacity_col]),
                'score': round(float(scores[idx]), 3),
                'destination_lat': float(hospital[lat_col]),
                'destination_lon': float(hospital[lon_col])
            })
        
        return {
            'status': 'success',
            'incident_location': {'lat': incident_lat, 'lon': incident_lon},
            'routes': routes,
            'total_hospitals_considered': len(hospital_df)
        }

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
        
        分析当前设施分布与人口密度的匹配度，推荐新设施选址
        
        Args:
            current_facilities: 现有设施数据
            population_heatmap: 人口热力图数据
            optimization_method: 优化方法 ('coverage_gap' 或 'demand_based')
            max_new_facilities: 最大新增设施数
            coverage_radius_km: 覆盖半径 (公里)
            min_population_threshold: 最小人口阈值
            facility_lat_col: 设施纬度列名
            facility_lon_col: 设施经度列名
            pop_lat_col: 人口纬度列名
            pop_lon_col: 人口经度列名
            pop_col: 人口列名
            
        Returns:
            包含优化建议的字典
        """
        self.stats['layout_optimizations'] += 1
        
        if population_heatmap.empty:
            return {
                'status': 'error',
                'message': 'Population data is empty',
                'recommendations': []
            }
        
        # 筛选高密度人口区域
        high_pop_areas = population_heatmap[
            population_heatmap[pop_col] >= min_population_threshold
        ].copy()
        
        if high_pop_areas.empty:
            return {
                'status': 'warning',
                'message': f'No areas with population >= {min_population_threshold}',
                'recommendations': []
            }
        
        # 计算每个高人口区域的设施覆盖情况
        pop_coords = high_pop_areas[[pop_lat_col, pop_lon_col]].values
        
        if current_facilities.empty:
            # 无现有设施，所有高人口区域都是缺口
            coverage_gap = high_pop_areas[pop_col].values
            uncovered = high_pop_areas.copy()
        else:
            facility_coords = current_facilities[[facility_lat_col, facility_lon_col]].values
            
            # 计算每个人口区域到最近设施的距离
            min_distances = np.zeros(len(high_pop_areas))
            for i in range(len(high_pop_areas)):
                distances = SpatialUtils.haversine_distance(
                    pop_coords[i, 0], pop_coords[i, 1],
                    facility_coords[:, 0], facility_coords[:, 1]
                )
                min_distances[i] = distances.min()
            
            # 识别覆盖缺口 (距离 > 覆盖半径)
            high_pop_areas['distance_to_nearest'] = min_distances
            uncovered = high_pop_areas[min_distances > coverage_radius_km].copy()
            
            if uncovered.empty:
                return {
                    'status': 'success',
                    'message': 'All high-population areas are adequately covered',
                    'recommendations': [],
                    'coverage_rate': 1.0
                }
            
            # 按人口加权缺口排序
            coverage_gap = uncovered[pop_col].values
            pop_coords = uncovered[[pop_lat_col, pop_lon_col]].values
        
        # 简单的聚类推荐 (选择缺口最大的点)
        # 实际应用中可以使用更复杂的算法如 k-means 或 p-median
        recommendations = []
        
        # 按缺口大小排序并选择
        gap_indices = np.argsort(coverage_gap)[-max_new_facilities:][::-1]
        
        for rank, idx in enumerate(gap_indices, 1):
            recommendations.append({
                'rank': rank,
                'recommended_lat': float(pop_coords[idx, 0]),
                'recommended_lon': float(pop_coords[idx, 1]),
                'target_population': int(uncovered.iloc[idx][pop_col]),
                'coverage_gap_score': round(float(coverage_gap[idx]), 2),
                'rationale': f'High population area with insufficient facility coverage'
            })
        
        total_high_pop = len(high_pop_areas)
        uncovered_count = len(uncovered)
        
        return {
            'status': 'success',
            'optimization_method': optimization_method,
            'coverage_radius_km': coverage_radius_km,
            'total_high_population_areas': total_high_pop,
            'uncovered_areas': int(uncovered_count),
            'coverage_rate': round(1 - uncovered_count / total_high_pop, 3) if total_high_pop > 0 else 0,
            'recommendations': recommendations
        }

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.stats.copy()

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            'distance_calculations': 0,
            'cache_hits': 0,
            'accessibility_computations': 0,
            'emergency_plans': 0,
            'layout_optimizations': 0
        }


# 向后兼容：保留原有的函数接口
def baseline_2sfca(
    distance_matrix: np.ndarray,
    demand_array: np.ndarray,
    supply_array: np.ndarray,
    catchment: float = 30.0,
    decay: DecayType = "uniform",
    beta: float = 1.0,
) -> AccessibilityResult:
    """
    基线版 2SFCA：显式双层循环，便于理解但性能较低。
    """
    d = np.asarray(distance_matrix, dtype=np.float64)
    dem = np.asarray(demand_array, dtype=np.float64)
    sup = np.asarray(supply_array, dtype=np.float64)

    n, m = d.shape
    weights = [[0.0 for _ in range(m)] for _ in range(n)]
    for i in range(n):
        for j in range(m):
            dij = d[i, j]
            if dij <= catchment:
                if decay == "uniform":
                    weights[i][j] = 1.0
                elif decay == "inverse_power":
                    safe_d = dij if dij > 0 else 1e-9
                    weights[i][j] = safe_d ** (-beta)
                else:
                    raise ValueError(f"Unsupported decay: {decay}")

    weights_shadow = [row[:] for row in weights]
    weights_meta = [
        [{"w": weights_shadow[i][j], "d": float(d[i, j])} for j in range(m)]
        for i in range(n)
    ]

    supply_ratio = np.zeros(m, dtype=np.float64)
    for j in range(m):
        weighted_demand = 0.0
        for i in range(n):
            weighted_demand += dem[i] * weights_meta[i][j]["w"]
        if weighted_demand > 0:
            supply_ratio[j] = sup[j] / weighted_demand
        else:
            supply_ratio[j] = 0.0

    accessibility = np.zeros(n, dtype=np.float64)
    for i in range(n):
        acc = 0.0
        for j in range(m):
            acc += supply_ratio[j] * weights_meta[i][j]["w"]
        accessibility[i] = acc

    return AccessibilityResult(
        accessibility=accessibility,
        supply_ratio=supply_ratio,
        metadata={"n_demand": float(n), "n_supply": float(m)},
    )


def optimized_2sfca(
    distance_matrix: np.ndarray,
    demand_array: np.ndarray,
    supply_array: np.ndarray,
    catchment: float = 30.0,
    decay: DecayType = "uniform",
    beta: float = 1.0,
    precomputed_weights: Optional[np.ndarray] = None,
) -> AccessibilityResult:
    """
    向量化优化版 2SFCA。
    """
    d = np.asarray(distance_matrix, dtype=np.float64)
    dem = np.asarray(demand_array, dtype=np.float64)
    sup = np.asarray(supply_array, dtype=np.float64)

    def _build_weight_matrix(
        distance_matrix: np.ndarray,
        catchment: float,
        decay: DecayType,
        beta: float,
    ) -> np.ndarray:
        if decay == "uniform":
            return (distance_matrix <= catchment).astype(np.float64)
        if decay == "inverse_power":
            mask = distance_matrix <= catchment
            safe_d = np.where(distance_matrix <= 0, 1e-9, distance_matrix)
            w = np.where(mask, np.power(safe_d, -beta), 0.0)
            return w.astype(np.float64)
        raise ValueError(f"Unsupported decay: {decay}")

    if precomputed_weights is not None:
        w = np.asarray(precomputed_weights, dtype=np.float64)
        sparsity_val = float((w == 0.0).sum() / w.size)
        weighted_demand_by_supply = (dem[:, None] * w).sum(axis=0)
        supply_ratio = np.divide(
            sup,
            weighted_demand_by_supply,
            out=np.zeros_like(sup, dtype=np.float64),
            where=weighted_demand_by_supply > 0,
        )
        accessibility = (w * supply_ratio[None, :]).sum(axis=1)
    else:
        n, m = d.shape
        sparsity_val = float((d > catchment).sum() / d.size)
        block = max(128, min(2048, m))
        weighted_demand_by_supply = np.zeros(m, dtype=np.float64)

        for j0 in range(0, m, block):
            j1 = min(m, j0 + block)
            dist_block = d[:, j0:j1]
            w_block = _build_weight_matrix(dist_block, catchment=catchment, decay=decay, beta=beta)
            weighted_demand_by_supply[j0:j1] = (dem[:, None] * w_block).sum(axis=0)

        supply_ratio = np.divide(
            sup,
            weighted_demand_by_supply,
            out=np.zeros_like(sup, dtype=np.float64),
            where=weighted_demand_by_supply > 0,
        )

        accessibility = np.zeros(n, dtype=np.float64)
        for j0 in range(0, m, block):
            j1 = min(m, j0 + block)
            dist_block = d[:, j0:j1]
            w_block = _build_weight_matrix(dist_block, catchment=catchment, decay=decay, beta=beta)
            accessibility += (w_block * supply_ratio[None, j0:j1]).sum(axis=1)

    return AccessibilityResult(
        accessibility=accessibility,
        supply_ratio=supply_ratio,
        metadata={
            "n_demand": float(d.shape[0]),
            "n_supply": float(d.shape[1]),
            "sparsity": sparsity_val,
        },
    )


def gini_coefficient(values: np.ndarray) -> float:
    """
    计算可达性公平性指标（Gini 系数）。
    """
    x = np.asarray(values, dtype=np.float64).flatten()
    if x.size == 0:
        return 0.0
    if np.allclose(x, 0.0):
        return 0.0
    x = np.sort(x)
    n = x.size
    cum = np.cumsum(x)
    g = (n + 1 - 2 * np.sum(cum) / cum[-1]) / n
    return float(g)


def make_synthetic_dataset(num_pairs: int, seed: int = 42):
    """
    构造 benchmark 数据集。
    - num_pairs=1e4  -> 100 x 100
    - num_pairs=1e5  -> 316 x 316
    - num_pairs=1e6  -> 1000 x 1000
    """
    side = int(np.sqrt(num_pairs))
    if side * side != num_pairs:
        side = int(np.ceil(np.sqrt(num_pairs)))
    rng = np.random.default_rng(seed)
    distance_matrix = rng.uniform(1.0, 60.0, size=(side, side)).astype(np.float64)
    demand_array = rng.uniform(10.0, 1500.0, size=side).astype(np.float64)
    supply_array = rng.uniform(5.0, 300.0, size=side).astype(np.float64)
    return distance_matrix, demand_array, supply_array
