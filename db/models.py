# db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from db.connection import Base
from datetime import datetime


class HealthResource(Base):
    """卫生资源配置表"""
    __tablename__ = "health_resources"

    id = Column(Integer, primary_key=True, index=True)
    region_name = Column(String(50), index=True, comment="省份/地区名称")
    year = Column(Integer, index=True, comment="年份")

    # 核心指标
    physicians_per_1000 = Column(Float, default=0.0, comment="每千人口执业(助理)医师数")
    nurses_per_1000 = Column(Float, default=0.0, comment="每千人口注册护士数")
    hospital_beds_per_1000 = Column(Float, default=0.0, comment="每千人口医疗卫生机构床位数")
    population = Column(Float, comment="总人口(万人)")

    # 分析结果缓存
    supply_index = Column(Float, comment="综合供给指数")
    theoretical_need = Column(Float, comment="理论需求指数")
    gap_ratio = Column(Float, comment="资源缺口率")
    gap_severity = Column(String(20), comment="缺口严重程度")

    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DiseaseRisk(Base):
    """疾病风险分析表"""
    __tablename__ = "disease_risks"

    id = Column(Integer, primary_key=True, index=True)
    region_name = Column(String(50), index=True)
    year = Column(Integer)
    cause = Column(String(100), comment="疾病分类")
    risk_score = Column(Float, comment="风险得分")
    intervention_suggestions = Column(String(500), comment="干预建议摘要")