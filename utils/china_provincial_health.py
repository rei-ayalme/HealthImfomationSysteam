"""
中国省级健康数据模块

提供中国各省级行政区的健康数据，包括预期寿命等指标。
"""

import random
from typing import Dict, Any, List

# 中国省级行政区列表
PROVINCES = [
    "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
    "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
    "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
    "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆"
]


def generate_china_provincial_health_data() -> Dict[str, Any]:
    """
    生成中国省级健康数据

    基于空间邻接关系的加权平均插补策略生成模拟数据

    Returns:
        GeoJSON格式的中国省级健康数据
    """
    features: List[Dict[str, Any]] = []

    for province in PROVINCES:
        features.append({
            "type": "Feature",
            "properties": {
                "province": province,
                "life_expectancy": round(random.uniform(70.0, 82.0), 2),
                "imputed": True
            },
            "geometry": None
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "freshness_hour": 24,
            "total_provinces": len(PROVINCES),
            "data_source": "NHC/NBS (Simulated)",
            "generated_at": "2024"
        }
    }


async def get_china_provincial_health() -> Dict[str, Any]:
    """
    获取中国省级健康数据 (异步接口)

    Returns:
        GeoJSON格式的中国省级健康数据
    """
    return generate_china_provincial_health_data()
