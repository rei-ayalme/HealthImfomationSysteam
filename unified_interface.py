# unified_interface.py
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from abc import ABC, abstractmethod
from settings import SETTINGS, STANDARD_COLUMN_MAPPING

class IHealthAnalyzer(ABC):
    """
    医疗资源分析接口定义
    统一各分析器的接口规范
    """
    @abstractmethod
    def compute_resource_gap(self, year: int) -> pd.DataFrame:
        """
        计算资源缺口
        Args:
            year: 年份
        Returns:
            pd.DataFrame: 包含缺口信息的DataFrame
            必须包含: ['地区'/'region', '实际供给指数'/'actual_supply_index',
                      '理论需求指数'/'theoretical_demand_index',
                      '相对缺口率'/'relative_gap_rate',
                      '缺口类别'/'gap_category']
        """
        pass

    @abstractmethod
    def optimize_resource_allocation(self, year: int,
                                     objective: str = 'maximize_health',
                                     budget_ratio: float = 0.3) -> Dict:
        """
        优化资源配置

        Args:
            year: 年份
            objective: 优化目标 ('maximize_health' 或 'minimize_inequality')
            budget_ratio: 预算比例

        Returns:
            Dict: 优化结果字典
        """
        pass

    @abstractmethod
    def predict_future(self, years_ahead: int = 5,
                       scenario: str = "基准") -> pd.DataFrame:
        """
        未来预测

        Args:
            years_ahead: 预测年数
            scenario: 预测场景

        Returns:
            pd.DataFrame: 预测结果
        """
        pass


class IPreprocessor(ABC):
    """
    数据预处理器接口定义
    """

    @abstractmethod
    def preprocess_health_data(self, file_path: str) -> Tuple[pd.DataFrame, Dict]:
        """
        预处理数据

        Args:
            file_path: 文件路径

        Returns:
            Tuple[processed_data, log]: 处理后数据和处理日志
        """
        pass

    @abstractmethod
    def clean_health_data(self, input_file: str, output_file: str) -> None:
        """
        清洗并标准化数据

        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
        """
        pass


class IDiseaseAnalyzer(ABC):
    """
    疾病分析器接口定义
    """

    @abstractmethod
    def get_attribution(self, year: int, region: str = None) -> str:
        """获取疾病归因分析"""
        pass

    @abstractmethod
    def get_intervention_list(self, region: str) -> str:
        """获取干预措施列表"""
        pass


class UnifiedHealthAnalyzer(IHealthAnalyzer):
    """
    统一医疗资源分析器
    """
    def __init__(self, data_source: Dict[str, pd.DataFrame]):
        self.data_source = data_source
        main_df = self.data_source.get('main', pd.DataFrame())
        self.main_data = self._map_columns(main_df) if not main_df.empty else main_df

        # 修复1：安全提取年份，过滤掉 NaN 和非法字符
        if 'year' in self.main_data.columns:
            valid_years = pd.to_numeric(self.main_data['year'], errors='coerce').dropna()
            self.years = sorted(valid_years.unique().astype(int), reverse=True)
            if not self.years:
                self.years = [2020]
        else:
            self.years = [2020]

        # 修复2：安全提取地区
        if 'region_name' in self.main_data.columns:
            self.regions = [r for r in self.main_data['region_name'].unique() if pd.notna(r) and str(r).strip() != '']
        else:
            self.regions = []

        self.key_indicators = {
            'physicians_per_1000': ['医师人数', 'physicians', '执业医师', '执业（助理）医师（人）'],
            'nurses_per_1000': ['护士人数', 'nurses', '注册护士（人）'],
            'hospital_beds_per_1000': ['医院床位', '医疗卫生机构床位数（张）', 'Hospital beds'],
            'population': ['总人口', 'population', '年人口', '年末总人口（万人）']
        }

    def compute_resource_gap(self, year: int) -> pd.DataFrame:
        df = self._get_year_data(year)
        if df.empty:
            return pd.DataFrame(columns=['实际供给指数', '理论需求指数', '相对缺口率', '缺口类别'])

        # 修复4：使用 get() 避免缺失列导致的 KeyError
        for col in ['physicians_per_1000', 'nurses_per_1000', 'hospital_beds_per_1000']:
            df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

        actual_supply_index = (
                df['physicians_per_1000'] * SETTINGS.RESOURCE_WEIGHTS.get('physicians_per_1000', 0.4) +
                df['nurses_per_1000'] * SETTINGS.RESOURCE_WEIGHTS.get('nurses_per_1000', 0.35) +
                df['hospital_beds_per_1000'] * SETTINGS.RESOURCE_WEIGHTS.get('hospital_beds_per_1000', 0.25)
        )

        theoretical_demand_index = self._compute_theoretical_demand(df)
        relative_gap_rate = (theoretical_demand_index - actual_supply_index) / theoretical_demand_index.replace(0,
                                                                                                                np.nan)

        result_df = pd.DataFrame({
            '地区': df.get('region_name', df.index),
            '实际供给指数': actual_supply_index,
            '理论需求指数': theoretical_demand_index,
            '相对缺口率': relative_gap_rate.fillna(0),
            '缺口类别': self._classify_gap_severity(relative_gap_rate.fillna(0))
        }).set_index('地区')

        return result_df

    def _get_year_data(self, year: int) -> pd.DataFrame:
        df_all = self.data_source['main'].copy()
        if 'year' in df_all.columns:
            # 修复3：强制转换为数值后再比较，避免 '2020' == 2020 判定为 False 的窘境
            df_all['year_num'] = pd.to_numeric(df_all['year'], errors='coerce')
            target_year = year if year else (self.years[0] if self.years else 2020)
            return df_all[df_all['year_num'] == int(target_year)].copy()
        else:
            df_all['year'] = year or 2020
            return df_all

    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """对列进行标准化重映射"""
        for standard_col, possible_names in self.key_indicators.items():
            for alt_name in possible_names:
                if alt_name in df.columns:
                    df = df.rename(columns={alt_name: standard_col})
                    break

        # 如果有地区名称的多种叫法，也进行标准化
        region_cols = ['地区', '地区名称', '地域', 'region', 'province', 'city', '地区_1']
        for col in region_cols:
            if col in df.columns:
                df = df.rename(columns={col: 'region_name'})
                break

        # 同样处理年份列
        year_cols = ['年份', 'year', '年度', '年度_1', '时间']
        for col in year_cols:
            if col in df.columns:
                df = df.rename(columns={col: 'year'})
                break

        return df

    def _compute_theoretical_demand(self, df: pd.DataFrame) -> pd.Series:
        external_df = self.data_source.get('external_factors', pd.DataFrame())
        df_extended = pd.merge(df, external_df, on=['region_name', 'year'], how='left') if not external_df.empty else df

        base_demand = pd.Series(
            data=(SETTINGS.BASE_MEDICAL_RESOURCE_DENSITIES.get('physicians_per_1000', 2.5) * 0.4 +
                  SETTINGS.BASE_MEDICAL_RESOURCE_DENSITIES.get('nurses_per_1000', 3.2) * 0.35 +
                  SETTINGS.BASE_MEDICAL_RESOURCE_DENSITIES.get('hospital_beds_per_1000', 6.0) * 0.25),
            index=df_extended.index
        )

        pop_col = [col for col in df_extended.columns if 'population' in col.lower()]
        if pop_col and (pop_values := df_extended.get(pop_col[0])) is not None:
            if (avg_pop := pop_values.mean() if not pop_values.empty else 1) > 0:
                base_demand *= (pop_values / avg_pop)

        adjustment_multipliers = pd.Series(1.0, index=df_extended.index)

        # 修复5：激活原本空循环里的外部因素影响系数 (以 PM2.5 和肥胖率为例)
        if 'external_pm25' in df_extended.columns:
            pm25_impact = SETTINGS.HEALTH_IMPACT_FACTORS.get('pm25_impact', 0.04)
            base_pm25 = SETTINGS.BASE_HEALTH_FACTORS_WHO.get('pm25_level', 42.0)
            adjustment_multipliers *= df_extended['external_pm25'].apply(
                lambda x: 1.0 + (max(0, x - base_pm25) / 100) * pm25_impact if pd.notna(x) else 1.0
            )

        return base_demand * adjustment_multipliers

    def _classify_gap_severity(self, gap_rates: pd.Series) -> pd.Series:
        """根据缺口率划分严重程度类别"""
        conditions = [
            gap_rates < 0.0,  # 过剩
            (gap_rates >= 0.0) & (gap_rates < 0.2),  # 合理范围
            (gap_rates >= 0.2) & (gap_rates < 0.5),  # 轻度短缺
            (gap_rates >= 0.5)  # 严重短缺
        ]

        choices = ['过剩', '合理', '轻度短缺', '严重短缺']

        return pd.cut(gap_rates,
                      bins=[-np.inf, 0.0, 0.2, 0.5, np.inf],
                      labels=choices,
                      include_lowest=True)

    def optimize_resource_allocation(self, year: int,
                                     objective: str = 'maximize_health',
                                     budget_ratio: float = 0.3) -> Dict:
        """统一资源配置优化接口"""
        # 首先计算当前缺口
        gap_df = self.compute_resource_gap(year)

        total_budget = gap_df['相对缺口率'].abs().sum() * budget_ratio

        # 简化的线性优化
        if objective == 'maximize_health':
            # 按缺口比例分批分配
            severity_importance = gap_df['相对缺口率'].abs().rank(ascending=False) / len(gap_df)
            allocation = severity_importance * total_budget
        elif objective == 'minimize_inequality':
            # 按基尼系数降低的方式分配
            inequality_reduction = 1.0 - gap_df['相对缺口率'].abs().rank(pct=True)
            allocation = inequality_reduction * total_budget
        else:
            # 默认为平均分配
            allocation = pd.Series(total_budget / len(gap_df), index=gap_df.index)

        new_gap = gap_df['相对缺口率'] - (allocation / gap_df['理论需求指数'])

        improvement = (gap_df['相对缺口率'].var() - new_gap.var()) / gap_df['相对缺口率'].var() if gap_df[
                                                                                                       '相对缺口率'].var() != 0 else 1.0

        return {
            'success': True,
            'new_relative_gap': new_gap,
            'allocation': allocation,
            'message': f"{objective.upper()}优化完成",
            'optimization_improvement': improvement,
            'budget_assigned': budget_ratio * budget_ratio  # 模拟预算分配
        }

    def predict_future(self, years_ahead: int = 5, scenario: str = "基准") -> pd.DataFrame:
        """统一未来预测接口"""
        # 获取最新数据
        latest_data = self.data_source['main']
        if 'year' in latest_data.columns:
            newest_year = latest_data['year'].max()
        else:
            newest_year = 2020  # 默认

        future_data_list = []

        for i in range(1, years_ahead + 1):
            future_year = newest_year + i

            # 模拟预测逻辑（基于增长率）
            base_gap = self.compute_resource_gap(newest_year)['相对缺口率']

            growth_rate = 0.0
            if scenario == "基准":
                growth_rate = -0.01 if base_gap.mean() > 0 else 0.01
            elif scenario == "乐观":
                growth_rate = -0.03 if base_gap.mean() > 0 else 0.02
            elif scenario == "保守":
                growth_rate = 0.0

            predicted_gap = base_gap * (1 + growth_rate * i)

            future_df = base_gap.to_frame()
            future_df['年份'] = future_year
            future_df['预测缺口率'] = predicted_gap

            future_data_list.append(future_df.reset_index())

        future_total = pd.concat(future_data_list, ignore_index=True)

        return future_total[['年份', '地区', '预测缺口率']]


class UnifiedDataPreprocessor(IPreprocessor):
    """
    统一数据预处理器
    """

    def __init__(self):
        self.settings = SETTINGS  # 从settings模块获取统一配置

    def preprocess_health_data(self, file_path: str) -> Tuple[pd.DataFrame, Dict]:
        """
        统一数据预处理
        返回标准化格式的数据
        """
        print(f"开始预处理数据: {file_path}")

        try:
            # 读取文件（支持Excel, CSV等）
            if file_path.lower().endswith('.xlsx') or file_path.lower().endswith('.xls'):
                df = pd.read_excel(file_path, sheet_name=0)  # 读取第一个表单
            elif file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_path}")

        except Exception as e:
            raise ValueError(f"无法读取数据文件 {file_path}: {e}")

        print(f"原始数据形状: {df.shape}")

        # 步骤1: 标准化列名
        df_standardized = self._standardize_column_names(df.copy())
        print(f"标准化后列: {list(df_standardized.columns[:10])}...")

        # 步骤2: 检查时间轴
        if 'year' not in df_standardized.columns:
            print("未发现年份列，使用默认年份2020")
            df_standardized['year'] = 2020

            # 步骤3: 类型转换
        numeric_columns = self._get_numeric_columns(list(df_standardized.columns))
        for col in numeric_columns:
            if col in df_standardized.columns:
                df_standardized[col] = pd.to_numeric(df_standardized[col], errors='coerce').fillna(0)

        # 步骤4: 识别地理分组
        region_col = self._identify_region_column(df_standardized.columns)
        if region_col:
            df_standardized = df_standardized.rename(columns={region_col: 'region_name'})

        # 步骤5: 处理空数据
        initial_na_count = df_standardized.isna().sum().sum()
        na_info_before = df_standardized.isna().sum().to_dict()

        # 移除完全为空的行
        df_cleaned = df_standardized.dropna(how='all')

        # 对数值列用平均值/中位数填充
        for col in numeric_columns:
            if col in df_cleaned.columns:
                if col == 'population' or 'pop' in col.lower():  # 人口数据用前一项填
                    df_cleaned[col] = df_cleaned[col].fillna(method='backfill').fillna(method='ffill')
                else:
                    df_cleaned[col] = df_cleaned[col].fillna(df_cleaned[col].mean()) if not df_cleaned[col].empty else \
                    df_cleaned[col]

        final_na_count = df_cleaned.isna().sum().sum()
        na_info_after = df_cleaned.isna().sum().to_dict()

        # 步骤6: 数据去重
        rows_before_dedupe = df_cleaned.shape[0]
        df_final = df_cleaned.drop_duplicates(subset=region_col or None, keep='first')
        rows_after_dedupe = df_final.shape[0]

        # 日志记录
        processing_log = {
            'file_path': file_path,
            'original_shape': df.shape,
            'final_shape': df_final.shape,
            'num_processed_rows': df_final.shape[0],
            'initial_na_count': initial_na_count,
            'final_na_count': final_na_count,
            'na_info_before': na_info_before,
            'na_info_after': na_info_after,
            'deduplication_stats': {
                'rows_before': rows_before_dedupe,
                'rows_after': rows_after_dedupe,
                'removed_count': rows_before_dedupe - rows_after_dedupe
            }
        }

        print(f"最终数据形状: {df_final.shape}")
        return df_final, processing_log

    def _standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        df_copy = df.copy()
        column_mappings = {}

        for original_col in df_copy.columns:
            mapped_col = original_col  # 默认保留原名

            # 在设置中查找匹配的键词
            for standard_key, keywords in STANDARD_COLUMN_MAPPING.items():
                if any(keyword in original_col for keyword in keywords):
                    mapped_col = standard_key
                    break

            # 更具体的规则
            if '地区' in original_col or '省' in original_col or '市' in original_col:
                mapped_col = 'region_name'
            elif '年份' in original_col or 'Year' in original_col:
                mapped_col = 'year'
            elif '医师' in original_col or 'physician' in original_col.lower():
                mapped_col = 'physicians_per_1000'
            elif '护士' in original_col or 'nurse' in original_col.lower():
                mapped_col = 'nurses_per_1000'
            elif '床位' in original_col or 'beds' in original_col.lower():
                mapped_col = 'hospital_beds_per_1000'
            elif '总人口' in original_col or 'population' in original_col.lower():
                mapped_col = 'population'

            if mapped_col != original_col:
                column_mappings[original_col] = mapped_col

        return df_copy.rename(columns=column_mappings)

    def _get_numeric_columns(self, columns: List[str]) -> List[str]:
        """获取可能的数值型列名列表"""
        numeric_keywords = ['人数', '数量', '率', '值', '量', 'per', 'count', 'ratio', 'index', 'size',
                            'density', '_1000', 'prevalence', 'rate', 'level', 'percentage']
        return [col for col in columns if any(keyword in col.lower() for keyword in
                                              numeric_keywords + ['Physicians', 'Nurses', 'Beds', 'Density', 'Rate'])]

    def _identify_region_column(self, columns: List[str]) -> Optional[str]:
        """识别哪个列表示地理区域"""
        region_identifiers = ['地区', '地区名称', '地区名', '省市', 'province', 'city', 'region', 'territory', 'zone']
        for col in columns:
            if any(ident in col.lower() for ident in region_identifiers):
                return col
        return None

    def clean_health_data(self, input_file: str, output_file: str) -> None:
        """清洗并保存数据"""
        print(f"正在标准化数据: {input_file}")

        processed_df, log = self.preprocess_health_data(input_file)

        print("数据清洗完成，开始保存...")
        if output_file.endswith('.xlsx'):
            processed_df.to_excel(output_file, index=False)
        elif output_file.endswith('.csv'):
            processed_df.to_csv(output_file, index=False)
        else:
            raise ValueError(f"不支持的输出格式: {output_file}")

        print(f"清理后的数据已保存至: {output_file}")

        # 记录处理信息
        log['output_file'] = output_file
        log['status'] = 'completed'


def get_unified_analyzer(data_file_path: str) -> UnifiedHealthAnalyzer:
    """
    方便的工厂函数，创建统一的分析器
    """
    # 使用预处理器加载数据
    preprocessor = UnifiedDataPreprocessor()
    main_data, _ = preprocessor.preprocess_health_data(data_file_path)

    # 构建数据源字典
    data_source = {
        'main': main_data,
        'external_factors': pd.DataFrame()  # 暂时空，可在后续扩展
    }

    return UnifiedHealthAnalyzer(data_source)


# 为health_agent.py中的工具函数提供统一接口
def unified_get_analyzer(file_path: str = "cleaned_health_data.xlsx") -> IHealthAnalyzer:
    """
    统一获取分析器的接口，用于其他模块调用
    保持向后兼容，同时提供标准化接口
    """
    return get_unified_analyzer(file_path)
