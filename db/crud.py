# db/crud.py
from sqlalchemy.orm import Session
from db.models import HealthResource
import pandas as pd


def _safe_float(value, default=0.0):
    if pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def save_processed_data_to_db(db: Session, df: pd.DataFrame):
    for _, row in df.iterrows():
        region = row.get('region_name') if 'region_name' in row else row.get('region')
        if pd.isna(region) or region is None:
            continue

        year_value = row.get('year', 2020)
        if pd.isna(year_value):
            year_value = 2020

        db_record = HealthResource(
            region=str(region),
            year=int(year_value),
            physicians_per_1000=_safe_float(row.get('physicians_per_1000', 0)),
            nurses_per_1000=_safe_float(row.get('nurses_per_1000', 0)),
            hospital_beds_per_1000=_safe_float(row.get('hospital_beds_per_1000', 0)),
            population=_safe_float(row.get('population', 0)),
            gap_ratio=_safe_float(row.get('resource_gap_ratio', 0)),
            gap_severity=row.get('gap_severity', '未知')
        )
        db.add(db_record)
    db.commit()


def get_resources_by_year(db: Session, year: int):
    """按年份查询所有地区资源"""
    return db.query(HealthResource).filter(HealthResource.year == year).all()


def get_province_history(db: Session, province: str):
    return db.query(HealthResource).filter(HealthResource.region == province).order_by(HealthResource.year).all()
