# db/connection.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 默认使用项目根目录下的 SQLite 数据库
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_URL = f"sqlite:///{os.path.join(BASE_DIR, 'health_system.db')}"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """获取数据库会话的依赖函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库表"""
    import db.models
    Base.metadata.create_all(bind=engine)0