# modules/analysis/advanced_algorithms.py
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
        n_dmus, m_inputs = X.shape
        _, s_outputs = Y.shape
        efficiencies = np.zeros(n_dmus)

        # 遍历每一个 DMU (决策单元，即每一个地区)
        for k in range(n_dmus):
            # 目标函数：最大化第 k 个 DMU 的加权产出
            # 在 scipy.linprog 中求最小值，因此目标系数取负
            c = np.concatenate((np.zeros(m_inputs), -Y[k, :]))

            # 约束条件 1: \sum v_i * x_{ik} = 1 (第 k 个 DMU 的加权投入等于 1)
            A_eq = np.concatenate((X[k, :], np.zeros(s_outputs))).reshape(1, -1)
            b_eq = np.array([1.0])

            # 约束条件 2: \sum u_r * y_{rj} - \sum v_i * x_{ij} <= 0 (所有 DMU 的产出不能超过投入)
            A_ub = np.hstack((-X, Y))
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
                        threshold_km: float = 60.0) -> pd.Series:
        """
        计算两步移动搜索法 (2SFCA - Two-Step Floating Catchment Area)
        评估医疗资源的地理空间可及性 (廖博玮等, 2022)

        参数:
            supply_df: 必须包含 ['lat', 'lon', 'capacity'] (如医院经纬度与医生数)
            demand_df: 必须包含 ['lat', 'lon', 'population'] (如居民区经纬度与人口)
            threshold_km: 搜寻半径阈值 (公里)
        返回:
            与 demand_df 索引对应的空间可及性指数序列
        """

        # 高斯距离衰减函数
        def gaussian_decay(d, d0):
            return np.where(d <= d0, np.exp(-(d ** 2) / (2 * (d0 / 2) ** 2)), 0)

        # 步骤 1：针对每个供给点 (医院)，计算供需比 (Supply-to-Demand Ratio)
        supply_ratios = []
        for _, s_row in supply_df.iterrows():
            # 计算该医院到所有居民点的距离
            distances = HealthMathModels.haversine_distance(
                s_row['lat'], s_row['lon'], demand_df['lat'].values, demand_df['lon'].values
            )
            # 应用衰减权重
            weights = gaussian_decay(distances, threshold_km)
            # 加权需求总和
            weighted_demand = np.sum(demand_df['population'].values * weights)

            # 供需比 = 医院容量 / 覆盖范围内加权需求总和
            ratio = s_row['capacity'] / weighted_demand if weighted_demand > 0 else 0
            supply_ratios.append(ratio)

        supply_df['R_j'] = supply_ratios

        # 步骤 2：针对每个需求点 (居民点)，聚合可及性指数
        access_scores = []
        for _, d_row in demand_df.iterrows():
            # 计算该居民点到所有医院的距离
            distances = HealthMathModels.haversine_distance(
                d_row['lat'], d_row['lon'], supply_df['lat'].values, supply_df['lon'].values
            )
            # 应用衰减权重
            weights = gaussian_decay(distances, threshold_km)
            # 空间可及性 = 覆盖范围内医院供需比的加权和
            accessibility = np.sum(supply_df['R_j'].values * weights)
            access_scores.append(accessibility)

        return pd.Series(access_scores, index=demand_df.index)