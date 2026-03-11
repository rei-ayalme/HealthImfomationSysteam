# db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from db.connection import Base
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime,Text,JSON
from db.connection import Base

Base = declarative_base()

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

class RawHealthData(Base):
    __tablename__ = "raw_health_data"
    id = Column(Integer, primary_key=True)
    upload_time = Column(DateTime, default=datetime.utcnow)
    file_name = Column(String)
    raw_content = Column(Text)  # 存储原始 JSON 或序列化的内容

class OWIDFetchLog(Base):
    __tablename__ = "owid_fetch_log"
    id = Column(Integer, primary_key=True, index=True)
    indicator_id = Column(String(100), index=True)  # OWID指标ID
    target_countries = Column(Text)  # 爬取的国家列表（JSON字符串）
    fetch_time = Column(DateTime, default=datetime.now)  # 爬取时间
    status = Column(Boolean, default=True)  # 爬取状态：True成功/False失败
    data_count = Column(Integer, default=0)  # 本次爬取的新数据量
    error_msg = Column(Text, nullable=True)  # 失败时的错误信息

class DeepSeekAnalysisResult(Base):
    __tablename__ = "deepseek_analysis_result"
    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(50), index=True)  # 分析任务类型：disease_risk/resource_allocation等
    indicator_ids = Column(Text)  # 分析的OWID指标ID（逗号分隔）
    countries = Column(Text)  # 分析的国家（逗号分隔）
    time_range = Column(String(20))  # 分析时间范围（如2010-2020）
    analysis_result = Column(JSON)  # 分析结果（JSON格式，存结构化数据）
    metadata = Column(JSON)  # 元信息
    create_time = Column(DateTime, default=datetime.now, index=True)

# 为了向后兼容之前的代码，可以保留别名
WHOGlobalHealth = GlobalHealthMetric