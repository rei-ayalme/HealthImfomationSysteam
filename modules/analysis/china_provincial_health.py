"""
中国省级健康数据分析模块

此模块作为 utils.china_provincial_health 的代理，
向后兼容现有代码和测试。

实际实现位于: utils/china_provincial_health.py
"""

from utils.china_provincial_health import (
    get_china_provincial_health,
    generate_china_provincial_health_data,
    PROVINCES,
)

__all__ = [
    "get_china_provincial_health",
    "generate_china_provincial_health_data",
    "PROVINCES",
]
