# db/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.settings import SETTINGS
import os
from db.models import Base, HealthResource
from db.crud import save_processed_data_to_db

# 使用外部配置文件中的数据库连接
DB_URL = SETTINGS.DATABASE_URL

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """获取数据库会话的依赖函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_db(db: Session):
    if db.query(HealthResource).count() == 0:
        import pandas as pd
        seed_path = os.path.join(SETTINGS.BASE_DIR, "data", "seed_health_data.csv")
        if os.path.exists(seed_path):
            initial_df = pd.read_csv(seed_path)
            save_processed_data_to_db(db, initial_df)
            print("基础卫生资源数据已预置。")

def init_db():
    Base.metadata.create_all(bind=engine)
