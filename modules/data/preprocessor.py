import pandas as pd
import numpy as np
import os
import logging
from typing import Tuple, Dict
from modules.core.interface import IPreprocessor
from modules.data.cleaner import HealthDataCleaner


class HealthDataPreprocessor(IPreprocessor):
    """
    统一健康数据预处理器
    实现从原始 Excel 到标准数据库格式的转化
    """

    def __init__(self):
        self.cleaner = HealthDataCleaner()
        self.logger = logging.getLogger("health_system.preprocessor")

        # 针对《中国卫生健康统计年鉴》定制的精准映射 (使用提取到的精确名称)
        self.col_map = {
            'physicians': ['执业（助理）医师（人）', '执业医师（人）', '医师数'],
            'nurses': ['注册护士（人）', '护士数'],
            'hospital_beds': ['医疗卫生机构床位数（张）', '床位数'],
            'population': ['总人口（万人）', '年末总人口'],
            'region_name': ['地区', '省份'],
            'year': ['年份', 'year']
        }

    def _identify_columns(self, df_columns: list) -> Dict[str, str]:
        """智能识别，并防止细分列(如城市/农村)覆盖总计列"""
        identified = {}
        found_keys = set()
        for col in df_columns:
            col_str = str(col)
            for std_key, keywords in self.col_map.items():
                if std_key in found_keys:
                    continue  # 保证只抓取最前面的总计列，跳过后续同名或包含该字眼的细分列
                if any(kw in col_str for kw in keywords):
                    identified[col] = std_key
                    found_keys.add(std_key)
                    break
        return identified

    def preprocess_health_data(self, file_path: str) -> Tuple[pd.DataFrame, Dict]:
        """执行完整预处理流程"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"未找到原始文件: {file_path}")

            # 1. 读取数据
            df = pd.read_excel(file_path)
            original_shape = df.shape

            # 2. 列名标准化
            mapping = self._identify_columns(df.columns)
            df = self.cleaner.standardize_indicators(df, mapping)

            # 3. 缺失值与基础清洗
            df = self.cleaner.handle_missing_values(df)

            # 4. 核心计算：绝对值 -> 千人比率 (解决严重逻辑错误)
            if 'population' in df.columns:
                df['population'] = pd.to_numeric(df['population'], errors='coerce').fillna(0)

                # 年鉴的人口单位是“万人”，1万人 = 10个千人
                if 'physicians' in df.columns:
                    df['physicians'] = pd.to_numeric(df['physicians'], errors='coerce').fillna(0)
                    df['physicians_per_1000'] = df['physicians'] / (df['population'] * 10)

                if 'nurses' in df.columns:
                    df['nurses'] = pd.to_numeric(df['nurses'], errors='coerce').fillna(0)
                    df['nurses_per_1000'] = df['nurses'] / (df['population'] * 10)

                if 'hospital_beds' in df.columns:
                    df['hospital_beds'] = pd.to_numeric(df['hospital_beds'], errors='coerce').fillna(0)
                    df['hospital_beds_per_1000'] = df['hospital_beds'] / (df['population'] * 10)

            # 5. 确保核心列存在且格式正确
            numeric_cols = ['physicians_per_1000', 'nurses_per_1000',
                            'hospital_beds_per_1000', 'population', 'year']
            for col in numeric_cols:
                if col not in df.columns:
                    print(f"⚠️ 警告: 原数据缺少核心列映射 [{col}]，已自动填充为0。")
                    df[col] = 0.0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            # 6. 去重并剔除分母为0导致的无限大异常值
            df = df.replace([np.inf, -np.inf], 0)
            df = df.drop_duplicates()

            stats = {
                "original_rows": original_shape[0],
                "processed_rows": df.shape[0],
                "identified_columns": list(mapping.values())
            }
            return df, stats

        except Exception as e:
            self.logger.error(f"预处理失败: {str(e)}")
            return pd.DataFrame(), {"error": str(e)}

    def clean_health_data(self, input_file: str, output_file: str) -> None:
        """实现接口要求的持久化清洗方法"""
        df, stats = self.preprocess_health_data(input_file)

        if "error" in stats or df.empty:
            error_msg = stats.get("error", "文件无有效数据或全部清洗被过滤")
            raise RuntimeError(f"数据清洗失败: {error_msg}")

        df.to_excel(output_file, index=False)
        print(f"✅ 清洗完成: {stats['processed_rows']} 条记录已保存至 {output_file}")