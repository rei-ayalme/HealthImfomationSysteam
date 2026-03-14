# db/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime,Text,JSON,Boolean
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

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

class GlobalHealthMetric(Base):
    """基础平台核心表：存储国内外卫生指标"""
    __tablename__ = "global_health_metrics"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(20), index=True)      # 数据来源: 'WHO', 'Local', 'Search'
    region = Column(String(100), index=True)     # 国家代码或省份名称
    indicator = Column(String(200), index=True)  # 指标名称
    year = Column(Integer, index=True)           # 年份
    value = Column(Float)                        # 指标数值
    unit = Column(String(50))                    # 单位
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

WHOGlobalHealth = GlobalHealthMetric

class DiseaseRisk(Base):
    """疾病风险分析表"""
    __tablename__ = "disease_risks"

    id = Column(Integer, primary_key=True, index=True)
    region_name = Column(String(50), index=True)
    year = Column(Integer)
    cause = Column(String(100), comment="疾病分类")
    risk_score = Column(Float, comment="风险得分")
    intervention_suggestions = Column(String(500), comment="干预建议摘要")


class RawHealthData(Base):
    __tablename__ = "raw_health_data"
    id = Column(Integer, primary_key=True)
    upload_time = Column(DateTime, default=datetime.utcnow)
    file_name = Column(String)
    raw_content = Column(Text)  # 存储原始 JSON 或序列化的内容

class OWIDFetchLog(Base):
    __tablename__ = "owid_fetch_logs"
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
    analysis_result = Column(JSON, nullable=True, comment="分析结果数据")
    analysis_metadata = Column(JSON, nullable=True)  # 分析结果（JSON格式，存结构化数据）????
    create_time = Column(DateTime, default=datetime.now, index=True)


class AdvancedDiseaseTransition(Base):
    """问题1：疾病谱系时空变迁分析表"""
    __tablename__ = "adv_disease_transition"

    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(100), index=True, comment="国家或地区名称")
    year = Column(Integer, index=True, comment="年份")
    cause_name = Column(String(200), comment="疾病名称")
    disease_category = Column(String(50), comment="疾病大类(传染/非传染/伤害)")
    val = Column(Float, comment="疾病负担绝对值(如DALYs)")
    eti = Column(Float, comment="流行病学转型指数(ETI)")
    transition_stage = Column(String(50), comment="转型阶段(如: late_transition)")
    latitude = Column(Float, nullable=True, comment="纬度(城市规划基准)")
    longitude = Column(Float, nullable=True, comment="经度(城市规划基准)")
    urban_zone_type = Column(String(50), nullable=True, comment="城市区划: 老城区/新开发区/边缘区")
    elderly_ratio = Column(Float, nullable=True, comment="老龄化比例(弱势群体权重)")

class AdvancedRiskCloud(Base):
    """问题2：风险因素归因与云模型分析表"""
    __tablename__ = "adv_risk_cloud"

    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(100), index=True)
    year = Column(Integer, index=True)
    rei_name = Column(String(200), comment="风险因素名称(如 PM2.5, Smoking)")
    risk_category = Column(String(50), comment="风险类别(环境/行为/代谢等)")
    paf = Column(Float, comment="人群归因分数(PAF)")
    exposure_category = Column(String(50), comment="暴露等级语言变量(高/中/低)")

    # 云模型三参数 (张翔等, 2026)
    cloud_ex = Column(Float, nullable=True, comment="云模型-期望(Ex)")
    cloud_en = Column(Float, nullable=True, comment="云模型-熵(En)")
    cloud_he = Column(Float, nullable=True, comment="云模型-超熵(He)")


class AdvancedResourceEfficiency(Base):
    """问题3：卫生资源配置效率与空间可及性表"""
    __tablename__ = "adv_resource_efficiency"

    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(100), index=True)
    year = Column(Integer, index=True)

    # DEA 效率得分 (邵龙龙等, 2025; 常景双, 2019)
    dea_efficiency = Column(Float, nullable=True, comment="DEA综合技术效率(0-1)")
    resource_quadrant = Column(String(50), comment="投入产出四象限(如: 高投入_低产出)")

    # 空间可及性 (廖博玮, 2022)
    spatial_accessibility = Column(Float, nullable=True, comment="2SFCA空间可及性指数")

    # 鲁棒不确定性数据 (JSON 格式存储弹性上下界)
    robust_data = Column(JSON, nullable=True, comment="鲁棒DEA的上下界弹性数据")