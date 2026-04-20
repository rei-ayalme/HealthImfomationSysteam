# tests/test_integrated_pipeline_v2.py
"""
统一数据调用管道单元测试

测试范围:
1. ColumnMappingManager 列名映射管理
2. DataCache 数据缓存机制
3. DataValidator 数据验证器
4. IntegratedPipeline 统一管道

优化验证 (2026-04-17):
- 验证动态列名映射功能
- 验证数据缓存消除冗余调用
- 验证性能监控指标记录
- 验证数据格式验证功能
"""

import unittest
import json
import tempfile
import shutil
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
root = str(Path(__file__).parent.parent)
if root not in sys.path:
    sys.path.insert(0, root)

from modules.integrated_pipeline_v2 import (
    ColumnMappingManager,
    DataCache,
    DataValidator,
    DataLoadMetrics,
    IntegratedPipeline
)


class TestColumnMappingManager(unittest.TestCase):
    """测试列名映射管理器"""
    
    def setUp(self):
        """创建临时配置文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_column_mapping.json"
        
        test_config = {
            "_meta": {"version": "1.0.0"},
            "region_name": {
                "standard_name": "region_name",
                "aliases": ["地区", "省份", "region", "province"]
            },
            "population": {
                "standard_name": "population",
                "aliases": ["人口", "总人口", "population", "pop"]
            },
            "physicians": {
                "standard_name": "physicians",
                "aliases": ["医生", "医师", "physicians", "doctors"]
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False)
        
        self.manager = ColumnMappingManager(str(self.config_file))
    
    def tearDown(self):
        """清理临时文件"""
        shutil.rmtree(self.temp_dir)
    
    def test_get_standard_name(self):
        """测试获取标准列名"""
        # 测试中文别名
        self.assertEqual(self.manager.get_standard_name("地区"), "region_name")
        self.assertEqual(self.manager.get_standard_name("省份"), "region_name")
        
        # 测试英文别名
        self.assertEqual(self.manager.get_standard_name("region"), "region_name")
        self.assertEqual(self.manager.get_standard_name("province"), "region_name")
        
        # 测试标准名称本身
        self.assertEqual(self.manager.get_standard_name("region_name"), "region_name")
        
        # 测试不存在的列名
        self.assertIsNone(self.manager.get_standard_name("不存在的列"))
    
    def test_create_mapping_dict(self):
        """测试创建映射字典"""
        columns = ["地区", "人口", "医生数", "未知列"]
        mapping = self.manager.create_mapping_dict(columns)
        
        self.assertEqual(mapping["地区"], "region_name")
        self.assertEqual(mapping["人口"], "population")
        # 未知列不会被映射
        self.assertNotIn("未知列", mapping)
    
    def test_apply_mapping(self):
        """测试应用列名映射"""
        df = pd.DataFrame({
            "地区": ["北京", "上海"],
            "人口": [2000, 2500],
            "医生": [50000, 60000]
        })
        
        df_mapped = self.manager.apply_mapping(df)
        
        self.assertIn("region_name", df_mapped.columns)
        self.assertIn("population", df_mapped.columns)
        # "医生" 应该被映射到 "physicians"
        self.assertIn("physicians", df_mapped.columns)
    
    def test_validate_columns(self):
        """测试列验证"""
        df = pd.DataFrame({
            "region_name": ["北京", "上海"],
            "population": [2000, 2500]
        })
        
        # 验证存在的列
        is_valid, missing = self.manager.validate_columns(df, ["region_name", "population"])
        self.assertTrue(is_valid)
        self.assertEqual(len(missing), 0)
        
        # 验证缺失的列
        is_valid, missing = self.manager.validate_columns(df, ["region_name", "physicians"])
        self.assertFalse(is_valid)
        self.assertIn("physicians", missing)


class TestDataCache(unittest.TestCase):
    """测试数据缓存管理器"""
    
    def setUp(self):
        """创建临时缓存目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = DataCache(max_memory_items=3, cache_dir=self.temp_dir)
    
    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.temp_dir)
    
    def test_cache_key_generation(self):
        """测试缓存键生成"""
        key1 = self.cache._generate_cache_key("source1", {"a": 1, "b": 2})
        key2 = self.cache._generate_cache_key("source1", {"b": 2, "a": 1})
        key3 = self.cache._generate_cache_key("source2", {"a": 1, "b": 2})
        
        # 相同参数应该生成相同键（不考虑顺序）
        self.assertEqual(key1, key2)
        # 不同数据源应该生成不同键
        self.assertNotEqual(key1, key3)
    
    def test_memory_cache(self):
        """测试内存缓存"""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        
        # 保存到缓存
        self.cache.set("test_source", {"param": 1}, df)
        
        # 从缓存获取
        cached_df, cache_hit = self.cache.get("test_source", {"param": 1})
        
        self.assertTrue(cache_hit)
        self.assertIsNotNone(cached_df)
        pd.testing.assert_frame_equal(df, cached_df)
    
    def test_file_cache(self):
        """测试文件缓存"""
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        
        # 保存到缓存
        self.cache.set("file_test", {"year": 2020}, df)
        
        # 清空内存缓存，强制从文件读取
        self.cache._memory_cache.clear()
        
        # 从文件缓存获取
        cached_df, cache_hit = self.cache.get("file_test", {"year": 2020})
        
        self.assertTrue(cache_hit)
        self.assertIsNotNone(cached_df)
        pd.testing.assert_frame_equal(df, cached_df)
    
    def test_cache_miss(self):
        """测试缓存未命中"""
        cached_df, cache_hit = self.cache.get("nonexistent", {"param": 1})
        
        self.assertFalse(cache_hit)
        self.assertIsNone(cached_df)
    
    def test_lru_eviction(self):
        """测试LRU淘汰策略"""
        # 添加超过最大数量的缓存项
        for i in range(5):
            df = pd.DataFrame({"data": [i]})
            self.cache.set(f"source_{i}", {}, df)
        
        # 内存缓存应该只保留最近3个
        self.assertEqual(len(self.cache._memory_cache), 3)
    
    def test_clear_cache(self):
        """测试清空缓存"""
        df = pd.DataFrame({"a": [1]})
        self.cache.set("test", {}, df)
        
        self.cache.clear()
        
        self.assertEqual(len(self.cache._memory_cache), 0)
        self.assertEqual(len(list(Path(self.temp_dir).glob("*.parquet"))), 0)


class TestDataValidator(unittest.TestCase):
    """测试数据验证器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        config_file = Path(self.temp_dir) / "mapping.json"
        
        test_config = {
            "region_name": {"standard_name": "region_name", "aliases": ["地区"]},
            "population": {"standard_name": "population", "aliases": ["人口"]}
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f)
        
        self.column_manager = ColumnMappingManager(str(config_file))
        self.validator = DataValidator(self.column_manager)
    
    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir)
    
    def test_validate_empty_dataframe(self):
        """测试验证空数据框"""
        df = pd.DataFrame()
        is_valid, errors = self.validator.validate_dataframe(df)
        
        self.assertFalse(is_valid)
        self.assertIn("数据框为空", errors)
    
    def test_validate_required_columns(self):
        """测试验证必需列"""
        df = pd.DataFrame({
            "region_name": ["北京", "上海"],
            "population": [1000, 2000]
        })
        
        is_valid, errors = self.validator.validate_dataframe(
            df, required_columns=["region_name"]
        )
        self.assertTrue(is_valid)
        
        is_valid, errors = self.validator.validate_dataframe(
            df, required_columns=["region_name", "missing_col"]
        )
        self.assertFalse(is_valid)
    
    def test_validate_numeric_columns(self):
        """测试验证数值列"""
        df = pd.DataFrame({
            "region_name": ["北京", "上海"],
            "population": [1000, "not_a_number"]  # 包含非数值
        })
        
        # 先转换类型
        df["population"] = pd.to_numeric(df["population"], errors='coerce')
        
        is_valid, errors = self.validator.validate_dataframe(
            df, numeric_columns=["population"]
        )
        # 转换后应该是数值类型
        self.assertTrue(is_valid or not errors)
    
    def test_validate_infinite_values(self):
        """测试验证无穷大值"""
        df = pd.DataFrame({
            "region_name": ["北京", "上海"],
            "value": [1.0, np.inf]
        })
        
        is_valid, errors = self.validator.validate_dataframe(df)
        self.assertFalse(is_valid)
        self.assertTrue(any("无穷大" in err for err in errors))
    
    def test_clean_dataframe(self):
        """测试清洗数据框"""
        df = pd.DataFrame({
            "a": [1, 2, None, np.inf],
            "b": [4, 5, 6, 7]
        })
        
        df_clean = self.validator.clean_dataframe(df)
        
        # 验证行数（清洗后应该保留所有行，但inf被替换为NaN）
        self.assertEqual(len(df_clean), 4)
        # 无穷大值应该被替换为NaN
        self.assertFalse(np.isinf(df_clean['a']).any())
        # 验证NaN值存在（原来的None和inf转换后的NaN）
        self.assertTrue(df_clean['a'].isna().any())


class TestDataLoadMetrics(unittest.TestCase):
    """测试数据加载性能指标"""
    
    def test_metrics_calculation(self):
        """测试指标计算"""
        import time
        
        metrics = DataLoadMetrics(data_source="test")
        time.sleep(0.01)  # 等待10ms
        metrics.load_end_time = time.time()
        
        # 验证耗时计算
        self.assertGreaterEqual(metrics.load_duration_ms, 10)
        
        # 验证字典转换
        dict_data = metrics.to_dict()
        self.assertIn('load_duration_ms', dict_data)
        self.assertIn('cache_hit', dict_data)
        self.assertEqual(dict_data['data_source'], "test")


class TestIntegratedPipeline(unittest.TestCase):
    """测试统一管道（需要更多设置，可以标记为集成测试）"""
    
    @unittest.skip("需要完整的数据库和配置环境")
    def test_pipeline_initialization(self):
        """测试管道初始化"""
        # 此测试需要完整的环境，通常作为集成测试运行
        pass
    
    def test_performance_metrics(self):
        """测试性能指标收集"""
        # 创建模拟的指标数据
        metrics_list = [
            DataLoadMetrics(data_source="source1", rows_loaded=100),
            DataLoadMetrics(data_source="source2", rows_loaded=200, cache_hit=True),
        ]
        
        # 验证指标属性
        self.assertEqual(metrics_list[0].rows_loaded, 100)
        self.assertTrue(metrics_list[1].cache_hit)


class TestColumnMappingIntegration(unittest.TestCase):
    """列名映射集成测试"""
    
    def test_real_column_mapping_file(self):
        """测试使用真实的列名映射文件"""
        # 尝试加载真实的配置文件
        real_config_path = Path(__file__).parent.parent / "config" / "column_mapping.json"
        
        if not real_config_path.exists():
            self.skipTest("真实的列名映射文件不存在")
        
        manager = ColumnMappingManager(str(real_config_path))
        
        # 验证核心列映射
        self.assertIsNotNone(manager.get_standard_name("地区"))
        self.assertIsNotNone(manager.get_standard_name("人口"))
        self.assertIsNotNone(manager.get_standard_name("执业医师"))
        
        # 验证版本信息
        version = manager.column_map.get("_meta", {}).get("version")
        self.assertIsNotNone(version)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestColumnMappingManager))
    suite.addTests(loader.loadTestsFromTestCase(TestDataCache))
    suite.addTests(loader.loadTestsFromTestCase(TestDataValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestDataLoadMetrics))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegratedPipeline))
    suite.addTests(loader.loadTestsFromTestCase(TestColumnMappingIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
