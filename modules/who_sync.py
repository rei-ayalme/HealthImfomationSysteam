# modules/who_sync.py
import requests
import pandas as pd
from db.connection import SessionLocal
from db.models import WHOGlobalHealth


def fetch_and_store_who_data(indicator_code="MDG_000001"):  # 示例：预期寿命
    url = f"https://ghoapi.azureedge.net/api/{indicator_code}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()['value']
        df = pd.DataFrame(data)

        # 清洗逻辑：提取核心列
        df_clean = df[['SpatialDim', 'TimeDim', 'NumericValue']].copy()
        df_clean.columns = ['country_code', 'year', 'value']

        # 存入数据库
        db = SessionLocal()
        for _, row in df_clean.iterrows():
            record = WHOGlobalHealth(
                country_code=row['country_code'],
                year=int(row['year']),
                value=float(row['value']),
                indicator_code=indicator_code
            )
            db.add(record)
        db.commit()
        db.close()
        return True
    return False