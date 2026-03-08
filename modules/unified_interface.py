# unified_interface.py
import pandas as pd
import numpy as np
from typing import Dict, Tuple
from abc import ABC, abstractmethod

try:
    # 适配新结构：从 config 包导入 settings
    from config.settings import SETTINGS
except ImportError:
    # 增加容错：如果路径不匹配，尝试从同级或父级查找，或使用占位符
    print("⚠️ 无法在 modules/unified_interface.py 中找到 config.settings")
    SETTINGS = None

class IHealthAnalyzer(ABC):
    """医疗资源分析接口定义"""
    @abstractmethod
    def compute_resource_gap(self, year: int) -> pd.DataFrame:
        pass

    @abstractmethod
    def optimize_resource_allocation(self, year: int,
                                     objective: str = 'maximize_health',
                                     budget_ratio: float = 0.3) -> Dict:
        pass

    @abstractmethod
    def predict_future(self, years_ahead: int = 5,
                       scenario: str = "基准") -> pd.DataFrame:
        pass


class IPreprocessor(ABC):
    """数据预处理器接口定义 """

    @abstractmethod
    def preprocess_health_data(self, file_path: str) -> Tuple[pd.DataFrame, Dict]:
        pass

    @abstractmethod
    def clean_health_data(self, input_file: str, output_file: str) -> None:
        pass



class UnifiedHealthAnalyzer(IHealthAnalyzer):
    """ 统一医疗资源分析器 """
    def __init__(self, data_source: Dict[str, pd.DataFrame]):
        self.data_source = data_source
        main_df = self.data_source.get('main', pd.DataFrame())
        self.main_data = self._map_columns(main_df) if not main_df.empty else main_df

        # 安全提取年份
        if 'year' in self.main_data.columns:
            valid_years = pd.to_numeric(self.main_data['year'], errors='coerce').dropna()
            self.years = sorted(valid_years.unique().astype(int), reverse=True)
            if not self.years: self.years = [2020]
        else:
            self.years = [2020]

        # 安全提取地区
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
        if df.empty or SETTINGS is None:
            return pd.DataFrame(columns=['实际供给指数', '理论需求指数', '相对缺口率', '缺口类别'])

        for col in ['physicians_per_1000', 'nurses_per_1000', 'hospital_beds_per_1000']:
            df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

        weights = SETTINGS.RESOURCE_WEIGHTS
        actual_supply_index = (
                df['physicians_per_1000'] * weights.get('physicians_per_1000', 0.4) +
                df['nurses_per_1000'] * weights.get('nurses_per_1000', 0.35) +
                df['hospital_beds_per_1000'] * weights.get('hospital_beds_per_1000', 0.25)
        )

        theoretical_demand_index = self._compute_theoretical_demand(df)
        relative_gap_rate = (theoretical_demand_index - actual_supply_index) / theoretical_demand_index.replace(0, np.nan)

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
            df_all['year_num'] = pd.to_numeric(df_all['year'], errors='coerce')
            target_year = year if year else (self.years[0] if self.years else 2020)
            return df_all[df_all['year_num'] == int(target_year)].copy()
        return df_all

    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """列名标准化"""
        for standard_col, possible_names in self.key_indicators.items():
            for alt_name in possible_names:
                if alt_name in df.columns:
                    df = df.rename(columns={alt_name: standard_col})
                    break

        region_cols = ['地区', '地区名称', 'region', 'province']
        for col in region_cols:
            if col in df.columns:
                df = df.rename(columns={col: 'region_name'})
                break

        if 'year' not in df.columns:
            for col in ['年份', '年度', '时间']:
                if col in df.columns:
                    df = df.rename(columns={col: 'year'})
                    break
        return df

    def _compute_theoretical_demand(self, df: pd.DataFrame) -> pd.Series:
        if SETTINGS is None:
            return pd.Series(1.0, index=df.index)

        # 基础需求计算
        base_densities = SETTINGS.BASE_MEDICAL_RESOURCE_DENSITIES
        base_demand_val = (base_densities.get('physicians_per_1000', 2.5) * 0.4 +
                           base_densities.get('nurses_per_1000', 3.2) * 0.35 +
                           base_densities.get('hospital_beds_per_1000', 6.0) * 0.25)

        base_demand = pd.Series(base_demand_val, index=df.index)

        # 人口调节
        pop_col = [col for col in df.columns if 'population' in col.lower()]
        if pop_col:
            pop_values = pd.to_numeric(df[pop_col[0]], errors='coerce').fillna(1)
            avg_pop = pop_values.mean() if not pop_values.empty else 1
            base_demand *= (pop_values / avg_pop)

        return base_demand

    def _classify_gap_severity(self, gap_rates: pd.Series) -> pd.Series:
        choices = ['过剩', '合理', '轻度短缺', '严重短缺']
        return pd.cut(gap_rates, bins=[-np.inf, 0.0, 0.2, 0.5, np.inf], labels=choices, include_lowest=True)

    def optimize_resource_allocation(self, year: int, objective: str = 'maximize_health', budget_ratio: float = 0.3) -> Dict:
        # 模拟优化逻辑
        gap_df = self.compute_resource_gap(year)
        improvement = 0.15 # 模拟改善率
        return {
            'success': True,
            'new_relative_gap': gap_df['相对缺口率'] * 0.8,
            'allocation': gap_df['理论需求指数'] * budget_ratio,
            'message': f"基于{objective}的目标优化完成",
            'optimization_improvement': improvement
        }

    def predict_future(self, years_ahead: int = 5, scenario: str = "基准") -> pd.DataFrame:
        # 模拟预测逻辑
        latest_year = self.years[0] if self.years else 2020
        results = []
        for i in range(1, years_ahead + 1):
            year = latest_year + i
            for reg in self.regions:
                results.append({'年份': year, '地区': reg, '预测缺口率': np.random.uniform(0, 0.3)})
        return pd.DataFrame(results)


class UnifiedDataPreprocessor(IPreprocessor):
    """统一数据预处理器"""

    def preprocess_health_data(self, file_path: str) -> Tuple[pd.DataFrame, Dict]:
        try:
            if file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                df = pd.read_csv(file_path)
            return df.drop_duplicates(), {'status': 'success', 'rows': len(df)}
        except Exception as e:
            return pd.DataFrame(), {'status': 'error', 'message': str(e)}

    def clean_health_data(self, input_file: str, output_file: str) -> None:
        df, _ = self.preprocess_health_data(input_file)
        if not df.empty:
            df.to_excel(output_file, index=False)


def get_unified_analyzer(data_file_path: str) -> UnifiedHealthAnalyzer:
    """工厂函数"""
    preprocessor = UnifiedDataPreprocessor()
    main_data, _ = preprocessor.preprocess_health_data(data_file_path)
    return UnifiedHealthAnalyzer({'main': main_data})

