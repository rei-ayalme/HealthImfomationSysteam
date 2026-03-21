# modules/analysis/advanced_algorithms.py
import numpy as np
import pandas as pd
from scipy.optimize import linprog
import logging
from typing import List, Dict, Union
import requests
import json
from config.settings import SETTINGS

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
    def calculate_2sfca(supply_df: pd.DataFrame, demand_df: pd.DataFrame,
                        threshold_km: float = 60.0, use_network_distance: bool = False) -> pd.Series:
        """
        计算两步移动搜索法 (2SFCA - Two-Step Floating Catchment Area)
        评估医疗资源的地理空间可及性 (廖博玮等, 2022)

        参数:
            supply_df: 必须包含 ['lat', 'lon', 'capacity'] (如医院经纬度与医生数)
            demand_df: 必须包含 ['lat', 'lon', 'population'] (如居民区经纬度与人口)
            threshold_km: 搜寻半径阈值 (公里)
            use_network_distance: 是否使用高德API获取真实路网距离(如果超过配额则回退到直线距离)
        返回:
            与 demand_df 索引对应的空间可及性指数序列
        """
        from scipy.spatial.distance import cdist

        # 高斯距离衰减函数
        def gaussian_decay(d, d0):
            return np.where(d <= d0, np.exp(-(d ** 2) / (2 * (d0 / 2) ** 2)), 0)

        # 提取坐标数组
        supply_coords = supply_df[['lat', 'lon']].values
        demand_coords = demand_df[['lat', 'lon']].values

        # 计算距离矩阵 (行: 供给点, 列: 需求点)
        if use_network_distance:
            # 如果要求使用网络距离，这里为了避免 API 频率限制，可以做成批量请求或者使用距离矩阵预计算。
            # 为了简化并保持向量化优势，在没有专门距离矩阵 API 时，这里依然回退为球面距离计算（可后续对接高德的 distance/matrix 接口）
            pass

        # 统一使用球面距离计算两两距离，避免 iterrows 的极度低效
        # 注意: cdist 默认是欧式距离，若要精确球面距离可以使用自定义 metric
        # 为了高效，这里使用一个粗略的球面距离转换 (度转弧度后计算)
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

        # 步骤 1：计算供需比 (Supply-to-Demand Ratio) R_j
        weights_matrix = gaussian_decay(dist_matrix, threshold_km)
        demand_pop = demand_df['population'].values
        # weighted_demand 的形状是 (n_supply,)
        weighted_demand = np.sum(weights_matrix * demand_pop, axis=1)
        
        supply_capacity = supply_df['capacity'].values
        R_j = np.zeros_like(supply_capacity, dtype=float)
        valid_idx = weighted_demand > 0
        R_j[valid_idx] = supply_capacity[valid_idx] / weighted_demand[valid_idx]

        # 将 R_j 放回 supply_df（如果需要供后续分析或验证）
        supply_df['R_j'] = R_j

        # 步骤 2：计算空间可及性指数
        # access_scores 的形状是 (n_demand,)
        access_scores = np.sum(weights_matrix * R_j[:, np.newaxis], axis=0)

        return pd.Series(access_scores, index=demand_df.index)