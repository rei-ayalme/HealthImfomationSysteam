"""
Dataset API Routes
数据集管理 API 路由模块

提供数据集列表获取和详情查询功能，包括：
- 疾病负担数据
- 风险因素数据
- 卫生资源效率数据
- 全球健康总览数据
- 干预措施数据
- 人口统计数据
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from db.connection import SessionLocal
from db.models import (
    GlobalHealthMetric, HealthResource,
    AdvancedDiseaseTransition, AdvancedRiskCloud, AdvancedResourceEfficiency
)
from utils.logger import logger


# ============ Pydantic Models ============

class DatasetItem(BaseModel):
    """数据集列表项模型"""
    id: str
    name: str
    type: str
    typeName: str
    topic: str
    topicName: str
    country: str
    year: int
    value: float
    unit: str
    z_weight: Optional[float] = None
    status: str


class DatasetField(BaseModel):
    """数据集字段定义"""
    name: str
    type: str
    description: str


class DatasetInfo(BaseModel):
    """数据集详细信息"""
    title: str
    category: str
    record_count: int
    region_coverage: int
    year_min: int
    year_max: int
    latest_updated: str
    fields: List[DatasetField]


class PreviewData(BaseModel):
    """预览数据项"""
    region: str
    year: int
    metric: str
    value: float
    source: str


class DatasetDetailResponse(BaseModel):
    """数据集详情响应"""
    status: str
    dataset: DatasetInfo
    preview: List[dict]
    msg: Optional[str] = None


class DatasetListResponse(BaseModel):
    """数据集列表响应"""
    items: List[DatasetItem]


# ============ Database Dependency ============

def get_db():
    """数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============ Router Definition ============

router = APIRouter(prefix="/api", tags=["dataset"])


# ============ Helper Functions ============

class DatasetDetailResult:
    """数据集详情结果容器"""
    def __init__(self):
        self.title = ""
        self.category = ""
        self.record_count = 0
        self.region_coverage = 0
        self.year_min = None
        self.year_max = None
        self.latest_updated = ""
        self.fields = []
        self.preview = []


def get_empty_dataset_detail(dataset_id: str) -> DatasetDetailResult:
    """获取空数据集详情结构"""
    result = DatasetDetailResult()
    result.title = f"数据集：{dataset_id}"
    result.category = "未知"
    result.record_count = 0
    result.region_coverage = 0
    result.year_min = 2000
    result.year_max = 2024
    result.latest_updated = datetime.now().strftime("%Y-%m-%d")
    result.fields = [
        {"name": "region", "type": "string", "description": "国家/地区"},
        {"name": "year", "type": "int", "description": "年份"},
        {"name": "metric", "type": "string", "description": "指标名称"},
        {"name": "value", "type": "float", "description": "数值"},
        {"name": "source", "type": "string", "description": "数据来源"}
    ]
    result.preview = []
    return result


def get_disease_dataset_detail(db: Session, dataset_id: str, limit: int = 50) -> DatasetDetailResult:
    """获取疾病负担数据集详情"""
    result = DatasetDetailResult()
    result.title = "疾病负担与流行病学数据"
    result.category = "疾病谱系数据"
    
    # 从数据库查询疾病数据
    try:
        query = db.query(AdvancedDiseaseTransition)
        data = query.limit(limit).all()
        
        if data:
            years = [d.year for d in data if d.year]
            regions = set([d.location_name for d in data if d.location_name])
            
            result.record_count = len(data)
            result.region_coverage = len(regions)
            result.year_min = min(years) if years else 2000
            result.year_max = max(years) if years else 2024
            result.latest_updated = datetime.now().strftime("%Y-%m-%d")
            
            result.fields = [
                {"name": "cause_name", "type": "string", "description": "疾病名称"},
                {"name": "location_name", "type": "string", "description": "地区"},
                {"name": "year", "type": "int", "description": "年份"},
                {"name": "val", "type": "float", "description": "DALYs值"},
                {"name": "source", "type": "string", "description": "数据来源"}
            ]
            
            result.preview = [
                {
                    "region": d.location_name,
                    "year": d.year,
                    "metric": d.cause_name,
                    "value": float(d.val) if d.val else 0,
                    "source": "GBD"
                }
                for d in data[:limit]
            ]
    except Exception as e:
        logger.error(f"查询疾病数据失败: {e}")
    
    return result


def get_risk_dataset_detail(db: Session, dataset_id: str, limit: int = 50) -> DatasetDetailResult:
    """获取风险因素数据集详情"""
    result = DatasetDetailResult()
    result.title = "风险因素归因数据"
    result.category = "风险因素数据"
    
    try:
        query = db.query(AdvancedRiskCloud)
        data = query.limit(limit).all()
        
        if data:
            years = [d.year for d in data if d.year]
            regions = set([d.location_name for d in data if d.location_name])
            
            result.record_count = len(data)
            result.region_coverage = len(regions)
            result.year_min = min(years) if years else 2000
            result.year_max = max(years) if years else 2024
            result.latest_updated = datetime.now().strftime("%Y-%m-%d")
            
            result.fields = [
                {"name": "rei_name", "type": "string", "description": "风险因素名称"},
                {"name": "location_name", "type": "string", "description": "地区"},
                {"name": "year", "type": "int", "description": "年份"},
                {"name": "paf", "type": "float", "description": "人群归因分数"},
                {"name": "source", "type": "string", "description": "数据来源"}
            ]
            
            result.preview = [
                {
                    "region": d.location_name,
                    "year": d.year,
                    "metric": d.rei_name,
                    "value": float(d.paf) if d.paf else 0,
                    "source": "GBD"
                }
                for d in data[:limit]
            ]
    except Exception as e:
        logger.error(f"查询风险数据失败: {e}")
    
    return result


def get_resource_dataset_detail(db: Session, dataset_id: str, limit: int = 50) -> DatasetDetailResult:
    """获取卫生资源数据集详情"""
    result = DatasetDetailResult()
    result.title = "卫生资源效率数据"
    result.category = "资源效率数据"
    
    try:
        # 根据 dataset_id 决定查询哪个表
        if "fallback" in dataset_id:
            query = db.query(HealthResource)
        else:
            query = db.query(AdvancedResourceEfficiency)
        
        data = query.limit(limit).all()
        
        if data:
            if "fallback" in dataset_id:
                years = [d.year for d in data if hasattr(d, 'year') and d.year]
                regions = set([d.region for d in data if hasattr(d, 'region') and d.region])
                
                result.record_count = len(data)
                result.region_coverage = len(regions)
                result.year_min = min(years) if years else 2000
                result.year_max = max(years) if years else 2024
                
                result.fields = [
                    {"name": "region", "type": "string", "description": "地区"},
                    {"name": "year", "type": "int", "description": "年份"},
                    {"name": "beds_per_1000", "type": "float", "description": "每千人床位数"},
                    {"name": "gap_ratio", "type": "float", "description": "资源缺口率"}
                ]
                
                result.preview = [
                    {
                        "region": d.region,
                        "year": d.year,
                        "metric": "卫生资源综合指标",
                        "value": float(d.gap_ratio) if hasattr(d, 'gap_ratio') and d.gap_ratio else 0,
                        "source": "Health Resource"
                    }
                    for d in data[:limit]
                ]
            else:
                years = [d.year for d in data if hasattr(d, 'year') and d.year]
                regions = set([d.location_name for d in data if hasattr(d, 'location_name') and d.location_name])
                
                result.record_count = len(data)
                result.region_coverage = len(regions)
                result.year_min = min(years) if years else 2000
                result.year_max = max(years) if years else 2024
                
                result.fields = [
                    {"name": "location_name", "type": "string", "description": "地区"},
                    {"name": "year", "type": "int", "description": "年份"},
                    {"name": "dea_efficiency", "type": "float", "description": "DEA效率值"}
                ]
                
                result.preview = [
                    {
                        "region": d.location_name,
                        "year": d.year,
                        "metric": "DEA效率",
                        "value": float(d.dea_efficiency) if hasattr(d, 'dea_efficiency') and d.dea_efficiency else 0,
                        "source": "DEA Analysis"
                    }
                    for d in data[:limit]
                ]
            
            result.latest_updated = datetime.now().strftime("%Y-%m-%d")
    except Exception as e:
        logger.error(f"查询资源数据失败: {e}")
    
    return result


def get_global_overview_dataset_detail(db: Session, dataset_id: str, limit: int = 50) -> DatasetDetailResult:
    """获取全球健康总览数据集详情"""
    result = DatasetDetailResult()
    result.title = "全球健康指标总览"
    result.category = "全球健康数据"
    
    try:
        query = db.query(GlobalHealthMetric)
        data = query.limit(limit).all()
        
        if data:
            years = [d.year for d in data if hasattr(d, 'year') and d.year]
            regions = set([d.country for d in data if hasattr(d, 'country') and d.country])
            
            result.record_count = len(data)
            result.region_coverage = len(regions)
            result.year_min = min(years) if years else 2000
            result.year_max = max(years) if years else 2024
            result.latest_updated = datetime.now().strftime("%Y-%m-%d")
            
            result.fields = [
                {"name": "country", "type": "string", "description": "国家/地区"},
                {"name": "year", "type": "int", "description": "年份"},
                {"name": "indicator", "type": "string", "description": "指标名称"},
                {"name": "value", "type": "float", "description": "指标值"}
            ]
            
            result.preview = [
                {
                    "region": d.country,
                    "year": d.year,
                    "metric": d.indicator if hasattr(d, 'indicator') else "综合指标",
                    "value": float(d.value) if hasattr(d, 'value') and d.value else 0,
                    "source": "Global Health"
                }
                for d in data[:limit]
            ]
    except Exception as e:
        logger.error(f"查询全球数据失败: {e}")
    
    return result


# ============ API Endpoints ============

@router.get("/dataset", response_model=DatasetListResponse)
async def get_dataset(limit: int = Query(60, ge=1, le=1000), db: Session = Depends(get_db)):
    """
    获取数据集列表 API
    
    返回所有可用的数据集列表，包括疾病负担、风险因素、卫生资源效率等类型。
    每种类型至少返回一个代表性数据集。
    
    Args:
        limit: 返回的最大数据集数量 (1-1000)
        db: 数据库会话
    
    Returns:
        DatasetListResponse: 包含数据集列表的响应
    """
    try:
        items = []
        
        # 1. 获取疾病负担数据
        disease_data = db.query(AdvancedDiseaseTransition).limit(max(20, limit)).all()
        max_dalys = max([d.val for d in disease_data]) if disease_data else 1.0
        if max_dalys == 0:
            max_dalys = 1.0
        
        for i, d in enumerate(disease_data):
            z_weight = round(0.1 + 0.9 * (d.val / max_dalys), 4)
            items.append(DatasetItem(
                id=f"disease_{d.id}",
                name=f"{d.cause_name} 疾病负担",
                type="disease_burden",
                typeName="疾病谱系",
                topic="health-indicators",
                topicName="健康指标分析",
                country=d.location_name,
                year=d.year,
                value=d.val,
                unit="DALYs",
                z_weight=z_weight,
                status="success"
            ))
        
        # 2. 获取风险归因数据
        risk_data = db.query(AdvancedRiskCloud).limit(max(20, limit)).all()
        for i, r in enumerate(risk_data):
            items.append(DatasetItem(
                id=f"risk_{r.id}",
                name=f"{r.rei_name} 风险归因",
                type="risk_factor",
                typeName="风险因素",
                topic="health-indicators",
                topicName="健康指标分析",
                country=r.location_name,
                year=r.year,
                value=r.paf,
                unit="PAF",
                status="success"
            ))
        
        # 3. 获取卫生资源效率数据
        resource_data = db.query(AdvancedResourceEfficiency).limit(max(20, limit)).all()
        for i, r in enumerate(resource_data):
            items.append(DatasetItem(
                id=f"resource_{r.id}",
                name="卫生资源 DEA 效率",
                type="resource_efficiency",
                typeName="资源效率",
                topic="health-indicators",
                topicName="健康指标分析",
                country=r.location_name,
                year=r.year,
                value=r.dea_efficiency if r.dea_efficiency else 0,
                unit="指数",
                status="success"
            ))

        # 4. 兜底数据 - 当数据库查询结果为空时
        if not items:
            fallback_rows = db.query(HealthResource).order_by(HealthResource.year.desc()).limit(max(20, limit)).all()
            for row in fallback_rows:
                items.append(DatasetItem(
                    id=f"resource_fallback_{row.id}",
                    name="卫生资源综合指标",
                    type="resource_efficiency",
                    typeName="资源效率",
                    topic="health-indicators",
                    topicName="健康指标分析",
                    country=row.region,
                    year=row.year,
                    value=float(row.gap_ratio if row.gap_ratio is not None else 0),
                    unit="缺口率",
                    status="success"
                ))

        # 5. 确保核心类别都有数据
        categories_existing = {item.type for item in items}
        
        if "global_overview" not in categories_existing:
            items.append(DatasetItem(
                id="global_overview_default",
                name="全球健康总览",
                type="global_overview",
                typeName="全球健康数据",
                topic="health-indicators",
                topicName="健康指标分析",
                country="Global",
                year=2024,
                value=1.0,
                unit="指数",
                status="success"
            ))
        
        if "intervention_policy" not in categories_existing:
            items.append(DatasetItem(
                id="intervention_policy_default",
                name="干预措施评估",
                type="intervention_policy",
                typeName="干预措施数据",
                topic="health-indicators",
                topicName="健康指标分析",
                country="China",
                year=2024,
                value=0.76,
                unit="有效率",
                status="success"
            ))
        
        if "risk_factor" not in categories_existing:
            items.append(DatasetItem(
                id="risk_factor_default",
                name="风险因素总览",
                type="risk_factor",
                typeName="风险因素数据",
                topic="health-indicators",
                topicName="健康指标分析",
                country="China",
                year=2024,
                value=0.25,
                unit="PAF",
                status="success"
            ))
        
        if "demographic_stats" not in categories_existing:
            items.append(DatasetItem(
                id="demographic_stats_default",
                name="人口统计结构",
                type="demographic_stats",
                typeName="人口统计数据",
                topic="health-indicators",
                topicName="健康指标分析",
                country="China",
                year=2024,
                value=0.187,
                unit="占比",
                status="success"
            ))

        # 6. 按优先级排序和限制数量
        final_limit = max(1, limit)
        priority_types = [
            "global_overview",
            "disease_burden",
            "risk_factor",
            "intervention_policy",
            "demographic_stats",
            "resource_efficiency"
        ]
        selected = []
        selected_ids = set()

        for p_type in priority_types:
            candidate = next((item for item in items if item.type == p_type and item.id not in selected_ids), None)
            if candidate and len(selected) < final_limit:
                selected.append(candidate)
                selected_ids.add(candidate.id)

        for item in items:
            if len(selected) >= final_limit:
                break
            if item.id in selected_ids:
                continue
            selected.append(item)
            selected_ids.add(item.id)

        return DatasetListResponse(items=selected)
        
    except Exception as e:
        logger.exception("数据库查询异常")
        return DatasetListResponse(items=[])


@router.get("/dataset/{dataset_id}/detail")
async def get_dataset_detail(
    dataset_id: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    获取数据集详情 API
    
    根据数据集 ID 返回详细的数据集信息，包括元数据、字段定义和数据预览。
    支持的数据集类型：
    - disease_*: 疾病负担数据
    - risk_*: 风险因素数据
    - resource_*: 卫生资源数据
    - global_overview*: 全球健康总览
    - intervention_*: 干预措施数据
    - demographic_*: 人口统计数据
    
    Args:
        dataset_id: 数据集唯一标识符
        limit: 预览数据条数限制 (1-100)
        db: 数据库会话
    
    Returns:
        包含数据集详情和预览数据的响应
    """
    try:
        # 检查数据库表是否存在
        inspector = inspect(db.bind)
        
        # 根据 dataset_id 前缀路由到不同的查询函数
        if dataset_id.startswith("disease_"):
            if inspector.has_table("adv_disease_transition"):
                result = get_disease_dataset_detail(db, dataset_id, limit)
            else:
                result = get_empty_dataset_detail(dataset_id)
                result.title = "疾病负担数据（表不存在）"
                
        elif dataset_id.startswith("risk_"):
            if inspector.has_table("adv_risk_cloud"):
                result = get_risk_dataset_detail(db, dataset_id, limit)
            else:
                result = get_empty_dataset_detail(dataset_id)
                result.title = "风险因素数据（表不存在）"
                
        elif dataset_id.startswith("resource_"):
            # resource_ 可能对应多个表：AdvancedResourceEfficiency 或 HealthResource（fallback）
            if "fallback" in dataset_id:
                if inspector.has_table("health_resources"):
                    result = get_resource_dataset_detail(db, dataset_id, limit)
                else:
                    result = get_empty_dataset_detail(dataset_id)
                    result.title = "卫生资源数据（表不存在）"
            else:
                if inspector.has_table("adv_resource_efficiency"):
                    result = get_resource_dataset_detail(db, dataset_id, limit)
                else:
                    result = get_empty_dataset_detail(dataset_id)
                    result.title = "卫生资源效率数据（表不存在）"
                    
        elif dataset_id.startswith("global_overview"):
            if inspector.has_table("global_health_metrics"):
                result = get_global_overview_dataset_detail(db, dataset_id, limit)
            else:
                result = get_empty_dataset_detail(dataset_id)
                result.title = "全球健康总览数据（表不存在）"
                
        elif dataset_id.startswith("intervention_"):
            # 干预措施数据 - 目前使用疾病负担表作为替代
            if inspector.has_table("adv_disease_transition"):
                result = get_disease_dataset_detail(db, dataset_id, limit)
                result.title = "干预措施评估数据"
                result.category = "干预措施数据"
            else:
                result = get_empty_dataset_detail(dataset_id)
                result.title = "干预措施数据（表不存在）"
                
        elif dataset_id.startswith("demographic_"):
            # 人口统计数据 - 使用卫生资源表
            if inspector.has_table("health_resources"):
                result = get_resource_dataset_detail(db, "resource_fallback_0", limit)
                result.title = "人口统计与健康指标数据"
                result.category = "人口统计数据"
            else:
                result = get_empty_dataset_detail(dataset_id)
                result.title = "人口统计数据（表不存在）"
        else:
            # 未知的数据集类型，返回空结构
            result = get_empty_dataset_detail(dataset_id)
            result.title = f"未知数据集：{dataset_id}"
        
        # 构造返回结果
        # 如果数据库中没有数据，返回友好的空结构
        if result.record_count == 0 and not result.preview:
            return {
                "status": "success",
                "dataset": {
                    "title": result.title,
                    "category": result.category,
                    "record_count": 0,
                    "region_coverage": 0,
                    "year_min": result.year_min or 2000,
                    "year_max": result.year_max or 2024,
                    "latest_updated": result.latest_updated,
                    "fields": result.fields
                },
                "preview": [],
                "msg": "该数据集暂无数据记录"
            }
        
        return {
            "status": "success",
            "dataset": {
                "title": result.title,
                "category": result.category,
                "record_count": result.record_count,
                "region_coverage": result.region_coverage,
                "year_min": result.year_min or 2000,
                "year_max": result.year_max or 2024,
                "latest_updated": result.latest_updated,
                "fields": result.fields
            },
            "preview": result.preview
        }
        
    except Exception as e:
        logger.exception(f"获取数据集详情失败: dataset_id={dataset_id}, error={e}")
        
        # 返回友好的错误响应，而不是让前端脚本报错
        return {
            "status": "error",
            "msg": f"获取数据集详情失败: {str(e)}",
            "dataset": {
                "title": f"数据集：{dataset_id}",
                "category": "未知",
                "record_count": 0,
                "region_coverage": 0,
                "year_min": 2000,
                "year_max": 2024,
                "latest_updated": "2024-01-01",
                "fields": [
                    {"name": "region", "type": "string", "description": "国家/地区"},
                    {"name": "year", "type": "int", "description": "年份"},
                    {"name": "metric", "type": "string", "description": "指标名称"},
                    {"name": "value", "type": "float", "description": "数值"},
                    {"name": "source", "type": "string", "description": "数据来源"}
                ]
            },
            "preview": []
        }
