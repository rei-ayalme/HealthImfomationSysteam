# integrated_data_preprocessing_optimized.py
import pandas as pd
import numpy as np
import requests
import re
import time
import threading
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import reduce
from sklearn.preprocessing import MinMaxScaler
from unified_interface import UnifiedDataPreprocessor
from settings import SETTINGS, STANDARD_COLUMN_MAPPING


def identify_column_types(df_columns) -> Dict[str, str]:
    """识别DataFrame列的类型"""
    identified_columns = {}

    for col in df_columns:
        col_lower = col.lower()

        for standard_key, keywords in STANDARD_COLUMN_MAPPING.items():
            if any(keyword.lower() in col_lower for keyword in keywords):
                identified_columns[col] = standard_key
                break
        else:
            # 如果没有匹配的关键词，保留原列名
            if '年份' in col or 'year' in col_lower:
                identified_columns[col] = 'year'
            elif 'area' in col_lower or 'region' in col_lower or 'location' in col_lower:
                identified_columns[col] = 'region_name'
            elif col not in ['index', 'unnamed']:
                identified_columns[col] = f'unknown_{col}'

    return identified_columns


class HealthDataPreprocessor:
    def __init__(self):
        self.standard_mapping = STANDARD_COLUMN_MAPPING
        self.logger = logging.getLogger(__name__)

    def clean_health_data(input_file, output_file):
        """
        使用统一接口清洗健康数据
        """
        preprocessor = UnifiedDataPreprocessor()
        # 调用统一的方法清洗和保存数据
        preprocessor.clean_health_data(input_file, output_file)
        print(f"数据已从 {input_file} 清洗并保存至 {output_file}")

    def process_multilevel_headers(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理多级表头，将其扁平化"""
        if isinstance(df.columns, pd.MultiIndex):
            # 将多级列名扁平化
            df.columns = ['_'.join([str(c) for c in col]).strip() for col in df.columns]

        # 清理列名，移除多余的下划线和空格
        df.columns = [re.sub(r'\s+', '_', col.strip()) for col in df.columns]
        df.columns = [re.sub(r'_+', '_', col) for col in df.columns]  # 合并多个下划线

        return df

    def apply_standard_mapping(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """应用标准列名映射"""
        identified_cols = identify_column_types(df.columns)

        # 创建反向映射
        inverse_mapping = {}
        for original_col, standard_name in identified_cols.items():
            new_col = standard_name
            if original_col != standard_name:
                # 处理重复的标准列名
                counter = 1
                temp_name = new_col
                while temp_name in inverse_mapping.values():
                    temp_name = f"{standard_name}_{counter}"
                    counter += 1
                new_col = temp_name

            inverse_mapping[original_col] = new_col

        # 重命名列
        df_renamed = df.rename(columns=inverse_mapping)
        return df_renamed, inverse_mapping

    def get_medical_density(self, country_code: str = 'CN', year: str = '2023') -> Optional[Dict[str, float]]:
        """从API获取医疗资源数据"""
        wb_data = {}

        medical_indicators = {
            'physicians_per_1000': 'SH.MED.PHYS.ZS',  # 每千人医生数
            'nurses_per_1000': 'SH.MED.NUMW.P3',  # 每千人护士数
            'hospital_beds_per_1000': 'SH.MED.BEDS.ZS'  # 每千人病床数
        }

        for resource, indicator in medical_indicators.items():
            try:
                # 世界银行API URL
                url = f"{SETTINGS.API_CONFIG['world_bank_base_url']}country/{country_code}/indicator/{indicator}"
                params = {
                    'date': year,
                    'format': 'json',
                    'per_page': 100
                }

                response = requests.get(url, params=params, timeout=SETTINGS.API_CONFIG['world_bank_api_timeout'])
                response.raise_for_status()

                data = response.json()
                # 世界银行API返回格式：[元数据, 数据列表]
                if len(data) > 1 and data[1] and len(data[1]) > 0:
                    value = data[1][0].get('value')
                    try:
                        wb_data[resource] = float(value) if value is not None else 0.0
                    except (ValueError, TypeError):
                        wb_data[resource] = 0.0
                else:
                    wb_data[resource] = 0.0

                # 控制API请求频率
                time.sleep(SETTINGS.API_CONFIG['request_delay'])

            except Exception as e:
                self.logger.warning(f"获取世界银行数据失败 {indicator}: {e}")
                wb_data[resource] = 0.0

        return wb_data

    def get_fallback_config(self) -> Dict[str, float]:
        """API失败时的后备医疗资源配置"""
        return SETTINGS.BASE_MEDICAL_RESOURCE_DENSITIES.copy()

    def fetch_who_gho_data(self, indicators: List[str], region_code: str = "CHN") -> Dict:
        """获取WHO GHO数据"""
        who_data = {}
        retry_count = SETTINGS.API_CONFIG['max_retry_attempts']

        for indicator in indicators:
            attempt = 0
            success = False

            while attempt < retry_count and not success:
                try:
                    url = f"{SETTINGS.API_CONFIG['who_gho_base_url']}{indicator}"

                    # 根据WHO GHO API文档构建过滤器
                    params = {}
                    if region_code and region_code != "":
                        params["$filter"] = f"AreaCode eq '{region_code}'"  # WHO API参数

                    response = requests.get(url, params=params, timeout=SETTINGS.API_CONFIG['who_gho_timeout'])

                    if response.status_code == 200:
                        data = response.json().get('value', [])

                        # 将WHO数据组织成年份映射
                        year_data = {}
                        for entry in data:
                            year = str(entry.get('TimeDim', entry.get('Date', '')))
                            # WHO API可能有不同字段存储数值
                            value_str = entry.get('NumericValue', entry.get('DisplayValue', '0'))

                            try:
                                value = float(value_str) if value_str not in ['N/A', '', None] else 0.0
                                if year not in year_data:
                                    year_data[year] = []
                                year_data[year].append(value)
                            except (ValueError, TypeError):
                                continue

                        who_data[indicator] = year_data
                        success = True
                    else:
                        self.logger.warning(f"WHO API请求失败: {response.status_code}, 尝试次数: {attempt + 1}")
                        attempt += 1

                except Exception as e:
                    self.logger.warning(f"获取WHO数据失败 {indicator}, 尝试次数: {attempt + 1}, 错误: {e}")
                    attempt += 1

                if not success:
                    time.sleep(SETTINGS.API_CONFIG['request_delay'] * (2 ** attempt))  # 指数退避

            if not success:
                # 如果所有重试都失败，添加默认值
                who_data[indicator] = {}

        return who_data

    def get_real_medical_data(self, country: str = 'CN') -> Dict[str, float]:
        """获取真实医疗资源配置数据"""
        real_data = self.get_medical_density(country_code=country)

        # 如果API失败，使用后备值
        if not real_data or all(v == 0.0 for v in real_data.values()):
            self.logger.info(f"API获取{country}数据失败，使用后备配置")
            return self.get_fallback_config()

        return real_data

    def merge_external_data(self, main_df: pd.DataFrame, who_data: Dict) -> pd.DataFrame:
        """将WHO外部数据整合到主数据集"""
        df_with_external = main_df.copy()
        df_with_external = df_with_external.copy()  # 确保可写

        for indicator_code, year_data in who_data.items():
            # 查找对应的列名映射
            corresponding_col_name = SETTINGS.WHO_RESULT_COLUMN_MAPPINGS.get(indicator_code,
                                                                             f"external_{indicator_code.lower()}")

            # 添加外部列
            df_with_external[corresponding_col_name] = np.nan

            for idx, row in df_with_external.iterrows():
                # 获取年份，优先从year列，否则使用索引或其它日期列
                year_found = str(row.get('year', ''))
                if year_found == '':
                    # 如果year为空，尝试其他可能的日期相关列
                    possible_date_cols = [c for c in df_with_external.columns if
                                          'year' in c.lower() or 'time' in c.lower() or 'date' in c.lower()]
                    for date_col in possible_date_cols:
                        val = row.get(date_col)
                        if val is not None:
                            year_found = str(val)
                            break
                        else:
                            year_found = str(row.name) if hasattr(row, 'name') else str(idx)

                if year_found in year_data and len(year_data[year_found]) > 0:
                    # 取该年份的平均值
                    avg_value = np.mean(year_data[year_found])
                    df_with_external.loc[df_with_external.index[idx], corresponding_col_name] = avg_value

        return df_with_external

    def preprocess_health_data(self, file_path: str) -> Tuple[pd.DataFrame, Dict]:
        """完整的数据预处理流程"""
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path, header=[0, 1] if self._has_multilevel_header(file_path) else 0)
        except Exception as e:
            self.logger.error(f"无法读取文件: {file_path}, 错误: {e}")
            raise

        # 处理多级表头
        df = self.process_multilevel_headers(df)

        # 应用标准列名映射
        df_mapped, mapping_log = self.apply_standard_mapping(df)

        # 如果年份列为空，在某些情况下可能需要特殊处理
        if 'year' in df_mapped.columns and df_mapped['year'].isna().all():
            df_mapped['year'] = df_mapped.index.strftime('%Y') if hasattr(df_mapped.index,
                                                                          'strftime') else df_mapped.index.astype(str)

        # 尝试获取WHO外部数据 (使用映射中的WHO指标)
        who_markers = list(SETTINGS.WHO_INDICATOR_CODES.values())
        who_data = self.fetch_who_gho_data(who_markers, region_code="CHN")  # 使用中国区域代码

        # 整合外部数据
        df_final = self.merge_external_data(df_mapped, who_data)

        # 数据清洗：删除完全空的行，填充缺失值
        df_final = df_final.drop_duplicates().dropna(how='all').fillna(
            SETTINGS.TOLERANCE_LEVELS['nan_substitution_default'])

        # 返回最终数据表和处理日志
        processing_log = {
            'original_shape': df.shape,
            'final_shape': df_final.shape,
            'mapping_log': mapping_log,
            'external_features_added': [col for col in df_final.columns if col.startswith('external_')],
            'nan_counts': df_final.isna().sum().to_dict(),
            'api_integration_success': bool(who_data)  # 记录API集成是否成功
        }

        return df_final, processing_log

    def _has_multilevel_header(self, file_path: str) -> bool:
        """检测文件是否有双层表头"""
        try:
            df_test = pd.read_excel(file_path, header=[0, 1], nrows=2)  # 只读前两行用于判断
            # 检查前两行的数据模式来判断是否为多级索引
            if df_test.shape[0] >= 2:
                first_row = df_test.iloc[0].fillna('')
                second_row = df_test.iloc[1].fillna('')

                # 计算两行中的非空值交集，如果交集很小，可能是多级表头格式
                non_null_first = set([str(x) for x in first_row if x != ''])
                non_null_second = set([str(x) for x in second_row if x != ''])
                intersection_len = len(non_null_first.intersection(non_null_second))

                # 如果两行之间的共同信息较少，可能为多层级结构
                non_null_ratio_first = len(non_null_first) / len(df_test.columns)
                non_null_ratio_second = len(non_null_second) / len(df_test.columns)

                return (intersection_len / max(len(non_null_first), 1) < 0.3 and
                        non_null_ratio_first > 0.1 and
                        non_null_ratio_second > 0.1)

            # 如果获取的行数不够，采用简单策略
            return True  # 默认保守地认为可能存在双层表头
        except:
            return False  # 出现错误时不认为是多级表头


class HealthResourceAnalyzer:
    """医疗资源配置分析器"""

    def __init__(self, weighting_method: str = 'equal',
                 custom_weights: Optional[Dict] = None,
                 benchmark_data: Optional[Dict] = None,
                 normalize_output: bool = True):
        self.theoretical_need_multipliers = {}
        self.weighting_method = weighting_method
        self.custom_weights = custom_weights or {}
        self.benchmark_data = benchmark_data or SETTINGS.BASE_MEDICAL_RESOURCE_DENSITIES
        self.normalize_output = normalize_output
        self.logger = logging.getLogger(__name__)

    def calculate_base_theoretical_need(self, df: pd.DataFrame) -> pd.Series:
        """根据标准配置计算基础理论需求"""
        # 基础理论需求 = 基准配置 * 人口规模修正
        base_values = pd.Series(data=np.ones(len(df)) * 0.1, index=df.index)

        # 如果有人口数据，则根据地区人口与平均人口的比值进行调整
        if 'population' in df.columns:
            avg_pop = df['population'].mean()
            if avg_pop > 0:
                pop_factor = df['population'] / avg_pop
                base_values = base_values * pop_factor

        return base_values

    def calculate_supply_index(self, df: pd.DataFrame) -> pd.Series:
        """计算医疗资源供给指数"""
        all_resources = ['physicians_per_1000', 'nurses_per_1000', 'hospital_beds_per_1000']
        # 只选择在DataFrame中存在的列
        available_resources = [col for col in all_resources if col in df.columns]

        if not available_resources:
            return pd.Series(0.0, index=df.index)

        # 获取数据
        resource_data = df[available_resources].fillna(0)

        if self.weighting_method == 'benchmark_relative':
            return self._calculate_benchmark_relative_index(resource_data, available_resources)
        else:
            return self._calculate_weighted_index(resource_data, available_resources)

    def _calculate_weighted_index(self, data: pd.DataFrame, resources: list) -> pd.Series:
        """计算加权指数"""
        weights = self._get_dynamic_weights(resources, data)

        # 标准化处理（消除量纲影响）
        if self.normalize_output:
            scaler = MinMaxScaler()
            try:
                scaled_data = scaler.fit_transform(data.values.reshape(-1, len(resources)) if len(resources) == 1
                                                   else data[resources].values)
                if len(resources) > 1:
                    normalized_data = pd.DataFrame(scaled_data, columns=resources, index=data.index)
                else:
                    normalized_data = pd.DataFrame(scaled_data, columns=resources, index=data.index)
            except:
                # 如果标准化失败，使用原始数据
                normalized_data = data
        else:
            normalized_data = data

        # 计算加权和
        supply_index = pd.Series(0.0, index=data.index)
        for resource, weight in zip(resources, weights):
            if resource in normalized_data.columns:
                supply_index += normalized_data[resource] * weight

        return supply_index

    def _calculate_benchmark_relative_index(self, data: pd.DataFrame, resources: list) -> pd.Series:
        """计算基于基准的相对指数"""
        supply_index = pd.Series(0.0, index=data.index)
        weights = self._get_dynamic_weights(resources, data)

        for resource, weight in zip(resources, weights):
            if resource in data.columns:
                # 获取对应的基准值
                benchmark = self.benchmark_data.get(resource, data[resource].median())

                # 防止除以零
                safe_benchmark = benchmark if abs(benchmark) > SETTINGS.TOLERANCE_LEVELS[
                    'zero_division_fallback'] else 1.0

                # 计算相对得分（0-200%，超过200%的按200%计算）
                relative_score = np.minimum(data[resource] / safe_benchmark * 100, 200)
                supply_index += relative_score * weight / 100.0  # 由于relative_score是百分比，要除以100

        return supply_index

    def _get_dynamic_weights(self, resources: list, data: pd.DataFrame) -> list:
        """获取动态权重"""
        if self.weighting_method == 'equal':
            return [1.0 / len(resources)] * len(resources)

        elif self.weighting_method == 'expert':
            expert_weights = SETTINGS.RESOURCE_WEIGHTS
            weights = [expert_weights.get(r, 1.0 / len(resources)) for r in resources]
            total_weight = sum(weights)
            return [w / total_weight for w in weights] if total_weight > 0 else [1.0 / len(resources)] * len(resources)

        elif self.weighting_method == 'inverse_variance':
            # 基于数据方差的权重
            variances = data.var(numeric_only=True, skipna=True) + SETTINGS.TOLERANCE_LEVELS['zero_division_fallback']
            effective_vars = variances.reindex(resources, fill_value=1.0)
            inverse_vars = 1.0 / effective_vars
            total_inv_var = inverse_vars.sum()
            return (inverse_vars / total_inv_var).tolist() if total_inv_var > 0 else [1.0 / len(resources)] * len(
                resources)

        else:  # custom weights
            weights = [self.custom_weights.get(r, SETTINGS.RESOURCE_WEIGHTS.get(r, 1.0 / len(resources))) for r in
                       resources]
            total_weight = sum(weights)
            return [w / total_weight for w in weights] if total_weight > 0 else [1.0 / len(resources)] * len(resources)

    def apply_external_factors_to_theoretical_need(self, df: pd.DataFrame) -> pd.Series:
        """应用外部健康因素调整理论需求"""
        base_need = self.calculate_base_theoretical_need(df)

        # 初始化调整乘数
        adjustment_multiplier = pd.Series(data=np.ones(len(df)), index=df.index)

        # 高血压患病率调整因子
        hypertension_cols = [col for col in df.columns if
                             any(kw in col.lower() for kw in ['hypertension', '高血压', '高血压患病'])]
        if hypertension_cols:
            hypertension_rate = df[hypertension_cols[0]].fillna(0)
            hypertension_impact = SETTINGS.HEALTH_IMPACT_FACTORS['hypertension_prevalence_impact']
            hypertension_factor = hypertension_rate.apply(
                # 基于基础WHO高血压患病率25.2%进行对比调整
                lambda x: 1.0 + (max(0, x - SETTINGS.BASE_HEALTH_FACTORS_WHO.get('hypertension_prevalence',
                                                                                 25.2)) / 100) * hypertension_impact
            )
            adjustment_multiplier *= hypertension_factor

        # PM2.5浓度调整因子
        pm25_cols = [col for col in df.columns if any(kw in col.lower() for kw in ['pm2', 'pm2.5', 'pm25', '细颗粒物'])]
        if pm25_cols:
            pm25_concentration = df[pm25_cols[0]].fillna(0)
            pm25_impact = SETTINGS.HEALTH_IMPACT_FACTORS['pm25_impact']
            pm25_factor = pm25_concentration.apply(
                # 超过标准WHO水平(42μg/m³)的部分按影响系数调整
                lambda x: 1.0 + (
                            max(0, x - SETTINGS.BASE_HEALTH_FACTORS_WHO.get('pm25_level', 42.0)) / 100) * pm25_impact
            )
            adjustment_multiplier *= pm25_factor

        # 肥胖率调整因子
        obesity_cols = [col for col in df.columns if
                        any(kw in col.lower() for kw in ['obesity', '肥胖', 'bmi', '超重'])]
        if obesity_cols:
            obesity_rate = df[obesity_cols[0]].fillna(0)
            obesity_impact = SETTINGS.HEALTH_IMPACT_FACTORS['obesity_impact']
            obesity_factor = obesity_rate.apply(
                # 基于WHO基准肥胖率16.4%进行调整
                lambda x: 1.0 + (max(0, x - SETTINGS.BASE_HEALTH_FACTORS_WHO.get('obesity_rate',
                                                                                 16.4)) / 100) * obesity_impact
            )
            adjustment_multiplier *= obesity_factor

        # 吸烟率调整因子
        smoking_cols = [col for col in df.columns if any(kw in col.lower() for kw in ['smoking', '吸烟', '烟草'])]
        if smoking_cols:
            smoking_rate = df[smoking_cols[0]].fillna(0)
            smoking_impact = SETTINGS.HEALTH_IMPACT_FACTORS['smoking_impact']
            smoking_factor = smoking_rate.apply(
                # 基于WHO基准吸烟率26.6%
                lambda x: 1.0 + (max(0, x - SETTINGS.BASE_HEALTH_FACTORS_WHO.get('smoking_rate',
                                                                                 26.6)) / 100) * smoking_impact
            )
            adjustment_multiplier *= smoking_factor

        # 预期寿命调整因子 (反向关系 - 预期寿命越高，单位时间的医疗需求相对减少)
        life_exp_cols = [col for col in df.columns if any(kw in col.lower() for kw in ['life', '期望寿命', '预期寿命'])]
        if life_exp_cols:
            life_expectancy = df[life_exp_cols[0]].fillna(SETTINGS.BASE_HEALTH_FACTORS_WHO.get('life_expectancy', 70))
            life_exp_adjust = SETTINGS.HEALTH_IMPACT_FACTORS['life_expectancy_adjustment']
            life_exp_factor = life_expectancy.apply(
                # 较高预期寿命可能意味着更健康的生活方式，减少资源需求
                lambda x: 1.0 + (x - SETTINGS.BASE_HEALTH_FACTORS_WHO.get('life_expectancy', 70)) * life_exp_adjust
            )
            adjustment_multiplier *= life_exp_factor

        final_theoretical_need = base_need * adjustment_multiplier

        return final_theoretical_need.clip(lower=0.05)  # 确保需求不低于最小安全值

    def calculate_resource_gap_ratio(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算医疗资源供需差距比率"""
        supply_index = self.calculate_supply_index(df)
        theoretical_need = self.apply_external_factors_to_theoretical_need(df)

        # 计算差距比率 (供给 - 需求) / 需求
        # 防止除以零
        denominator = theoretical_need.where(theoretical_need != 0, 1)
        gap_ratio = (supply_index - theoretical_need) / denominator

        result_df = df.copy()
        result_df['supply_index'] = supply_index
        result_df['theoretical_need'] = theoretical_need
        result_df['resource_gap_ratio'] = gap_ratio

        # 确定缺口严重程度
        min_threshold = SETTINGS.ANALYSIS_PARAMS['min_gap_threshold']
        max_threshold = SETTINGS.ANALYSIS_PARAMS['max_gap_threshold']

        labels = SETTINGS.ANALYSIS_PARAMS['gap_severity_labels']

        severity_categories = pd.cut(
            gap_ratio,
            bins=[-float('inf'), min_threshold, max_threshold, float('inf')],
            labels=[labels['shortage'], labels['balanced'], labels['excess']]
        )

        result_df['gap_severity'] = severity_categories.astype(str)

        return result_df

    def generate_report_summary(self, analysis_result: pd.DataFrame) -> Dict:
        """生成报告摘要"""
        gap_ratios = analysis_result['resource_gap_ratio']

        overall_stats = {
            'total_regions_year_combinations': len(analysis_result),
            'average_supply_index': analysis_result['supply_index'].mean(),
            'average_theoretical_need': analysis_result['theoretical_need'].mean(),
            'average_gap_ratio': gap_ratios.mean(),
            'std_gap_ratio': gap_ratios.std(),
            'regions_over_supplied': (gap_ratios > SETTINGS.ANALYSIS_PARAMS['max_gap_threshold']).sum(),
            'regions_shortage': (gap_ratios < SETTINGS.ANALYSIS_PARAMS['min_gap_threshold']).sum(),
            'regions_in_balance': ((gap_ratios >= SETTINGS.ANALYSIS_PARAMS['min_gap_threshold']) &
                                   (gap_ratios <= SETTINGS.ANALYSIS_PARAMS['max_gap_threshold'])).sum(),
            'max_surplus_percentage': (gap_ratios.max()) * 100 if not gap_ratios.empty else 0.0,
            'max_deficit_percentage': (gap_ratios.min()) * 100 if not gap_ratios.empty else 0.0
        }

        return overall_stats


def create_mock_data() -> pd.DataFrame:
    """创建示例数据用于测试"""
    np.random.seed(42)
    regions = [f'地区A_{i}' for i in range(1, 11)]
    years = list(range(2015, 2021))

    data = {
        'region_name': [],
        'year': [],
        'physicians_per_1000': [],
        'nurses_per_1000': [],
        'hospital_beds_per_1000': [],
        'population': [],
        'external_hypertension_prevalence': [],
        'external_pm25': [],
        'external_obesity': [],
        'external_smoking': []
    }

    for region in regions:
        for year in years:
            data['region_name'].append(region)
            data['year'].append(year)
            data['physicians_per_1000'].append(np.random.uniform(1.0, 4.0))
            data['nurses_per_1000'].append(np.random.uniform(2.0, 6.0))
            data['hospital_beds_per_1000'].append(np.random.uniform(3.0, 8.0))
            data['population'].append(np.random.uniform(1000000, 10000000))
            data['external_hypertension_prevalence'].append(np.random.uniform(20, 80))  # 百分比
            data['external_pm25'].append(np.random.uniform(25, 75))  # μg/m³
            data['external_obesity'].append(np.random.uniform(10, 40))  # 百分比
            data['external_smoking'].append(np.random.uniform(10, 30))  # 百分比

    return pd.DataFrame(data)


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    # 创建处理器
    preprocessor = HealthDataPreprocessor()
    analyzer = HealthResourceAnalyzer(weighting_method='expert')

    # 示例：使用示例数据进行测试 (实际应用中替换为真实文件路径)
    try:
        # 假设我们有真实数据文件，使用示例数据进行演示
        if not preprocessor._has_multilevel_header(SETTINGS.RAW_DATA_FILE) if SETTINGS.RAW_DATA_FILE else True:
            sample_data = create_mock_data()
            processed_data = sample_data
        else:
            # 实际读取文件
            processed_data, log = preprocessor.preprocess_health_data(SETTINGS.RAW_DATA_FILE)

        # 执行分析
        results = analyzer.calculate_resource_gap_ratio(processed_data)
        summary = analyzer.generate_report_summary(results)

        print("=== 医疗资源配置分析结果 ===")
        print(f"总体统计：{summary}")
        print(f"\n缺口等级分布：")
        print(results['gap_severity'].value_counts())

        # 显示前几行结果以供审查
        report_cols = [col for col in ['region_name', 'year', 'supply_index', 'theoretical_need',
                                       'resource_gap_ratio', 'gap_severity'] if col in results.columns]
        print(f"\n前5行分析结果：")
        print(results[report_cols].head())

    except FileNotFoundError:
        print(f"未找到配置的文件 {SETTINGS.RAW_DATA_FILE}，使用模拟数据进行演示...")
        # 使用示例数据作为替代
        sample_data = create_mock_data()

        # 整合预处理器和分析器
        processed_sample = preprocessor.process_multilevel_headers(sample_data)
        results = analyzer.calculate_resource_gap_ratio(processed_sample)
        summary = analyzer.generate_report_summary(results)

        print("=== 基于示例数据的分析结果 ===")
        print(f"总体统计：{summary}")
        print(f"\n缺口等级分布：")
        print(results['gap_severity'].value_counts())
        report_cols = [col for col in ['region_name', 'year', 'supply_index', 'theoretical_need',
                                       'resource_gap_ratio', 'gap_severity'] if col in results.columns]
        print(f"\n前5行分析结果：")
        print(results[report_cols].head())
