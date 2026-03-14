import numpy as np
import pandas as pd
from scipy.spatial import distance_matrix


class SpatialAccessibilityModel:
    def __init__(self, demand_df: pd.DataFrame, facility_df: pd.DataFrame):
        """
        初始化空间可达性模型
        :param demand_df: 需求端数据 (需包含 x/longitude, y/latitude, population, elderly_ratio)
        :param facility_df: 供给端数据 (需包含 x/longitude, y/latitude, physicians, beds)
        """
        self.demand = demand_df.copy()
        self.facility = facility_df.copy()

        # 预计算距离矩阵 (实际项目中可替换为高德API返回的真实路网时间)
        demand_coords = self.demand[['longitude', 'latitude']].values
        facility_coords = self.facility[['longitude', 'latitude']].values
        self.dist_matrix = distance_matrix(demand_coords, facility_coords) + 0.001  # 避免除0

    def compute_gravity_model(self, beta: float = 2.0) -> pd.DataFrame:
        """白鸽：引力模型潜在可达性"""
        supply = self.facility['physicians'].values * 0.6 + self.facility['beds'].values * 0.4
        pop = self.demand['population'].values

        decay_matrix = self.dist_matrix ** -beta
        V_j = np.dot(pop, decay_matrix)
        A_i = np.dot(decay_matrix, supply / V_j)

        self.demand['gravity_access_index'] = A_i
        return self.demand

    def compute_enhanced_2sfca(self, threshold_dist: float = 5.0) -> pd.DataFrame:
        """刘承承/汤君友：高斯衰减 + 弱势群体权重的 2SFCA"""
        supply = self.facility['physicians'].values + self.facility['beds'].values
        pop = self.demand['population'].values

        # 高斯衰减 W = exp(-(d/d0)^2)
        W = np.exp(-(self.dist_matrix / threshold_dist) ** 2)
        W[self.dist_matrix > threshold_dist] = 0

        # 第一步：供需比 R_j
        weighted_pop = np.dot(W.T, pop)
        R_j = np.where(weighted_pop > 0, supply / weighted_pop, 0)

        # 第二步：计算可达性并施加弱势群体(老龄化)权重
        A_i = np.dot(W, R_j)
        # 如果老龄化率大于20%，可达性需求阻抗权重放大1.5倍（暴露其更严重的短缺）
        weights = np.where(self.demand.get('elderly_ratio', 0) > 0.2, 1.5, 1.0)
        self.demand['enhanced_2sfca_index'] = A_i / weights

        return self.demand