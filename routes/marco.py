"""
宏观分析数据总线 (Marco Data Bus)

提供全球尺度、国家尺度和区域尺度的健康数据与地理信息接口。
包括全球风险地图、预期寿命、世界地图指标和GeoJSON数据服务。

"""

import os
import json
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from config.settings import SETTINGS  # 统一从 settings 调取配置

# 创建 APIRouter 实例
router = APIRouter(prefix="/api", tags=["marco"])


# ==================== 数据模型定义 ====================

class WorldMetricItem(BaseModel):
    """世界地图指标项模型"""
    country: str
    value: float
    indicator: str
    data_year: int
    source: str
    source_type: str
    method: str
    is_fallback: bool


class WorldMetricsResponse(BaseModel):
    """世界地图指标响应模型"""
    status: str
    region: str
    metric: str
    year: int
    data: List[WorldMetricItem]
    meta: Dict[str, Any]


class GeoJSONResponse(BaseModel):
    """
    GeoJSON 响应模型

    Attributes:
        status: 响应状态 (success/warning/error)
        path: 资源路径，从 config.settings 调取
        msg: 附加消息或错误详情
        data: 真正的 GeoJSON FeatureCollection 数据
    """
    status: str = Field(..., description="响应状态: success/warning/error")
    path: Optional[str] = Field(None, description="资源路径，从 config.settings 调取")
    msg: Optional[str] = Field(None, description="附加消息或错误详情")
    data: Optional[Dict[str, Any]] = Field(None, description="GeoJSON FeatureCollection 数据")


class LifeExpectancyFeature(BaseModel):
    """预期寿命特征数据模型"""
    type: str = "Feature"
    properties: Dict[str, Any] = Field(..., description="包含country_code和life_expectancy的属性")
    geometry: Optional[Any] = None


class GlobalLifeExpectancyResponse(BaseModel):
    """
    全球预期寿命响应模型

    Attributes:
        type: GeoJSON类型，固定为FeatureCollection
        features: 包含各国预期寿命数据的特征列表
        meta: 元数据信息
    """
    type: str = "FeatureCollection"
    features: List[Dict[str, Any]] = Field(..., description="各国预期寿命数据列表")
    meta: Dict[str, Any] = Field(default_factory=dict, description="元数据信息")


# ==================== 辅助函数 ====================

def load_geojson_data(file_path: str) -> Optional[Dict]:
    """
    统一的数据读取辅助函数
    
    Args:
        file_path: GeoJSON 文件的完整路径
        
    Returns:
        解析后的 GeoJSON 字典，文件不存在时返回 None
    """
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            # 文件存在但解析失败
            return None
    return None


def _normalize_region_candidates(region: str):
    """标准化地区候选名称"""
    region_key = (region or "").strip().lower()
    alias = {
        "global": ["global", ""],
        "china": ["China", "中国", "全国"],
        "east_asia": ["China", "中国", "Japan", "South Korea"],
        "southeast_asia": ["Singapore", "Thailand", "Indonesia", "Malaysia"],
        "europe": ["Europe", "Germany", "France", "United Kingdom"],
        "north_america": ["United States", "Canada", "Mexico"],
        "usa": ["United States", "USA", "United States of America"],
        "japan": ["Japan"],
        "india": ["India"],
        "germany": ["Germany"]
    }
    return alias.get(region_key, [region])


def _build_location_filter(model_cls, region_candidates):
    """构建地区过滤条件"""
    conditions = []
    for token in region_candidates:
        token = (token or "").strip()
        if not token:
            continue
        conditions.append(model_cls.location_name.ilike(f"%{token}%"))
    return or_(*conditions) if conditions else None


def _normalize_country_key(name: str) -> str:
    """标准化国家名称键"""
    text = (name or "").strip().lower()
    alias = {
        "united states of america": "unitedstates",
        "united states": "unitedstates",
        "usa": "unitedstates",
        "u.s.a": "unitedstates",
        "korea, republic of": "southkorea",
        "republic of korea": "southkorea",
        "south korea": "southkorea",
        "korea": "southkorea",
        "russian federation": "russia",
        "viet nam": "vietnam",
        "czechia": "czechrepublic",
        "uk": "unitedkingdom",
        "u.k.": "unitedkingdom",
        "taiwan": "china",
        "taiwan, province of china": "china",
        "taiwan (province of china)": "china"
    }
    text = alias.get(text, text)
    return "".join(ch for ch in text if ch.isalnum())


def _region_focus_countries(region: str):
    """获取区域重点关注国家列表"""
    region_key = (region or "global").strip().lower()
    return {
        "east_asia": ["China", "Japan", "South Korea", "Mongolia", "North Korea", "Taiwan"],
        "southeast_asia": ["Vietnam", "Thailand", "Indonesia", "Malaysia", "Philippines", "Singapore", "Myanmar"],
        "europe": ["France", "Germany", "United Kingdom", "Italy", "Spain", "Russia", "Ukraine", "Poland", "Switzerland"],
        "north_america": ["United States of America", "Canada", "Mexico"]
    }.get(region_key, [])


def _metric_indicator_tokens(metric: str):
    """获取指标指示词列表"""
    metric_key = (metric or "dalys").strip().lower()
    return {
        "dalys": ["daly", "dalys", "disability-adjusted life years"],
        "deaths": ["death", "mortality", "deaths"],
        "prevalence": ["prevalence", "prevalent"],
        "ylls": ["yll", "years of life lost"],
        "ylds": ["yld", "years lived with disability"]
    }.get(metric_key, [metric_key])


def _is_international_source(source: str) -> bool:
    """判断是否为国际数据源"""
    source_key = (source or "").strip().upper()
    return source_key in {"WHO", "OWID", "WB", "WORLD_BANK", "UN", "IHME", "GBD", "SEARCH"}


def _source_priority(source: str) -> int:
    """获取数据源优先级"""
    source_key = (source or "").strip().upper()
    if source_key in {"WHO", "OWID", "WB", "WORLD_BANK", "UN", "IHME", "GBD", "SEARCH"}:
        return 0
    if source_key in {"LOCAL"}:
        return 1
    return 2


def _calc_reproducible_map_fallback(country_name: str, metric: str, year: int):
    """计算可复现的回退值"""
    metric_key = (metric or "dalys").strip().lower()
    seed_text = f"{country_name}|{metric_key}|{year}"
    seed = 0
    for ch in seed_text:
        seed = ((seed << 5) - seed + ord(ch)) & 0xFFFFFFFF

    base_value_map = {
        "dalys": 62.0,
        "deaths": 54.0,
        "prevalence": 38.0,
        "ylls": 41.0,
        "ylds": 33.0
    }
    base = base_value_map.get(metric_key, 50.0)
    noise = (seed % 1000) / 1000.0
    year_factor = 1.0 + ((int(year or 2024) - 2010) * 0.004)
    value = base * year_factor * (0.78 + noise * 0.44)
    return round(max(1.0, min(value, 100.0)), 2)


def get_db():
    """获取数据库会话"""
    from db.connection import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== API 路由定义 ====================

@router.get("/map/global-risk")
async def get_global_risk_map() -> Dict[str, Any]:
    """
    获取全球风险地图数据
    
    Returns:
        全球风险地图数据
    """
    from utils.global_risk import get_global_risk_map
    return await get_global_risk_map()


@router.get(
    "/map/global-life-expectancy",
    response_model=GlobalLifeExpectancyResponse,
    summary="获取全球预期寿命数据",
    description="获取全球195个国家的预期寿命数据，用于世界地图可视化展示"
)
async def get_global_life_expectancy() -> Dict[str, Any]:
    """
    获取全球预期寿命地图数据

    返回GeoJSON格式的全球预期寿命数据，包含195个国家的预期寿命信息。
    数据基于UN 2019历史趋势外推法生成，数值范围49.2-85.4岁。

    Returns:
        GlobalLifeExpectancyResponse: GeoJSON格式的预期寿命数据
    """
    from utils.global_life_expectancy import get_global_life_expectancy
    return await get_global_life_expectancy()


@router.get("/map/china-provincial-health")
async def get_china_provincial_health() -> Dict[str, Any]:
    """
    获取中国省级健康数据
    
    Returns:
        中国各省级行政区健康指标数据
    """
    from utils.china_provincial_health import get_china_provincial_health
    return await get_china_provincial_health()


@router.get("/map/chengdu-e2sfca")
async def get_chengdu_e2sfca() -> Dict[str, Any]:
    """
    获取成都市E2SFCA空间可及性数据
    
    Returns:
        成都市医疗资源空间可及性分析数据
    """
    from utils.chengdu_e2sfca import get_chengdu_e2sfca
    return await get_chengdu_e2sfca()


@router.get("/map/world-metrics")
async def get_world_map_metrics(
    region: str = Query(default="global", description="区域名称"),
    metric: str = Query(default="dalys", description="指标类型"),
    year: int = Query(default=2024, description="目标年份"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取世界地图指标数据
    
    1) 优先返回国际来源数据（WHO/OWID/GBD等）
    2) 对分区重点国家在缺失时生成可复现回退值
    3) 返回 tooltip 所需完整元信息
    
    Args:
        region: 区域名称，如 "global", "east_asia", "europe"
        metric: 指标类型，如 "dalys", "deaths", "prevalence"
        year: 目标年份
        
    Returns:
        包含世界地图指标数据的响应
    """
    try:
        from db.models import GlobalHealthMetric
        
        region_key = (region or "global").strip().lower()
        metric_key = (metric or "dalys").strip().lower()
        target_year = int(year or 2024)

        indicator_tokens = _metric_indicator_tokens(metric_key)
        query = db.query(
            GlobalHealthMetric.region,
            GlobalHealthMetric.indicator,
            GlobalHealthMetric.year,
            GlobalHealthMetric.value,
            GlobalHealthMetric.source
        ).filter(
            GlobalHealthMetric.region.isnot(None),
            GlobalHealthMetric.value.isnot(None),
            GlobalHealthMetric.year.isnot(None),
            GlobalHealthMetric.year <= target_year,
            GlobalHealthMetric.year >= max(1990, target_year - 15)
        )
        if indicator_tokens:
            query = query.filter(or_(*[GlobalHealthMetric.indicator.ilike(f"%{token}%") for token in indicator_tokens]))

        rows = query.all()
        focus_countries = _region_focus_countries(region_key)
        focus_keys = {_normalize_country_key(name) for name in focus_countries}

        best_by_country = {}
        for row in rows:
            country_name = (row.region or "").strip()
            country_key = _normalize_country_key(country_name)
            if not country_key:
                continue
            if region_key != "global" and focus_keys and country_key not in focus_keys:
                continue

            source = (row.source or "").strip() or "UNKNOWN"
            row_year = int(row.year or target_year)
            score = (_source_priority(source), abs(target_year - row_year))

            existing = best_by_country.get(country_key)
            if existing is None or score < existing["score"]:
                best_by_country[country_key] = {
                    "score": score,
                    "country": country_name,
                    "value": round(float(row.value), 4),
                    "indicator": row.indicator or metric_key,
                    "data_year": row_year,
                    "source": source,
                    "source_type": "international" if _is_international_source(source) else "local",
                    "method": "international_priority"
                }

        if region_key != "global":
            for country in focus_countries:
                country_key = _normalize_country_key(country)
                if country_key in best_by_country:
                    continue
                fallback_value = _calc_reproducible_map_fallback(country, metric_key, target_year)
                best_by_country[country_key] = {
                    "score": (99, 99),
                    "country": country,
                    "value": fallback_value,
                    "indicator": metric_key,
                    "data_year": target_year,
                    "source": "FALLBACK",
                    "source_type": "fallback",
                    "method": "reproducible_fallback_v1"
                }

        payload = []
        for item in best_by_country.values():
            payload.append({
                "country": item["country"],
                "value": item["value"],
                "indicator": item["indicator"],
                "data_year": item["data_year"],
                "source": item["source"],
                "source_type": item["source_type"],
                "method": item["method"],
                "is_fallback": item["source_type"] == "fallback"
            })

        payload.sort(key=lambda x: x["value"], reverse=True)
        return {
            "status": "success",
            "region": region_key,
            "metric": metric_key,
            "year": target_year,
            "data": payload,
            "meta": {
                "count": len(payload),
                "fallback": "reproducible_fallback_v1",
                "priority": "international>local>fallback"
            }
        }
    except Exception as e:
        from utils.logger import logger
        logger.exception("获取世界地图指标失败")
        return {
            "status": "error",
            "region": (region or "global"),
            "metric": (metric or "dalys"),
            "year": int(year or 2024),
            "data": [],
            "msg": str(e)
        }


@router.get(
    "/geojson/world",
    response_model=GeoJSONResponse,
    summary="获取世界地图 GeoJSON",
    description="从 settings 调取路径配置，返回统一格式的 GeoJSON 响应"
)
async def get_world_geojson() -> GeoJSONResponse:
    """
    获取世界地图 GeoJSON 数据
    
    严格遵循 GeoJSONResponse 模型约束，path 字段从 settings 调取。
    前端可直接使用 response.data 渲染地图（如 ECharts）。
    
    Returns:
        GeoJSONResponse: 包含 status, path(从settings获取), msg, data
    """
    # 步骤1: 摒弃硬编码，从 settings 获取配置路径
    settings_path = getattr(SETTINGS, 'GEOJSON_PATH_WORLD', 'data/geojson/ne_10m_admin_0_countries.geojson')
    file_path = os.path.join(SETTINGS.BASE_DIR, settings_path)
    
    # 步骤2: 尝试读取并返回标准模型
    geo_data = load_geojson_data(file_path)
    if geo_data:
        return GeoJSONResponse(
            status="success",
            path=settings_path,
            msg="Loaded from configured path",
            data=geo_data  # 前端可以直接拿 response.data 去渲染 ECharts
        )
    
    # 步骤3: Fallback 兜底逻辑
    fallback_path = "data/geojson/ne_10m_admin_0_countries.geojson"
    full_fallback = os.path.join(SETTINGS.BASE_DIR, fallback_path)
    fallback_data = load_geojson_data(full_fallback)
    
    if fallback_data:
        return GeoJSONResponse(
            status="warning",
            path=fallback_path,
            msg="Primary file missing, using fallback",
            data=fallback_data
        )
        
    # 步骤4: 错误处理，严格遵守契约返回
    return GeoJSONResponse(
        status="error",
        path=settings_path,
        msg=f"GeoJSON file completely missing at: {settings_path}",
        data={"type": "FeatureCollection", "features": []}  # 至少给前端一个空结构防止崩溃
    )


@router.get(
    "/geojson/continents",
    response_model=GeoJSONResponse,
    summary="获取大洲地图 GeoJSON",
    description="从 settings 调取路径配置，返回统一格式的 GeoJSON 响应"
)
async def get_continents_geojson() -> GeoJSONResponse:
    """
    获取大洲地图 GeoJSON 数据
    
    Returns:
        GeoJSONResponse: 包含 status, path(从settings获取), msg, data
    """
    # 从 settings 调取路径配置
    settings_path = getattr(SETTINGS, 'GEOJSON_PATH_CONTINENTS', 'data/geojson/continents.geojson')
    file_path = os.path.join(SETTINGS.BASE_DIR, settings_path)
    
    # 尝试读取数据
    geo_data = load_geojson_data(file_path)
    if geo_data:
        return GeoJSONResponse(
            status="success",
            path=settings_path,
            msg="Loaded from configured path",
            data=geo_data
        )
    
    # 错误处理：返回 settings 配置路径
    return GeoJSONResponse(
        status="error",
        path=settings_path,
        msg=f"Continents GeoJSON file not found at: {settings_path}",
        data={"type": "FeatureCollection", "features": []}
    )


@router.get(
    "/geojson/china",
    response_model=GeoJSONResponse,
    summary="获取中国地图 GeoJSON",
    description="从 settings 调取路径配置，返回统一格式的 GeoJSON 响应"
)
async def get_china_geojson() -> GeoJSONResponse:
    """
    获取中国地图 GeoJSON 数据
    
    Returns:
        GeoJSONResponse: 包含 status, path(从settings获取), msg, data
    """
    # 从 settings 调取路径配置
    settings_path = getattr(SETTINGS, 'GEOJSON_PATH_CHINA', 'data/geojson/china.geojson')
    file_path = os.path.join(SETTINGS.BASE_DIR, settings_path)
    
    # 尝试主路径
    geo_data = load_geojson_data(file_path)
    if geo_data:
        return GeoJSONResponse(
            status="success",
            path=settings_path,
            msg="Loaded from configured path",
            data=geo_data
        )
    
    # Fallback 路径
    fallback_path = "data/geojson/中华人民共和国.geojson"
    full_fallback = os.path.join(SETTINGS.BASE_DIR, fallback_path)
    fallback_data = load_geojson_data(full_fallback)
    
    if fallback_data:
        return GeoJSONResponse(
            status="warning",
            path=fallback_path,
            msg="Primary file missing, using fallback",
            data=fallback_data
        )
    
    # 错误处理
    return GeoJSONResponse(
        status="error",
        path=settings_path,
        msg=f"China GeoJSON file not found at: {settings_path}",
        data={"type": "FeatureCollection", "features": []}
    )


@router.get(
    "/geojson/{region_name}",
    response_model=GeoJSONResponse,
    summary="获取指定区域地图 GeoJSON",
    description="根据前端传来的名字（world, china 等）动态查找并返回对应的 GeoJSON 数据"
)
async def get_map_geojson(region_name: str) -> GeoJSONResponse:
    """
    动态获取指定区域的 GeoJSON 地图数据
    
    根据 region_name 参数动态查找对应的 GeoJSON 文件，支持从 settings 配置
    或直接按路径查找。找不到文件时返回空结构，防止前端解析崩溃。
    
    Args:
        region_name: 区域名称，如 "world", "china", "chengdu" 等
        
    Returns:
        GeoJSONResponse: 包含 status, path, msg, data 的标准响应
    """
    # 根据前端传来的名字动态找文件
    # 优先尝试从 settings 获取配置路径（如 GEOJSON_PATH_WORLD）
    settings_attr = f'GEOJSON_PATH_{region_name.upper()}'
    settings_path = getattr(SETTINGS, settings_attr, None)
    
    # 如果没有 settings 配置，使用默认路径格式
    if settings_path is None:
        # 尝试多种可能的文件路径
        possible_paths = [
            f'data/geojson/{region_name}.geojson',
            f'data/geojson/{region_name}.json',
            f'data/geojson/countries/{region_name.upper()}.geo.json',
        ]
        # 使用第一个存在的路径，或默认使用第一个
        settings_path = possible_paths[0]
        for path in possible_paths:
            test_path = os.path.join(SETTINGS.BASE_DIR, path)
            if os.path.exists(test_path):
                settings_path = path
                break
    
    abs_path = os.path.join(SETTINGS.BASE_DIR, settings_path)
    
    # 检查文件是否存在
    if not os.path.exists(abs_path):
        # 找不到文件时，一定要返回明确的空结构，不要让前端解析崩溃
        return GeoJSONResponse(
            status="error",
            path=settings_path,
            msg=f"GeoJSON file not found for region: {region_name}",
            data={"type": "FeatureCollection", "features": []}
        )
    
    # 读取并返回 GeoJSON 数据
    geo_data = load_geojson_data(abs_path)
    if geo_data:
        return GeoJSONResponse(
            status="success",
            path=settings_path,
            msg=f"Loaded GeoJSON for region: {region_name}",
            data=geo_data
        )
    
    # 文件存在但解析失败
    return GeoJSONResponse(
        status="error",
        path=settings_path,
        msg=f"Failed to parse GeoJSON file for region: {region_name}",
        data={"type": "FeatureCollection", "features": []}
    )


@router.get("/regions")
async def get_available_regions() -> Dict[str, Any]:
    """
    获取可用的区域列表
    
    Returns:
        支持的区域列表及其描述
    """
    regions = [
        {"code": "global", "name": "全球", "description": "全球所有国家和地区"},
        {"code": "east_asia", "name": "东亚", "description": "中国、日本、韩国等地区"},
        {"code": "southeast_asia", "name": "东南亚", "description": "新加坡、泰国、印尼等地区"},
        {"code": "europe", "name": "欧洲", "description": "欧洲主要国家"},
        {"code": "north_america", "name": "北美", "description": "美国、加拿大、墨西哥"}
    ]
    
    return {
        "status": "success",
        "regions": regions
    }


@router.get("/metrics")
async def get_available_metrics() -> Dict[str, Any]:
    """
    获取可用的指标列表
    
    Returns:
        支持的指标类型列表
    """
    metrics = [
        {"code": "dalys", "name": "DALYs", "description": "伤残调整生命年", "unit": "年"},
        {"code": "deaths", "name": "死亡人数", "description": "疾病导致的死亡人数", "unit": "人"},
        {"code": "prevalence", "name": "患病率", "description": "疾病患病率", "unit": "%"},
        {"code": "ylls", "name": "YLLs", "description": "寿命损失年", "unit": "年"},
        {"code": "ylds", "name": "YLDs", "description": "残疾生活年", "unit": "年"}
    ]
    
    return {
        "status": "success",
        "metrics": metrics
    }


# ==================== 模块测试 ====================

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI

    app = FastAPI(title="Marco Data Bus Test")
    app.include_router(router)

    print("启动 Marco Data Bus 测试服务器...")
    print("访问 http://127.0.0.1:8000/docs 查看 API 文档")
    uvicorn.run(app, host="127.0.0.1", port=8000)
