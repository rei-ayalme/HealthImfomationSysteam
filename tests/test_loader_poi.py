"""
DataLoader POI 功能单元测试

测试覆盖：
1. fetch_poi_data 接口
2. fetch_community_demand 接口
3. GeoJSON 保存功能
"""

import unittest
import pandas as pd
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.data.loader import DataLoader


class TestFetchPOIData(unittest.TestCase):
    """POI数据获取测试"""

    def setUp(self):
        self.loader = DataLoader(enable_fallback=False)

    def test_invalid_provider(self):
        """测试无效的提供商"""
        with self.assertRaises(ValueError) as context:
            self.loader.fetch_poi_data("成都市", "医院", provider="invalid")
        self.assertIn("不支持的地图服务提供商", str(context.exception))

    @patch('modules.data.loader.requests.get')
    def test_amap_poi_fetch_success(self, mock_get):
        """测试高德POI获取成功"""
        # 模拟API响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '1',
            'count': '2',
            'pois': [
                {
                    'name': '测试医院1',
                    'location': '104.0,30.0',
                    'address': '测试地址1',
                    'type': '医疗保健服务'
                },
                {
                    'name': '测试医院2',
                    'location': '104.1,30.1',
                    'address': '测试地址2',
                    'type': '医疗保健服务'
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # 模拟API配置
        self.loader.api_config = {
            'amap': {
                'api_key': 'test_key',
                'poi_url': 'https://test.api.com'
            }
        }

        df = self.loader._fetch_amap_poi("成都市", "医院")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertIn('name', df.columns)
        self.assertIn('lon', df.columns)
        self.assertIn('lat', df.columns)

    @patch('modules.data.loader.requests.get')
    def test_amap_poi_empty_response(self, mock_get):
        """测试高德POI空响应"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '1',
            'count': '0',
            'pois': []
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        self.loader.api_config = {
            'amap': {
                'api_key': 'test_key',
                'poi_url': 'https://test.api.com'
            }
        }

        df = self.loader._fetch_amap_poi("成都市", "医院")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.empty)

    def test_amap_no_api_key(self):
        """测试高德API密钥未配置"""
        self.loader.api_config = {'amap': {}}

        df = self.loader._fetch_amap_poi("成都市", "医院")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.empty)

    @patch('modules.data.loader.requests.get')
    def test_baidu_poi_fetch_success(self, mock_get):
        """测试百度POI获取成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 0,
            'results': [
                {
                    'name': '测试医院1',
                    'location': {'lat': 30.0, 'lng': 104.0},
                    'address': '测试地址1',
                    'detail_info': {'tag': '医院'}
                },
                {
                    'name': '测试医院2',
                    'location': {'lat': 30.1, 'lng': 104.1},
                    'address': '测试地址2',
                    'detail_info': {'tag': '医院'}
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        self.loader.api_config = {
            'baidu': {
                'api_key': 'test_key',
                'poi_url': 'https://test.api.com'
            }
        }

        df = self.loader._fetch_baidu_poi("成都市", "医院")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertIn('name', df.columns)

    def test_baidu_no_api_key(self):
        """测试百度API密钥未配置"""
        self.loader.api_config = {'baidu': {}}

        df = self.loader._fetch_baidu_poi("成都市", "医院")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.empty)


class TestFetchCommunityDemand(unittest.TestCase):
    """社区需求数据获取测试"""

    def setUp(self):
        self.loader = DataLoader(enable_fallback=False)

    def test_chengdu_community_data(self):
        """测试成都市社区数据"""
        df = self.loader.fetch_community_demand("成都市")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        self.assertIn('name', df.columns)
        self.assertIn('lon', df.columns)
        self.assertIn('lat', df.columns)
        self.assertIn('population', df.columns)
        self.assertIn('elderly_ratio', df.columns)

        # 验证数据完整性
        self.assertTrue(all(df['population'] > 0))
        self.assertTrue(all(df['elderly_ratio'] > 0))

    def test_unknown_city(self):
        """测试未知城市"""
        df = self.loader.fetch_community_demand("未知城市")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.empty)

    def test_default_city(self):
        """测试默认城市参数"""
        df = self.loader.fetch_community_demand()

        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)


class TestSavePOIToGeoJSON(unittest.TestCase):
    """POI保存为GeoJSON测试"""

    def setUp(self):
        self.loader = DataLoader(enable_fallback=False)
        self.test_df = pd.DataFrame({
            'name': ['医院1', '医院2'],
            'lon': [104.0, 104.1],
            'lat': [30.0, 30.1],
            'address': ['地址1', '地址2'],
            'capacity': [1000, 800]
        })

    @patch('modules.data.loader.os.makedirs')
    @patch('builtins.open', create=True)
    @patch('modules.data.loader.json.dump')
    def test_save_geojson_success(self, mock_json_dump, mock_open, mock_makedirs):
        """测试保存GeoJSON成功"""
        self.loader._save_poi_to_geojson(self.test_df, "成都市", "三甲医院")

        mock_makedirs.assert_called_once()
        mock_open.assert_called_once()
        mock_json_dump.assert_called_once()

        # 验证传入的数据结构
        call_args = mock_json_dump.call_args
        geojson_data = call_args[0][0]
        self.assertEqual(geojson_data['type'], 'FeatureCollection')
        self.assertEqual(len(geojson_data['features']), 2)

    @patch('modules.data.loader.os.makedirs')
    @patch('builtins.open', create=True)
    def test_save_geojson_io_error(self, mock_open, mock_makedirs):
        """测试保存GeoJSON IO错误"""
        mock_open.side_effect = IOError("写入失败")

        # 应该不抛出异常
        try:
            self.loader._save_poi_to_geojson(self.test_df, "成都市", "医院")
        except IOError:
            self.fail("_save_poi_to_geojson 不应该抛出IOError")


class TestPOIIntegration(unittest.TestCase):
    """POI功能集成测试"""

    def setUp(self):
        self.loader = DataLoader(enable_fallback=False)

    def test_poi_data_structure(self):
        """测试POI数据结构一致性"""
        # 验证DataLoader有POI相关方法
        self.assertTrue(hasattr(self.loader, 'fetch_poi_data'))
        self.assertTrue(hasattr(self.loader, 'fetch_community_demand'))
        self.assertTrue(hasattr(self.loader, '_save_poi_to_geojson'))

    def test_community_data_types(self):
        """测试社区数据类型"""
        df = self.loader.fetch_community_demand("成都市")

        if not df.empty:
            # 验证数据类型
            self.assertTrue(pd.api.types.is_numeric_dtype(df['lon']))
            self.assertTrue(pd.api.types.is_numeric_dtype(df['lat']))
            self.assertTrue(pd.api.types.is_integer_dtype(df['population']))
            self.assertTrue(pd.api.types.is_float_dtype(df['elderly_ratio']))


if __name__ == "__main__":
    unittest.main(verbosity=2)
