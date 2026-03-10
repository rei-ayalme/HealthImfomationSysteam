# modules/offline_preprocessor.py
import pandas as pd
from modules.data_cleaner import HealthDataCleaner
from db.crud import save_processed_data_to_db
from db.connection import SessionLocal


def run_offline_import(excel_path):
    """离线读取本地 Excel 并存入数据库"""
    print(f"正在读取本地大型数据集: {excel_path}")
    df = pd.read_excel(excel_path)

    # 调用提取出来的通用清洗算法
    cleaner = HealthDataCleaner()
    df = cleaner.standardize_indicators(df, {"医师数": "physicians", "人口": "population"})
    df = cleaner.calculate_core_metrics(df)

    # 存入数据库
    db = SessionLocal()
    save_processed_data_to_db(db, df)
    db.close()
    print("离线数据导入完成，已存入数据库。")