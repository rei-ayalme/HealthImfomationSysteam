# db/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Dict, Any, Optional, Tuple
from db.models import (
    HealthResource, GlobalHealthMetric, AdvancedDiseaseTransition,
    AdvancedRiskCloud, AdvancedResourceEfficiency, OWIDFetchLog
)
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


# ==========================================
# 数据集详情查询函数
# ==========================================

class DatasetDetailResult:
    """数据集详情查询结果类"""
    def __init__(self):
        self.title: str = ""
        self.category: str = ""
        self.record_count: int = 0
        self.region_coverage: int = 0
        self.year_min: Optional[int] = None
        self.year_max: Optional[int] = None
        self.latest_updated: str = ""
        self.fields: List[Dict[str, str]] = []
        self.preview: List[Dict[str, Any]] = []


def get_disease_dataset_detail(db: Session, dataset_id: str, limit: int = 50) -> DatasetDetailResult:
    """
    获取疾病负担数据集详情
    
    Args:
        db: 数据库会话
        dataset_id: 数据集ID，格式如 "disease_123" 或 "disease_default"
        limit: 预览数据条数限制
    
    Returns:
        DatasetDetailResult: 数据集详情结果
    """
    result = DatasetDetailResult()
    
    # 解析 dataset_id，提取具体 ID 或类型
    # 格式: disease_<id>，如 disease_1, disease_default 等
    parts = dataset_id.split("_")
    specific_id = parts[1] if len(parts) > 1 else None
    
    # 基础查询
    base_query = db.query(AdvancedDiseaseTransition)
    
    # 如果指定了具体 ID 且不是 default，尝试获取该特定记录用于筛选
    if specific_id and specific_id != "default" and specific_id.isdigit():
        specific_record = base_query.filter(
            AdvancedDiseaseTransition.id == int(specific_id)
        ).first()
        if specific_record and specific_record.cause_name:
            # 按疾病名称筛选相关数据
            base_query = base_query.filter(
                AdvancedDiseaseTransition.cause_name == specific_record.cause_name
            )
            result.title = f"{specific_record.cause_name} 疾病负担数据"
        else:
            result.title = "疾病负担数据"
    else:
        result.title = "全球疾病负担数据 (GBD)"
    
    result.category = "疾病负担数据"
    
    # 获取统计数据
    stats = db.query(
        func.count(AdvancedDiseaseTransition.id).label("count"),
        func.count(func.distinct(AdvancedDiseaseTransition.location_name)).label("regions"),
        func.min(AdvancedDiseaseTransition.year).label("year_min"),
        func.max(AdvancedDiseaseTransition.year).label("year_max"),
        func.max(AdvancedDiseaseTransition.updated_at).label("latest_updated")
    ).first()
    
    result.record_count = stats.count if stats else 0
    result.region_coverage = stats.regions if stats else 0
    result.year_min = stats.year_min
    result.year_max = stats.year_max
    result.latest_updated = stats.latest_updated.strftime("%Y-%m-%d") if stats and stats.latest_updated else "2024-01-01"
    
    # 定义字段结构
    result.fields = [
        {"name": "region", "type": "string", "description": "国家/地区名称"},
        {"name": "year", "type": "int", "description": "数据年份"},
        {"name": "metric", "type": "string", "description": "疾病名称/指标"},
        {"name": "value", "type": "float", "description": "DALYs 数值（伤残调整寿命年）"},
        {"name": "source", "type": "string", "description": "数据来源（GBD 2019/2021）"},
        {"name": "disease_category", "type": "string", "description": "疾病大类（传染/非传染/伤害）"},
        {"name": "eti", "type": "float", "description": "流行病学转型指数"},
        {"name": "transition_stage", "type": "string", "description": "转型阶段"}
    ]
    
    # 获取预览数据
    records = base_query.limit(limit).all()
    for r in records:
        result.preview.append({
            "region": r.location_name or "未知",
            "year": r.year,
            "metric": r.cause_name or "未知疾病",
            "value": round(float(r.val), 4) if r.val is not None else None,
            "source": "GBD 2019",
            "disease_category": r.disease_category or "-",
            "eti": round(float(r.eti), 4) if r.eti is not None else None,
            "transition_stage": r.transition_stage or "-"
        })
    
    return result


def get_risk_dataset_detail(db: Session, dataset_id: str, limit: int = 50) -> DatasetDetailResult:
    """
    获取风险因素数据集详情
    
    Args:
        db: 数据库会话
        dataset_id: 数据集ID，格式如 "risk_123" 或 "risk_default"
        limit: 预览数据条数限制
    
    Returns:
        DatasetDetailResult: 数据集详情结果
    """
    result = DatasetDetailResult()
    
    parts = dataset_id.split("_")
    specific_id = parts[1] if len(parts) > 1 else None
    
    base_query = db.query(AdvancedRiskCloud)
    
    if specific_id and specific_id != "default" and specific_id.isdigit():
        specific_record = base_query.filter(
            AdvancedRiskCloud.id == int(specific_id)
        ).first()
        if specific_record and specific_record.rei_name:
            base_query = base_query.filter(
                AdvancedRiskCloud.rei_name == specific_record.rei_name
            )
            result.title = f"{specific_record.rei_name} 风险因素数据"
        else:
            result.title = "健康风险因素数据"
    else:
        result.title = "健康风险因素归因数据"
    
    result.category = "风险因素数据"
    
    # 获取统计数据
    stats = db.query(
        func.count(AdvancedRiskCloud.id).label("count"),
        func.count(func.distinct(AdvancedRiskCloud.location_name)).label("regions"),
        func.min(AdvancedRiskCloud.year).label("year_min"),
        func.max(AdvancedRiskCloud.year).label("year_max"),
        func.max(AdvancedRiskCloud.updated_at).label("latest_updated")
    ).first()
    
    result.record_count = stats.count if stats else 0
    result.region_coverage = stats.regions if stats else 0
    result.year_min = stats.year_min
    result.year_max = stats.year_max
    result.latest_updated = stats.latest_updated.strftime("%Y-%m-%d") if stats and stats.latest_updated else "2024-01-01"
    
    # 定义字段结构
    result.fields = [
        {"name": "region", "type": "string", "description": "国家/地区名称"},
        {"name": "year", "type": "int", "description": "数据年份"},
        {"name": "metric", "type": "string", "description": "风险因素名称"},
        {"name": "value", "type": "float", "description": "人群归因分数 (PAF)"},
        {"name": "source", "type": "string", "description": "数据来源（GBD 2019/2021）"},
        {"name": "risk_category", "type": "string", "description": "风险类别（环境/行为/代谢等）"},
        {"name": "exposure_category", "type": "string", "description": "暴露等级（高/中/低）"},
        {"name": "cloud_ex", "type": "float", "description": "云模型-期望(Ex)"},
        {"name": "cloud_en", "type": "float", "description": "云模型-熵(En)"},
        {"name": "cloud_he", "type": "float", "description": "云模型-超熵(He)"}
    ]
    
    # 获取预览数据
    records = base_query.limit(limit).all()
    for r in records:
        result.preview.append({
            "region": r.location_name or "未知",
            "year": r.year,
            "metric": r.rei_name or "未知风险",
            "value": round(float(r.paf), 4) if r.paf is not None else None,
            "source": "GBD 2019",
            "risk_category": r.risk_category or "-",
            "exposure_category": r.exposure_category or "-",
            "cloud_ex": round(float(r.cloud_ex), 4) if r.cloud_ex is not None else None,
            "cloud_en": round(float(r.cloud_en), 4) if r.cloud_en is not None else None,
            "cloud_he": round(float(r.cloud_he), 4) if r.cloud_he is not None else None
        })
    
    return result


def get_resource_dataset_detail(db: Session, dataset_id: str, limit: int = 50) -> DatasetDetailResult:
    """
    获取卫生资源效率数据集详情
    
    Args:
        db: 数据库会话
        dataset_id: 数据集ID，格式如 "resource_123" 或 "resource_default"
        limit: 预览数据条数限制
    
    Returns:
        DatasetDetailResult: 数据集详情结果
    """
    result = DatasetDetailResult()
    
    parts = dataset_id.split("_")
    specific_id = parts[1] if len(parts) > 1 else None
    
    # 区分 fallback 类型和正常 resource 类型
    is_fallback = "fallback" in dataset_id
    
    if is_fallback:
        # 使用 HealthResource 表作为回退数据
        base_query = db.query(HealthResource)
        result.title = "卫生资源配置综合数据"
        result.category = "卫生资源数据"
        
        # 获取统计数据
        stats = db.query(
            func.count(HealthResource.id).label("count"),
            func.count(func.distinct(HealthResource.region)).label("regions"),
            func.min(HealthResource.year).label("year_min"),
            func.max(HealthResource.year).label("year_max"),
            func.max(HealthResource.updated_at).label("latest_updated")
        ).first()
        
        result.record_count = stats.count if stats else 0
        result.region_coverage = stats.regions if stats else 0
        result.year_min = stats.year_min
        result.year_max = stats.year_max
        result.latest_updated = stats.latest_updated.strftime("%Y-%m-%d") if stats and stats.latest_updated else "2024-01-01"
        
        # 定义字段结构
        result.fields = [
            {"name": "region", "type": "string", "description": "省份/地区名称"},
            {"name": "year", "type": "int", "description": "数据年份"},
            {"name": "metric", "type": "string", "description": "资源指标类型"},
            {"name": "value", "type": "float", "description": "指标数值"},
            {"name": "source", "type": "string", "description": "数据来源（WHO/Local）"},
            {"name": "physicians_per_1000", "type": "float", "description": "每千人口执业(助理)医师数"},
            {"name": "nurses_per_1000", "type": "float", "description": "每千人口注册护士数"},
            {"name": "hospital_beds_per_1000", "type": "float", "description": "每千人口医疗卫生机构床位数"},
            {"name": "population", "type": "float", "description": "总人口(万人)"},
            {"name": "gap_ratio", "type": "float", "description": "资源缺口率"},
            {"name": "gap_severity", "type": "string", "description": "缺口严重程度"}
        ]
        
        # 获取预览数据
        records = base_query.limit(limit).all()
        for r in records:
            result.preview.append({
                "region": r.region or "未知",
                "year": r.year,
                "metric": "卫生资源配置",
                "value": round(float(r.gap_ratio), 4) if r.gap_ratio is not None else 0.0,
                "source": r.source or "Local",
                "physicians_per_1000": round(float(r.physicians_per_1000), 4) if r.physicians_per_1000 else 0.0,
                "nurses_per_1000": round(float(r.nurses_per_1000), 4) if r.nurses_per_1000 else 0.0,
                "hospital_beds_per_1000": round(float(r.hospital_beds_per_1000), 4) if r.hospital_beds_per_1000 else 0.0,
                "population": round(float(r.population), 2) if r.population else 0.0,
                "gap_ratio": round(float(r.gap_ratio), 4) if r.gap_ratio else 0.0,
                "gap_severity": r.gap_severity or "未知"
            })
    else:
        # 使用 AdvancedResourceEfficiency 表
        base_query = db.query(AdvancedResourceEfficiency)
        
        if specific_id and specific_id != "default" and specific_id.isdigit():
            specific_record = base_query.filter(
                AdvancedResourceEfficiency.id == int(specific_id)
            ).first()
            if specific_record and specific_record.location_name:
                base_query = base_query.filter(
                    AdvancedResourceEfficiency.location_name == specific_record.location_name
                )
                result.title = f"{specific_record.location_name} 卫生资源效率数据"
            else:
                result.title = "卫生资源效率数据"
        else:
            result.title = "卫生资源配置效率分析数据"
        
        result.category = "卫生资源数据"
        
        # 获取统计数据
        stats = db.query(
            func.count(AdvancedResourceEfficiency.id).label("count"),
            func.count(func.distinct(AdvancedResourceEfficiency.location_name)).label("regions"),
            func.min(AdvancedResourceEfficiency.year).label("year_min"),
            func.max(AdvancedResourceEfficiency.year).label("year_max"),
            func.max(AdvancedResourceEfficiency.updated_at).label("latest_updated")
        ).first()
        
        result.record_count = stats.count if stats else 0
        result.region_coverage = stats.regions if stats else 0
        result.year_min = stats.year_min
        result.year_max = stats.year_max
        result.latest_updated = stats.latest_updated.strftime("%Y-%m-%d") if stats and stats.latest_updated else "2024-01-01"
        
        # 定义字段结构
        result.fields = [
            {"name": "region", "type": "string", "description": "国家/地区名称"},
            {"name": "year", "type": "int", "description": "数据年份"},
            {"name": "metric", "type": "string", "description": "效率指标类型"},
            {"name": "value", "type": "float", "description": "DEA 综合技术效率(0-1)"},
            {"name": "source", "type": "string", "description": "数据来源（WDI/Local）"},
            {"name": "resource_quadrant", "type": "string", "description": "投入产出四象限分类"},
            {"name": "spatial_accessibility", "type": "float", "description": "2SFCA空间可及性指数"},
            {"name": "robust_data", "type": "json", "description": "鲁棒DEA弹性上下界数据"}
        ]
        
        # 获取预览数据
        records = base_query.limit(limit).all()
        for r in records:
            result.preview.append({
                "region": r.location_name or "未知",
                "year": r.year,
                "metric": "DEA 效率",
                "value": round(float(r.dea_efficiency), 4) if r.dea_efficiency is not None else None,
                "source": "WDI / Local",
                "resource_quadrant": r.resource_quadrant or "-",
                "spatial_accessibility": round(float(r.spatial_accessibility), 4) if r.spatial_accessibility is not None else None,
                "robust_data": r.robust_data if r.robust_data else None
            })
    
    return result


def get_global_overview_dataset_detail(db: Session, dataset_id: str, limit: int = 50) -> DatasetDetailResult:
    """
    获取全球健康总览数据集详情
    
    Args:
        db: 数据库会话
        dataset_id: 数据集ID
        limit: 预览数据条数限制
    
    Returns:
        DatasetDetailResult: 数据集详情结果
    """
    result = DatasetDetailResult()
    result.title = "全球健康指标总览数据"
    result.category = "全球健康数据"
    
    # 使用 GlobalHealthMetric 表
    base_query = db.query(GlobalHealthMetric)
    
    # 获取统计数据
    stats = db.query(
        func.count(GlobalHealthMetric.id).label("count"),
        func.count(func.distinct(GlobalHealthMetric.region)).label("regions"),
        func.min(GlobalHealthMetric.year).label("year_min"),
        func.max(GlobalHealthMetric.year).label("year_max"),
        func.max(GlobalHealthMetric.updated_at).label("latest_updated")
    ).first()
    
    result.record_count = stats.count if stats else 0
    result.region_coverage = stats.regions if stats else 0
    result.year_min = stats.year_min
    result.year_max = stats.year_max
    result.latest_updated = stats.latest_updated.strftime("%Y-%m-%d") if stats and stats.latest_updated else "2024-01-01"
    
    # 定义字段结构
    result.fields = [
        {"name": "region", "type": "string", "description": "国家/地区名称"},
        {"name": "year", "type": "int", "description": "数据年份"},
        {"name": "metric", "type": "string", "description": "健康指标名称"},
        {"name": "value", "type": "float", "description": "指标数值"},
        {"name": "source", "type": "string", "description": "数据来源（WHO/OWID/Local）"},
        {"name": "unit", "type": "string", "description": "计量单位"}
    ]
    
    # 获取预览数据
    records = base_query.limit(limit).all()
    for r in records:
        result.preview.append({
            "region": r.region or "未知",
            "year": r.year,
            "metric": r.indicator or "未知指标",
            "value": round(float(r.value), 4) if r.value is not None else None,
            "source": r.source or "Unknown",
            "unit": r.unit or "-"
        })
    
    return result


def get_empty_dataset_detail(dataset_id: str) -> DatasetDetailResult:
    """
    获取空数据集详情（当数据库中没有对应数据时使用）
    
    Args:
        dataset_id: 数据集ID
    
    Returns:
        DatasetDetailResult: 空数据集详情结果
    """
    result = DatasetDetailResult()
    result.title = f"数据集：{dataset_id}"
    result.category = "健康指标"
    result.record_count = 0
    result.region_coverage = 0
    result.year_min = None
    result.year_max = None
    result.latest_updated = "2024-01-01"
    result.fields = [
        {"name": "region", "type": "string", "description": "国家/地区"},
        {"name": "year", "type": "int", "description": "年份"},
        {"name": "metric", "type": "string", "description": "指标名称"},
        {"name": "value", "type": "float", "description": "数值"},
        {"name": "source", "type": "string", "description": "数据来源"}
    ]
    result.preview = []
    return result
