# db/connection.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,Session
from config.settings import SETTINGS
import os
from db.models import Base, HealthResource, GlobalHealthMetric

# 使用外部配置文件中的数据库连接
DB_URL = SETTINGS.DATABASE_URL

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """获取数据库会话的依赖函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_db(db: Session):
    # 检查表中是否已有基础数据
    if db.query(HealthResource).count() == 0:
        import pandas as pd
        # 加载开发者准备的预清洗数据
        initial_df = pd.read_csv("data/seed_health_data.csv")
        # 将其保存到生产表 (health_resources)
        save_processed_data_to_db(db, initial_df)
        print("基础卫生资源数据已预置。")

def init_db():
    """初始化数据库表"""
    import db.models
    Base.metadata.create_all(bind=engine)