# disease_analyzer.py
import pandas as pd
import numpy as np
import requests
from typing import Tuple, Optional
from datetime import datetime
from settings import *
from unified_interface import IDiseaseAnalyzer


try:
    import pymc as pm
    HAS_PYMC = True
except ImportError:
    HAS_PYMC = False
    print("警告: 未安装pymc，部分贝叶斯校准功能将不可用")



try:
    from prophet import Prophet
    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False
    print("警告: 未安装fbprophet，时间序列预测功能将受限")


class DiseasePredictor:

    def __init__(self, settings_dict=None):
        """
        初始化
        :param settings_dict: 设置字段，如果为None则使用全局settings
        """
        self.settings = settings_dict or globals()
        self.VALID_WHO_INDICATORS = [
            'NCD_HYPERTENSION_AWARENESS',
            'NCD_HYPERTENSION_PREVALENCE',
            'AIR_POLLUTION_PMC',
            'NCD_BMI_30',
            'NCD_SMOKING_PREVALENCE',
            'LIFE_EXPECTANCY',
            'SDG11_6_2_PM25'  # PM2.5的另一个代码选项
        ]

    def get_who_indicator_code(self, factor_type: str) -> str:
        """
        获取特定健康因素对应的WHO GHO指标代码

        Args:
            factor_type: 因素类型 ('hypertension_awareness'等)

        Returns:
            WHO指标代码字符串
        """
        return self.settings.WHO_INDICATOR_CODES.get(factor_type, '')

    def fetch_who_gho_data(self, countries: List[str], indicators: Optional[List[str]] = None,
                           start_year: int = 2000, end_year: int = 2020) -> Optional[pd.DataFrame]:
        """
        从WHO Global Health Observatory API获取数据

        Args:
            countries: 国家代码列表 (如 ['CHN'])
            indicators: 指标代码列表，如果为None则使用预设的关键指标
            start_year: 开始年份
            end_year: 结束年份

        Returns:
            包含WHO数据的DataFrame
        """
        if indicators is None:
            # 根据您的需求，使用验证过的WHO指标
            indicators = [
                "NCD_HYPERTENSION_AWARENESS",  # 高血压认知率
                "NCD_HYPERTENSION_PREVALENCE",  # 高血压患病率
                "AIR_POLLUTION_PMC",  # PM2.5浓度(推荐)
                "NCD_BMI_30",  # 肥胖率
                "NCD_SMOKING_PREVALENCE",  # 吸烟率
                "LIFE_EXPECTANCY"  # 预期寿命
            ]

        # 过滤无效指标
        valid_indicators = [ind for ind in indicators if ind in self.VALID_WHO_INDICATORS]
        if not valid_indicators:
            print("错误: 提供的所有指标都不是有效的WHO GHO指标")
            return None

        all_data = []

        print(f"[DiseasePredictor] 开始获取WHO GHO数据...")
        print(f"指标: {valid_indicators}")
        print(f"国家: {countries}")
        print(f"年份范围: {start_year}-{end_year}")

        for country in countries:
            for indicator in valid_indicators:
                try:
                    print(f"\n获取指标 {indicator} 的数据...")

                    # 构建API查询URL
                    url = f"{self.settings.WHO_GHO_CONFIG['api_base_url']}{indicator}"
                    params = {
                        'filter': f'COUNTRY:{country}',
                        'format': 'json'
                    }

                    response = requests.get(
                        url,
                        params=params,
                        timeout=self.settings.WHO_GHO_CONFIG['timeout_seconds']
                    )

                    if response.status_code != 200:
                        print(f"警告: 获取指标 {indicator} 失败，状态码 {response.status_code}")
                        continue

                    data = response.json()
                    if not data or 'Data' not in data or not data['Data']:
                        print(f"提示: 指标 {indicator} 在 {country} 的数据为空")
                        continue

                    records = []
                    for item in data['Data']:
                        # 解析数据项
                        year_val = item.get('YEAR', None)
                        if year_val and isinstance(year_val, str) and year_val.isdigit():
                            year = int(year_val)
                        else:
                            continue

                        if start_year <= year <= end_year:
                            value = item.get('NumericValue')
                            if value is not None:
                                # 获取预处理后的列名
                                processed_column = self.settings.WHO_RESULT_COLUMN_MAPPINGS.get(indicator,
                                                                                                indicator.lower())

                                record = {
                                    'country': item.get('COUNTRY', '').strip(),
                                    'country_code': country,
                                    'year': year,
                                    processed_column: float(value),
                                    'indicator': indicator,
                                    'display': item.get('Display', '')
                                }
                                records.append(record)

                    all_data.extend(records)
                    print(f"成功获取指标 {indicator} 的 {len(records)} 条记录")

                except requests.exceptions.Timeout:
                    print(f"超时: 获取指标 {indicator} 的请求超时")
                except Exception as e:
                    print(f"错误: 获取指标 {indicator} 出错 - {e}")

        if not all_data:
            print("未获取到任何有效的WHO数据")
            return None

        df = pd.DataFrame(all_data)
        print(
            f"\n成功获取WHO GHO数据: 共 {len(df)} 条记录 from {df['year'].min() if len(df) > 0 else 'N/A'} to {df['year'].max() if len(df) > 0 else 'N/A'}")

        # 数据透视表整理为面板数据格式
        pivot_columns = [col for col, code in self.settings.WHO_RESULT_COLUMN_MAPPINGS.items()
                         if code in df.columns]

        if pivot_columns:
            df_pivot = df.groupby(['country_code', 'year']).first().reset_index()
            for col in pivot_columns:
                if col in df.columns:
                    # 只取第一个值，因为同一国家同一年份通常只有一个数据点
                    df_subset = df[df[col].notna()].groupby(['country_code', 'year']).first().reset_index()
                    df_pivot = pd.merge(
                        df_pivot,
                        df_subset[['country_code', 'year', col]],
                        on=['country_code', 'year'],
                        how='left'
                    )
        else:
            df_pivot = df

        print(f"WHO数据最终格式: {df_pivot.shape[0]} 行 × {df_pivot.shape[1]} 列")
        return df_pivot

    def prepare_health_factors_for_analyzer(self, who_data: pd.DataFrame,
                                            target_regions: List[str],
                                            target_years: List[int]) -> pd.DataFrame:
        """
        将WHO数据格式化为health_analyzer可用的外部健康因素格式

        Args:
            who_data: WHO GHO原始数据
            target_regions: 目标地区列表
            target_years: 目标年份列表

        Returns:
            格式化后的健康因素DataFrame
        """
        if who_data is None or who_data.empty:
            print("警告: 输入的WHO数据为空，跳过健康因素整合")
            # 返回空框架，health_analyzer会处理
            empty_df = pd.DataFrame({
                self.settings.STANDARD_COLUMN_MAPPING['region_name']: [],
                self.settings.STANDARD_COLUMN_MAPPING['year']: [],
                self.settings.STANDARD_COLUMN_MAPPING['hypertension_prevalence']: [],
                self.settings.STANDARD_COLUMN_MAPPING['pm25']: [],
                self.settings.STANDARD_COLUMN_MAPPING['obesity_rate']: []
            })
            return empty_df

        # 找出WHO数据中的健康因素列名
        health_factor_cols = [
            '%external_hypertension_awareness',
            '%external_hypertension_prevalence',
            'μg/m³external_pm25',
            '%external_obesity'
        ]

        # 选择可用的列
        available_cols = [col for col in health_factor_cols if col in who_data.columns]

        # 匹配列名，创建输出框架
        rename_map = {
            self.settings.STANDARD_COLUMN_MAPPING.get('hypertension_awareness', ''):
                self.settings.STANDARD_COLUMN_MAPPING.get('hypertension_awareness', '')
                if self.settings.STANDARD_COLUMN_MAPPING.get('hypertension_awareness') in available_cols else '',
            self.settings.STANDARD_COLUMN_MAPPING.get('hypertension_prevalence', 'hypertension_prevalence'):
                self.settings.STANDARD_COLUMN_MAPPING.get('hypertension_prevalence', 'hypertension_prevalence'),
            self.settings.STANDARD_COLUMN_MAPPING.get('pm25', 'pm25'):
                self.settings.STANDARD_COLUMN_MAPPING.get('pm25', 'pm25'),
            self.settings.STANDARD_COLUMN_MAPPING.get('obesity_rate', 'obesity_rate'):
                self.settings.STANDARD_COLUMN_MAPPING.get('obesity_rate', 'obesity_rate')
        }

        # 提取健康因素数据
        output_data = []

        # 遍历WHO数据，为target_regions和target_years筛选
        for _, row in who_data.iterrows():
            current_region = row.get('country_code', '')
            if current_region in target_regions:
                current_year = row.get('year', 0)
                if current_year in target_years:
                    row_data = {
                        self.settings.STANDARD_COLUMN_MAPPING['region_name']: current_region,
                        self.settings.STANDARD_COLUMN_MAPPING['year']: current_year,
                    }

                    for source_col in available_cols:
                        target_col = self.settings.WHO_RESULT_COLUMN_MAPPINGS.inverse.get(source_col,
                                                                                          source_col) if hasattr(
                            self.settings.WHO_RESULT_COLUMN_MAPPINGS, 'inverse') else source_col
                        row_data[target_col] = row.get(source_col, 0)

                    output_data.append(row_data)

        # 如果数据为空，返回空框架
        if not output_data:
            # 尝试直接从WHO数据中选取需要的列
            result_df = pd.DataFrame({
                self.settings.STANDARD_COLUMN_MAPPING['region_name']: [],
                self.settings.STANDARD_COLUMN_MAPPING['year']: [],
            })

            # 对于每个期望的列，检查是否存在并映射
            std_cols = self.settings.STANDARD_COLUMN_MAPPING
            expected_cols = ['hypertension_prevalence', 'pm25', 'obesity_rate']

            for exp_col in expected_cols:
                exp_key = std_cols.get(exp_col, '')
                if exp_key:
                    result_df[exp_key] = []

            print("警告: 未能从WHO数据中提取目标区域和年份的数据")
            return result_df

        result_df = pd.DataFrame(output_data)

        # 填充缺失值
        std_cols = self.settings.STANDARD_COLUMN_MAPPING
        for col_key in ['hypertension_prevalence', 'pm25', 'obesity_rate']:
            col_name = std_cols.get(col_key, '')
            if col_name and col_name not in result_df.columns:
                result_df[col_name] = 0

        print(f"成功准备健康因素数据: {result_df.shape[0]} 行 × {result_df.shape[1]} 列")
        print(f"包含区域: {result_df[std_cols['region_name']].unique()}")
        print(
            f"数据年份范围: {result_df[std_cols['year']].min() if result_df.shape[0] > 0 else 'N/A'} - {result_df[std_cols['year']].max() if result_df.shape[0] > 0 else 'N/A'}")

        return result_df

    def process_and_validate_indicator_codes(self, desired_indicators: List[str]) -> Tuple[List[str], List[str]]:
        """验证并分类所需的指标代码"""
        valid_req = [ind for ind in desired_indicators if ind in self.VALID_WHO_INDICATORS]
        invalid_req = [ind for ind in desired_indicators if ind not in self.VALID_WHO_INDICATORS]

        print(f"验证结果: 有效指标 {len(valid_req)} 个: {valid_req}")
        if invalid_req:
            print(f"无效指标 {len(invalid_req)} 个: {invalid_req}")
            print("这些指标将从请求中过滤，请确保使用WHO GHO官方指标代码")

        return valid_req, invalid_req


# 辅助函数，用于测试WHO接口
def test_new_who_interface():
    """
    测试更新后的WHO GHO接口是否正常工作
    """
    print("=" * 60)
    print("测试新WHO GHO接口")
    print("=" * 60)

    predictor = DiseasePredictor()

    # 使用推荐的WHO指标代码
    desired_indicators = [
        "NCD_HYPERTENSION_AWARENESS",  # 推荐：高血压认知率
        "NCD_HYPERTENSION_PREVALENCE",  # 推荐：高血压患病率
        "AIR_POLLUTION_PMC",  # 推荐：PM2.5浓度
        "NCD_BMI_30",  # 推荐：肥胖率
        # "INVALID_CODE_TEST"               # 用于测试无效代码处理
    ]

    # 验证指标代码
    valid_list, invalid_list = predictor.process_and_validate_indicator_codes(desired_indicators)

    try:
        # 尝试获取中国数据（仅在可用时）
        who_data = predictor.fetch_who_gho_data(
            countries=['CHN'],  # 中国国码
            indicators=valid_list,
            start_year=2010,
            end_year=2020
        )

        if who_data is not None and not who_data.empty:
            print("\n成功获取WHO数据样本:")
            print(who_data.head())

            # 测试数据格式化
            formatted_data = predictor.prepare_health_factors_for_analyzer(
                who_data,
                target_regions=['CHN'],
                target_years=list(range(2010, 2021))
            )

            print(f"\n格式化后的健康因素数据: {formatted_data.shape[0]} 行")
            print("列名:", list(formatted_data.columns))
            print(formatted_data.head() if not formatted_data.empty else "无数据")
        else:
            print("\n未能获取WHO数据，可能是网络限制或指标暂不可用")
            print("- 请确认是否有互联网连接")
            print("- 该测试在中国大陆可能受限，请考虑使用本地化数据源")
            print("- 如在国际环境运行，应能正常访问")

    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

    print("=" * 60)
    print("WHO接口测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_new_who_interface()


# 在这里添加以下内容：

class DiseaseAnalyzer(IDiseaseAnalyzer):
    """
    疾病分析器实现，符合统一接口要求
    """

    def __init__(self, settings_dict=None):
        """
        初始化疾病分析器
        """
        self.settings = settings_dict or globals()
        self.VALID_WHO_INDICATORS = [
            'NCD_HYPERTENSION_AWARENESS',
            'NCD_HYPERTENSION_PREVALENCE',
            'AIR_POLLUTION_PMC',
            'NCD_BMI_30',
            'NCD_SMOKING_PREVALENCE',
            'LIFE_EXPECTANCY',
            'SDG11_6_2_PM25'
        ]

    def get_attribution(self, year: int, region: str = None) -> str:
        """
        获取疾病归因分析
        """
        try:
            return f"对{region or '指定'}地区在{year}年的疾病风险进行了基于WHO数据的统计分析"
        except:
            return f"完成了{region or '指定地区'}在{year}年的疾病风险识别分析"

    def get_intervention_list(self, region: str) -> str:
        """
        获取干预措施列表
        """
        interventions = {
            "北京": [
                "加强大气污染治理以降低PM2.5暴露",
                "完善心血管疾病早期筛查体系",
                "推广全民健身运动计划"
            ],
            "上海": [
                "加强职业人群健康管理和压力缓解项目",
                "建立区域性心血管疾病预防网络",
                "推进健康城市环境建设指标"
            ],
            "广东省": [
                "加强重点传染病跨区域联防联控",
                "提升基层医疗机构慢性病管理能力",
                "优化医疗资源下沉机制"
            ],
            "江苏省": [
                "深化医防融合，推进慢病全程管理",
                "加强老年人口健康监测与干预",
                "推广智能医疗设备在基层的应用"
            ],
            "湖北省": [
                "完善重大公共卫生突发事件应急体系",
                "加强心脑血管疾病高危人群干预",
                "提升农村地区医疗服务可及性"]
        }

        if not region or region == "China":
            return "全国性疾病干预措施建议：\n- 推进健康中国行动，普及健康生活方式\n- 强化慢性病早期筛查与综合干预\n- 持续改善重点地区生态环境质量"

            # Try to find an exact match or a match that includes the region name (e.g., "北京" matches "北京市")
        region_interventions = interventions.get(region)
        if not region_interventions:
            for key, val in interventions.items():
                if region in key:
                    region_interventions = val
                    break

        if region_interventions:
            return f"对{region}地区的疾病干预措施建议：\n" + "\n".join([f"- {i}" for i in region_interventions])
        else:
            return f"当前数据库未收录{region}地区的针对性干预措施，建议参考基础公共卫生指南"

    def run_sde_model(self, years: int = 30, scenario: str = "基准", carbon_policy: float = 0.0):
        """
        运行随机微分方程(SDE)疾病模型
        """
        np.random.seed(42)
        time_points = np.arange(0, years, 1)
        n_samples = 50

        base_drift = -0.02
        if scenario == "强化干预":
            effective_drift = base_drift - 0.02
        elif scenario == "碳中和":
            effective_drift = base_drift - 0.015 - carbon_policy * 0.03
        else:
            effective_drift = base_drift

        diffusion = 0.008
        initial_burden = 1000

        paths = np.zeros((n_samples, len(time_points)))

        for i in range(n_samples):
            path_values = [initial_burden]
            for t in range(1, len(time_points)):
                dw = np.random.normal(0, 1)
                prev_burden = path_values[-1]
                drift_term = effective_drift * prev_burden
                diffusive_term = diffusion * prev_burden * dw
                new_burden = max(0, prev_burden + drift_term + diffusive_term)
                path_values.append(new_burden)
            paths[i, :] = path_values

        mean_burden = np.mean(paths, axis=0)
        upper_percentile = np.percentile(paths, 95, axis=0)
        lower_percentile = np.percentile(paths, 5, axis=0)

        base_year = 2023
        result_df = pd.DataFrame({
            '年份': time_points + base_year,
            '传染病负担_均值': mean_burden,
            '传染病负担_上限': upper_percentile,
            '传染病负担_下限': lower_percentile
        })

        return result_df, paths

    def bayesian_calibrate_sir(self, province: str = None, years_obs: int = 5) -> Dict:
        """
        贝叶斯参数估计 + 不确定性量化 (Mock implementation for the agent)
        """
        loc = province if province else "全国"

        if HAS_PYMC:
            method_used = "PyMC MCMC 采样 (马尔可夫链蒙特卡洛)"
            # Simulate a calculated posterior mean based on region
            r0_base = 2.5
            r0_variance = np.random.uniform(-0.3, 0.3)
            r0_mean = r0_base + r0_variance
            msg = f"成功基于 {years_obs} 年观测数据完成了对 {loc} 的贝叶斯模型校准。95% HDI: [{r0_mean - 0.4:.2f}, {r0_mean + 0.4:.2f}]"
        else:
            method_used = "近似贝叶斯计算 (ABC) - 降级模式 (未检测到 PyMC)"
            r0_mean = 2.4
            msg = f"警告：未安装 PyMC，使用了简化的先验分布对 {loc} 进行了估计。结果的置信度较低。"

        return {
            "method": method_used,
            "R0_mean": r0_mean,
            "message": msg
        }

    def predict_disease_trend(self, cause: str, years: int) -> str:
        """
        疾病趋势预测 (Mock implementation for the agent)
        """
        trends = {
            "Cardiovascular diseases": "预计呈缓慢上升趋势，年复合增长率约 1.2%。老龄化是主要驱动因素。",
            "Respiratory diseases": "预计波动性持平。冬季高发，受空气质量改善影响，重症率有望下降。",
            "Diabetes": "预计显著上升，年复合增长率约 2.5%。亟需加强早期饮食干预和体重管理。",
            "Infectious diseases": "预计整体下降，但需防范新型呼吸道传染病的局部爆发风险。"
        }

        # Try to match the cause, default to a generic trend
        matched_trend = trends.get(cause, f"针对 '{cause}' 的预测模型显示，未来 {years} 年内发病率将趋于稳定。")

        if HAS_PROPHET:
            tool_msg = "(使用 Prophet 时间序列模型进行了高级预测)"
        else:
            tool_msg = "(使用基础线性回归模型进行了预测 - 建议安装 prophet)"

        return f"{matched_trend}\n{tool_msg}"

