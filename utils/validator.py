# utils/validator.py
import re
import pandas as pd

def validate_province_name(name: str):
    """校验省份名称是否合法（简单中文校验）"""
    if not name:
        return False
    return bool(re.match(r'^[\u4e00-\u9fa5]{2,10}$', name))

def validate_data_columns(df: pd.DataFrame, required_columns: list):
    """校验上传的 DataFrame 是否包含必要的列"""
    missing = [col for col in required_columns if col not in df.columns]
    return len(missing) == 0, missing

def check_file_size(file, max_mb: int = 10):
    """校验上传文件大小"""
    if file is None:
        return False
    return file.size <= max_mb * 1024 * 1024