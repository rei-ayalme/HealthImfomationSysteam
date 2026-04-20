"""
分析模块包

提供各种健康数据分析功能模块
"""

from .global_life_expectancy import get_global_life_expectancy
from .china_provincial_health import get_china_provincial_health

__all__ = [
    "get_global_life_expectancy",
    "get_china_provincial_health",
]
