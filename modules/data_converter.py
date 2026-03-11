# modules/data_converter.py
import os
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from config.settings import DATA_CONFIG  # 新增数据配置
from pydantic import BaseModel


# ====================== 配置（新增到config/settings.py） ======================
# DATA_CONFIG = {
#     "supported_formats": [".csv", ".xlsx", ".xls"],  # 支持的文件格式
#     "default_encoding": ["utf-8", "gbk", "gb2312"],  # 自动尝试的编码
#     "default_sep": [",", "\t", ";"],  # 自动尝试的分隔符
#     "null_values": ["无数据", "NaN", "NA", "-", 0, -999],  # 识别为空值的标记
#     "numeric_cols": ["value", "数值", "数量", "占比", "密度"],  # 需转为数值的列名关键词
#     "date_cols": ["year", "年份", "日期", "时间"],  # 需转为日期的列名关键词
#     "standard_output_cols": ["country", "year", "indicator", "value", "region"]  # 标准化列名
# }

# 定义转换结果模型（结构化返回）
class DataConvertResult(BaseModel):
    status: bool  # 转换状态
    data: Optional[pd.DataFrame] = None  # 标准化DataFrame
    standard_format: Optional[Dict] = None  # 算法适配的结构化Dict
    agent_prompt: Optional[str] = None  # 智能体适配的自然语言描述
    error_msg: Optional[str] = None  # 错误信息
    metadata: Optional[Dict] = None  # 元信息（文件大小/行数/列数等）


def validate_file(file_path: str) -> Tuple[bool, str]:
    """
    第一步：文件校验（格式/完整性/大小）
    """
    # 1. 检查文件存在
    if not os.path.exists(file_path):
        return False, "文件不存在"
    # 2. 检查格式支持
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in DATA_CONFIG["supported_formats"]:
        return False, f"不支持的文件格式：{file_ext}，仅支持{DATA_CONFIG['supported_formats']}"
    # 3. 检查文件大小（避免过大）
    file_size = os.path.getsize(file_path) / 1024 / 1024  # MB
    if file_size > 100:  # 限制100MB
        return False, f"文件过大（{file_size:.2f}MB），最大支持100MB"
    # 4. 检查文件完整性（简单校验）
    try:
        if file_ext in [".xlsx", ".xls"]:
            pd.ExcelFile(file_path)
        else:
            with open(file_path, "rb") as f:
                f.read(1024)  # 读取前1024字节
    except Exception as e:
        return False, f"文件损坏或不完整：{str(e)[:100]}"
    return True, "文件校验通过"


def read_file_unified(file_path: str) -> Tuple[pd.DataFrame, str]:
    """
    第二步：统一读取（自动适配编码/分隔符/多Sheet）
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    df = None
    error_msg = ""
    try:
        # 读取Excel（自动识别有效Sheet）
        if file_ext in [".xlsx", ".xls"]:
            excel_file = pd.ExcelFile(file_path)
            # 选择非空、行数最多的Sheet
            sheet_stats = []
            for sheet in excel_file.sheet_names:
                try:
                    temp_df = pd.read_excel(file_path, sheet_name=sheet, nrows=5)
                    sheet_stats.append((sheet, len(temp_df), len(temp_df.columns)))
                except:
                    continue
            if not sheet_stats:
                return None, "Excel无有效Sheet"
            best_sheet = max(sheet_stats, key=lambda x: x[1] * x[2])[0]
            df = pd.read_excel(file_path, sheet_name=best_sheet)
        # 读取CSV（自动适配编码/分隔符）
        else:
            # 尝试不同编码
            for encoding in DATA_CONFIG["default_encoding"]:
                # 尝试不同分隔符
                for sep in DATA_CONFIG["default_sep"]:
                    try:
                        df = pd.read_csv(
                            file_path,
                            encoding=encoding,
                            sep=sep,
                            na_values=DATA_CONFIG["null_values"],
                            keep_default_na=True
                        )
                        if len(df) > 0:
                            break
                    except:
                        continue
                if df is not None and len(df) > 0:
                    break
        if df is None or len(df) == 0:
            error_msg = "文件无有效数据"
        else:
            # 清理空行/空列
            df = df.dropna(how="all", axis=0).dropna(how="all", axis=1)
            # 重置列名（去除空格/特殊字符）
            df.columns = [str(col).strip().replace(" ", "_").replace("/", "_") for col in df.columns]
    except Exception as e:
        error_msg = f"读取失败：{str(e)[:100]}"
    return df, error_msg


def clean_data_standard(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """
    第三步：数据清洗（空值/异常值/类型转换/列名标准化）
    """
    cleaned_df = df.copy()
    error_msg = ""
    try:
        # 1. 空值处理（数值列填充0，分类列填充"未知"）
        for col in cleaned_df.columns:
            # 识别数值列
            if any(keyword in col.lower() for keyword in DATA_CONFIG["numeric_cols"]):
                cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors="coerce").fillna(0)
            # 识别日期列
            elif any(keyword in col.lower() for keyword in DATA_CONFIG["date_cols"]):
                cleaned_df[col] = pd.to_datetime(cleaned_df[col], errors="coerce")
            # 分类列
            else:
                cleaned_df[col] = cleaned_df[col].fillna("未知").astype(str)

        # 2. 列名标准化（映射到算法/智能体通用列名）
        col_mapping = {}
        for std_col in DATA_CONFIG["standard_output_cols"]:
            # 模糊匹配列名
            for raw_col in cleaned_df.columns:
                if std_col in raw_col.lower() or raw_col.lower() in std_col:
                    col_mapping[raw_col] = std_col
                    break
        # 重命名列
        cleaned_df = cleaned_df.rename(columns=col_mapping)
        # 确保核心列存在（无则创建空列）
        for std_col in DATA_CONFIG["standard_output_cols"]:
            if std_col not in cleaned_df.columns:
                cleaned_df[std_col] = np.nan

        # 3. 去重
        cleaned_df = cleaned_df.drop_duplicates()
        # 4. 重置索引
        cleaned_df = cleaned_df.reset_index(drop=True)
    except Exception as e:
        error_msg = f"清洗失败：{str(e)[:100]}"
    return cleaned_df, error_msg


def adapt_to_algorithm(df: pd.DataFrame) -> Dict:
    """
    第四步-1：适配算法（DeepSeek_Analyzer）→ 结构化Dict
    输出格式：{国家: {年份: {指标: 数值}}}，和deepseek_adapter.py兼容
    """
    # 确保核心列存在
    required_cols = ["country", "year", "indicator", "value"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = "未知" if col != "value" else 0

    # 转换为算法要求的格式
    algo_data = {}
    for country in df["country"].unique():
        country_df = df[df["country"] == country]
        year_dict = {}
        for year in country_df["year"].unique():
            year_df = country_df[country_df["year"] == year]
            indicator_dict = year_df.set_index("indicator")["value"].to_dict()
            year_dict[int(year) if pd.notna(year) else year] = indicator_dict
        algo_data[country] = year_dict
    return algo_data


def adapt_to_agent(df: pd.DataFrame, file_name: str) -> str:
    """
    第四步-2：适配智能体（AI助手）→ 自然语言描述+结构化数据
    输出prompt，让智能体能理解数据内容并回答问题
    """
    # 基础元信息
    n_rows = len(df)
    n_cols = len(df.columns)
    core_cols = [col for col in DATA_CONFIG["standard_output_cols"] if col in df.columns]
    # 数据概览
    country_list = df["country"].dropna().unique()[:10]  # 前10个国家
    year_range = (df["year"].min(), df["year"].max()) if pd.notna(df["year"]).any() else ("未知", "未知")
    indicator_list = df["indicator"].dropna().unique()[:10]  # 前10个指标

    # 构建智能体prompt
    agent_prompt = f"""
    以下是上传的{file_name}数据文件的标准化信息：
    1. 数据规模：共{n_rows}行，{n_cols}列，核心列包含{core_cols}；
    2. 覆盖范围：国家{list(country_list)}（共{len(df["country"].unique())}个），年份{year_range[0]}-{year_range[1]}；
    3. 指标类型：{list(indicator_list)}（共{len(df["indicator"].unique())}个）；
    4. 结构化数据：
    {df[DATA_CONFIG["standard_output_cols"]].head(20).to_dict(orient="records")}

    请基于以上数据回答用户关于卫生资源配置、疾病风险、资源缺口的问题，回答需结合数据，标注数据来源。
    """
    return agent_prompt.strip()


def convert_data(file_path: str, file_name: str) -> DataConvertResult:
    """
    全链路转换入口：校验→读取→清洗→适配算法/智能体
    """
    # 1. 文件校验
    validate_ok, validate_msg = validate_file(file_path)
    if not validate_ok:
        return DataConvertResult(status=False, error_msg=validate_msg)

    # 2. 统一读取
    df, read_msg = read_file_unified(file_path)
    if df is None or read_msg:
        return DataConvertResult(status=False, error_msg=read_msg)

    # 3. 数据清洗
    cleaned_df, clean_msg = clean_data_standard(df)
    if clean_msg:
        return DataConvertResult(status=False, error_msg=clean_msg)

    # 4. 适配算法
    standard_format = adapt_to_algorithm(cleaned_df)

    # 5. 适配智能体
    agent_prompt = adapt_to_agent(cleaned_df, file_name)

    # 6. 元信息
    metadata = {
        "file_name": file_name,
        "file_size": os.path.getsize(file_path) / 1024 / 1024,  # MB
        "rows": len(cleaned_df),
        "columns": list(cleaned_df.columns),
        "standard_columns": [col for col in DATA_CONFIG["standard_output_cols"] if col in cleaned_df.columns]
    }

    return DataConvertResult(
        status=True,
        data=cleaned_df,
        standard_format=standard_format,
        agent_prompt=agent_prompt,
        metadata=metadata
    )


# 本地测试
if __name__ == "__main__":
    # 测试CSV/Excel转换
    test_file = "test_health_data.csv"  # 替换为你的测试文件
    result = convert_data(test_file, os.path.basename(test_file))
    if result.status:
        print("转换成功！")
        print(f"元信息：{result.metadata}")
        print(f"算法适配数据：{result.standard_format}")
        print(f"智能体Prompt：{result.agent_prompt[:200]}...")
    else:
        print(f"转换失败：{result.error_msg}")