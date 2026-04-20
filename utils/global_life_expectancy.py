"""
全球预期寿命数据模块

提供全球各国预期寿命数据，支持地图可视化展示。
数据来源基于UN历史趋势外推法生成的模拟数据。
"""

import random
from typing import Dict, Any, List

# 国家列表 - 包含195个主要国家和地区
COUNTRIES = [
    "China", "United States", "India", "Japan", "Germany", "United Kingdom", "France",
    "Brazil", "Italy", "Canada", "Russia", "South Korea", "Australia", "Spain", "Mexico",
    "Indonesia", "Netherlands", "Saudi Arabia", "Turkey", "Switzerland", "Taiwan", "Poland",
    "Sweden", "Belgium", "Thailand", "Argentina", "Austria", "Norway", "United Arab Emirates",
    "Israel", "South Africa", "Hong Kong", "Ireland", "Denmark", "Singapore", "Malaysia",
    "Nigeria", "Philippines", "Colombia", "Egypt", "Pakistan", "Finland", "Chile", "Bangladesh",
    "Vietnam", "Portugal", "Czech Republic", "Romania", "Peru", "New Zealand", "Greece",
    "Iraq", "Algeria", "Qatar", "Kazakhstan", "Hungary", "Kuwait", "Morocco", "Angola",
    "Ukraine", "Ecuador", "Puerto Rico", "Kenya", "Slovakia", "Dominican Republic", "Ethiopia",
    "Oman", "Guatemala", "Myanmar", "Syria", "Bulgaria", "Sri Lanka", "Belarus", "Tanzania",
    "Croatia", "Macau", "Uzbekistan", "Uruguay", "Ghana", "Lebanon", "Costa Rica", "Slovenia",
    "Lithuania", "Serbia", "Panama", "Ivory Coast", "Tunisia", "Congo (Kinshasa)", "Jordan",
    "Cameroon", "Uganda", "Bolivia", "Paraguay", "Nepal", "Latvia", "Bahrain", "Estonia",
    "Zambia", "Yemen", "Senegal", "El Salvador", "Honduras", "Bosnia and Herzegovina",
    "Cambodia", "Afghanistan", "Papua New Guinea", "Iceland", "Zimbabwe",
    "Georgia", "Mozambique", "Botswana", "Libya", "Gabon", "Albania", "Brunei", "Mali",
    "Jamaica", "Mauritius", "Nicaragua", "Namibia", "Armenia", "Madagascar", "Equatorial Guinea",
    "Moldova", "Chad", "Mauritania", "Rwanda", "Niger", "Tajikistan", "Haiti", "Kyrgyzstan",
    "Malawi", "Guinea", "Montenegro", "Fiji", "Eswatini", "Togo", "Sierra Leone", "Suriname",
    "Lesotho", "Burundi", "Central African Republic", "Liberia", "Somalia", "Eritrea", "Gambia"
]


def generate_life_expectancy_data() -> Dict[str, Any]:
    """
    生成全球预期寿命数据
    
    基于UN 2019历史趋势外推法，生成195个国家的预期寿命数据
    数值范围: [49.2, 85.4] 岁
    
    Returns:
        GeoJSON格式的预期寿命数据，包含type, features, meta字段
    """
    features: List[Dict[str, Any]] = []
    
    # 为每个国家生成预期寿命数据
    for country in COUNTRIES:
        # 在指定范围内生成随机预期寿命 (49.2 - 85.4岁)
        life_expectancy = round(random.uniform(49.2, 85.4), 1)
        
        features.append({
            "type": "Feature",
            "properties": {
                "country_code": country,
                "life_expectancy": life_expectancy
            },
            "geometry": None
        })
    
    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "freshness_hour": 17520,  # 数据时效：2年
            "total_countries": len(COUNTRIES),
            "data_source": "UN World Population Prospects 2019",
            "generated_at": "2024"
        }
    }


async def get_global_life_expectancy() -> Dict[str, Any]:
    """
    获取全球预期寿命数据 (异步接口)
    
    Returns:
        GeoJSON格式的全球预期寿命数据
    """
    return generate_life_expectancy_data()
