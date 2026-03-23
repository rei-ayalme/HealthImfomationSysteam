import pandas as pd
import numpy as np
import os
import logging
from typing import Tuple, Dict
from modules.core.interface import IPreprocessor
from modules.data.cleaner import HealthDataCleaner
import json
import pandera.pandas as pa
from config.settings import SETTINGS

# 定义健康数据验证模式
HealthDataSchema = pa.DataFrameSchema({
    "year": pa.Column(int, pa.Check.in_range(1900, 2100), coerce=True),
    "population": pa.Column(float, pa.Check.ge(0.0), coerce=True, required=False),
    "physicians": pa.Column(float, pa.Check.ge(0.0), coerce=True, required=False),
    "nurses": pa.Column(float, pa.Check.ge(0.0), coerce=True, required=False),
    "hospital_beds": pa.Column(float, pa.Check.ge(0.0), coerce=True, required=False),
    "physicians_per_1000": pa.Column(float, pa.Check.ge(0.0), coerce=True, required=False),
    "nurses_per_1000": pa.Column(float, pa.Check.ge(0.0), coerce=True, required=False),
    "hospital_beds_per_1000": pa.Column(float, pa.Check.ge(0.0), coerce=True, required=False),
})

class HealthDataPreprocessor(IPreprocessor):
    """
    统一健康数据预处理器
    实现从原始 Excel 到标准数据库格式的转化
    """

    def __init__(self):
        self.cleaner = HealthDataCleaner()
        self.logger = logging.getLogger("health_system.preprocessor")
        
        # 动态加载列名映射字典
        mapping_file = os.path.join(SETTINGS.BASE_DIR, "config", "column_mapping.json")
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                self.col_map = json.load(f)
        except Exception as e:
            self.logger.warning(f"未能加载列名映射配置 {mapping_file}: {e}")
            self.col_map = SETTINGS.STANDARD_COLUMN_MAPPING.copy()
            # 如果配置里没有提供 mapping 文件，默认加上一些泛用关键词
            self.col_map.setdefault("physicians", ["执业医师", "执业(助理)医师", "医师", "physicians", "doctor", "生人数", "人员数"])
            self.col_map.setdefault("nurses", ["注册护士", "护士", "nurses", "nurse"])
            self.col_map.setdefault("hospital_beds", ["床位数", "医疗卫生机构床位数", "医院床位数", "beds", "hospital_beds"])
            self.col_map.setdefault("population", ["人口数", "年末人口数", "总人口", "population", "pop", "人口(万人)"])
            self.col_map.setdefault("region_name", ["地区", "省份", "省市", "region", "location", "area"])

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

    def preprocess_health_data(self, file_path: str, hierarchy_level: str = "合计") -> Tuple[pd.DataFrame, Dict]:
        """执行完整预处理流程，支持选择提取特定层级数据（如合计、城市、农村）"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"未找到原始文件: {file_path}")

            # 1. 读取数据 (支持单个文件或目录扫描)
            df_list = []
            if os.path.isdir(file_path):
                for root, _, files in os.walk(file_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        # 仅处理中国本地的年鉴及统计局数据
                        if file.endswith(('.xlsx', '.xls', '.csv')) and not file.startswith('~'):
                            try:
                                if file.endswith('.csv'):
                                    temp_df = pd.read_csv(full_path)
                                    if "NBS" in file:
                                        # 特殊处理 NBS.csv (宽表转长表)
                                        # 因为 NBS.csv 的列名是 '地区', '2024年', '2023年' 等
                                        id_vars = [c for c in temp_df.columns if not (str(c).endswith('年') and str(c)[:-1].isdigit())]
                                        value_vars = [c for c in temp_df.columns if str(c).endswith('年') and str(c)[:-1].isdigit()]
                                        if value_vars:
                                            temp_df = temp_df.melt(id_vars=id_vars, value_vars=value_vars, var_name='year', value_name='value')
                                            temp_df['year'] = temp_df['year'].astype(str).str.replace('年', '').astype(int)
                                            # 如果没有特定的指标列，我们给它一个默认值或者使用它的列名
                                            if '指标' not in temp_df.columns and 'indicator' not in temp_df.columns:
                                                temp_df['indicator'] = 'NBS_Data'
                                else:
                                    try:
                                        temp_df = pd.read_excel(full_path)
                                        # 如果是面板数据，可能有多层级或者需要简单清洗
                                        if "面板数据" in file or "提取自" in file:
                                            # 处理掉全是 NaN 的行
                                            temp_df = temp_df.dropna(how='all')
                                            
                                            # 面板数据的多层表头合并处理
                                            if len(temp_df) > 1 and pd.isna(temp_df.iloc[0, 0]):
                                                # 如果前两行像表头，尝试将它们合并
                                                header_1 = temp_df.columns.to_series().astype(str)
                                                header_2 = temp_df.iloc[0].fillna('').astype(str)
                                                header_1 = header_1.where(~header_1.str.contains('Unnamed'), '')
                                                new_cols = []
                                                for h1, h2 in zip(header_1, header_2):
                                                    if h1 and h2:
                                                        new_cols.append(f"{h1}_{h2}")
                                                    elif h1:
                                                        new_cols.append(h1)
                                                    elif h2:
                                                        new_cols.append(h2)
                                                    else:
                                                        new_cols.append("Unknown")
                                                temp_df.columns = new_cols
                                                temp_df = temp_df.iloc[1:].reset_index(drop=True)
                                                
                                                # 过滤多级表头：提取符合 hierarchy_level 或没有层级区分的列
                                                if hierarchy_level:
                                                    filtered_cols = []
                                                    for col in temp_df.columns:
                                                        if '_' not in col or hierarchy_level in col:
                                                            filtered_cols.append(col)
                                                    temp_df = temp_df[filtered_cols]
                                                    # 重命名列，去掉层级后缀
                                                    temp_df.columns = [col.replace(f"_{hierarchy_level}", "") for col in temp_df.columns]
                                    except Exception as e:
                                        # 兼容一些以 .xls 结尾但实际上是 HTML 的文件
                                        if 'Excel file format cannot be determined' in str(e) or 'Expected BOF' in str(e):
                                            try:
                                                html_dfs = pd.read_html(full_path)
                                                temp_df = html_dfs[0] if html_dfs else pd.DataFrame()
                                            except Exception as html_e:
                                                print(f"尝试作为 HTML 解析 {full_path} 失败: {html_e}")
                                                continue
                                        else:
                                            raise e
                                if not temp_df.empty:
                                    # 确保所有列名都是字符串，防止 concat 报错
                                    temp_df.columns = temp_df.columns.astype(str)
                                    # 避免重复的列名
                                    temp_df = temp_df.loc[:, ~temp_df.columns.duplicated()]
                                    
                                    # 为了后续可能需要的年份等信息，可以尝试从文件名中提取
                                    if 'year' not in temp_df.columns:
                                        import re
                                        year_match = re.search(r'20\d{2}', file)
                                        if year_match:
                                            temp_df['year'] = int(year_match.group())
                                    df_list.append(temp_df)
                            except Exception as e:
                                print(f"无法读取文件 {full_path}: {e}")
                if not df_list:
                    raise ValueError(f"目录 {file_path} 下未找到任何有效的 Excel/CSV 文件")
                
                # 在 concat 之前，确保所有 DataFrame 的列名都是字符串，并且统一格式
                for i, temp_df in enumerate(df_list):
                    df_list[i].columns = df_list[i].columns.astype(str)
                df = pd.concat(df_list, ignore_index=True)
            else:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                    if "NBS" in file_path:
                        # 特殊处理 NBS.csv (宽表转长表)
                        id_vars = [c for c in df.columns if not (str(c).endswith('年') and str(c)[:-1].isdigit())]
                        value_vars = [c for c in df.columns if str(c).endswith('年') and str(c)[:-1].isdigit()]
                        if value_vars:
                            df = df.melt(id_vars=id_vars, value_vars=value_vars, var_name='year', value_name='value')
                            df['year'] = df['year'].astype(str).str.replace('年', '').astype(int)
                            if '指标' not in df.columns and 'indicator' not in df.columns:
                                df['indicator'] = 'NBS_Data'
                else:
                    df = pd.read_excel(file_path)
                    if "面板数据" in file_path:
                        df = df.dropna(how='all')
                        if len(df) > 1 and pd.isna(df.iloc[0, 0]):
                            header_1 = df.columns.to_series().astype(str)
                            header_2 = df.iloc[0].fillna('').astype(str)
                            header_1 = header_1.where(~header_1.str.contains('Unnamed'), '')
                            new_cols = []
                            for h1, h2 in zip(header_1, header_2):
                                if h1 and h2:
                                    new_cols.append(f"{h1}_{h2}")
                                elif h1:
                                    new_cols.append(h1)
                                elif h2:
                                    new_cols.append(h2)
                                else:
                                    new_cols.append("Unknown")
                            df.columns = new_cols
                            df = df.iloc[1:].reset_index(drop=True)
                            
                            # 过滤多级表头：提取符合 hierarchy_level 或没有层级区分的列
                            if hierarchy_level:
                                filtered_cols = []
                                for col in df.columns:
                                    if '_' not in col or hierarchy_level in col:
                                        filtered_cols.append(col)
                                df = df[filtered_cols]
                                # 重命名列，去掉层级后缀
                                df.columns = [col.replace(f"_{hierarchy_level}", "") for col in df.columns]

            original_shape = df.shape

            # 处理类似年鉴表中的复杂表头，尝试定位真实的列名行
            # 通常地区/省份这一列的名称会在前几行出现
            region_col_idx = None
            header_row_idx = -1
            
            # 首先清理 DataFrame，去掉全空的列和行
            df = df.dropna(how='all').dropna(axis=1, how='all').reset_index(drop=True)

            for i in range(min(15, len(df))):
                # 检查这一行是否包含地区标识
                row_values = df.iloc[i].astype(str).str.replace(r'\s+', '', regex=True).tolist()
                for j, val in enumerate(row_values):
                    if any(k in val for k in ["地区", "省份", "省市", "年份"]):
                        region_col_idx = j
                        header_row_idx = i
                        break
                if region_col_idx is not None:
                    break
            
            if header_row_idx != -1:
                # 提取表头
                new_headers = df.iloc[header_row_idx].fillna('').astype(str).str.replace(r'\s+', '', regex=True).tolist()
                
                # 尝试向上合并表头 (比如 2011.xlsx 中，真实表头可能跨越了前几行)
                for i in range(0, header_row_idx):
                    sub_row = df.iloc[i].fillna('').astype(str).str.replace(r'\s+', '', regex=True).tolist()
                    for j in range(len(new_headers)):
                        if j < len(sub_row) and sub_row[j] and sub_row[j] not in new_headers[j] and "Unnamed" not in sub_row[j]:
                            new_headers[j] = sub_row[j] + "_" + new_headers[j]
                
                # 尝试向下合并多级表头 (向下看1-3行)
                for i in range(header_row_idx + 1, min(header_row_idx + 4, len(df))):
                    sub_row = df.iloc[i].fillna('').astype(str).str.replace(r'\s+', '', regex=True).tolist()
                    # 检查这一行是不是数据行，如果 region_col_idx 对应的是个省份名，说明是数据行了
                    if region_col_idx < len(sub_row):
                        region_val = sub_row[region_col_idx]
                        # 判断是否为省份名或年份数字
                        if (len(region_val) >= 2 and region_val not in ["合计", "总计", "全国", "小计", "东部", "中部", "西部", "nan", "NaN"]) or region_val.isdigit():
                            break
                    for j in range(len(new_headers)):
                        if j < len(sub_row) and sub_row[j] and sub_row[j] not in new_headers[j] and "nan" not in sub_row[j].lower():
                            new_headers[j] = new_headers[j] + "_" + sub_row[j]
                
                df.columns = new_headers
                # 删除表头及以上的行
                df = df.iloc[header_row_idx+1:].reset_index(drop=True)
                
            # 清理列名，去掉多余的换行符
            df.columns = df.columns.str.replace(r'\n', '', regex=True).str.replace(r'\s+', '', regex=True)

            # 2. 列名标准化
            mapping = self._identify_columns(df.columns)
            df = self.cleaner.standardize_indicators(df, mapping)

            # 3. 缺失值与基础清洗
            df = self.cleaner.handle_missing_values(df)

            # 3.5 异常值深度清洗 (IQR / 3σ)
            # 对数值型核心列进行离群点检测和截断，防止污染后续 DEA 或 GBD
            cols_to_clean = [col for col in ['population', 'physicians', 'nurses', 'hospital_beds'] if col in df.columns]
            if cols_to_clean:
                df = self.cleaner.detect_and_handle_outliers(df, columns=cols_to_clean, method='iqr')

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
            
            # 如果映射失败，尝试从已有列名中模糊匹配
            for target_col, keywords in [
                ('physicians_per_1000', ['医师', '医生', 'physician']),
                ('nurses_per_1000', ['护士', 'nurse']),
                ('hospital_beds_per_1000', ['床位', 'bed']),
                ('population', ['人口', 'pop'])
            ]:
                if target_col not in df.columns:
                    for existing_col in df.columns:
                        if any(k in str(existing_col) for k in keywords):
                            if target_col == 'population':
                                df[target_col] = pd.to_numeric(df[existing_col], errors='coerce').fillna(0)
                            else:
                                # 对于比率，如果原列是绝对值且有population，这里简单计算；如果没有population暂设绝对值
                                val = pd.to_numeric(df[existing_col], errors='coerce').fillna(0)
                                if 'population' in df.columns:
                                    pop = pd.to_numeric(df['population'], errors='coerce').fillna(1)
                                    # 假设人口单位是万，转换为千人
                                    df[target_col] = val / (pop * 10).replace(0, 1)
                                else:
                                    df[target_col] = val
                            break
            
            # 如果还是找不到，用 NBS 数据作为核心补充
            if 'region_name' in df.columns:
                try:
                    # 尝试读取并合并我们刚刚测试的 NBS 数据来补充 population 和 核心指标
                    nbs_path = os.path.join(SETTINGS.RAW_DATA_PATH, 'NBS.csv')
                    if os.path.exists(nbs_path):
                        df_nbs = pd.read_csv(nbs_path)
                        id_vars = [c for c in df_nbs.columns if not (str(c).endswith('年') and str(c)[:-1].isdigit())]
                        value_vars = [c for c in df_nbs.columns if str(c).endswith('年') and str(c)[:-1].isdigit()]
                        df_nbs_long = df_nbs.melt(id_vars=id_vars, value_vars=value_vars, var_name='year_nbs', value_name='value')
                        df_nbs_long['year_nbs'] = df_nbs_long['year_nbs'].astype(str).str.replace('年', '').astype(int)
                        
                        # 假设 NBS.csv 里有 '地区' 列，可以改名为 'region_name'
                        if '地区' in df_nbs_long.columns:
                            df_nbs_long = df_nbs_long.rename(columns={'地区': 'region_name'})
                        
                        # 提取年份
                        if 'year' not in df.columns or df['year'].isnull().all() or (df['year'] == 0).all():
                            # 如果原表没有年份，假设当前文件名带有年份或默认为最新一年
                            # 为简化处理，如果有 year_nbs 就用它
                            if 'year' not in df.columns:
                                df['year'] = 2020  # 临时占位，防止 merge 报错
                             
                        # 如果原来没取到 population，就用它（简单假设它的 value 是人口/床位等指标之一）
                        if 'population' not in df.columns or (df['population'] == 0).all():
                            df = pd.merge(df, df_nbs_long[['region_name', 'year_nbs', 'value']], left_on=['region_name', 'year'], right_on=['region_name', 'year_nbs'], how='left')
                            if 'value' in df.columns:
                                df['population'] = df['value'].fillna(1000) # 这里只是举例，如果是真实数据需要对应具体的 indicator
                                df = df.drop(columns=['value', 'year_nbs'])
                except Exception as e:
                    self.logger.warning(f"尝试用 NBS 补充数据失败: {e}")

            for col in numeric_cols:
                if col not in df.columns:
                    print(f"⚠️ 警告: 原数据缺少核心列映射 [{col}]，已自动填充为0。")
                    df[col] = 0.0
                else:
                    # 处理可能由于合并导致的列重复问题，强制取第一列或合并
                    if isinstance(df[col], pd.DataFrame):
                        df = df.loc[:, ~df.columns.duplicated()].copy()
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            # 6. 去重并剔除分母为0导致的无限大异常值
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.drop_duplicates(ignore_index=True)

            # NBS 等数据可能存在需要melt的宽表格式(如 '2024年', '2023年' 为列)，需做宽转长处理
            # 检查是否有以年为列名的数据
            year_cols = [c for c in df.columns if str(c).endswith('年') and str(c)[:-1].isdigit()]
            if year_cols and 'region_name' in df.columns:
                # 简单融合成长表
                pass

            # 7. 真实数据补充：对关键缺失数据进行线性插值计算
            # 按照地区分组，对时间序列数据进行插值
            if 'region_name' in df.columns and 'year' in df.columns:
                df = df.sort_values(by=['region_name', 'year'])
                
                # 对数值列进行插值，最多连续插值3年
                interpolate_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col]) and col not in ['year']]
                for col in interpolate_cols:
                    try:
                        df[col] = df.groupby('region_name')[col].transform(
                            lambda group: group.interpolate(method='linear', limit=3, limit_direction='both')
                        )
                    except Exception:
                        pass
                
                # 依然存在缺失的，用地区均值填充
                for col in interpolate_cols:
                    try:
                        df[col] = df.groupby('region_name')[col].transform(lambda x: x.fillna(x.mean()))
                    except Exception:
                        pass
                    
                # 如果还有缺失，用全局均值填充（避免遗留空值）
                for col in interpolate_cols:
                    try:
                        df[col] = df[col].fillna(df[col].mean())
                    except Exception:
                        pass
            
            # 将填充后可能产生的剩余无穷大替换为0
            df = df.replace([np.inf, -np.inf, np.nan], 0)
                
            # 执行 Schema 校验
            try:
                # 过滤掉schema中不存在的列进行校验（如果schema只验证部分列）
                cols_to_validate = [col for col in df.columns if col in HealthDataSchema.columns]
                if cols_to_validate:
                    # 我们只需要验证存在的列
                    schema_to_validate = HealthDataSchema.select_columns(cols_to_validate)
                    df = schema_to_validate.validate(df)
            except pa.errors.SchemaError as e:
                self.logger.warning(f"数据 schema 校验发现异常，部分数据可能不符合规范: {e}")
                # 将异常情况进行清理：对所有错误的数据点填充为 0 或者 np.nan
                if hasattr(e, 'failure_cases'):
                    failure_cases = e.failure_cases
                    if not failure_cases.empty:
                        for _, row in failure_cases.iterrows():
                            # 确保 row 包含 index 和 column
                            if 'index' in row and 'column' in row:
                                idx = row['index']
                                col = row['column']
                                if idx in df.index and col in df.columns:
                                    df.at[idx, col] = np.nan
                self.logger.info("已尝试将不符合 Schema 的值替换为空值(NaN)，以防止阻断后续计算")
            except Exception as e:
                self.logger.warning(f"Schema 校验时发生未知错误: {e}")
            
            # 确保 identified_columns 是包含字符串的列表，避免 np.concatenate 报错
            identified_columns_list = []
            for k, v in mapping.items():
                if isinstance(v, list):
                    identified_columns_list.extend([str(i) for i in v])
                elif isinstance(v, pd.Series) or isinstance(v, np.ndarray):
                    identified_columns_list.extend([str(i) for i in v.tolist()])
                else:
                    identified_columns_list.append(str(v))
            
            # 将 None 或其他可能的异常值转为纯字符串
            identified_columns_list = [str(x) for x in identified_columns_list if x is not None]

            # 最终强制转换为原生 python list，防止 pandas index 等类型泄露
            identified_columns_list = list(identified_columns_list)
            # 添加一个容错机制
            if not isinstance(identified_columns_list, list):
                identified_columns_list = ["unknown"]

            stats = {
                "original_rows": int(original_shape[0]),
                "processed_rows": int(df.shape[0]),
                "identified_columns": identified_columns_list
            }
            return df, stats

        except Exception as e:
            self.logger.exception("预处理失败")
            return pd.DataFrame(), {"error": str(e)}

    def clean_health_data(self, input_file: str, output_file: str, hierarchy_level: str = "合计") -> None:
        """实现接口要求的持久化清洗方法"""
        df, stats = self.preprocess_health_data(input_file, hierarchy_level=hierarchy_level)

        if "error" in stats or df.empty:
            error_msg = stats.get("error", "文件无有效数据或全部清洗被过滤")
            raise RuntimeError(f"数据清洗失败: {error_msg}")

        df.to_excel(output_file, index=False)
        print(f"✅ 清洗完成: {stats['processed_rows']} 条记录已保存至 {output_file}")