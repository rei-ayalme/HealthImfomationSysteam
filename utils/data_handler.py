#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局 Mock 数据管理模块

根据 mock_data_report.md 规范要求，实施统一的全局 Mock 数据管理策略，
将所有系统兜底数据集中收纳并建立标准化坐标系。

作者: Health Information System Team
日期: 2026-04-16
"""

from typing import Dict, List, Any


class MicroDataHandler:
    """
    微观数据处理器
    
    提供标准化的 Mock 数据管理，确保数据格式统一、坐标系规范、元数据完整。
    解决报告 7.1.2 章节中关于 Mock 数据标准化的问题。
    """
    
    @staticmethod
    def get_fallback_pois() -> Dict[str, Any]:
        """
        获取标准化的 POI 兜底数据
        
        解决报告 7.1.2：统一使用 WGS84 坐标系，并标注元数据
        返回标准化的 POI 兜底数据，包含元数据和 POI 特征数组
        
        Returns:
            Dict[str, Any]: 包含 metadata 和 features 的标准化数据结构
            - metadata: 包含 coordinate_system、source、freshness 的元数据字典
            - features: POI 对象数组，每个对象包含 name、lng、lat、capacity 属性
            
        Example:
            >>> data = MicroDataHandler.get_fallback_pois()
            >>> print(data["metadata"]["coordinate_system"])
            'WGS84'
            >>> print(len(data["features"]))
            8
        """
        return {
            "metadata": {
                "coordinate_system": "WGS84",      # 统一使用 WGS84 坐标系
                "source": "Manual_Collection",      # 数据来源标识
                "freshness": "2026-Q2"              # 数据新鲜度标识
            },
            "features": [
                {
                    "name": "四川大学华西医院",
                    "lng": 104.0632,    # 经度，保留4位小数
                    "lat": 30.6418,     # 纬度，保留4位小数
                    "capacity": 4300    # 床位数
                },
                {
                    "name": "四川省人民医院",
                    "lng": 104.0435,
                    "lat": 30.6589,
                    "capacity": 3200
                },
                {
                    "name": "成都市第三人民医院",
                    "lng": 104.0578,
                    "lat": 30.6745,
                    "capacity": 2100
                },
                {
                    "name": "成都市第一人民医院",
                    "lng": 104.0412,
                    "lat": 30.6245,
                    "capacity": 1800
                },
                {
                    "name": "成都市第二人民医院",
                    "lng": 104.0823,
                    "lat": 30.6656,
                    "capacity": 1500
                },
                {
                    "name": "四川省肿瘤医院",
                    "lng": 104.0534,
                    "lat": 30.6356,
                    "capacity": 1200
                },
                {
                    "name": "成都市妇女儿童中心医院",
                    "lng": 104.0123,
                    "lat": 30.6845,
                    "capacity": 1600
                },
                {
                    "name": "四川省骨科医院",
                    "lng": 104.0712,
                    "lat": 30.6489,
                    "capacity": 800
                }
            ]
        }
    
    @staticmethod
    def get_fallback_trend_data(disease_type: str = "hypertension") -> Dict[str, Any]:
        """
        获取标准化的趋势数据兜底数据
        
        解决报告 2.1 和 4.5 中关于数据长度不匹配的问题
        返回标准化的趋势数据，确保 years 和 values 数组长度一致
        
        Args:
            disease_type: 疾病类型，支持 'hypertension' 和 'diabetes'
            
        Returns:
            Dict[str, Any]: 包含 status、data、meta 的标准化响应结构
            
        Example:
            >>> data = MicroDataHandler.get_fallback_trend_data("hypertension")
            >>> print(len(data["data"]["years"]))
            8
            >>> print(len(data["data"]["values"]))
            8
        """
        # 标准年份数组（2010-2024，共8个点）
        standard_years = ['2010', '2012', '2014', '2016', '2018', '2020', '2022', '2024']
        
        # 标准化数据映射，确保所有数据长度为8
        trend_data_map = {
            'hypertension': [31.0, 30.2, 29.5, 28.2, 27.5, 26.6, 25.8, 24.8],
            'diabetes': [10.5, 11.2, 12.0, 12.5, 12.8, 13.2, 13.5, 13.8]
        }
        
        # 获取对应疾病数据，无效参数时返回8个0的数组
        if disease_type not in trend_data_map:
            series_data = [0] * 8
        else:
            series_data = trend_data_map[disease_type]
        
        return {
            "status": "success",
            "data": {
                "years": standard_years,
                "values": series_data
            },
            "meta": {
                "source": "GBD Study 2021",
                "last_updated": "2026-04-16",
                "is_mock": True,  # 明确标识为 Mock 数据
                "data_type": disease_type
            }
        }
    
    @staticmethod
    def validate_poi_data(poi_data: Dict[str, Any]) -> bool:
        """
        验证 POI 数据格式是否符合标准
        
        Args:
            poi_data: 待验证的 POI 数据字典
            
        Returns:
            bool: 数据格式是否有效
        """
        # 检查必需字段
        required_fields = ["name", "lng", "lat", "capacity"]
        for field in required_fields:
            if field not in poi_data:
                return False
        
        # 检查坐标范围有效性
        lng = poi_data.get("lng")
        lat = poi_data.get("lat")
        
        if not isinstance(lng, (int, float)) or not isinstance(lat, (int, float)):
            return False
        
        # 经度范围：-180 到 180
        if lng < -180 or lng > 180:
            return False
        
        # 纬度范围：-90 到 90
        if lat < -90 or lat > 90:
            return False
        
        # 检查 capacity 为正整数
        capacity = poi_data.get("capacity")
        if not isinstance(capacity, int) or capacity < 0:
            return False
        
        return True
    
    @staticmethod
    def format_poi_for_response(poi_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        将 POI 列表格式化为标准响应格式
        
        Args:
            poi_list: POI 对象列表
            
        Returns:
            Dict[str, Any]: 包含 metadata 和 features 的标准化响应
        """
        # 过滤并验证 POI 数据
        valid_features = [
            poi for poi in poi_list 
            if MicroDataHandler.validate_poi_data(poi)
        ]
        
        return {
            "metadata": {
                "coordinate_system": "WGS84",
                "source": "Database",
                "freshness": "2026-Q2",
                "total_count": len(poi_list),
                "valid_count": len(valid_features)
            },
            "features": valid_features
        }


# 模块测试
if __name__ == "__main__":
    # 测试 get_fallback_pois
    print("=" * 60)
    print("测试 MicroDataHandler.get_fallback_pois()")
    print("=" * 60)
    
    pois_data = MicroDataHandler.get_fallback_pois()
    print(f"元数据: {pois_data['metadata']}")
    print(f"POI 数量: {len(pois_data['features'])}")
    print(f"第一个 POI: {pois_data['features'][0]}")
    
    # 验证数据格式
    assert "metadata" in pois_data, "缺少 metadata 字段"
    assert "features" in pois_data, "缺少 features 字段"
    assert pois_data["metadata"]["coordinate_system"] == "WGS84", "坐标系错误"
    assert len(pois_data["features"]) > 0, "POI 列表为空"
    
    # 验证每个 POI 的格式
    for poi in pois_data["features"]:
        assert MicroDataHandler.validate_poi_data(poi), f"POI 数据格式错误: {poi}"
    
    print("\n所有 POI 数据格式验证通过！")
    
    # 测试 get_fallback_trend_data
    print("\n" + "=" * 60)
    print("测试 MicroDataHandler.get_fallback_trend_data()")
    print("=" * 60)
    
    trend_data = MicroDataHandler.get_fallback_trend_data("hypertension")
    print(f"状态: {trend_data['status']}")
    print(f"年份数组: {trend_data['data']['years']}")
    print(f"数值数组: {trend_data['data']['values']}")
    print(f"元数据: {trend_data['meta']}")
    
    # 验证数据长度
    assert len(trend_data["data"]["years"]) == 8, "年份数组长度必须为8"
    assert len(trend_data["data"]["values"]) == 8, "数值数组长度必须为8"
    assert trend_data["data"]["years"] == ['2010', '2012', '2014', '2016', '2018', '2020', '2022', '2024'], "年份数据错误"
    
    print("\n趋势数据验证通过！")
    
    # 测试无效参数
    print("\n" + "=" * 60)
    print("测试无效参数处理")
    print("=" * 60)
    
    invalid_data = MicroDataHandler.get_fallback_trend_data("invalid_type")
    print(f"无效参数返回: {invalid_data['data']['values']}")
    assert all(v == 0 for v in invalid_data["data"]["values"]), "无效参数应返回8个0"
    
    print("\n无效参数处理验证通过！")
    print("\n所有测试通过！")
