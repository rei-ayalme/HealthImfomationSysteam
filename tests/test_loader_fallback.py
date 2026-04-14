"""
DataLoader 降级机制单元测试与集成测试
测试覆盖：
1. 降级缓存功能
2. API 降级装饰器
3. 异常处理与降级策略
"""

import time
import unittest
from unittest.mock import MagicMock, patch, Mock
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.data.loader import DataLoader


class TestFallbackCache(unittest.TestCase):
    """降级缓存功能测试"""

    def setUp(self):
        self.loader = DataLoader(enable_fallback=True, fallback_expire=3600)

    def test_cache_key_generation(self):
        """测试缓存键生成"""
        key1 = self.loader._get_cache_key('owid', 'test_indicator')
        self.assertEqual(key1, 'loader:fallback:owid:test_indicator:all')

        key2 = self.loader._get_cache_key('who', 'test_indicator', target_countries=['USA', 'CHN'])
        self.assertEqual(key2, 'loader:fallback:who:test_indicator:CHN,USA')

    def test_memory_cache_set_and_get(self):
        """测试内存缓存设置和获取"""
        df = pd.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
        cache_key = 'test:cache:key'

        # 设置缓存
        result = self.loader._set_fallback_data(cache_key, df)
        self.assertTrue(result)

        # 获取缓存
        cached_df = self.loader._get_fallback_data(cache_key)
        self.assertIsNotNone(cached_df)
        self.assertEqual(len(cached_df), 3)
        self.assertListEqual(list(cached_df.columns), ['col1', 'col2'])

    def test_memory_cache_expiration(self):
        """测试内存缓存过期"""
        # 创建短过期时间的 loader
        loader = DataLoader(enable_fallback=True, fallback_expire=1)
        df = pd.DataFrame({'col': [1, 2, 3]})
        cache_key = 'test:expiring:key'

        # 设置缓存
        loader._set_fallback_data(cache_key, df)

        # 立即获取应该成功
        cached = loader._get_fallback_data(cache_key)
        self.assertIsNotNone(cached)

        # 等待过期
        time.sleep(1.1)

        # 过期后获取应该失败
        cached = loader._get_fallback_data(cache_key)
        self.assertIsNone(cached)

    def test_empty_dataframe_not_cached(self):
        """测试空 DataFrame 不会被缓存"""
        df = pd.DataFrame()
        cache_key = 'test:empty:key'

        result = self.loader._set_fallback_data(cache_key, df)
        self.assertFalse(result)

    def test_disabled_fallback(self):
        """测试禁用降级缓存"""
        loader = DataLoader(enable_fallback=False)
        df = pd.DataFrame({'col': [1, 2, 3]})
        cache_key = 'test:disabled:key'

        # 设置应该失败
        result = loader._set_fallback_data(cache_key, df)
        self.assertFalse(result)

        # 获取应该返回 None
        cached = loader._get_fallback_data(cache_key)
        self.assertIsNone(cached)


class TestAPIFallbackDecorator(unittest.TestCase):
    """API 降级装饰器测试"""

    def setUp(self):
        self.loader = DataLoader(enable_fallback=True, fallback_expire=3600)

    def test_decorator_caches_successful_result(self):
        """测试装饰器缓存成功的结果"""
        call_count = [0]

        @self.loader.api_fallback_decorator(source='test', indicator_param='indicator')
        def mock_api_call(indicator, target_countries=None):
            call_count[0] += 1
            return pd.DataFrame({'indicator': [indicator], 'value': [100]})

        # 第一次调用
        result1 = mock_api_call('test_indicator')
        self.assertEqual(call_count[0], 1)
        self.assertEqual(len(result1), 1)

        # 第二次调用（装饰器会调用函数，但失败时会使用缓存）
        result2 = mock_api_call('test_indicator')
        self.assertEqual(call_count[0], 2)  # 会再次调用
        self.assertEqual(len(result2), 1)

        # 验证缓存已设置
        cached = self.loader._get_fallback_data(
            self.loader._get_cache_key('test', 'test_indicator')
        )
        self.assertIsNotNone(cached)

    def test_decorator_returns_fallback_on_failure(self):
        """测试装饰器在失败时返回降级数据"""
        call_count = [0]

        # 首先缓存一些数据
        df = pd.DataFrame({'indicator': ['cached'], 'value': [50]})
        self.loader._set_fallback_data(
            self.loader._get_cache_key('test', 'fail_indicator'),
            df
        )

        @self.loader.api_fallback_decorator(source='test', indicator_param='indicator')
        def failing_api_call(indicator, target_countries=None):
            call_count[0] += 1
            raise Exception("API Error")

        # 调用应该返回缓存数据
        result = failing_api_call('fail_indicator')
        self.assertEqual(call_count[0], 1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result['value'].iloc[0], 50)

    def test_decorator_returns_empty_on_no_fallback(self):
        """测试无缓存时返回空 DataFrame"""
        @self.loader.api_fallback_decorator(source='test', indicator_param='indicator')
        def failing_api_call(indicator, target_countries=None):
            raise Exception("API Error")

        result = failing_api_call('no_cache_indicator')
        self.assertTrue(result.empty)


class TestOWIDFallback(unittest.TestCase):
    """OWID API 降级测试"""

    def setUp(self):
        self.loader = DataLoader(enable_fallback=True, fallback_expire=3600)

    @patch.object(DataLoader, '_fetch_owid_data_impl')
    def test_owid_success_caches_result(self, mock_impl):
        """测试 OWID 成功时缓存结果"""
        mock_df = pd.DataFrame({
            'country_name': ['China', 'USA'],
            'value': [10.0, 20.0]
        })
        mock_impl.return_value = mock_df

        # 第一次调用
        result1 = self.loader._fetch_owid_data('test_indicator')
        self.assertEqual(len(result1), 2)
        self.assertEqual(mock_impl.call_count, 1)

        # 第二次调用（会继续调用实现，但缓存已更新）
        result2 = self.loader._fetch_owid_data('test_indicator')
        self.assertEqual(len(result2), 2)
        self.assertEqual(mock_impl.call_count, 2)

        # 验证缓存已设置
        cached = self.loader._get_fallback_data(
            self.loader._get_cache_key('owid', 'test_indicator')
        )
        self.assertIsNotNone(cached)
        self.assertEqual(len(cached), 2)

    @patch.object(DataLoader, '_fetch_owid_data_impl')
    def test_owid_failure_returns_fallback(self, mock_impl):
        """测试 OWID 失败时返回降级数据"""
        # 先缓存数据
        cached_df = pd.DataFrame({
            'country_name': ['Cached'],
            'value': [99.0]
        })
        self.loader._set_fallback_data(
            self.loader._get_cache_key('owid', 'test_indicator'),
            cached_df
        )

        # 模拟失败
        mock_impl.side_effect = Exception("Network Error")

        result = self.loader._fetch_owid_data('test_indicator')
        self.assertEqual(len(result), 1)
        self.assertEqual(result['value'].iloc[0], 99.0)


class TestWHOFallback(unittest.TestCase):
    """WHO API 降级测试"""

    def setUp(self):
        self.loader = DataLoader(enable_fallback=True, fallback_expire=3600)

    @patch.object(DataLoader, '_fetch_who_data_impl')
    def test_who_success_caches_result(self, mock_impl):
        """测试 WHO 成功时缓存结果"""
        mock_df = pd.DataFrame({
            'region': ['China'],
            'value': [100.0]
        })
        mock_impl.return_value = mock_df

        result = self.loader._fetch_who_data('test_indicator')
        self.assertEqual(len(result), 1)

    @patch.object(DataLoader, '_fetch_who_data_impl')
    def test_who_failure_returns_fallback(self, mock_impl):
        """测试 WHO 失败时返回降级数据"""
        cached_df = pd.DataFrame({'region': ['Cached'], 'value': [50.0]})
        self.loader._set_fallback_data(
            self.loader._get_cache_key('who', 'test_indicator'),
            cached_df
        )

        mock_impl.side_effect = Exception("API Error")

        result = self.loader._fetch_who_data('test_indicator')
        self.assertEqual(len(result), 1)
        self.assertEqual(result['value'].iloc[0], 50.0)


class TestWorldBankFallback(unittest.TestCase):
    """World Bank API 降级测试"""

    def setUp(self):
        self.loader = DataLoader(enable_fallback=True, fallback_expire=3600)

    @patch.object(DataLoader, '_fetch_world_bank_data_impl')
    def test_world_bank_success_caches_result(self, mock_impl):
        """测试 World Bank 成功时缓存结果"""
        mock_df = pd.DataFrame({
            'region': ['CHN'],
            'value': [75.0]
        })
        mock_impl.return_value = mock_df

        result = self.loader._fetch_world_bank_data('test_indicator')
        self.assertEqual(len(result), 1)

    @patch.object(DataLoader, '_fetch_world_bank_data_impl')
    def test_world_bank_failure_returns_fallback(self, mock_impl):
        """测试 World Bank 失败时返回降级数据"""
        cached_df = pd.DataFrame({'region': ['CHN'], 'value': [25.0]})
        self.loader._set_fallback_data(
            self.loader._get_cache_key('world_bank', 'test_indicator'),
            cached_df
        )

        mock_impl.side_effect = Exception("Connection Error")

        result = self.loader._fetch_world_bank_data('test_indicator')
        self.assertEqual(len(result), 1)
        self.assertEqual(result['value'].iloc[0], 25.0)


class TestFetchAPIIntegration(unittest.TestCase):
    """fetch_api_data 集成测试"""

    def setUp(self):
        self.loader = DataLoader(enable_fallback=True, fallback_expire=3600)

    @patch.object(DataLoader, '_fetch_owid_data_impl')
    def test_fetch_api_with_fallback_owid(self, mock_impl):
        """测试 fetch_api_data 使用 OWID 降级"""
        mock_df = pd.DataFrame({
            'country_name': ['Test'],
            'value': [42.0]
        })
        mock_impl.return_value = mock_df

        # 第一次调用
        result1 = self.loader.fetch_api_data('owid', 'test_indicator')
        self.assertEqual(len(result1), 1)

        # 模拟失败，第二次调用应该使用缓存
        mock_impl.side_effect = Exception("API Down")
        result2 = self.loader.fetch_api_data('owid', 'test_indicator')
        self.assertEqual(len(result2), 1)
        self.assertEqual(result2['value'].iloc[0], 42.0)


class TestRedisIntegration(unittest.TestCase):
    """Redis 集成测试"""

    def test_redis_unavailable_uses_memory(self):
        """测试 Redis 不可用时使用内存缓存"""
        with patch('modules.data.loader.REDIS_AVAILABLE', False):
            loader = DataLoader(enable_fallback=True)
            self.assertIsNone(loader._redis_client)

            df = pd.DataFrame({'col': [1, 2, 3]})
            cache_key = 'test:redis:unavailable'

            # 应该能正常使用内存缓存
            loader._set_fallback_data(cache_key, df)
            cached = loader._get_fallback_data(cache_key)
            self.assertIsNotNone(cached)


class TestCacheKeyWithCountries(unittest.TestCase):
    """带国家参数的缓存键测试"""

    def setUp(self):
        self.loader = DataLoader(enable_fallback=True)

    def test_different_countries_different_keys(self):
        """测试不同国家生成不同缓存键"""
        key1 = self.loader._get_cache_key('owid', 'indicator1', target_countries=['USA'])
        key2 = self.loader._get_cache_key('owid', 'indicator1', target_countries=['CHN'])
        key3 = self.loader._get_cache_key('owid', 'indicator1', target_countries=['USA', 'CHN'])

        self.assertNotEqual(key1, key2)
        self.assertNotEqual(key1, key3)
        self.assertNotEqual(key2, key3)

    def test_same_countries_same_key(self):
        """测试相同国家生成相同缓存键（顺序无关）"""
        key1 = self.loader._get_cache_key('owid', 'indicator1', target_countries=['USA', 'CHN'])
        key2 = self.loader._get_cache_key('owid', 'indicator1', target_countries=['CHN', 'USA'])

        self.assertEqual(key1, key2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
