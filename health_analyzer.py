# health_analyzer.py - 医疗资源供需分析器
import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, Optional
import warnings


class HealthResourceAnalyzer:
    """
    医疗资源供需分析器
    评估医疗资源供给与需求匹配情况
    """

    def __init__(self, settings: Dict, base_year: int = 2020):
        """
        初始化健康资源分析器

        Args:
            settings: 配置字典
            base_year: 基准年份
        """
        self.settings = settings
        self.base_year = base_year
        self.resource_data = None
        self.population_data = None
        self.area_data = None

    def load_data(self, resource_df: pd.DataFrame, population_df: pd.DataFrame,
                  area_df: pd.DataFrame = None) -> None:
        """
        加载医疗资源、人口和地区面积数据

        Args:
            resource_df: 医疗资源数据
            population_df: 人口数据
            area_df: 地区面积数据（可选）
        """
        self.resource_data = resource_df.copy()
        self.population_data = population_df.copy()
        self.area_data = area_df.copy() if area_df is not None else None

        print(f"[HealthResourceAnalyzer] 数据加载完成 - 资源数据{len(resource_df)}行，人口数据{len(population_df)}行")

    def calculate_standardized_density(self, resource_type: str) -> pd.Series:
        """
        计算标准化的医疗资源密度

        Args:
            resource_type: 资源类型 ('hospital_beds', 'doctors', 'nurses', 'medical_facilities')

        Returns:
            人口标准化密度和面积标准化密度
        """
        if self.resource_data is None or self.population_data is None:
            raise ValueError("请先加载数据")

        # 获取配置中的基准密度
        target_density = self.settings['RESOURCE_DENSITY_BASELINE'].get(resource_type, 1.0)
        target_density_area = self.settings.get('AREA_DENSITY_RATE', {}).get(resource_type, 0.001)

        # 合并数据
        merged_df = self._merge_data_with_validation()

        # 计算现有人口密度
        resource_col = self.settings['COLUMN_MAPPING'][resource_type]
        pop_col = self.settings['COLUMN_MAPPING']['population']

        actual_density_per_capita = (
                merged_df[resource_col] / merged_df[pop_col] * 10000
        ).fillna(0)  # 每万人拥有的资源数

        # 计算需求基准
        required_resources_base = merged_df[pop_col] * target_density / 10000
        supply_gap = (required_resources_base - merged_df[resource_col]).clip(lower=0)
        gap_percentage = (supply_gap / required_resources_base * 100).fillna(0)

        # 如果有面积数据，计算地理密度
        if self.area_data is not None:
            area_col = self.settings['COLUMN_MAPPING']['area']
            actual_density_per_area = (
                    merged_df[resource_col] / merged_df[area_col]
            ).fillna(0)  # 每平方公里拥有的资源数

            return pd.DataFrame({
                f'{resource_type}_density_per_capita': actual_density_per_capita,
                f'{resource_type}_density_per_area': actual_density_per_area,
                f'{resource_type}_required_base': required_resources_base,
                f'{resource_type}_gap_count': supply_gap,
                f'{resource_type}_gap_percentage': gap_percentage
            })

        return pd.DataFrame({
            f'{resource_type}_density_per_capita': actual_density_per_capita,
            f'{resource_type}_required_base': required_resources_base,
            f'{resource_type}_gap_count': supply_gap,
            f'{resource_type}_gap_percentage': gap_percentage
        })

    def adjust_for_external_factors(self, resource_type: str, factors: Dict[str, float] = None) -> Dict:
        """
        根据外部因素调整资源需求

        Args:
            resource_type: 资源类型
            factors: 外部因素影响系数 {'age_factor': 1.2, 'disease_burden': 0.8, ...}

        Returns:
            调整后的供需分析结果
        """
        if factors is None:
            factors = {}

        base_analysis = self.calculate_standardized_density(resource_type)

        # 外部因素调节
        age_coef = factors.get('age_coefficient', 1.0)  # 老龄化影响
        disease_coef = factors.get('disease_burden_coefficient', 1.0)  # 疾病负担影响
        urban_coef = factors.get('urbanization_coefficient', 1.0)  # 城市化影响
        economic_coef = factors.get('economic_development_coefficient', 1.0)  # 经济发展水平影响

        factor_multiplier = age_coef * disease_coef * urban_coef * economic_coef

        # 调整后的需求
        adjusted_required = (
                base_analysis[f'{resource_type}_required_base'] *
                factor_multiplier
        )

        # 基于调整后的需求重新计算缺口
        actual_resources = self.resource_data[self.settings['COLUMN_MAPPING'][resource_type]]
        gap_after_adjustment = (adjusted_required - actual_resources).clip(lower=0)
        gap_pct_after_adjustment = (
                gap_after_adjustment / adjusted_required * 100
        ).fillna(0)

        analysis_result = {
            'original': base_analysis,
            'adjusted_demand': adjusted_required,
            'adjusted_supply_gap': gap_after_adjustment,
            'adjusted_gap_percentage': gap_pct_after_adjustment,
            'adjustment_factor': factor_multiplier,
            'factors_applied': factors
        }

        return analysis_result

    def generate_recommendation(self, resource_types: List[str],
                                external_factors: Dict[str, Dict] = None) -> Dict:
        """
        生成资源配置建议综合报告

        Args:
            resource_types: 资源类型列表
            external_factors: 外部因素字典

        Returns:
            综合推荐报告
        """
        recommendations = {}

        for resource_type in resource_types:
            print(f"[HealthResourceAnalyzer] 分析资源类型: {resource_type}")

            if external_factors and resource_type in external_factors:
                analysis = self.adjust_for_external_factors(
                    resource_type, external_factors[resource_type]
                )
            else:
                analysis = self.adjust_for_external_factors(resource_type)

            # 计算优化优先级
            gap_severity = analysis['adjusted_gap_percentage']
            current_density = analysis['original'][f'{resource_type}_density_per_capita']

            # 综合评分 = 缺口严重程度 + 当前密度倒数（密度越低，需求越紧急）
            priority_score = gap_severity + 100 / (current_density + 1)  # 防止除零
            priority_level = self._classify_priority(priority_score)

            recommendations[resource_type] = {
                'current_density_per_10k': analysis['original'][f'{resource_type}_density_per_capita'],
                'required_after_adjustment': analysis['adjusted_demand'],
                'supply_gap_after_adjustment': analysis['adjusted_supply_gap'],
                'gap_percentage': analysis['adjusted_gap_percentage'],
                'priority_score': priority_score,
                'priority_level': priority_level,
                'adjustment_details': analysis['factors_applied'],
                'recommended_additional_count': analysis['adjusted_supply_gap'].round(0),
                'time_horizon_months': 24,  # 默认24个月建设周期
                'estimated_cost_per_unit': self.settings.get('RESOURCE_COST_BASELINE', {}).get(resource_type, 100000)
            }

        return recommendations

    def export_resource_efficiency_report(self, region_id: Optional[str] = None) -> pd.DataFrame:
        """
        导出资源效率评估报告

        Args:
            region_id: 指定地区ID，如果None则输出所有地区

        Returns:
            效率评估DataFrame
        """
        if not all([self.resource_data, self.population_data]):
            raise ValueError("数据未加载")

        merged_data = self._merge_data_with_validation()

        if region_id:
            merged_data = merged_data[merged_data[self.settings['COLUMN_MAPPING']['region']] == region_id]

        efficiency_indicators = []

        for _, row in merged_data.iterrows():
            region = row[self.settings['COLUMN_MAPPING']['region']]

            # 计算各类效率指标
            metrics = {
                'region': region,
                'region_code': row.get(self.settings['COLUMN_MAPPING'].get('code'), ''),
                'total_population': row[self.settings['COLUMN_MAPPING']['population']],
                'area_km2': row.get(self.settings['COLUMN_MAPPING'].get('area'), 0) if self.area_data else 0,

                # 床位效率
                'beds_per_pop': (row.get(self.settings['COLUMN_MAPPING']['hospital_beds'], 0) /
                                 row[self.settings['COLUMN_MAPPING']['population']] * 10000) if row[self.settings[
                    'COLUMN_MAPPING']['population']] > 0 else 0,

                'beds_per_sqkm': (row.get(self.settings['COLUMN_MAPPING']['hospital_beds'], 0) /
                                  row.get(self.settings['COLUMN_MAPPING'].get('area'), 1) if row.get(
                    self.settings['COLUMN_MAPPING'].get('area'), 0) > 0 else 0),

                # 医生效率
                'doctors_per_pop': (row.get(self.settings['COLUMN_MAPPING']['doctors'], 0) /
                                    row[self.settings['COLUMN_MAPPING']['population']] * 10000) if row[self.settings[
                    'COLUMN_MAPPING']['population']] > 0 else 0,

                'nurses_per_pop': (row.get(self.settings['COLUMN_MAPPING']['nurses'], 0) /
                                   row[self.settings['COLUMN_MAPPING']['population']] * 10000) if row[self.settings[
                    'COLUMN_MAPPING']['population']] > 0 else 0,

                # 设施效率
                'facilities_per_pop': (row.get(self.settings['COLUMN_MAPPING']['medical_facilities'], 0) /
                                       row[self.settings['COLUMN_MAPPING']['population']] * 10000) if row[self.settings[
                    'COLUMN_MAPPING']['population']] > 0 else 0,

                'facilities_per_sqkm': (row.get(self.settings['COLUMN_MAPPING']['medical_facilities'], 0) /
                                        row.get(self.settings['COLUMN_MAPPING'].get('area'), 1) if row.get(
                    self.settings['COLUMN_MAPPING'].get('area'), 0) > 0 else 0),
            }

            efficiency_indicators.append(metrics)

        df_efficiency = pd.DataFrame(efficiency_indicators)

        # 添加效率等级评定
        df_efficiency['overall_efficiency_grade'] = self._calculate_efficiency_grade(df_efficiency)

        return df_efficiency

    def _merge_data_with_validation(self) -> pd.DataFrame:
        """合并并验证数据"""
        # 获取标识列
        id_col = self.settings['COLUMN_MAPPING']['region']

        # 确保索引一致
        resource_df = self.resource_data.set_index(id_col)
        population_df = self.population_data.set_index(id_col)

        merged_df = resource_df.join(population_df, how='inner')

        if self.area_data is not None:
            area_df = self.area_data.set_index(id_col)
            merged_df = merged_df.join(area_df, how='inner')

        if len(merged_df) == 0:
            raise ValueError("数据合并失败，没有共同的地区标识")

        print(f"[HealthResourceAnalyzer] 数据验证: 共{len(merged_df)}个有效区域")
        return merged_df.reset_index()

    def _classify_priority(self, score: pd.Series) -> pd.Series:
        """根据综合得分分类优先级"""
        conditions = [
            score >= 80,
            score >= 60,
            score >= 40,
            score >= 20,
            score < 20
        ]
        choices = ['极高', '高', '中', '低', '很低']

        return pd.cut(score, bins=[0, 20, 40, 60, 80, 100],
                      labels=choices, include_lowest=True)

    def _calculate_efficiency_grade(self, df: pd.DataFrame) -> pd.Series:
        """计算总体效率等级"""
        # 计算标准化效率得分
        # 各项指标相对全国平均水平的比例
        efficiency_scores = []

        for idx, row in df.iterrows():
            # 床位相对效率
            beds_rel = row['beds_per_pop'] / df['beds_per_pop'].mean() if df['beds_per_pop'].mean() > 0 else 0
            # 医生相对效率
            docs_rel = row['doctors_per_pop'] / df['doctors_per_pop'].mean() if df['doctors_per_pop'].mean() > 0 else 0
            # 护士相对效率
            nurs_rel = row['nurses_per_pop'] / df['nurses_per_pop'].mean() if df['nurses_per_pop'].mean() > 0 else 0
            # 设施相对效率
            facs_rel = row['facilities_per_pop'] / df['facilities_per_pop'].mean() if df[
                                                                                          'facilities_per_pop'].mean() > 0 else 0

            # 综合效率得分
            comp_score = (beds_rel + docs_rel + nurs_rel + facs_rel) / 4 * 100
            efficiency_scores.append(comp_score)

        # 转换为效率等级
        score_series = pd.Series(efficiency_scores)
        return pd.cut(score_series,
                      bins=[0, 25, 50, 75, 90, 100],
                      labels=['极差', '较差', '一般', '良好', '优秀'],
                      include_lowest=True)


def demo_health_analyzer():
    """
    Demo函数：展示HealthResourceAnalyzer的基本用法
    """
    print("=" * 60)
    print("HealthResourceAnalyzer Demo")
    print("=" * 60)

    from settings import get_settings

    # 获取配置
    config = get_settings()

    # 创建模拟数据
    regions = [f'区域_{i + 1}' for i in range(10)]
    n_regions = len(regions)

    # 模拟资源数据
    resource_data = pd.DataFrame({
        config['COLUMN_MAPPING']['region']: regions,
        config['COLUMN_MAPPING']['hospital_beds']: np.random.randint(500, 5000, n_regions),
        config['COLUMN_MAPPING']['doctors']: np.random.randint(100, 2000, n_regions),
        config['COLUMN_MAPPING']['nurses']: np.random.randint(200, 3000, n_regions),
        config['COLUMN_MAPPING']['medical_facilities']: np.random.randint(10, 100, n_regions),
    })

    # 模拟人口数据
    population_data = pd.DataFrame({
        config['COLUMN_MAPPING']['region']: regions,
        config['COLUMN_MAPPING']['population']: np.random.randint(500000, 10000000, n_regions),
    })

    # 模拟面积数据
    area_data = pd.DataFrame({
        config['COLUMN_MAPPING']['region']: regions,
        config['COLUMN_MAPPING'].get('area', 'area'): np.random.randint(1000, 50000, n_regions),
    })

    print("[Demo] 模拟数据创建完成")
    print(f"资源配置数据: \n{resource_data.head()}")
    print(f"人口数据: \n{population_data.head()}")
    print(f"面积数据: \n{area_data.head()}")

    # 实例化分析器
    analyzer = HealthResourceAnalyzer(config)

    # 加载数据
    analyzer.load_data(resource_data, population_data, area_data)

    # 计算床位密度
    bed_density = analyzer.calculate_standardized_density('hospital_beds')
    print(f"\n[Results] 床位密度分析:\n{bed_density.head()}")

    # 基于外部因素调整
    external_factors = {
        'age_coefficient': 1.2,  # 老龄化程度较高
        'disease_burden_coefficient': 0.8,  # 疾病负担较低，实际需求减少
        'urbanization_coefficient': 0.9,  # 半城市化
        'economic_development_coefficient': 1.1  # 经济水平略高
    }

    adjusted_analysis = analyzer.adjust_for_external_factors('hospital_beds', external_factors)
    print(f"\n[Results] 调整后需求分析:\n{adjusted_analysis['adjusted_supply_gap'].head()}")

    # 生成推荐
    recommendations = analyzer.generate_recommendation(
        ['hospital_beds', 'doctors'],
        {'hospital_beds': external_factors, 'doctors': external_factors}
    )

    print(f"\n[Results] 推荐报告:")
    for res_type, rec in recommendations.items():
        print(f"\n{res_type}:")
        print(f"  优先级: {rec['priority_level']}")
        print(f"  综合评分: {rec['priority_score'].mean():.2f}")
        print(f"  缺失数量估算: {rec['recommended_additional_count'].sum():.0f}")

    # 导出效率报告
    efficiency_report = analyzer.export_resource_efficiency_report()
    print(f"\n[Results] 效率评估报告:\n")
    print(efficiency_report[['region', 'beds_per_pop', 'doctors_per_pop',
                             'nurses_per_pop', 'overall_efficiency_grade']].head())

    print("=" * 60)
    print("Demo完成")
    print("=" * 60)


if __name__ == "__main__":
    demo_health_analyzer()
