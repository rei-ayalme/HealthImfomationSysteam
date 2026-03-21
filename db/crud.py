# db/crud.py
from sqlalchemy.orm import Session
from db.models import HealthResource
import pandas as pd


def save_processed_data_to_db(db: Session, df: pd.DataFrame):
    """将清洗后的 DataFrame 批量写入数据库"""
    # 清空旧数据（根据需求可选）
    # db.query(HealthResource).delete()

    for _, row in df.iterrows():
        db_record = HealthResource(
            region=row.get('region_name'),
            year=int(row.get('year', 2020)),
            physicians_per_1000=row.get('physicians_per_1000', 0),
            nurses_per_1000=row.get('nurses_per_1000', 0),
            hospital_beds_per_1000=row.get('hospital_beds_per_1000', 0),
            population=row.get('population', 0),
            gap_ratio=row.get('resource_gap_ratio', 0),
            gap_severity=row.get('gap_severity', '未知')
        )
        db.add(db_record)
    db.commit()


def get_resources_by_year(db: Session, year: int):
    """按年份查询所有地区资源"""
    return db.query(HealthResource).filter(HealthResource.year == year).all()


def get_province_history(db: Session, province: str):
    """查询特定省份的历史趋势数据"""
    return db.query(HealthResource).filter(HealthResource.region_name == province).order_by(HealthResource.year).all()