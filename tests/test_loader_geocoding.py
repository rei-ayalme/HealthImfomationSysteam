"""
测试 loader.py 中的地理编码功能

测试 fetch_coordinates_by_address 和 batch_geocode 方法
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.data.loader import DataLoader


class TestFetchCoordinatesByAddress(unittest.TestCase):
    """测试 fetch_coordinates_by_address 方法"""

    def setUp(self):
        """设置测试环境"""
        self.loader = DataLoader()
        # 模拟配置
        self.loader.api_config = {
            "amap": {"api_key": "test_api_key_123"}
        }

    @patch('modules.data.loader.requests.get')
    def test_successful_geocoding(self, mock_get):
        """测试成功的地理编码"""
        # 模拟成功响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "1",
            "count": "1",
            "geocodes": [{
                "location": "116.4890,39.9350",
                "formatted_address": "北京市朝阳区朝阳公园"
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.loader.fetch_coordinates_by_address("北京市朝阳区朝阳公园")

        self.assertEqual(result, "116.4890,39.9350")
        mock_get.assert_called_once()

    @patch('modules.data.loader.requests.get')
    def test_geocoding_no_results(self, mock_get):
        """测试无结果的地理编码"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "1",
            "count": "0",
            "geocodes": []
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.loader.fetch_coordinates_by_address("不存在的地址xyz")

        self.assertIsNone(result)

    @patch('modules.data.loader.requests.get')
    def test_geocoding_api_error(self, mock_get):
        """测试API返回错误状态"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "0",
            "info": "INVALID_KEY",
            "count": "0"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.loader.fetch_coordinates_by_address("北京市朝阳区")

        self.assertIsNone(result)

    @patch('modules.data.loader.requests.get')
    def test_geocoding_timeout_retry(self, mock_get):
        """测试超时重试机制"""
        from requests.exceptions import Timeout

        # 前两次超时，第三次成功
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "1",
            "count": "1",
            "geocodes": [{"location": "116.4,39.9"}]
        }
        mock_response.raise_for_status = Mock()

        mock_get.side_effect = [Timeout(), Timeout(), mock_response]

        with patch('modules.data.loader.time.sleep', return_value=None):  # 跳过实际等待
            result = self.loader.fetch_coordinates_by_address(
                "北京市朝阳区",
                max_retries=3
            )

        self.assertEqual(result, "116.4,39.9")
        self.assertEqual(mock_get.call_count, 3)

    @patch('modules.data.loader.requests.get')
    def test_geocoding_all_retries_fail(self, mock_get):
        """测试所有重试都失败的情况"""
        from requests.exceptions import Timeout

        mock_get.side_effect = Timeout()

        with patch('modules.data.loader.time.sleep', return_value=None):
            result = self.loader.fetch_coordinates_by_address(
                "北京市朝阳区",
                max_retries=2
            )

        self.assertIsNone(result)
        self.assertEqual(mock_get.call_count, 2)

    def test_geocoding_no_api_key(self):
        """测试未配置API密钥的情况"""
        self.loader.api_config = {}  # 清空配置

        result = self.loader.fetch_coordinates_by_address("北京市朝阳区")

        self.assertIsNone(result)

    @patch('modules.data.loader.requests.get')
    def test_geocoding_request_exception(self, mock_get):
        """测试请求异常处理"""
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("网络连接失败")

        with patch('modules.data.loader.time.sleep', return_value=None):
            result = self.loader.fetch_coordinates_by_address("北京市朝阳区")

        self.assertIsNone(result)

    @patch('modules.data.loader.requests.get')
    def test_geocoding_malformed_response(self, mock_get):
        """测试异常响应格式处理"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "1",
            # 缺少 geocodes 字段
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.loader.fetch_coordinates_by_address("北京市朝阳区")

        self.assertIsNone(result)

    @patch('modules.data.loader.requests.get')
    def test_geocoding_with_city_param(self, mock_get):
        """测试指定城市参数"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "1",
            "count": "1",
            "geocodes": [{"location": "121.4737,31.2304"}]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.loader.fetch_coordinates_by_address(
            "人民广场",
            city="上海市"
        )

        self.assertEqual(result, "121.4737,31.2304")
        # 验证调用参数包含城市
        call_args = mock_get.call_args
        self.assertEqual(call_args[1]["params"]["city"], "上海市")


class TestBatchGeocode(unittest.TestCase):
    """测试 batch_geocode 批量地理编码方法"""

    def setUp(self):
        """设置测试环境"""
        self.loader = DataLoader()
        self.loader.api_config = {
            "amap": {"api_key": "test_api_key"}
        }

    @patch('modules.data.loader.DataLoader.fetch_coordinates_by_address')
    @patch('modules.data.loader.time.sleep', return_value=None)
    def test_batch_geocode_success(self, mock_sleep, mock_fetch):
        """测试批量地理编码成功"""
        mock_fetch.side_effect = [
            "116.4,39.9",
            "121.5,31.2",
            "113.3,23.1"
        ]

        addresses = ["北京", "上海", "广州"]
        results = self.loader.batch_geocode(addresses)

        self.assertEqual(results["北京"], "116.4,39.9")
        self.assertEqual(results["上海"], "121.5,31.2")
        self.assertEqual(results["广州"], "113.3,23.1")
        self.assertEqual(len(results), 3)

    @patch('modules.data.loader.DataLoader.fetch_coordinates_by_address')
    @patch('modules.data.loader.time.sleep', return_value=None)
    def test_batch_geocode_partial_failure(self, mock_sleep, mock_fetch):
        """测试批量地理编码部分失败"""
        mock_fetch.side_effect = [
            "116.4,39.9",
            None,  # 上海失败
            "113.3,23.1"
        ]

        addresses = ["北京", "上海", "广州"]
        results = self.loader.batch_geocode(addresses)

        self.assertEqual(results["北京"], "116.4,39.9")
        self.assertIsNone(results["上海"])
        self.assertEqual(results["广州"], "113.3,23.1")

    @patch('modules.data.loader.DataLoader.fetch_coordinates_by_address')
    @patch('modules.data.loader.time.sleep', return_value=None)
    def test_batch_geocode_empty_list(self, mock_sleep, mock_fetch):
        """测试空地址列表"""
        results = self.loader.batch_geocode([])

        self.assertEqual(results, {})
        mock_fetch.assert_not_called()

    @patch('modules.data.loader.DataLoader.fetch_coordinates_by_address')
    @patch('modules.data.loader.time.sleep', return_value=None)
    def test_batch_geocode_delay_between_requests(self, mock_sleep, mock_fetch):
        """测试请求间延迟"""
        mock_fetch.return_value = "116.4,39.9"

        addresses = ["地址1", "地址2", "地址3"]
        self.loader.batch_geocode(addresses, delay=0.5)

        # 3个地址，应该有2次延迟（最后一个不需要延迟）
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(0.5)


class TestGeocodingIntegration(unittest.TestCase):
    """地理编码集成测试"""

    def setUp(self):
        """设置测试环境"""
        self.loader = DataLoader()
        self.loader.api_config = {
            "AMAP_KEY": "test_key"  # 使用替代配置键
        }

    @patch('modules.data.loader.requests.get')
    def test_amap_key_fallback(self, mock_get):
        """测试 AMAP_KEY 配置回退"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "1",
            "count": "1",
            "geocodes": [{"location": "116.4,39.9"}]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # 使用 AMAP_KEY 而不是 amap.api_key
        result = self.loader.fetch_coordinates_by_address("北京市")

        self.assertEqual(result, "116.4,39.9")


class TestGeocodingCoordinateConversion(unittest.TestCase):
    """测试地理编码与坐标转换的集成"""

    @patch('modules.data.loader.requests.get')
    def test_gcj02_to_wgs84_conversion(self, mock_get):
        """测试GCJ-02转WGS-84坐标"""
        from utils.spatial_utils import gcj02_to_wgs84

        # 模拟高德返回的GCJ-02坐标
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "1",
            "count": "1",
            "geocodes": [{"location": "116.397428,39.90923"}]  # 天安门GCJ-02
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        loader = DataLoader()
        loader.api_config = {"amap": {"api_key": "test"}}

        gcj_coords = loader.fetch_coordinates_by_address("天安门")
        self.assertIsNotNone(gcj_coords)

        # 解析坐标
        lon, lat = map(float, gcj_coords.split(','))

        # 转换为WGS-84
        wgs_lat, wgs_lon = gcj02_to_wgs84(lat, lon)

        # 验证转换结果合理（WGS-84与GCJ-02有偏移但相近）
        self.assertAlmostEqual(wgs_lat, lat, delta=0.1)
        self.assertAlmostEqual(wgs_lon, lon, delta=0.1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
