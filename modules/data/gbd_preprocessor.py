# modules/data/gbd_preprocessor.py
import pandas as pd
import numpy as np
import logging
from typing import Dict, List
from config.settings import GBD_ANALYSIS_CONFIG


class AdvancedGlobalHealthCleaner:
    """
    高级全球健康数据清洗器
    融合多篇核心文献方法 (鲁棒DEA、云模型、疾病谱系ETI)
    """

    def __init__(self):
        self.config = GBD_ANALYSIS_CONFIG
        self.logger = logging.getLogger("health_system.advanced_cleaner")

        # 鲁棒DEA不确定性参数
        self.gamma = self.config.get('uncertainty_budget', 0.1)
        # 云模型参数
        self.cloud_params = self.config.get('cloud_params', {'zeta_min': 0.8, 'zeta_max': 1.2, 'beta': 9})

    def standardize_schema(self, df: pd.DataFrame, data_source: str) -> pd.DataFrame:
        """多源数据字段标准化"""
        column_maps = {
            'gbd': {
                'cause_id': ['cause_id', 'Cause ID', 'cause'],
                'cause_name': ['cause_name', 'Cause Name', 'disease'],
                'rei_name': ['rei_name', 'Risk Name', 'risk_factor'],
                'location_id': ['location_id', 'Location ID', 'iso3'],
                'location_name': ['location_name', 'Location', 'country'],
                'year': ['year', 'Year', 'time'],
                'measure_id': ['measure_id', 'Measure ID'],
                'val': ['val', 'Value', 'mean', 'attributable_dalys'],
                'paf': ['paf', 'PAF'],
                'exposure_category': ['exposure_category', 'exposure_level'],
                'sdi': ['sdi', 'SDI']
            },
            'who': {
                'location_name': ['location_name', 'Location', 'country'],
                'year': ['year', 'Year', 'time'],
                'physicians_per_1000': ['Medical doctors (per 1000)', 'physicians'],
                'hospital_beds_per_1000': ['Hospital beds (per 1000)', 'beds'],
                'health_expenditure_per_capita': ['health expenditure per capita'],
                'hale': ['Healthy life expectancy', 'hale'],
                'gdp_per_capita': ['GDP per capita', 'gdp']
            }
        }

        mapping = column_maps.get(data_source, {})
        reverse_map = {var.lower(): std_name for std_name, variants in mapping.items() for var in variants}

        df_renamed = df.rename(columns={col: reverse_map.get(col.lower(), col) for col in df.columns})
        return df_renamed

    def clean_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据类型转换与基础清洗"""
        df_clean = df.copy()
        numeric_cols = ['val', 'year', 'sdi', 'paf', 'physicians_per_1000', 'hale']

        for col in numeric_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

        if 'year' in df_clean.columns:
            df_clean = df_clean[
                (df_clean['year'] >= self.config.get('min_year', 1990)) &
                (df_clean['year'] <= self.config.get('max_year', 2025))
                ]

        # 修复 KeyError: 动态检查列是否存在，只对存在的列执行去空操作
        # 注意：不再强制丢弃没有 year 的行，以应对部分 WDI 或其他源缺失 year 列
        subset_cols = [c for c in ['year', 'val'] if c in df_clean.columns]
        if subset_cols:
            # 修改：只在所有检查列都为空时才丢弃，或者直接用默认的 any 视情况而定
            # 如果是 val 为空才丢弃比较合理
            if 'val' in df_clean.columns:
                df_clean = df_clean.dropna(subset=['val'], how='any')
            else:
                df_clean = df_clean.dropna(subset=subset_cols, how='all')

        return df_clean.copy()

    def engineer_disease_transition(self, df: pd.DataFrame) -> pd.DataFrame:
        """问题1：疾病谱系转型特征 (ETI)"""
        if 'cause_id' not in df.columns:
            return df

        df_feat = df.copy()

        # 1. 疾病大类映射
        def classify_cause(cid):
            try:
                cid = int(cid)
                if 300 <= cid < 500:
                    return 'communicable'
                elif 500 <= cid < 1000:
                    return 'non_communicable'
                elif 1000 <= cid < 1500:
                    return 'injuries'
            except:
                pass
            return 'other'

        df_feat['disease_category'] = df_feat['cause_id'].apply(classify_cause)

        # 2. 计算流行病学转型指数 (ETI)
        pivot_dalys = df_feat.pivot_table(
            index=['location_name', 'year'], columns='disease_category',
            values='val', aggfunc='sum', fill_value=0
        )

        total = pivot_dalys.sum(axis=1)
        pivot_dalys['eti'] = pivot_dalys.get('non_communicable', 0) / total.replace(0, np.nan)

        # 转型阶段划分
        pivot_dalys['transition_stage'] = pd.cut(
            pivot_dalys['eti'], bins=[0, 0.3, 0.5, 0.7, 1.0],
            labels=['pre_transition', 'early_transition', 'late_transition', 'post_transition']
        )

        return df_feat.merge(pivot_dalys[['eti', 'transition_stage']].reset_index(), on=['location_name', 'year'],
                             how='left')

    def _linguistic_to_cloud(self, df: pd.DataFrame, linguistic_col: str) -> pd.DataFrame:
        """云模型转换核心算法 (张翔等, 2026)"""
        term_set = ['极低', '低', '中', '高', '极高']
        n = len(term_set)
        tau = (n - 1) // 2
        beta = self.cloud_params['beta']

        theta = []
        for i in range(n):
            if i <= tau:
                theta.append((beta ** tau - beta ** (tau - i)) / (2 * beta ** tau - 2))
            else:
                theta.append((beta ** tau + beta ** (i - tau) - 2) / (2 * beta ** tau - 2))

        Ex = theta
        En, He = [], []
        zeta_min, zeta_max = self.cloud_params['zeta_min'], self.cloud_params['zeta_max']

        for i in range(n):
            if i == 0:
                En.append((zeta_min + zeta_max) * (Ex[i + 1] - Ex[i]) / 6)
                He.append((zeta_max - zeta_min) * (Ex[i + 1] - Ex[i]) / 18)
            elif i == n - 1:
                En.append((zeta_min + zeta_max) * (Ex[i] - Ex[i - 1]) / 6)
                He.append((zeta_max - zeta_min) * (Ex[i] - Ex[i - 1]) / 18)
            else:
                En.append((zeta_min + zeta_max) * (Ex[i + 1] - Ex[i - 1]) / 12)
                He.append((zeta_max - zeta_min) * (Ex[i + 1] - Ex[i - 1]) / 18)

        cloud_map = {t: {'Ex': Ex[i], 'En': En[i], 'He': He[i]} for i, t in enumerate(term_set)}

        df[f'{linguistic_col}_Ex'] = df[linguistic_col].map(lambda x: cloud_map.get(x, {}).get('Ex', np.nan))
        df[f'{linguistic_col}_En'] = df[linguistic_col].map(lambda x: cloud_map.get(x, {}).get('En', np.nan))
        df[f'{linguistic_col}_He'] = df[linguistic_col].map(lambda x: cloud_map.get(x, {}).get('He', np.nan))
        return df

    def engineer_risk_attribution(self, df: pd.DataFrame) -> pd.DataFrame:
        """问题2：风险因素归因与云模型"""
        df_feat = df.copy()

        # 1. 补回：风险因素分类映射
        risk_categories = {
            'environmental': ['particulate matter', 'air pollution', 'temperature', 'Lead'],
            'behavioral': ['Smoking', 'Alcohol', 'Drug', 'Diet', 'physical activity'],
            'metabolic': ['blood pressure', 'glucose', 'BMI', 'cholesterol', 'Kidney']
        }

        def map_risk(rei_name):
            if pd.isna(rei_name): return 'other'
            for cat, risks in risk_categories.items():
                if any(r.lower() in str(rei_name).lower() for r in risks): return cat
            return 'other'

        if 'rei_name' in df_feat.columns:
            df_feat['risk_category'] = df_feat['rei_name'].apply(map_risk)

        # 2. 云模型转换
        if 'exposure_category' in df_feat.columns:
            df_feat = self._linguistic_to_cloud(df_feat, 'exposure_category')

        return df_feat

    def engineer_resource_efficiency(self, resources_df: pd.DataFrame, burden_df: pd.DataFrame) -> pd.DataFrame:
        """问题3：卫生资源效率特征准备 (邵龙龙等 鲁棒DEA预处理)"""
        # 按地点和年份汇总负担
        burden_summary = burden_df.groupby(['location_name', 'year'])['val'].sum().reset_index(name='total_burden')
        df_merged = pd.merge(resources_df, burden_summary, on=['location_name', 'year'], how='inner')

        # 提取投入指标并计算鲁棒不确定性区间
        inputs = ['physicians_per_1000', 'hospital_beds_per_1000', 'health_expenditure_per_capita']
        for col in inputs:
            if col in df_merged.columns:
                # 假设数据存在波动，为其生成不确定性上下界
                df_merged[f'{col}_robust_upper'] = df_merged[col] * (1 + self.gamma)
                df_merged[f'{col}_robust_lower'] = df_merged[col] * (1 - self.gamma)

        # 基于中位数划分四象限 (基础版)
        if 'health_expenditure_per_capita' in df_merged.columns and 'hale' in df_merged.columns:
            exp_median = df_merged['health_expenditure_per_capita'].median()
            out_median = df_merged['hale'].median()

            def classify_quadrant(row):
                if row['health_expenditure_per_capita'] > exp_median and row['hale'] > out_median:
                    return '高投入_高产出'
                elif row['health_expenditure_per_capita'] > exp_median and row['hale'] <= out_median:
                    return '高投入_低产出'
                elif row['health_expenditure_per_capita'] <= exp_median and row['hale'] > out_median:
                    return '低投入_高产出'
                else:
                    return '低投入_低产出'

            df_merged['resource_quadrant'] = df_merged.apply(classify_quadrant, axis=1)

        return df_merged

    def run_full_pipeline(self, raw_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """执行完整清洗管道"""
        results = {}

        # 1. 疾病谱系
        if 'gbd_disease' in raw_data:
            df1 = self.standardize_schema(raw_data['gbd_disease'], 'gbd')
            df1 = self.clean_data_types(df1)
            df1 = self.engineer_disease_transition(df1)
            results['disease_spectrum'] = df1
            self.logger.info("疾病谱系(问题1)特征构建完成。")

        # 2. 风险因素
        if 'gbd_risk' in raw_data:
            df2 = self.standardize_schema(raw_data['gbd_risk'], 'gbd')
            df2 = self.clean_data_types(df2)
            df2 = self.engineer_risk_attribution(df2)
            results['risk_attribution'] = df2
            self.logger.info("风险因素(问题2)特征构建完成。")

        # 3. 卫生资源效率
        if 'who_resources' in raw_data and 'disease_spectrum' in results:
            df3 = self.standardize_schema(raw_data['who_resources'], 'who')
            df3 = self.clean_data_types(df3)
            df3 = self.engineer_resource_efficiency(df3, results['disease_spectrum'])
            results['health_resources'] = df3
            self.logger.info("卫生资源效率(问题3)特征构建完成。")

        return results