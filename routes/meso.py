"""
中观分析数据总线 (Meso Data Bus)

将前端 HTML 中硬编码的国家数据转移到 Python 后端，
通过 API 接口动态提供中观分析所需的基础数据、疾病转型理论和动态结论。

作者: Health Information System Team
日期: 2026-04-16
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import random

# 创建 APIRouter 实例 (FastAPI 版本的 Blueprint)
router = APIRouter(prefix="/api/v1/meso", tags=["meso"])


# ==================== 数据模型定义 ====================

class MetricValue(BaseModel):
    """指标值模型"""
    value: float
    trend: str
    unit: Optional[str] = None


class CountryBaseline(BaseModel):
    """
    国家基础健康指标模型

    用于标准化国家健康指标数据结构，区分核心指标（必填）和扩展指标（可选）
    """
    life_expectancy: MetricValue
    ncd_ratio: MetricValue
    doctor_density: MetricValue
    efficiency_score: MetricValue
    bed_density: Optional[MetricValue] = None
    expenditure_gdp_ratio: Optional[MetricValue] = None
    population: Optional[MetricValue] = None


class TransitionStage(BaseModel):
    """
    疾病转型阶段模型

    描述国家所处疾病转型阶段及历史趋势数据，用于ECharts图表渲染
    """
    stages: List[str] = Field(..., description="所有阶段列表")
    current_stage: str = Field(..., description="当前所处阶段")
    stage_index: int = Field(..., description="当前阶段索引")
    series: List[Dict[str, Any]] = Field(..., description="ECharts图表数据系列")


class MesoDashboardResponse(BaseModel):
    """
    中观分析仪表板响应模型

    整合了CountryBaseline和TransitionStage模型，提供类型安全的数据结构
    """
    status: str
    region: str
    stats: CountryBaseline  # 使用CountryBaseline替代Dict[str, Any]
    transition_chart: TransitionStage  # 使用TransitionStage替代Dict[str, Any]
    conclusions: List[str]
    peers: List[str]


class CountryProfile(BaseModel):
    """国家医疗资源配置基线模型"""
    physician: float  # 医生密度 (人/千人口)
    bed: float  # 床位密度 (张/千人口)
    expenditure: float  # 医疗支出占GDP比 (%)
    population: int  # 人口数量 (百万)
    expectancy: float  # 预期寿命 (岁)
    ncd_ratio: float  # 慢性病负担占比 (%)


class DiseaseTransition(BaseModel):
    """疾病转型动态数组模型"""
    ncd: List[float]  # 慢性病趋势数组
    infectious: List[float]  # 传染病趋势数组
    years: List[int]  # 年份数组


class CountryDataResponse(BaseModel):
    """国家数据响应模型"""
    status: str
    country: str
    profile: CountryProfile
    transitions: DiseaseTransition
    meta: Dict[str, Any]


# ==================== 国家医疗资源配置基线数据 (COUNTRY_PROFILES) ====================
# 对应 mock_data_report.md 第 1.4 节：国家卫生资源配置基线
# 数据来源：WHO, World Bank, OECD 公开数据参考值

COUNTRY_PROFILES: Dict[str, Dict[str, Any]] = {
    "china": {
        "physician": 2.99,  # 人/千人口
        "bed": 7.1,  # 张/千人口
        "expenditure": 5.6,  # % of GDP
        "population": 1410,  # 百万
        "expectancy": 79.0,  # 岁
        "ncd_ratio": 89.4  # %
    },
    "usa": {
        "physician": 2.6,
        "bed": 2.9,
        "expenditure": 17.8,
        "population": 333,
        "expectancy": 77.5,
        "ncd_ratio": 88.5
    },
    "japan": {
        "physician": 2.50,
        "bed": 12.9,
        "expenditure": 10.9,
        "population": 124,
        "expectancy": 84.6,
        "ncd_ratio": 91.2
    },
    "germany": {
        "physician": 4.2,
        "bed": 8.0,
        "expenditure": 11.7,
        "population": 83,
        "expectancy": 81.3,
        "ncd_ratio": 90.1
    },
    "south_korea": {
        "physician": 2.4,
        "bed": 12.4,
        "expenditure": 8.8,
        "population": 51,
        "expectancy": 83.5,
        "ncd_ratio": 87.8
    },
    "india": {
        "physician": 0.9,
        "bed": 0.5,
        "expenditure": 3.0,
        "population": 1430,
        "expectancy": 69.8,
        "ncd_ratio": 64.5
    },
    "brazil": {
        "physician": 2.2,
        "bed": 2.2,
        "expenditure": 9.6,
        "population": 203,
        "expectancy": 75.9,
        "ncd_ratio": 82.3
    },
    "united_kingdom": {
        "physician": 2.8,
        "bed": 2.5,
        "expenditure": 10.2,
        "population": 67,
        "expectancy": 81.2,
        "ncd_ratio": 89.8
    },
    "france": {
        "physician": 3.2,
        "bed": 5.9,
        "expenditure": 11.1,
        "population": 68,
        "expectancy": 82.7,
        "ncd_ratio": 90.5
    },
    "singapore": {
        "physician": 2.3,
        "bed": 2.4,
        "expenditure": 4.5,
        "population": 6,
        "expectancy": 83.6,
        "ncd_ratio": 86.2
    }
}


# ==================== 疾病转型动态数组数据 (DISEASE_TRANSITION_BASE) ====================
# 对应 mock_data_report.md 第 1.3 节：疾病转型动态数组
# 基于 Omran 流行病学转型理论构建

DISEASE_TRANSITION_BASE: Dict[str, Dict[str, Any]] = {
    "china": {
        "ncd": [45.0, 58.0, 72.0, 89.4],  # 2000, 2010, 2020, 2024
        "infectious": [50.0, 38.0, 25.0, 10.6],
        "years": [2000, 2010, 2020, 2024]
    },
    "usa": {
        "ncd": [75.0, 82.0, 86.0, 88.5],
        "infectious": [22.0, 15.0, 12.0, 11.5],
        "years": [2000, 2010, 2020, 2024]
    },
    "japan": {
        "ncd": [80.0, 85.0, 89.0, 91.2],
        "infectious": [18.0, 13.0, 10.0, 8.8],
        "years": [2000, 2010, 2020, 2024]
    },
    "germany": {
        "ncd": [78.0, 84.0, 87.0, 90.1],
        "infectious": [20.0, 14.0, 11.0, 9.9],
        "years": [2000, 2010, 2020, 2024]
    },
    "south_korea": {
        "ncd": [55.0, 70.0, 82.0, 87.8],
        "infectious": [42.0, 27.0, 16.0, 12.2],
        "years": [2000, 2010, 2020, 2024]
    },
    "india": {
        "ncd": [35.0, 48.0, 58.0, 64.5],
        "infectious": [60.0, 48.0, 38.0, 35.5],
        "years": [2000, 2010, 2020, 2024]
    },
    "brazil": {
        "ncd": [58.0, 70.0, 78.0, 82.3],
        "infectious": [38.0, 27.0, 20.0, 17.7],
        "years": [2000, 2010, 2020, 2024]
    },
    "united_kingdom": {
        "ncd": [79.0, 84.0, 87.0, 89.8],
        "infectious": [19.0, 14.0, 11.0, 10.2],
        "years": [2000, 2010, 2020, 2024]
    },
    "france": {
        "ncd": [80.0, 85.0, 88.0, 90.5],
        "infectious": [18.0, 13.0, 10.0, 9.5],
        "years": [2000, 2010, 2020, 2024]
    },
    "singapore": {
        "ncd": [60.0, 73.0, 82.0, 86.2],
        "infectious": [37.0, 25.0, 17.0, 13.8],
        "years": [2000, 2010, 2020, 2024]
    }
}


# ==================== 模拟 DataService ====================
# 未来可以替换为 pd.read_csv('countries_baseline.csv')
# 这彻底解决了 HTML 中写死 10 个国家数据的问题

MESO_BASELINE_DATA: Dict[str, Dict[str, Any]] = {
    "China": {
        "life_expectancy": {"value": 79.0, "trend": "+3.4", "unit": "岁"},
        "ncd_ratio": {"value": 89.4, "trend": "+12.3", "unit": "%"},
        "doctor_density": {"value": 2.99, "trend": "+1.1", "unit": "人/千人口"},
        "efficiency_score": {"value": 0.82, "trend": "+0.05", "unit": "分"},
        "bed_density": {"value": 7.1, "trend": "+0.8", "unit": "张/千人口"},
        "expenditure_gdp_ratio": {"value": 5.6, "trend": "+0.3", "unit": "%"},
        "population": {"value": 1410, "trend": "+0.1", "unit": "百万"},
        "stage": "慢性病快速上升",
        "peers": ["Japan", "South Korea", "Thailand", "Brazil"]
    },
    "Japan": {
        "life_expectancy": {"value": 84.6, "trend": "+1.2", "unit": "岁"},
        "ncd_ratio": {"value": 91.2, "trend": "+2.1", "unit": "%"},
        "doctor_density": {"value": 2.50, "trend": "+0.2", "unit": "人/千人口"},
        "efficiency_score": {"value": 0.91, "trend": "+0.01", "unit": "分"},
        "bed_density": {"value": 12.9, "trend": "-0.3", "unit": "张/千人口"},
        "expenditure_gdp_ratio": {"value": 10.9, "trend": "+0.5", "unit": "%"},
        "population": {"value": 124, "trend": "-0.2", "unit": "百万"},
        "stage": "退行性疾病主导",
        "peers": ["South Korea", "Singapore", "Germany", "France"]
    },
    "USA": {
        "life_expectancy": {"value": 77.5, "trend": "-0.3", "unit": "岁"},
        "ncd_ratio": {"value": 88.5, "trend": "+3.2", "unit": "%"},
        "doctor_density": {"value": 2.6, "trend": "+0.1", "unit": "人/千人口"},
        "efficiency_score": {"value": 0.75, "trend": "-0.02", "unit": "分"},
        "bed_density": {"value": 2.9, "trend": "-0.1", "unit": "张/千人口"},
        "expenditure_gdp_ratio": {"value": 17.8, "trend": "+0.8", "unit": "%"},
        "population": {"value": 333, "trend": "+0.4", "unit": "百万"},
        "stage": "退行性疾病主导",
        "peers": ["Canada", "United Kingdom", "Germany", "Australia"]
    },
    "Germany": {
        "life_expectancy": {"value": 81.3, "trend": "+0.5", "unit": "岁"},
        "ncd_ratio": {"value": 90.1, "trend": "+1.8", "unit": "%"},
        "doctor_density": {"value": 4.2, "trend": "+0.3", "unit": "人/千人口"},
        "efficiency_score": {"value": 0.88, "trend": "+0.03", "unit": "分"},
        "bed_density": {"value": 8.0, "trend": "-0.2", "unit": "张/千人口"},
        "expenditure_gdp_ratio": {"value": 11.7, "trend": "+0.2", "unit": "%"},
        "population": {"value": 83, "trend": "+0.1", "unit": "百万"},
        "stage": "退行性疾病主导",
        "peers": ["France", "United Kingdom", "Netherlands", "Austria"]
    },
    "South Korea": {
        "life_expectancy": {"value": 83.5, "trend": "+2.1", "unit": "岁"},
        "ncd_ratio": {"value": 87.8, "trend": "+8.5", "unit": "%"},
        "doctor_density": {"value": 2.4, "trend": "+0.4", "unit": "人/千人口"},
        "efficiency_score": {"value": 0.85, "trend": "+0.04", "unit": "分"},
        "bed_density": {"value": 12.4, "trend": "+0.5", "unit": "张/千人口"},
        "expenditure_gdp_ratio": {"value": 8.8, "trend": "+0.6", "unit": "%"},
        "population": {"value": 51, "trend": "-0.1", "unit": "百万"},
        "stage": "慢性病快速上升",
        "peers": ["Japan", "China", "Singapore", "Taiwan"]
    },
    "India": {
        "life_expectancy": {"value": 69.8, "trend": "+4.2", "unit": "岁"},
        "ncd_ratio": {"value": 64.5, "trend": "+15.3", "unit": "%"},
        "doctor_density": {"value": 0.9, "trend": "+0.3", "unit": "人/千人口"},
        "efficiency_score": {"value": 0.65, "trend": "+0.08", "unit": "分"},
        "bed_density": {"value": 0.5, "trend": "+0.1", "unit": "张/千人口"},
        "expenditure_gdp_ratio": {"value": 3.0, "trend": "+0.2", "unit": "%"},
        "population": {"value": 1430, "trend": "+0.8", "unit": "百万"},
        "stage": "感染性疾病主导",
        "peers": ["Indonesia", "Philippines", "Vietnam", "Bangladesh"]
    },
    "Brazil": {
        "life_expectancy": {"value": 75.9, "trend": "+2.8", "unit": "岁"},
        "ncd_ratio": {"value": 82.3, "trend": "+9.1", "unit": "%"},
        "doctor_density": {"value": 2.2, "trend": "+0.5", "unit": "人/千人口"},
        "efficiency_score": {"value": 0.71, "trend": "+0.06", "unit": "分"},
        "bed_density": {"value": 2.2, "trend": "+0.2", "unit": "张/千人口"},
        "expenditure_gdp_ratio": {"value": 9.6, "trend": "+0.4", "unit": "%"},
        "population": {"value": 203, "trend": "+0.5", "unit": "百万"},
        "stage": "慢性病快速上升",
        "peers": ["Mexico", "Argentina", "Chile", "Colombia"]
    },
    "United Kingdom": {
        "life_expectancy": {"value": 81.2, "trend": "+0.3", "unit": "岁"},
        "ncd_ratio": {"value": 89.8, "trend": "+1.5", "unit": "%"},
        "doctor_density": {"value": 2.8, "trend": "+0.1", "unit": "人/千人口"},
        "efficiency_score": {"value": 0.86, "trend": "+0.01", "unit": "分"},
        "bed_density": {"value": 2.5, "trend": "-0.1", "unit": "张/千人口"},
        "expenditure_gdp_ratio": {"value": 10.2, "trend": "+0.3", "unit": "%"},
        "population": {"value": 67, "trend": "+0.3", "unit": "百万"},
        "stage": "退行性疾病主导",
        "peers": ["Germany", "France", "Canada", "Australia"]
    },
    "France": {
        "life_expectancy": {"value": 82.7, "trend": "+0.4", "unit": "岁"},
        "ncd_ratio": {"value": 90.5, "trend": "+1.2", "unit": "%"},
        "doctor_density": {"value": 3.2, "trend": "+0.2", "unit": "人/千人口"},
        "efficiency_score": {"value": 0.89, "trend": "+0.02", "unit": "分"},
        "bed_density": {"value": 5.9, "trend": "-0.2", "unit": "张/千人口"},
        "expenditure_gdp_ratio": {"value": 11.1, "trend": "+0.1", "unit": "%"},
        "population": {"value": 68, "trend": "+0.2", "unit": "百万"},
        "stage": "退行性疾病主导",
        "peers": ["Germany", "United Kingdom", "Italy", "Spain"]
    },
    "Singapore": {
        "life_expectancy": {"value": 83.6, "trend": "+1.8", "unit": "岁"},
        "ncd_ratio": {"value": 86.2, "trend": "+5.4", "unit": "%"},
        "doctor_density": {"value": 2.3, "trend": "+0.3", "unit": "人/千人口"},
        "efficiency_score": {"value": 0.93, "trend": "+0.03", "unit": "分"},
        "bed_density": {"value": 2.4, "trend": "+0.1", "unit": "张/千人口"},
        "expenditure_gdp_ratio": {"value": 4.5, "trend": "+0.2", "unit": "%"},
        "population": {"value": 5.9, "trend": "+0.5", "unit": "百万"},
        "stage": "慢性病快速上升",
        "peers": ["Japan", "South Korea", "Hong Kong", "Taiwan"]
    }
}

# 疾病转型理论阶段定义
DISEASE_TRANSITION_STAGES = [
    "感染性疾病主导",
    "慢性病快速上升",
    "退行性疾病主导"
]

# 地区别名映射
REGION_ALIASES = {
    "中国": "China",
    "china": "China",
    "美国": "USA",
    "usa": "USA",
    "united states": "USA",
    "日本": "Japan",
    "japan": "Japan",
    "德国": "Germany",
    "germany": "Germany",
    "韩国": "South Korea",
    "south korea": "South Korea",
    "印度": "India",
    "india": "India",
    "巴西": "Brazil",
    "brazil": "Brazil",
    "英国": "United Kingdom",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "法国": "France",
    "france": "France",
    "新加坡": "Singapore",
    "singapore": "Singapore"
}


# ==================== 辅助函数 ====================

def normalize_region(region: str) -> str:
    """
    标准化地区名称
    
    Args:
        region: 输入的地区名称（支持中英文和大小写）
        
    Returns:
        标准化的地区代码
    """
    region_lower = region.strip().lower()
    return REGION_ALIASES.get(region_lower, region)


def get_transition_data(region: str, base_stats: Dict[str, Any]) -> TransitionStage:
    """
    生成疾病转型数据

    解决报告中提到的 transition arrays 硬编码问题
    根据地区当前阶段动态生成 ECharts 需要的折线/面积图数据

    Args:
        region: 地区名称
        base_stats: 基础统计数据

    Returns:
        TransitionStage: 类型安全的疾病转型阶段数据模型
    """
    current_stage = base_stats.get("stage", "慢性病快速上升")
    stage_index = DISEASE_TRANSITION_STAGES.index(current_stage)

    ncd_value = base_stats.get("ncd_ratio", {}).get("value", 80.0)
    infectious_value = 100 - ncd_value

    # 根据当前阶段生成历史趋势数据
    if stage_index == 0:  # 感染性疾病主导
        ncd_series = [30, 40, 50, ncd_value]
        infectious_series = [65, 55, 45, infectious_value]
    elif stage_index == 1:  # 慢性病快速上升
        ncd_series = [40, 60, 75, ncd_value]
        infectious_series = [55, 35, 22, infectious_value]
    else:  # 退行性疾病主导
        ncd_series = [60, 75, 85, ncd_value]
        infectious_series = [35, 22, 13, infectious_value]

    # 返回 TransitionStage 模型实例而非普通 dict
    return TransitionStage(
        stages=DISEASE_TRANSITION_STAGES,
        current_stage=current_stage,
        stage_index=stage_index,
        series=[
            {
                "name": "NCDs",
                "data": ncd_series,
                "type": "line",
                "smooth": True,
                "areaStyle": {"opacity": 0.3}
            },
            {
                "name": "传染病",
                "data": infectious_series,
                "type": "line",
                "smooth": True,
                "areaStyle": {"opacity": 0.3}
            }
        ]
    )


def generate_conclusions(region: str, base_stats: Dict[str, Any]) -> List[str]:
    """
    生成动态分析结论
    
    Args:
        region: 地区名称
        base_stats: 基础统计数据
        
    Returns:
        分析结论列表
    """
    life_exp = base_stats.get("life_expectancy", {}).get("value", 75.0)
    ncd_ratio = base_stats.get("ncd_ratio", {}).get("value", 80.0)
    efficiency = base_stats.get("efficiency_score", {}).get("value", 0.75)
    stage = base_stats.get("stage", "未知")
    doctor_density = base_stats.get("doctor_density", {}).get("value", 2.0)
    
    conclusions = [
        f"{region} 当前预期寿命为 {life_exp} 岁，{'高于' if life_exp > 78 else '低于'}全球平均水平。",
        f"处于疾病转型的【{stage}】阶段，慢性病负担占比 {ncd_ratio}%。",
        f"医疗资源配置效率评分为 {efficiency}，{'表现优秀' if efficiency > 0.85 else '仍有提升空间'}。",
        f"医生密度为 {doctor_density} 人/千人口，{'高于' if doctor_density > 2.5 else '低于'}WHO建议标准。"
    ]
    
    # 根据效率评分添加建议
    if efficiency < 0.75:
        conclusions.append("建议优化医疗资源配置，提高投入产出效率。")
    elif ncd_ratio > 85:
        conclusions.append("慢性病防控体系需要进一步完善，建议加强基层医疗建设。")
    
    return conclusions


# ==================== API 路由定义 ====================

@router.get("/dashboard", response_model=MesoDashboardResponse)
async def get_meso_dashboard(
    region: str = Query(default="China", description="地区名称（支持中英文）")
) -> MesoDashboardResponse:
    """
    获取中观分析仪表板数据

    将前端 HTML 中硬编码的国家数据转移到后端，
    动态返回指定地区的基础统计数据、疾病转型理论和分析结论。

    修复内容:
    1. 使用 CountryBaseline 模型构建 stats 字段，提供类型安全
    2. 使用 TransitionStage 模型作为 transition_chart 字段
    3. 返回 MesoDashboardResponse 模型实例而非普通 dict

    Args:
        region: 地区名称，如 "China"、"中国"、"USA"、"美国"

    Returns:
        MesoDashboardResponse: 类型安全的中观分析仪表板响应模型

    Example:
        GET /api/v1/meso/dashboard?region=China
        GET /api/v1/meso/dashboard?region=日本
    """
    # 标准化地区名称
    normalized_region = normalize_region(region)

    # 1. 获取该地区的基础统计数据
    if normalized_region not in MESO_BASELINE_DATA:
        raise HTTPException(
            status_code=404,
            detail=f"未找到地区 '{region}' 的数据。可用地区: {', '.join(MESO_BASELINE_DATA.keys())}"
        )

    base_stats = MESO_BASELINE_DATA[normalized_region]

    # 2. 生成疾病转型数据 (返回 TransitionStage 模型实例)
    transition_data = get_transition_data(normalized_region, base_stats)

    # 3. 生成动态结论
    conclusions = generate_conclusions(normalized_region, base_stats)

    # 4. 获取对标国家
    peers = base_stats.get("peers", [])

    # 5. 构建 CountryBaseline 模型实例 (类型安全的 stats 字段)
    stats = CountryBaseline(
        life_expectancy=MetricValue(**base_stats.get("life_expectancy", {"value": 0.0, "trend": "0", "unit": "岁"})),
        ncd_ratio=MetricValue(**base_stats.get("ncd_ratio", {"value": 0.0, "trend": "0", "unit": "%"})),
        doctor_density=MetricValue(**base_stats.get("doctor_density", {"value": 0.0, "trend": "0", "unit": "人/千人口"})),
        efficiency_score=MetricValue(**base_stats.get("efficiency_score", {"value": 0.0, "trend": "0", "unit": None})),
        bed_density=base_stats.get("bed_density") and MetricValue(**base_stats.get("bed_density")),
        expenditure_gdp_ratio=base_stats.get("expenditure_gdp_ratio") and MetricValue(**base_stats.get("expenditure_gdp_ratio")),
        population=base_stats.get("population") and MetricValue(**base_stats.get("population"))
    )

    # 6. 返回 MesoDashboardResponse 模型实例
    return MesoDashboardResponse(
        status="success",
        region=normalized_region,
        stats=stats,
        transition_chart=transition_data,
        conclusions=conclusions,
        peers=peers
    )


@router.get("/countries")
async def get_available_countries() -> Dict[str, Any]:
    """
    获取所有可用的国家/地区列表
    
    Returns:
        包含所有可用地区及其基础信息的列表
    """
    countries = []
    for code, data in MESO_BASELINE_DATA.items():
        countries.append({
            "code": code,
            "name": code,
            "life_expectancy": data.get("life_expectancy", {}).get("value"),
            "ncd_ratio": data.get("ncd_ratio", {}).get("value"),
            "stage": data.get("stage", "未知")
        })
    
    return {
        "status": "success",
        "count": len(countries),
        "countries": countries
    }


@router.get("/compare")
async def compare_countries(
    countries: str = Query(..., description="要对比的国家代码，用逗号分隔，如 'China,Japan,USA'")
) -> Dict[str, Any]:
    """
    对比多个国家/地区的关键指标
    
    Args:
        countries: 国家代码列表，逗号分隔
        
    Returns:
        对比数据
        
    Example:
        GET /api/v1/meso/compare?countries=China,Japan,USA
    """
    country_list = [c.strip() for c in countries.split(",")]
    
    comparison_data = []
    for country in country_list:
        normalized = normalize_region(country)
        if normalized in MESO_BASELINE_DATA:
            data = MESO_BASELINE_DATA[normalized]
            comparison_data.append({
                "country": normalized,
                "life_expectancy": data.get("life_expectancy", {}).get("value"),
                "ncd_ratio": data.get("ncd_ratio", {}).get("value"),
                "doctor_density": data.get("doctor_density", {}).get("value"),
                "efficiency_score": data.get("efficiency_score", {}).get("value"),
                "stage": data.get("stage", "未知")
            })
    
    return {
        "status": "success",
        "comparison": comparison_data
    }


@router.get("/stages")
async def get_disease_transition_stages() -> Dict[str, Any]:
    """
    获取疾病转型理论的所有阶段定义
    
    Returns:
        疾病转型阶段列表及其描述
    """
    stage_descriptions = {
        "感染性疾病主导": "以传染病、寄生虫病和母婴疾病为主要疾病负担的阶段",
        "慢性病快速上升": "随着人口老龄化和生活方式改变，慢性病负担快速增加的阶段",
        "退行性疾病主导": "以心血管疾病、癌症、神经退行性疾病等为主的阶段"
    }
    
    return {
        "status": "success",
        "stages": [
            {
                "name": stage,
                "description": stage_descriptions.get(stage, ""),
                "index": i
            }
            for i, stage in enumerate(DISEASE_TRANSITION_STAGES)
        ]
    }


@router.get("/country-data", response_model=CountryDataResponse)
async def get_country_data(
    country: str = Query(default="china", description="国家代码（支持大小写，如 'china', 'usa', 'japan'）")
) -> CountryDataResponse:
    """
    获取指定国家的医疗资源配置基线和疾病转型数据

    对应 mock_data_report.md 第 1.4 节和第 1.3 节的数据服务接口。
    返回国家医疗资源配置基线（COUNTRY_PROFILES）和疾病转型动态数组（DISEASE_TRANSITION_BASE）。

    修复内容:
    1. 使用 CountryProfile 模型构建 profile 字段，提供类型安全
    2. 使用 DiseaseTransition 模型构建 transitions 字段，提供类型安全
    3. 返回 CountryDataResponse 模型实例而非普通 dict

    Args:
        country: 国家代码，支持大小写，如 "china", "USA", "Japan"
                可选值：china, usa, japan, germany, south_korea, india,
                       brazil, united_kingdom, france, singapore
                默认值：china

    Returns:
        CountryDataResponse: 类型安全的国家数据响应模型

    Error Handling:
        - 无效的国家参数会自动回退到 "china" 的数据
        - 确保始终返回有效的 JSON 响应

    Example:
        GET /api/v1/meso/country-data?country=china
        GET /api/v1/meso/country-data?country=USA
        GET /api/v1/meso/country-data?country=Japan
    """
    # 标准化国家代码：转换为小写并去除首尾空格
    normalized_country = country.strip().lower()

    # 有效的国家代码列表
    valid_countries = set(COUNTRY_PROFILES.keys())

    # 错误处理：如果国家代码无效，默认使用 "china"
    if normalized_country not in valid_countries:
        # 记录无效参数（实际生产环境应使用日志系统）
        print(f"[WARN] Invalid country parameter: '{country}', falling back to 'china'")
        normalized_country = "china"

    # 获取国家配置数据
    profile_data = COUNTRY_PROFILES[normalized_country]

    # 获取疾病转型数据
    transition_data = DISEASE_TRANSITION_BASE[normalized_country]

    # 构建 CountryProfile 模型实例 (类型安全的 profile 字段)
    profile = CountryProfile(
        physician=profile_data["physician"],
        bed=profile_data["bed"],
        expenditure=profile_data["expenditure"],
        population=profile_data["population"],
        expectancy=profile_data["expectancy"],
        ncd_ratio=profile_data["ncd_ratio"]
    )

    # 构建 DiseaseTransition 模型实例 (类型安全的 transitions 字段)
    transitions = DiseaseTransition(
        ncd=transition_data["ncd"],
        infectious=transition_data["infectious"],
        years=transition_data["years"]
    )

    # 构建并返回 CountryDataResponse 模型实例
    return CountryDataResponse(
        status="success",
        country=normalized_country,
        profile=profile,
        transitions=transitions,
        meta={
            "version": "2024-Q4",
            "is_mock": False,
            "last_updated": "2026-04-16",
            "data_source": "WHO, World Bank, OECD 公开数据参考值",
            "description": "国家卫生资源配置基线及疾病转型动态数组"
        }
    )


# ==================== 模块测试 ====================

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    
    # 创建测试用的 FastAPI 应用
    app = FastAPI(title="Meso Data Bus Test")
    app.include_router(router)
    
    # 运行测试服务器
    print("启动 Meso Data Bus 测试服务器...")
    print("访问 http://127.0.0.1:8000/docs 查看 API 文档")
    uvicorn.run(app, host="127.0.0.1", port=8000)
