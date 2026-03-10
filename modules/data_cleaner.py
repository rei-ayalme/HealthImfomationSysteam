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
        return df.replace(['N/A', 'nan', ''], np.nan).ffill().bfill()

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