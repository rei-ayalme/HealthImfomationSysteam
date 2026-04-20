"""
全球预期寿命分析模块

此模块作为 utils.global_life_expectancy 的代理，
向后兼容现有代码和测试。

实际实现位于: utils/global_life_expectancy.py
"""

from utils.global_life_expectancy import (
    get_global_life_expectancy,
    generate_life_expectancy_data,
    COUNTRIES,
)

__all__ = [
    "get_global_life_expectancy",
    "generate_life_expectancy_data",
    "COUNTRIES",
]
