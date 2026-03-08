# integrated_data_preprocessing_optimized.py
import pandas as pd
import numpy as np
import requests
import re
import time
from typing import Dict, List, Tuple, Optional
import logging
from sklearn.preprocessing import MinMaxScaler
from unified_interface import UnifiedDataPreprocessor
from config.settings import SETTINGS, STANDARD_COLUMN_MAPPING
from datetime import datetime

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

    def clean_health_data(self,input_file, output_file):
        """使用统一接口清洗健康数据"""
        preprocessor = UnifiedDataPreprocessor()
        preprocessor.clean_health_data(input_file, output_file)
        print(f"数据已从 {input_file} 清洗并保存至 {output_file}")

    def process_multilevel_headers(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理多级表头，将其扁平化"""
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join([str(c) for c in col]).strip() for col in df.columns]
        df.columns = [re.sub(r'\s+', '_', col.strip()) for col in df.columns]
        df.columns = [re.sub(r'_+', '_', col) for col in df.columns]
        return df

    def apply_standard_mapping(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        identified_cols = identify_column_types(df.columns)
        inverse_mapping = {}
        for original_col, standard_name in identified_cols.items():
            new_col = standard_name
            if original_col != standard_name:
                counter = 1
                temp_name = new_col
                while temp_name in inverse_mapping.values():
                    temp_name = f"{standard_name}_{counter}"
                    counter += 1
                new_col = temp_name
            inverse_mapping[original_col] = new_col
        return df.rename(columns=inverse_mapping), inverse_mapping

    def get_medical_density(self, country_code: str = 'CN', target_year: Optional[str] = None) -> Optional[Dict[str, float]]:
        """从API获取医疗资源数据（解除硬编码年份）"""
        year = target_year or str(datetime.now().year - 1)
        wb_data = {}
        medical_indicators = {
            'physicians_per_1000': 'SH.MED.PHYS.ZS',
            'nurses_per_1000': 'SH.MED.NUMW.P3',
            'hospital_beds_per_1000': 'SH.MED.BEDS.ZS'
        }

        for resource, indicator in medical_indicators.items():
            try:
                url = f"{SETTINGS.API_CONFIG['world_bank_base_url']}country/{country_code}/indicator/{indicator}"
                params = {'date': year, 'format': 'json', 'per_page': 100}
                response = requests.get(url, params=params, timeout=SETTINGS.API_CONFIG['world_bank_api_timeout'])
                response.raise_for_status()

                data = response.json()
                if len(data) > 1 and data[1] and len(data[1]) > 0:
                    value = data[1][0].get('value')
                    wb_data[resource] = float(value) if value is not None else 0.0
                else:
                    wb_data[resource] = 0.0
                time.sleep(SETTINGS.API_CONFIG['request_delay'])
            except Exception as e:
                self.logger.warning(f"获取世界银行数据失败 {indicator}: {e}")
                wb_data[resource] = 0.0

        return wb_data

    def get_fallback_config(self) -> Dict[str, float]:
        """API失败时的后备医疗资源配置"""
        return SETTINGS.BASE_MEDICAL_RESOURCE_DENSITIES.copy()

    def fetch_who_gho_data(self, indicators: Optional[List[str]] = None, region_code: str = "CHN") -> Dict:
        """获取WHO GHO数据"""
        who_data = {}
        retry_count = SETTINGS.API_CONFIG['max_retry_attempts']

        target_indicators = indicators or list(SETTINGS.WHO_INDICATOR_CODES.values())

        for indicator in indicators:
            attempt = 0
            success = False
            while attempt < retry_count and not success:
                try:
                    url = f"{SETTINGS.API_CONFIG['who_gho_base_url']}{indicator}"
                    params = {"$filter": f"AreaCode eq '{region_code}'"} if region_code else {}
                    response = requests.get(url, params=params, timeout=SETTINGS.API_CONFIG['who_gho_timeout'])

                    # 根据WHO GHO API文档构建过滤器
                    if response.status_code == 200:
                        data = response.json().get('value', [])
                        year_data = {}
                        for entry in data:
                            year = str(entry.get('TimeDim', entry.get('Date', '')))
                            value_str = entry.get('NumericValue', entry.get('DisplayValue', '0'))
                            try:
                                value = float(value_str) if value_str not in ['N/A', '', None] else 0.0
                                year_data.setdefault(year, []).append(value)
                            except (ValueError, TypeError):
                                continue
                        who_data[indicator] = year_data
                        success = True
                    else:
                        attempt += 1
                except Exception as e:
                    self.logger.warning(f"获取WHO数据失败 {indicator}: {e}")
                    attempt += 1

                if not success:
                    time.sleep(SETTINGS.API_CONFIG['request_delay'] * (2 ** attempt))

            if not success:
                    who_data[indicator] = {}
        return who_data

    def get_real_medical_data(self, country: str = 'CN') -> Dict[str, float]:
        """获取真实医疗资源配置数据"""
        real_data = self.get_medical_density(country_code=country)

        # 如果API失败，使用后备值
        if not real_data or all(v == 0.0 for v in real_data.values()):
            return self.get_fallback_config()
        return real_data

    def merge_external_data(self, main_df: pd.DataFrame, who_data: Dict) -> pd.DataFrame:
        """将WHO外部数据整合到主数据集"""
        df_with_external = main_df.copy()
        for indicator_code, year_data in who_data.items():
            col_name = SETTINGS.WHO_RESULT_COLUMN_MAPPINGS.get(indicator_code, f"external_{indicator_code.lower()}")
            df_with_external[col_name] = np.nan

            for idx, row in df_with_external.iterrows():
                year_found = str(row.get('year', ''))
                if not year_found:
                    possible_date_cols = [c for c in df_with_external.columns if
                                          'year' in c.lower() or 'time' in c.lower() or 'date' in c.lower()]
                    for date_col in possible_date_cols:
                        if (val := row.get(date_col)) is not None:
                            year_found = str(val)
                            break
                    else:
                        year_found = str(row.name) if hasattr(row, 'name') else str(idx)

                if year_found in year_data and year_data[year_found]:
                    df_with_external.loc[df_with_external.index[idx], col_name] = np.mean(year_data[year_found])
        return df_with_external

    def preprocess_health_data(self, file_path: str, region_code: str = "CHN") -> Tuple[pd.DataFrame, Dict]:
        try:
            df = pd.read_excel(file_path, header=[0, 1] if self._has_multilevel_header(file_path) else 0)
        except Exception as e:
            self.logger.error(f"无法读取文件: {e}")
            raise


        df = self.process_multilevel_headers(df)
        df_mapped, mapping_log = self.apply_standard_mapping(df)

        # 如果年份列为空，在某些情况下可能需要特殊处理
        if 'year' in df_mapped.columns and df_mapped['year'].isna().all():
            df_mapped['year'] = df_mapped.index.astype(str)

        # 尝试获取WHO外部数据 (使用映射中的WHO指标)
        who_markers = list(SETTINGS.WHO_INDICATOR_CODES.values())
        who_data = self.fetch_who_gho_data(who_markers, region_code=region_code)
        # 整合外部数据
        df_final = self.merge_external_data(df_mapped, who_data)
        df_final = df_final.drop_duplicates().dropna(how='all').fillna(
            SETTINGS.TOLERANCE_LEVELS['nan_substitution_default'])

        return df_final, {
            'original_shape': df.shape,
            'final_shape': df_final.shape,
            'mapping_log': mapping_log,
            'external_features_added': [col for col in df_final.columns if col.startswith('external_')],
            'nan_counts': df_final.isna().sum().to_dict(),
            'api_integration_success': bool(who_data)
        }


    def _has_multilevel_header(self, file_path: str) -> bool:
        try:
            df_test = pd.read_excel(file_path, header=[0, 1], nrows=2)
            if df_test.shape[0] >= 2:
                first_row = set([str(x) for x in df_test.iloc[0].fillna('') if x != ''])
                second_row = set([str(x) for x in df_test.iloc[1].fillna('') if x != ''])
                intersection_len = len(first_row.intersection(second_row))
                return (intersection_len / max(len(first_row), 1) < 0.3 and
                        len(first_row) / len(df_test.columns) > 0.1 and
                        len(second_row) / len(df_test.columns) > 0.1)
            return True
        except:
            return False

class HealthResourceAnalyzer:
    """医疗资源配置分析器"""

    def __init__(self, weighting_method: str = 'equal',
                 custom_weights: Optional[Dict] = None,
                 benchmark_data: Optional[Dict] = None,
                 health_impact_factors: Optional[Dict] = None,
                 base_health_factors: Optional[Dict] = None,
                 normalize_output: bool = True):
        self.weighting_method = weighting_method
        self.custom_weights = custom_weights or {}
        # 依赖注入，以SETTINGS为备用
        self.benchmark_data = benchmark_data or SETTINGS.BASE_MEDICAL_RESOURCE_DENSITIES
        self.health_impact_factors = health_impact_factors or SETTINGS.HEALTH_IMPACT_FACTORS
        self.base_health_factors = base_health_factors or SETTINGS.BASE_HEALTH_FACTORS_WHO
        self.normalize_output = normalize_output
        self.logger = logging.getLogger(__name__)

    def calculate_base_theoretical_need(self, df: pd.DataFrame) -> pd.Series:
        base_values = pd.Series(data=np.ones(len(df)) * 0.1, index=df.index)
        if 'population' in df.columns:
            avg_pop = df['population'].mean()
            if avg_pop > 0:
                base_values *= (df['population'] / avg_pop)
        return base_values

    def calculate_supply_index(self, df: pd.DataFrame) -> pd.Series:
        all_resources = ['physicians_per_1000', 'nurses_per_1000', 'hospital_beds_per_1000']
        available_resources = [col for col in all_resources if col in df.columns]

        if not available_resources:
            return pd.Series(0.0, index=df.index)

        resource_data = df[available_resources].fillna(0)
        if self.weighting_method == 'benchmark_relative':
            return self._calculate_benchmark_relative_index(resource_data, available_resources)
        return self._calculate_weighted_index(resource_data, available_resources)

    def _calculate_weighted_index(self, data: pd.DataFrame, resources: list) -> pd.Series:
        weights = self._get_dynamic_weights(resources, data)
        if self.normalize_output:
            scaler = MinMaxScaler()
            try:
                scaled_data = scaler.fit_transform(data.values.reshape(-1, len(resources)) if len(resources) == 1 else data[resources].values)
                normalized_data = pd.DataFrame(scaled_data, columns=resources, index=data.index)
            except:
                normalized_data = data
        else:
            normalized_data = data

        supply_index = pd.Series(0.0, index=data.index)
        for resource, weight in zip(resources, weights):
            if resource in normalized_data.columns:
                supply_index += normalized_data[resource] * weight
        return supply_index

    def _calculate_benchmark_relative_index(self, data: pd.DataFrame, resources: list) -> pd.Series:
        supply_index = pd.Series(0.0, index=data.index)
        weights = self._get_dynamic_weights(resources, data)

        for resource, weight in zip(resources, weights):
            if resource in data.columns:
                benchmark = self.benchmark_data.get(resource, data[resource].median())
                safe_benchmark = benchmark if abs(benchmark) > SETTINGS.TOLERANCE_LEVELS['zero_division_fallback'] else 1.0
                relative_score = np.minimum(data[resource] / safe_benchmark * 100, 200)
                supply_index += relative_score * weight / 100.0
        return supply_index

    def _get_dynamic_weights(self, resources: list, data: pd.DataFrame) -> list:
        if self.weighting_method == 'equal':
            return [1.0 / len(resources)] * len(resources)
        elif self.weighting_method == 'expert':
            weights = [SETTINGS.RESOURCE_WEIGHTS.get(r, 1.0 / len(resources)) for r in resources]
        elif self.weighting_method == 'inverse_variance':
            variances = data.var(numeric_only=True, skipna=True) + SETTINGS.TOLERANCE_LEVELS['zero_division_fallback']
            inverse_vars = 1.0 / variances.reindex(resources, fill_value=1.0)
            weights = inverse_vars.tolist()
        else:
            weights = [self.custom_weights.get(r, SETTINGS.RESOURCE_WEIGHTS.get(r, 1.0 / len(resources))) for r in
                       resources]

        total_weight = sum(weights)
        return [w / total_weight for w in weights] if total_weight > 0 else [1.0 / len(resources)] * len(resources)

    def apply_external_factors_to_theoretical_need(self, df: pd.DataFrame) -> pd.Series:
        base_need = self.calculate_base_theoretical_need(df)
        adjustment_multiplier = pd.Series(data=np.ones(len(df)), index=df.index)

        # 解除硬编码：全部从类的实例变量（注入的配置或SETTINGS）动态获取
        if hypertension_cols := [col for col in df.columns if any(kw in col.lower() for kw in ['hypertension', '高血压'])]:
            impact = self.health_impact_factors.get('hypertension_prevalence_impact', 0.3)
            base_val = self.base_health_factors.get('hypertension_prevalence', 25.2)
            adjustment_multiplier *= df[hypertension_cols[0]].fillna(0).apply(lambda x: 1.0 + (max(0, x - base_val) / 100) * impact)

        if pm25_cols := [col for col in df.columns if any(kw in col.lower() for kw in ['pm2', '细颗粒物'])]:
            impact = self.health_impact_factors.get('pm25_impact', 0.04)
            base_val = self.base_health_factors.get('pm25_level', 42.0)
            adjustment_multiplier *= df[pm25_cols[0]].fillna(0).apply(lambda x: 1.0 + (max(0, x - base_val) / 100) * impact)

        if obesity_cols := [col for col in df.columns if any(kw in col.lower() for kw in ['obesity', '肥胖', 'bmi', '超重'])]:
            impact = self.health_impact_factors.get('obesity_impact', 0.25)
            base_val = self.base_health_factors.get('obesity_rate', 16.4)
            adjustment_multiplier *= df[obesity_cols[0]].fillna(0).apply(lambda x: 1.0 + (max(0, x - base_val) / 100) * impact)

        if smoking_cols := [col for col in df.columns if any(kw in col.lower() for kw in ['smoking', '吸烟', '烟草'])]:
            impact = self.health_impact_factors.get('smoking_impact', 0.2)
            base_val = self.base_health_factors.get('smoking_rate', 26.6)
            adjustment_multiplier *= df[smoking_cols[0]].fillna(0).apply(lambda x: 1.0 + (max(0, x - base_val) / 100) * impact)

        if life_exp_cols := [col for col in df.columns if any(kw in col.lower() for kw in ['life', '预期寿命'])]:
            impact = self.health_impact_factors.get('life_expectancy_adjustment', -0.02)
            base_val = self.base_health_factors.get('life_expectancy', 70.0)
            adjustment_multiplier *= df[life_exp_cols[0]].fillna(base_val).apply(lambda x: 1.0 + (x - base_val) * impact)

        return (base_need * adjustment_multiplier).clip(lower=0.05)  # 确保需求不低于最小安全值

    def calculate_resource_gap_ratio(self, df: pd.DataFrame) -> pd.DataFrame:
        supply_index = self.calculate_supply_index(df)
        theoretical_need = self.apply_external_factors_to_theoretical_need(df)

        denominator = theoretical_need.where(theoretical_need != 0, 1)
        gap_ratio = (supply_index - theoretical_need) / denominator

        result_df = df.copy()
        result_df['supply_index'] = supply_index
        result_df['theoretical_need'] = theoretical_need
        result_df['resource_gap_ratio'] = gap_ratio

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
        gap_ratios = analysis_result['resource_gap_ratio']

        # 修复布尔类型强制转换：使用 int() 包裹 .sum() 避免返回 numpy.int64 造成后端序列化异常
        return {
            'total_regions_year_combinations': len(analysis_result),
            'average_supply_index': float(analysis_result['supply_index'].mean()),
            'average_theoretical_need': float(analysis_result['theoretical_need'].mean()),
            'average_gap_ratio': float(gap_ratios.mean()),
            'std_gap_ratio': float(gap_ratios.std()),
            'regions_over_supplied': int((gap_ratios > SETTINGS.ANALYSIS_PARAMS['max_gap_threshold']).sum()),
            'regions_shortage': int((gap_ratios < SETTINGS.ANALYSIS_PARAMS['min_gap_threshold']).sum()),
            'regions_in_balance': int(((gap_ratios >= SETTINGS.ANALYSIS_PARAMS['min_gap_threshold']) &
                                       (gap_ratios <= SETTINGS.ANALYSIS_PARAMS['max_gap_threshold'])).sum()),
            'max_surplus_percentage': float(gap_ratios.max() * 100) if not gap_ratios.empty else 0.0,
            'max_deficit_percentage': float(gap_ratios.min() * 100) if not gap_ratios.empty else 0.0
        }


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
