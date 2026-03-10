# db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from db.connection import Base
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from db.connection import Base

class HealthResource(Base):
    """卫生资源配置表"""
    __tablename__ = "health_resources"

    id = Column(Integer, primary_key=True)
    source = Column(String(20))  # 'WHO' 或 'Local'
    region = Column(String(50))  # 省份或国家代码
    indicator = Column(String(100))  # 指标名称
    year = Column(Integer)
    value = Column(Float)
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

class WHOGlobalHealth(Base):
    """WHO 全球卫生指标表"""
    __tablename__ = "who_global_health"

    id = Column(Integer, primary_key=True, index=True)
    country_code = Column(String(10), index=True)  # 如 CHN, USA
    indicator_code = Column(String(50), index=True) # 如 MDG_000001
    indicator_name = Column(String(200))
    year = Column(Integer, index=True)
    value = Column(Float)
    unit = Column(String(50))

GlobalHealthMetric = WHOGlobalHealth

class DiseaseRisk(Base):
    """疾病风险分析表"""
    __tablename__ = "disease_risks"

    id = Column(Integer, primary_key=True, index=True)
    region_name = Column(String(50), index=True)
    year = Column(Integer)
    cause = Column(String(100), comment="疾病分类")
    risk_score = Column(Float, comment="风险得分")
    intervention_suggestions = Column(String(500), comment="干预建议摘要")

class GlobalHealthMetric(Base):
    """基础平台核心表：存储国内外卫生指标"""
    __tablename__ = "health_metrics"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(20), index=True)      # 数据来源: 'WHO', 'Local', 'Search'
    region = Column(String(100), index=True)     # 国家代码或省份名称
    indicator = Column(String(200), index=True)  # 指标名称 (如: 预期寿命)
    year = Column(Integer, index=True)           # 年份
    value = Column(Float)                        # 指标数值
    unit = Column(String(50))                    # 单位
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# 为了向后兼容之前的代码，可以保留别名
WHOGlobalHealth = GlobalHealthMetric