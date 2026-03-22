# modules/data_cleaner.py
import pandas as pd
import numpy as np


class HealthDataCleaner:
    """纯粹的清洗算法工具类"""

    @staticmethod
    def standardize_indicators(df, mapping):
        """统一列名映射"""
        return df.rename(columns=mapping)

    @staticmethod
    def calculate_core_metrics(df):
        """执行核心指标计算逻辑（如：供给指数、需求预测等）"""
        # 示例：简单的供给指数计算逻辑
        if 'physicians' in df.columns and 'population' in df.columns:
            df['supply_index'] = df['physicians'] / df['population'] * 1000
        return df

    @staticmethod
    def handle_missing_values(df):
        """处理缺失值（搜索到的数据常有残缺）"""
        # 区分“真零”与“漏报”：对于人口、医生、床位等绝不可能为0的核心指标，将0视为缺失值
        core_non_zero_cols = ['population', 'physicians', 'nurses', 'hospital_beds']
        for col in core_non_zero_cols:
            if col in df.columns:
                df[col] = df[col].replace(0, np.nan)
                
        df = df.replace(['N/A', 'nan', ''], np.nan)
        # 使用线性插值或前后向填充
        df = df.interpolate(method='linear', limit_direction='both').ffill().bfill()
        return df

    @staticmethod
    def detect_and_handle_outliers(df: pd.DataFrame, columns: list = None, method: str = 'iqr') -> pd.DataFrame:
        """
        深度异常值清洗：基于拉依达准则（3σ）或 IQR 的离群点检测
        """
        df_clean = df.copy()
        if columns is None:
            # 默认处理数值型列
            columns = df_clean.select_dtypes(include=[np.number]).columns.tolist()
            
        for col in columns:
            if col not in df_clean.columns:
                continue
                
            series = df_clean[col]
            if method == 'iqr':
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
            elif method == '3sigma':
                mean = series.mean()
                std = series.std()
                lower_bound = mean - 3 * std
                upper_bound = mean + 3 * std
            else:
                continue
                
            # 将异常值替换为边界值（Winsorization）或设为 NaN 后插值，这里选择 Winsorization
            df_clean[col] = np.clip(series, lower_bound, upper_bound)
            
        return df_clean

    @staticmethod
    def quick_clean(df: pd.DataFrame):
        """通用清洗流程：去空、标准化、计算比率"""
        # 1. 填充缺失值
        df = df.fillna(0)
        # 2. 统一单位（示例：将万人转化为人）
        if 'population_ten_thousand' in df.columns:
            df['population'] = df['population_ten_thousand'] * 10000
        # 3. 计算千人拥有量
        if 'doctors' in df.columns and 'population' in df.columns:
            df['doctors_per_1000'] = (df['doctors'] / df['population']) * 1000
        return df