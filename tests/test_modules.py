import pytest
from unittest.mock import patch
from modules.analysis.china_provincial_health import get_china_provincial_health
from modules.analysis.global_life_expectancy import get_global_life_expectancy

@pytest.mark.asyncio
async def test_china_provincial_health_fallback():
    # 通过模拟内部获取函数强制触发回退
    with patch('modules.analysis.china_provincial_health.fetch_nhc_nbs_data', side_effect=Exception("Missing > 20%")):
        result = await get_china_provincial_health()
        assert result["type"] == "FeatureCollection"
        # 回退数据设置 'imputed' = True
        assert result["features"][0]["properties"]["imputed"] == True

@pytest.mark.asyncio
async def test_global_life_expectancy_fallback():
    # fetch_real_life_expectancy 抛出异常以触发回退
    result = await get_global_life_expectancy()
    assert result["type"] == "FeatureCollection"
    assert "country_code" in result["features"][0]["properties"]
    # 确保数值在回退范围内
    val = result["features"][0]["properties"]["life_expectancy"]
    assert 49.2 <= val <= 85.4
