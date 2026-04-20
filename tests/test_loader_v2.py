# tests/test_loader_v2.py
"""
DataLoaderV2 单元测试

测试范围:
1. CacheManager 缓存管理器（版本控制、过期策略）
2. VersionedDataFrame 带版本信息的数据框
3. DataMeta 元数据结构
4. DataLoaderV2 数据装载机

优化验证 (2026-04-17):
- 验证缓存版本控制功能
- 验证 Mock 数据标识功能
- 验证缓存过期策略
- 验证异常处理逻辑
"""

import unittest
import json
import time
import tempfile
import shutil
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
root = str(Path(__file__).parent.parent)
if root not in sys.path:
    sys.path.insert(0, root)

from modules.data.loader_v2 import (
    CacheManager,
    VersionedDataFrame,
    DataMeta,
    CacheMetadata,
    DataLoaderV2,
    DataSourceType
)


class TestCacheMetadata(unittest.TestCase):
    """测试缓存元数据结构"""
    
    def test_creation(self):
        """测试创建元数据"""
        meta = CacheMetadata(
            version="1.0.0",
            created_at=datetime.now().isoformat(),
            data_source="test_source",
            row_count=100
        )
        
        self.assertEqual(meta.version, "1.0.0")
        self.assertEqual(meta.data_source, "test_source")
        self.assertEqual(meta.row_count, 100)
    
    def test_serialization(self):
        """测试序列化和反序列化"""
        original = CacheMetadata(
            version="2.0.0",
            created_at="2024-01-01T00:00:00",
            expires_at="2024-01-02T00:00:00",
            is_mock=True
        )
        
        # 序列化
        data = original.to_dict()
        
        # 反序列化
        restored = CacheMetadata.from_dict(data)
        
        self.assertEqual(original.version, restored.version)
        self.assertEqual(original.is_mock, restored.is_mock)


class TestDataMeta(unittest.TestCase):
    """测试数据元数据结构"""
    
    def test_default_values(self):
        """测试默认值"""
        meta = DataMeta()
        
        self.assertFalse(meta.is_mock)
        self.assertEqual(meta.version, "1.0.0")
        self.assertIsNotNone(meta.fetched_at)
    
    def test_to_dict(self):
        """测试转换为字典"""
        meta = DataMeta(
            is_mock=True,
            data_source="test",
            row_count=50
        )
        
        data = meta.to_dict()
        
        self.assertTrue(data['is_mock'])
        self.assertEqual(data['data_source'], "test")
        self.assertEqual(data['row_count'], 50)


class TestVersionedDataFrame(unittest.TestCase):
    """测试带版本信息的数据框"""
    
    def setUp(self):
        """设置测试数据"""
        self.df = pd.DataFrame({
            'region': ['A', 'B', 'C'],
            'year': [2020, 2021, 2022],
            'value': [100, 200, 300]
        })
        self.meta = DataMeta(
            is_mock=False,
            data_source="test",
            version="1.0.0"
        )
    
    def test_creation(self):
        """测试创建"""
        vdf = VersionedDataFrame(self.df, self.meta)
        
        self.assertEqual(vdf.meta.row_count, 3)
        self.assertEqual(vdf.meta.column_count, 3)
        self.assertFalse(vdf.is_mock)
    
    def test_add_meta_column(self):
        """测试添加元数据列"""
        vdf = VersionedDataFrame(self.df, self.meta)
        result_df = vdf.add_meta_column()
        
        self.assertIn('_meta', result_df.columns)
        
        # 验证元数据可以解析
        meta_json = result_df['_meta'].iloc[0]
        parsed = json.loads(meta_json)
        self.assertEqual(parsed['data_source'], "test")
    
    def test_to_standard_format(self):
        """测试转换为标准格式"""
        vdf = VersionedDataFrame(self.df, self.meta)
        df, meta_dict = vdf.to_standard_format()
        
        pd.testing.assert_frame_equal(df, self.df)
        self.assertEqual(meta_dict['version'], "1.0.0")
    
    def test_empty_dataframe(self):
        """测试空数据框"""
        empty_df = pd.DataFrame()
        vdf = VersionedDataFrame(empty_df)
        
        self.assertTrue(vdf.df.empty)
        self.assertEqual(vdf.meta.row_count, 0)


class TestCacheManager(unittest.TestCase):
    """测试缓存管理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.cache_manager = CacheManager(
            current_version="1.0.0",
            default_ttl=3600,
            enable_redis=False  # 禁用 Redis，使用内存缓存
        )
    
    def test_generate_cache_key(self):
        """测试缓存键生成"""
        key1 = self.cache_manager._generate_cache_key(
            "owid", "life_expectancy", ["China", "USA"]
        )
        key2 = self.cache_manager._generate_cache_key(
            "owid", "life_expectancy", ["USA", "China"]  # 顺序不同
        )
        
        # 相同参数应该生成相同键（国家排序后）
        self.assertEqual(key1, key2)
        
        # 键应该包含版本号
        self.assertIn("v1.0.0", key1)
    
    def test_cache_lifecycle(self):
        """测试缓存生命周期"""
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        
        # 设置缓存
        success = self.cache_manager.set(
            "test", "indicator1", df, is_mock=False
        )
        self.assertTrue(success)
        
        # 获取缓存
        cached_df, meta = self.cache_manager.get("test", "indicator1")
        
        self.assertIsNotNone(cached_df)
        self.assertTrue(meta.cache_hit)
        self.assertEqual(meta.version, "1.0.0")
        self.assertFalse(meta.is_mock)
    
    def test_version_mismatch(self):
        """测试版本不匹配时缓存失效"""
        df = pd.DataFrame({'a': [1, 2]})
        
        # 使用版本 1.0.0 设置缓存
        self.cache_manager.set("test", "v1", df)
        
        # 修改版本号
        self.cache_manager.current_version = "2.0.0"
        
        # 尝试获取缓存（应该失败，因为版本不匹配）
        cached_df, meta = self.cache_manager.get("test", "v1")
        
        self.assertIsNone(cached_df)
    
    def test_cache_expiration(self):
        """测试缓存过期"""
        df = pd.DataFrame({'a': [1, 2]})
        
        # 设置短过期时间的缓存
        self.cache_manager.set(
            "test", "expire_test", df, ttl=1  # 1秒过期
        )
        
        # 立即获取应该成功
        cached_df, _ = self.cache_manager.get("test", "expire_test")
        self.assertIsNotNone(cached_df)
        
        # 等待过期
        time.sleep(2)
        
        # 过期后获取应该失败
        cached_df, _ = self.cache_manager.get("test", "expire_test")
        self.assertIsNone(cached_df)
    
    def test_invalidate_by_version(self):
        """测试按版本失效缓存"""
        df = pd.DataFrame({'a': [1, 2]})
        
        # 设置多个缓存
        self.cache_manager.set("source1", "ind1", df)
        self.cache_manager.set("source1", "ind2", df)
        self.cache_manager.set("source2", "ind1", df)
        
        # 验证缓存存在
        self.assertIsNotNone(self.cache_manager.get("source1", "ind1")[0])
        
        # 使版本 1.0.0 的缓存失效
        count = self.cache_manager.invalidate_by_version("1.0.0")
        
        self.assertGreaterEqual(count, 3)  # 至少失效3个内存缓存
        
        # 验证缓存已失效
        self.assertIsNone(self.cache_manager.get("source1", "ind1")[0])
    
    def test_is_cache_valid(self):
        """测试缓存有效性检查"""
        # 有效缓存
        valid_meta = CacheMetadata(
            version="1.0.0",
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=1)).isoformat()
        )
        self.assertTrue(self.cache_manager._is_cache_valid(valid_meta))
        
        # 版本不匹配
        invalid_version_meta = CacheMetadata(
            version="0.9.0",
            created_at=datetime.now().isoformat()
        )
        self.assertFalse(self.cache_manager._is_cache_valid(invalid_version_meta))
        
        # 已过期
        expired_meta = CacheMetadata(
            version="1.0.0",
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() - timedelta(hours=1)).isoformat()
        )
        self.assertFalse(self.cache_manager._is_cache_valid(expired_meta))
    
    def test_get_stats(self):
        """测试获取统计信息"""
        df = pd.DataFrame({'a': [1, 2]})
        self.cache_manager.set("test", "stat_test", df)
        
        stats = self.cache_manager.get_stats()
        
        self.assertEqual(stats['current_version'], "1.0.0")
        self.assertEqual(stats['memory_cache_items'], 1)
        self.assertFalse(stats['use_redis'])


class TestDataLoaderV2(unittest.TestCase):
    """测试 DataLoaderV2"""
    
    def setUp(self):
        """设置测试环境"""
        self.loader = DataLoaderV2(enable_cache=True, cache_ttl=3600)
    
    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.loader.CURRENT_VERSION, "2.0.0")
        self.assertTrue(self.loader.enable_cache)
        self.assertIsNotNone(self.loader.cache_manager)
    
    def test_create_mock_data(self):
        """测试创建 Mock 数据"""
        mock = self.loader._create_mock_data(
            "test_source", "test_indicator",
            reason="测试原因"
        )
        
        self.assertTrue(mock.is_mock)
        self.assertEqual(mock.meta.data_source, "test_source")
        self.assertIn("测试原因", mock.meta.notes)
        self.assertTrue(mock.df.empty)  # Mock 数据默认是空的
    
    def test_mock_data_with_schema(self):
        """测试带模式的 Mock 数据"""
        schema = {'col1': 'int', 'col2': 'str'}
        mock = self.loader._create_mock_data(
            "source", "ind",
            schema=schema,
            reason="测试"
        )

        # 验证列名 - 使用 list() 确保正确比较
        columns = list(mock.df.columns)
        self.assertIn('col1', columns)
        self.assertIn('col2', columns)
    
    def test_cache_stats(self):
        """测试缓存统计"""
        stats = self.loader.get_cache_stats()
        
        self.assertIn('current_version', stats)
        self.assertIn('memory_cache_items', stats)
    
    def test_invalidate_old_cache(self):
        """测试使旧缓存失效"""
        # 设置一些缓存
        df = pd.DataFrame({'a': [1]})
        self.loader.cache_manager.set("s", "i", df)
        
        # 使旧版本缓存失效
        count = self.loader.invalidate_old_cache("1.0.0")
        
        # 应该返回失效的数量（可能为0，因为版本是2.0.0）
        self.assertIsInstance(count, int)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 1. 创建 Loader
        loader = DataLoaderV2(enable_cache=True)
        
        # 2. 模拟 API 调用失败，应该返回 Mock 数据
        def failing_fetch(**kwargs):
            raise Exception("API Error")
        
        result = loader.api_call_with_fallback(
            "test", "indicator",
            failing_fetch
        )
        
        # 验证返回的是 Mock 数据
        self.assertTrue(result.is_mock)
        self.assertIn("API Error", result.meta.notes)
        
        # 3. 验证元数据完整性
        meta_dict = result.meta.to_dict()
        self.assertIn('is_mock', meta_dict)
        self.assertIn('version', meta_dict)
        self.assertIn('fetched_at', meta_dict)


class TestCacheVersionControl(unittest.TestCase):
    """测试缓存版本控制功能"""
    
    def test_version_upgrade_scenario(self):
        """测试版本升级场景"""
        # 模拟旧版本缓存
        old_cache = CacheManager(
            current_version="1.0.0",
            enable_redis=False
        )
        df = pd.DataFrame({'data': [1, 2, 3]})
        old_cache.set("source", "indicator", df)
        
        # 验证旧版本缓存可用
        cached, _ = old_cache.get("source", "indicator")
        self.assertIsNotNone(cached)
        
        # 升级到 2.0.0
        new_cache = CacheManager(
            current_version="2.0.0",
            enable_redis=False
        )
        # 复制内存缓存（模拟实际情况）
        new_cache._memory_cache = old_cache._memory_cache
        new_cache._cache_metadata = old_cache._cache_metadata
        
        # 新版本应该无法获取旧版本缓存
        cached, _ = new_cache.get("source", "indicator")
        self.assertIsNone(cached)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestCacheMetadata))
    suite.addTests(loader.loadTestsFromTestCase(TestDataMeta))
    suite.addTests(loader.loadTestsFromTestCase(TestVersionedDataFrame))
    suite.addTests(loader.loadTestsFromTestCase(TestCacheManager))
    suite.addTests(loader.loadTestsFromTestCase(TestDataLoaderV2))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestCacheVersionControl))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
