import pandas as pd
import numpy as np
import json
import os
import re
import logging
from typing import Optional, Dict, Any
from config.settings import SETTINGS


class DataProcessor:
    """
    数据提炼厂 —— 纯计算
    唯一职责：接收 loader 传来的原生态 DataFrame，通过一系列标准化流水线，
    吐出符合业务系统 Schema 校验的、能够直接进入数据库或算法引擎的"干净数据"
    """

    def __init__(self, geo_registry: Optional[dict] = None):
        """
        初始化数据处理器
        Args:
            geo_registry: 地理注册表，包含地区名称到经纬度的映射
        """
        self.geo_registry = geo_registry
        self.logger = logging.getLogger("health_system.processor")

        # 1. 动态加载列名映射字典（用于统一方言）
        mapping_file = os.path.join(SETTINGS.BASE_DIR, "config", "column_mapping.json")
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                self.col_map = json.load(f)
        except Exception as e:
            # 增强错误处理和日志记录
            self.logger.warning(f"未能加载 mapping 文件: {e}，将启用硬编码回退配置。")

            # 确保回退机制正确初始化，防止部分映射失败
            self.col_map = SETTINGS.STANDARD_COLUMN_MAPPING.copy()
            self.col_map.setdefault("physicians", ["执业医师", "执业(助理)医师", "医师", "physicians", "doctor", "生人数", "人员数"])
            self.col_map.setdefault("nurses", ["注册护士", "护士", "nurses", "nurse"])
            self.col_map.setdefault("hospital_beds", ["床位数", "医疗卫生机构床位数", "医院床位数", "beds", "hospital_beds"])
            self.col_map.setdefault("population", ["人口数", "年末人口数", "总人口", "population", "pop", "人口(万人)"])
            self.col_map.setdefault("region_name", ["地区", "省份", "省市", "region", "location", "area"])

        # 2. 新增：加载数据字典 Schema（用于强校验与类型转换）
        schema_file = os.path.join(SETTINGS.BASE_DIR, "config", "schema_dictionary.json")
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                self.schema_dict = json.load(f)
                self.logger.info(f"成功加载数据字典: {schema_file}")
        except Exception as e:
            self.logger.warning(f"无法加载数据字典，将跳过强校验: {e}")
            self.schema_dict = {}

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        接管列名映射（column_mapping.json）
        智能识别，并防止细分列(如城市/农村)覆盖总计列
        """
        identified = {}
        found_keys = set()
        for col in df.columns:
            col_str = str(col)
            for std_key, keywords in self.col_map.items():
                if std_key in found_keys:
                    continue  # 保证只抓取最前面的总计列，跳过后续同名或包含该字眼的细分列
                if any(kw in col_str for kw in keywords):
                    identified[col] = std_key
                    found_keys.add(std_key)
                    break
        return df.rename(columns=identified)

    def _validate_by_dictionary(self, df: pd.DataFrame, dataset_type: str) -> pd.DataFrame:
        """
        核心验证引擎：根据数据字典进行强校验与类型转换

        基于 schema_dictionary.json 中定义的 data_sources 规范，对数据进行：
        1. 必填列检查 - 确保核心字段存在
        2. 强制类型转换 - 剔除文本混杂，统一数据类型
        3. 极值过滤 - 剔除超出合理范围的异常值

        Args:
            df: 待验证的原始数据框
            dataset_type: 数据集类型，对应 schema_dictionary.json 中的 data_sources 键名
                         如 "yearbook_resource", "gbd_disease", "spatial_od_matrix"

        Returns:
            经过校验和清洗的数据框

        Raises:
            ValueError: 当缺失必填列时抛出

        Example:
            >>> processor = DataProcessor()
            >>> df_clean = processor._validate_by_dictionary(df_raw, "yearbook_resource")
        """
        # 如果数据字典未加载或没有该类型的定义，直接放行
        if not self.schema_dict or "data_sources" not in self.schema_dict:
            self.logger.debug(f"数据字典未加载，跳过 {dataset_type} 的校验")
            return df

        data_sources = self.schema_dict.get("data_sources", {})
        if dataset_type not in data_sources:
            self.logger.debug(f"数据字典中未定义 {dataset_type}，跳过校验")
            return df

        schema = data_sources[dataset_type]
        df_clean = df.copy()

        self.logger.info(f"开始对 {dataset_type} 进行数据字典校验...")

        # 1. 必填列检查
        required = schema.get("required_columns", [])
        missing = [col for col in required if col not in df_clean.columns]
        if missing:
            error_msg = f"[{dataset_type}] 数据校验失败，缺失核心列: {missing}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # 记录成功检查的列
        self.logger.debug(f"{dataset_type} 必填列检查通过: {required}")

        # 2. 强制类型转换 (剔除文本混杂)
        data_types = schema.get("data_types", {})
        for col, dtype in data_types.items():
            if col in df_clean.columns:
                try:
                    if dtype == "float":
                        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
                        self.logger.debug(f"列 '{col}' 转换为 float 类型")
                    elif dtype == "int":
                        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0).astype(int)
                        self.logger.debug(f"列 '{col}' 转换为 int 类型")
                    elif dtype == "string":
                        df_clean[col] = df_clean[col].astype(str)
                        self.logger.debug(f"列 '{col}' 转换为 string 类型")
                except Exception as e:
                    self.logger.warning(f"列 '{col}' 类型转换失败: {e}")

        # 3. 极值过滤 (剔除超出合理范围的数据)
        ranges = schema.get("value_ranges", {})
        for col, bounds in ranges.items():
            if col in df_clean.columns:
                min_val = bounds.get("min", -np.inf)
                max_val = bounds.get("max", np.inf)

                # 统计异常值数量
                out_of_range = df_clean[
                    (df_clean[col] < min_val) | (df_clean[col] > max_val)
                ].shape[0]

                if out_of_range > 0:
                    self.logger.warning(
                        f"列 '{col}' 发现 {out_of_range} 个超出范围值 "
                        f"[{min_val}, {max_val}]，将设为 NaN"
                    )

                # 将超出范围的值设为 NaN，后续由缺失值处理逻辑统一填补
                df_clean[col] = df_clean[col].apply(
                    lambda x: x if pd.isna(x) or (min_val <= x <= max_val) else np.nan
                )

        self.logger.info(f"{dataset_type} 数据字典校验完成")
        return df_clean

    def _handle_missing_and_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        接管原 cleaner.py 里的缺失值插值和 IQR 异常点清洗
        """
        df_clean = df.copy()

        # 1. 处理缺失值
        # 区分"真零"与"漏报"：对于人口、医生、床位等绝不可能为0的核心指标，将0视为缺失值
        core_non_zero_cols = ['population', 'physicians', 'nurses', 'hospital_beds']
        for col in core_non_zero_cols:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].replace(0, np.nan)

        df_clean = df_clean.replace(['N/A', 'nan', ''], np.nan)

        # 仅对数值列进行插值，避免字符串列的问题
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            # 对数值列进行插值
            df_clean[numeric_cols] = df_clean[numeric_cols].interpolate(method='linear', limit_direction='both')
            df_clean[numeric_cols] = df_clean[numeric_cols].ffill().bfill()

        # 2. 异常值处理
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
        for col in numeric_cols:
            if col not in df_clean.columns:
                continue

            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
            series = df_clean[col].dropna()
            if len(series) < 5:
                continue

            # IQR 方法处理异常值
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            # 将异常值替换为边界值（Winsorization）
            df_clean[col] = np.clip(series, lower_bound, upper_bound)

        return df_clean

    def process_yearbook_resource(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """
        接管原 cleaner.py，负责卫生年鉴、床位、医生数（将绝对值转化为千人率）

        处理流程：
        1. 统一列名（方言映射）
        2. 【新增】数据字典强校验
        3. 异常值处理与空值填充
        4. 核心指标转化（绝对值 -> 千人率）
        5. 地区标准化

        Args:
            raw_df: 原始卫生年鉴数据

        Returns:
            清洗后的数据框
        """
        df = raw_df.copy()

        # 1. 统一列名（方言映射）
        df = self._standardize_columns(df)

        # 2. 【新增】数据字典守门员拦截！
        df = self._validate_by_dictionary(df, "yearbook_resource")

        # 3. 异常值处理与空值填充
        df = self._handle_missing_and_outliers(df)

        # 3. 核心指标转化 (绝对值 -> 千人率)
        if 'population' in df.columns:
            # 确保人口数据有效
            df['population'] = pd.to_numeric(df['population'], errors='coerce')
            df['population'] = df['population'].replace(0, np.nan)

            if 'hospital_beds' in df.columns:
                df['hospital_beds_per_1000'] = (df['hospital_beds'] / df['population'].replace(0, 1)) * 1000
                df['hospital_beds_per_1000'] = df['hospital_beds_per_1000'].round(2)

            if 'physicians' in df.columns:
                df['physicians_per_1000'] = (df['physicians'] / df['population'].replace(0, 1)) * 1000
                df['physicians_per_1000'] = df['physicians_per_1000'].round(2)

            if 'hospital_beds_per_1000' in df.columns and 'physicians_per_1000' in df.columns:
                # 计算其他衍生指标
                df['beds_per_physician'] = df['hospital_beds_per_1000'] / df['physicians_per_1000'].replace(0, np.nan)
                df['beds_per_physician'] = df['beds_per_physician'].fillna(np.nan)

        # 4. 地区标准化
        if 'region_name' in df.columns:
            df['province_code'] = df['region_name'].apply(lambda x: f"{x}".zfill(2) if pd.notna(x) else np.nan)

        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理缺失值和异常值

        策略：
        - 数值型列：中位数填充
        - 分母列：1 填充（避免除以 0）
        - 标识列：保持原样
        """
        if df.empty:
            return df

        # 数值型列用中位数填充
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isna().any():
                median_val = df[col].median()
                if pd.isna(median_val):
                    df[col] = 0
                else:
                    df[col] = df[col].fillna(median_val)

        # 分母列特殊处理（避免除以 0）
        if 'population' in df.columns:
            df['population'] = df['population'].fillna(1)

        return df

    def process_gbd_disease(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """
        接管原 gbd_preprocessor.py，负责疾病风险、PAF 等指标清洗

        处理流程：
        1. 统一列名（方言映射，如果GBD数据有异构列名）
        2. 【新增】按照 GBD 的标准来安检！
        3. 数据类型转换与基础清洗
        4. 疾病谱系转型特征 (ETI)
        5. 风险因素归因与云模型

        Args:
            raw_df: 原始 GBD 数据

        Returns:
            清洗后的数据框
        """
        df = raw_df.copy()

        # 1. 统一列名（方言映射，如果GBD数据有异构列名）
        df = self._standardize_columns(df)

        # 2. 【新增】按照 GBD 的标准来安检！
        df = self._validate_by_dictionary(df, "gbd_disease")

        # 3. 数据类型转换与基础清洗
        df = self._clean_gbd_data_types(df)

        # 4. 疾病谱系转型特征 (ETI)
        df = self._engineer_disease_transition(df)

        # 5. 风险因素归因与云模型
        df = self._engineer_risk_attribution(df)

        return df

    def _clean_gbd_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据类型转换与基础清洗"""
        df_clean = df.copy()
        numeric_cols = ['val', 'year', 'sdi', 'paf', 'physicians_per_1000', 'hale']

        for col in numeric_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

        if 'year' in df_clean.columns:
            df_clean = df_clean[
                (df_clean['year'] >= 1990) &
                (df_clean['year'] <= 2025)
            ]

        # 修复 KeyError: 动态检查列是否存在，只对存在的列执行去空操作
        subset_cols = [c for c in ['year', 'val'] if c in df_clean.columns]
        if subset_cols:
            if 'val' in df_clean.columns:
                df_clean = df_clean.dropna(subset=['val'], how='any')
            else:
                df_clean = df_clean.dropna(subset=subset_cols, how='all')

        return df_clean.copy()

    def _engineer_disease_transition(self, df: pd.DataFrame) -> pd.DataFrame:
        """疾病谱系转型特征 (ETI)"""
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

    def _engineer_risk_attribution(self, df: pd.DataFrame) -> pd.DataFrame:
        """风险因素归因与云模型"""
        df_feat = df.copy()

        # 1. 风险因素分类映射
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

        return df_feat

    # ================= 第 3 阶段：空间富集 =================
    def enrich_spatial_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        为 E2SFCA 等算法做准备，添加空间特征

        处理流程：
        1. 地区名称到经纬度映射
        2. 计算医疗资源密度
        3. 生成空间权重矩阵（可选）

        Args:
            df: 包含地区名称的数据框

        Returns:
            添加空间特征的数据框
        """
        if df.empty:
            return df

        # 1. 地区名称到经纬度映射
        if self.geo_registry and 'region_name' in df.columns:
            # 简化版：使用固定经纬度（实际应从外部获取）
            region_to_coords = {
                '北京': (39.9042, 116.4074),
                '上海': (31.2304, 121.4737),
                '广州': (23.1291, 113.2644),
                '深圳': (22.5431, 114.0579),
                # ... 其他省市
            }

            # 尝试添加经纬度
            for region, coords in region_to_coords.items():
                if region in df['region_name'].values:
                    idx = df[df['region_name'] == region].index
                    df.loc[idx, 'latitude'] = coords[0]
                    df.loc[idx, 'longitude'] = coords[1]

        # 2. 计算医疗资源密度
        if 'hospital_beds_per_1000' in df.columns:
            df['medical_density'] = df['hospital_beds_per_1000'] / df['population'].replace(0, np.nan)

        return df

    # ================= 分析功能方法 (整合自 analysis/processor.py) =================

    def compute_resource_gap(self, data: pd.DataFrame, year: int,
                            weights: Dict[str, float], baselines: Dict[str, float],
                            threshold_adequate: float = 0.05, threshold_reasonable: float = 0.15,
                            threshold_mild: float = 0.30) -> pd.DataFrame:
        """
        计算指定年份的资源缺口
        整合自 analysis/processor.py 的 compute_resource_gap_pure 功能
        """
        df = data[data["year"] == year].copy() if "year" in data.columns else pd.DataFrame()
        if df.empty:
            return pd.DataFrame()

        df["actual_supply_index"] = (
            df["physicians_per_1000"] * weights["physicians_per_1000"]
            + df["nurses_per_1000"] * weights["nurses_per_1000"]
            + df["hospital_beds_per_1000"] * weights["hospital_beds_per_1000"]
        )

        base_demand = (
            baselines["physicians_per_1000"] * weights["physicians_per_1000"]
            + baselines["nurses_per_1000"] * weights["nurses_per_1000"]
            + baselines["hospital_beds_per_1000"] * weights["hospital_beds_per_1000"]
        )
        avg_pop = df["population"].mean() if df["population"].mean() > 0 else 1
        df["theoretical_demand_index"] = base_demand * (df["population"] / avg_pop)

        df["relative_gap_rate"] = (
            (df["theoretical_demand_index"] - df["actual_supply_index"]) / df["theoretical_demand_index"]
        ).fillna(0)

        df["gap_severity"] = pd.cut(
            df["relative_gap_rate"],
            bins=[-np.inf, threshold_adequate, threshold_reasonable, threshold_mild, np.inf],
            labels=["配置充足", "配置合理", "轻度短缺", "严重短缺"]
        )

        return df

    def analyze_trend(self, data: pd.DataFrame, metric: str = "physicians_per_1000") -> Dict[str, Any]:
        """
        分析指标趋势
        整合自 analysis/processor.py 的 analyze_trend_pure 功能
        """
        if data.empty or metric not in data.columns:
            return {"trend": "unknown", "growth_rate": 0.0}

        data_sorted = data.sort_values("year")
        values = data_sorted[metric].values
        years = data_sorted["year"].values

        if len(values) < 2:
            return {"trend": "stable", "growth_rate": 0.0}

        # 计算年均增长率
        growth_rate = (values[-1] / values[0]) ** (1 / (years[-1] - years[0])) - 1

        # 判断趋势
        if growth_rate > 0.05:
            trend = "rapid_growth"
        elif growth_rate > 0.02:
            trend = "steady_growth"
        elif growth_rate > -0.02:
            trend = "stable"
        elif growth_rate > -0.05:
            trend = "slight_decline"
        else:
            trend = "significant_decline"

        return {
            "trend": trend,
            "growth_rate": round(growth_rate * 100, 2),
            "start_value": values[0],
            "end_value": values[-1],
            "period": f"{years[0]}-{years[-1]}"
        }

    def compute_health_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算综合健康指标
        整合自 analysis/processor.py 的 compute_health_indicators_pure 功能

        Args:
            df: 包含基础健康数据的数据框

        Returns:
            包含健康指标的数据框
        """
        if df.empty:
            return df

        # 基础指标
        if 'physicians_per_1000' in df.columns and 'daly' in df.columns:
            # 计算每千人 DALYs 数（疾病负担与医疗资源比值）
            df['daly_per_physician'] = (df['daly'] / df['population'].replace(0, 1)) / df['physicians_per_1000'].replace(0, np.nan)

        # 资源适配指数（0-1，越高表示资源越充足）
        if 'physicians_per_1000' in df.columns:
            # 假设全国平均为基准
            avg_physicians = df['physicians_per_1000'].median()
            if avg_physicians > 0:
                df['resource_fit_index'] = df['physicians_per_1000'] / avg_physicians
                df['resource_fit_index'] = df['resource_fit_index'].clip(lower=0.5, upper=2.0)  # 限制范围

        return df


class YearbookProcessor:
    """
    中国卫生统计年鉴专属清洗引擎

    支持多级表头展平、正则模糊映射与自动量纲统一。
    专门处理中国卫生健康统计年鉴的Excel文件，能够智能识别各种格式的表头，
    自动展平多级表头，统一量纲（万人→人），并计算千人指标。

    Attributes:
        regex_mapping: 正则表达式映射规则，用于智能匹配列名
        logger: 日志记录器

    Example:
        >>> processor = YearbookProcessor()
        >>> df_clean = processor.process_raw_dataframe(df_raw, year=2020)
        >>> print(df_clean.columns)
        Index(['region_name', 'year', 'population', 'hospital_beds', 'physicians',
               'nurses', 'beds_per_1000', 'physicians_per_1000', 'nurses_per_1000'], dtype='object')
    """

    def __init__(self):
        self.logger = logging.getLogger("health_system.yearbook_processor")

        # 动态加载正则表达式映射配置
        self.regex_mapping = {}
        mapping_file = os.path.join(SETTINGS.BASE_DIR, "config", "column_mapping.json")

        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                col_map_config = json.load(f)

            for field_name, field_config in col_map_config.items():
                # 跳过元数据字段
                if field_name == "_meta":
                    continue

                aliases = field_config.get("aliases", [])
                if not aliases:
                    continue

                # 按长度降序排序别名，确保更具体的匹配优先
                sorted_aliases = sorted(aliases, key=len, reverse=True)

                # 转义特殊正则字符
                escaped_aliases = [re.escape(alias) for alias in sorted_aliases]

                # 构建正则表达式模式
                pattern = "(" + "|".join(escaped_aliases) + ")"

                # 特殊处理 population 字段：生成 population_10k 和 population_1 两个条目
                if field_name == "population":
                    self.regex_mapping["population_10k"] = pattern + r".*万"
                    self.regex_mapping["population_1"] = pattern + r"(?!.*万)"
                else:
                    self.regex_mapping[field_name] = pattern

            self.logger.info(f"成功加载列名映射配置: {mapping_file}")

        except FileNotFoundError as e:
            self.logger.error(f"列名映射配置文件未找到: {mapping_file} - {e}")
            # 使用硬编码回退配置
            self._load_fallback_mapping()
        except json.JSONDecodeError as e:
            self.logger.error(f"列名映射配置文件 JSON 格式无效: {mapping_file} - {e}")
            self._load_fallback_mapping()
        except Exception as e:
            self.logger.error(f"加载列名映射配置时发生错误: {e}")
            self._load_fallback_mapping()

    def _load_fallback_mapping(self):
        """
        加载硬编码回退配置，当 JSON 配置加载失败时使用
        """
        self.logger.warning("启用硬编码回退配置")
        self.regex_mapping = {
            "region_name": r"(地区|省份|地市|省市)",
            "population_10k": r"(常住人口|年末人口).*万",
            "population_1": r"(常住人口|年末人口)(?!.*万)",
            "hospital_beds": r"(医疗机构床位|机构床位|医疗卫生机构床位|床位数)",
            "physicians": r"(执业.*医师|执业.*助理.*医师|医生数)",
            "nurses": r"(注册护士|护士数)"
        }

    def _flatten_and_clean_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        核心优化 2：多级表头"降维打击"与深度清洗

        处理多级表头（MultiIndex），将其展平为单层字符串列名，
        同时清洗掉空格、制表符、换行符，统一括号格式。

        Args:
            df: 原始DataFrame，可能包含多级表头

        Returns:
            表头展平并清洗后的DataFrame

        Example:
            >>> df = pd.DataFrame(columns=[('卫生人员', '执业(助理)医师'), ('人口', '年末常住人口')])
            >>> df = processor._flatten_and_clean_columns(df)
            >>> print(df.columns)
            Index(['卫生人员_执业(助理)医师', '人口_年末常住人口'], dtype='object')
        """
        new_cols = []
        for col in df.columns:
            # 1. 降维：如果是多级表头 (MultiIndex)，将其拼接为单层字符串
            if isinstance(col, tuple):
                # 过滤掉 Pandas 自动生成的 'Unnamed: X_level_Y'
                valid_parts = [str(c) for c in col if not str(c).startswith("Unnamed")]
                col_name = "_".join(valid_parts)
            else:
                col_name = str(col)

            # 2. 清洗：干掉所有空格、制表符、换行符
            col_name = re.sub(r'\s+', '', col_name)
            # 将中文括号统一转为英文括号，方便阅读和正则匹配
            col_name = col_name.replace('（', '(').replace('）', ')')
            new_cols.append(col_name)

        df.columns = new_cols
        return df

    def _apply_regex_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        核心优化 3：基于正则表达式的智能列名重命名

        使用预定义的正则表达式规则，智能识别并标准化列名。
        一个原始列名只会被第一个匹配的规则命中。

        Args:
            df: 表头已清洗的DataFrame

        Returns:
            列名已标准化的DataFrame

        Example:
            >>> df.columns = ['地区', '执业（助理）医师（人）', '年末常住人口(万人)']
            >>> df = processor._apply_regex_mapping(df)
            >>> print(df.columns)
            Index(['region_name', 'physicians', 'population_10k'], dtype='object')
        """
        rename_dict = {}
        for original_col in df.columns:
            for std_name, pattern in self.regex_mapping.items():
                if re.search(pattern, original_col):
                    rename_dict[original_col] = std_name
                    self.logger.debug(f"匹配成功: '{original_col}' -> '{std_name}'")
                    break  # 一个列被命中后，跳过后续规则

        return df.rename(columns=rename_dict)

    def process_raw_dataframe(self, raw_df: pd.DataFrame, year: int = 2011) -> pd.DataFrame:
        """
        执行完整的清洗流水线

        输入单张 Sheet 的 DataFrame，输出标准宽表。
        处理流程包括：
        1. 展平与清洗表头
        2. 正则映射标准列名
        3. 提取基础列（地区、年份）
        4. 智能提取人口并统一量纲到"人"
        5. 提取医疗资源绝对值
        6. 计算千人指标
        7. 清理并圆整数据

        Args:
            raw_df: 原始DataFrame，来自Excel单张Sheet
            year: 数据年份，用于标记

        Returns:
            清洗后的标准宽表DataFrame，包含以下列：
            - region_name: 地区名称
            - year: 年份
            - population: 人口（人）
            - hospital_beds: 床位数
            - physicians: 医师数
            - nurses: 护士数
            - beds_per_1000: 每千人床位数
            - physicians_per_1000: 每千人医师数
            - nurses_per_1000: 每千人护士数

        Raises:
            ValueError: 当无法识别地区列时抛出

        Example:
            >>> processor = YearbookProcessor()
            >>> df_raw = pd.read_excel('2020年鉴.xlsx', sheet_name='卫生资源')
            >>> df_clean = processor.process_raw_dataframe(df_raw, year=2020)
            >>> print(df_clean.head())
               region_name  year  population  hospital_beds  physicians  nurses  \
            0       北京市  2020  21893000.0       125000.0    125000.0  95000.0
            ...
        """
        # 1. 展平与清洗表头
        df = self._flatten_and_clean_columns(raw_df.copy())

        # 2. 正则映射标准列名
        df = self._apply_regex_mapping(df)

        # 3. 提取必须的基础列
        result = pd.DataFrame()

        if "region_name" not in df.columns:
            raise ValueError("无法在数据中识别出'地区'列，请检查源数据。")

        result["region_name"] = df["region_name"]
        result["year"] = year

        # 4. 智能提取人口并统一下降到"人"的绝对量纲
        if "population_10k" in df.columns:
            result["population"] = pd.to_numeric(df["population_10k"], errors='coerce') * 10000
        elif "population_1" in df.columns:
            result["population"] = pd.to_numeric(df["population_1"], errors='coerce')

        # 5. 提取医疗资源绝对值 (如果找不到该列，填充 NaN)
        for metric in ["hospital_beds", "physicians", "nurses"]:
            if metric in df.columns:
                result[metric] = pd.to_numeric(df[metric], errors='coerce')
            else:
                result[metric] = np.nan
                self.logger.warning(f"未找到列 '{metric}'，将填充 NaN")

        # 6. 计算最终的"千人指标" (安全除法，防 Infinity)
        if "population" in result.columns:
            # 把人口为 0 的替换为 NaN，防止抛出除以 0 错误
            safe_pop = np.where(result["population"] == 0, np.nan, result["population"])

            if "hospital_beds" in result.columns:
                result["beds_per_1000"] = (result["hospital_beds"] / safe_pop) * 1000
            if "physicians" in result.columns:
                result["physicians_per_1000"] = (result["physicians"] / safe_pop) * 1000
            if "nurses" in result.columns:
                result["nurses_per_1000"] = (result["nurses"] / safe_pop) * 1000

        # 7. 清理并圆整数据
        # 删除没有地区名字的脏行（通常是 Excel 底部的"注：数据来源于..."说明文字）
        result = result.dropna(subset=["region_name"])
        # 将 NaN 填充为 0，并将千人指标保留 2 位小数
        return result.fillna(0).round(2)
