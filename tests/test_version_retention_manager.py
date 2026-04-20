# tests/test_version_retention_manager.py
"""
版本保留管理器单元测试

测试范围:
1. VersionedFile 数据类
2. VersionRetentionManager 核心功能
3. 版本解析和排序
4. 清理和验证流程

作者: AI Assistant
日期: 2026-04-17
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
root = str(Path(__file__).parent.parent)
if root not in sys.path:
    sys.path.insert(0, root)

from utils.version_retention_manager import (
    VersionedFile,
    CleanupResult,
    VersionRetentionManager
)


class TestVersionedFile(unittest.TestCase):
    """测试 VersionedFile 数据类"""
    
    def setUp(self):
        """创建临时测试文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test_v1.py"
        self.test_file.write_text("# test content")
    
    def tearDown(self):
        """清理临时文件"""
        shutil.rmtree(self.temp_dir)
    
    def test_creation(self):
        """测试创建 VersionedFile"""
        stat = self.test_file.stat()
        vf = VersionedFile(
            path=self.test_file,
            base_name="test",
            version="1",
            version_type="suffix",
            modified_time=stat.st_mtime,
            size=stat.st_size
        )
        
        self.assertEqual(vf.base_name, "test")
        self.assertEqual(vf.version, "1")
        self.assertEqual(vf.version_type, "suffix")
        self.assertTrue(vf.checksum)  # 校验和应该已计算
    
    def test_checksum_calculation(self):
        """测试校验和计算"""
        stat = self.test_file.stat()
        vf = VersionedFile(
            path=self.test_file,
            base_name="test",
            version="1",
            version_type="suffix",
            modified_time=stat.st_mtime,
            size=stat.st_size
        )
        
        # 校验和应该是32位MD5
        self.assertEqual(len(vf.checksum), 32)
        self.assertTrue(all(c in '0123456789abcdef' for c in vf.checksum))
    
    def test_to_dict(self):
        """测试转换为字典"""
        stat = self.test_file.stat()
        vf = VersionedFile(
            path=self.test_file,
            base_name="test",
            version="1.0.0",
            version_type="suffix",
            modified_time=stat.st_mtime,
            size=100
        )
        
        data = vf.to_dict()
        
        self.assertEqual(data['base_name'], "test")
        self.assertEqual(data['version'], "1.0.0")
        self.assertEqual(data['version_type'], "suffix")
        self.assertEqual(data['size'], 100)
        self.assertIn('modified_time', data)


class TestVersionParsing(unittest.TestCase):
    """测试版本解析功能"""
    
    def setUp(self):
        self.manager = VersionRetentionManager()
    
    def test_suffix_version(self):
        """测试后缀版本解析"""
        # file_v1.py
        result = self.manager.parse_version("file_v1.py")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "file")  # base_name
        self.assertEqual(result[1], "1")     # version
        self.assertEqual(result[2], "py")    # extension
        self.assertEqual(result[3], "suffix") # type
        
        # file_v2.0.0.py
        result = self.manager.parse_version("file_v2.0.0.py")
        self.assertEqual(result[1], "2.0.0")
        
        # file_v1 (无扩展名)
        result = self.manager.parse_version("file_v1")
        self.assertEqual(result[0], "file")
        self.assertEqual(result[1], "1")
        self.assertEqual(result[2], "")  # 无扩展名
    
    def test_prefix_version(self):
        """测试前缀版本解析"""
        # v1_file.py
        result = self.manager.parse_version("v1_file.py")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "file")
        self.assertEqual(result[1], "1")
        self.assertEqual(result[3], "prefix")
        
        # v2.1.0_config.json
        result = self.manager.parse_version("v2.1.0_config.json")
        self.assertEqual(result[0], "config")
        self.assertEqual(result[1], "2.1.0")
    
    def test_date_version(self):
        """测试日期版本解析"""
        # file_20240101.py
        result = self.manager.parse_version("file_20240101.py")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "file")
        self.assertEqual(result[1], "20240101")
        self.assertEqual(result[3], "date")
        
        # file_2024-01-01.py
        result = self.manager.parse_version("file_2024-01-01.py")
        self.assertEqual(result[1], "2024-01-01")
        
        # file_202401.py (年月)
        result = self.manager.parse_version("file_202401.py")
        self.assertEqual(result[1], "202401")
    
    def test_backup_version(self):
        """测试备份版本解析"""
        # file.py.backup
        result = self.manager.parse_version("file.py.backup")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "file.py")
        self.assertEqual(result[1], "backup")
        self.assertEqual(result[3], "backup")
        
        # file.py.old
        result = self.manager.parse_version("file.py.old")
        self.assertEqual(result[1], "old")
        
        # file.backup.py
        result = self.manager.parse_version("file.backup.py")
        self.assertEqual(result[0], "file")
        self.assertEqual(result[1], "backup")
    
    def test_numeric_version(self):
        """测试数字版本解析"""
        # file.1.py
        result = self.manager.parse_version("file.1.py")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "file")
        self.assertEqual(result[1], "1")
        self.assertEqual(result[3], "numeric")
        
        # file.10.json
        result = self.manager.parse_version("file.10.json")
        self.assertEqual(result[1], "10")
    
    def test_non_versioned_file(self):
        """测试非版本化文件"""
        result = self.manager.parse_version("file.py")
        self.assertIsNone(result)
        
        result = self.manager.parse_version("README.md")
        self.assertIsNone(result)
        
        result = self.manager.parse_version("test_file.py")
        self.assertIsNone(result)


class TestVersionSorting(unittest.TestCase):
    """测试版本排序功能"""
    
    def setUp(self):
        self.manager = VersionRetentionManager()
    
    def test_numeric_version_sorting(self):
        """测试数字版本排序"""
        versions = ["1", "2", "10", "11"]
        sorted_versions = sorted(versions, 
                                key=lambda v: self.manager._version_key(v, 'suffix'),
                                reverse=True)
        
        # 应该按数值排序: 11, 10, 2, 1
        self.assertEqual(sorted_versions, ["11", "10", "2", "1"])
    
    def test_semantic_version_sorting(self):
        """测试语义版本排序"""
        versions = ["1.0.0", "1.0.1", "1.1.0", "2.0.0", "1.10.0"]
        sorted_versions = sorted(versions,
                                key=lambda v: self.manager._version_key(v, 'suffix'),
                                reverse=True)
        
        # 应该按语义版本排序: 2.0.0, 1.10.0, 1.1.0, 1.0.1, 1.0.0
        expected = ["2.0.0", "1.10.0", "1.1.0", "1.0.1", "1.0.0"]
        self.assertEqual(sorted_versions, expected)
    
    def test_date_version_sorting(self):
        """测试日期版本排序"""
        versions = ["20240101", "20231231", "20240115"]
        sorted_versions = sorted(versions,
                                key=lambda v: self.manager._version_key(v, 'date'),
                                reverse=True)
        
        # 应该按日期排序: 20240115, 20240101, 20231231
        expected = ["20240115", "20240101", "20231231"]
        self.assertEqual(sorted_versions, expected)
    
    def test_backup_version_sorting(self):
        """测试备份版本排序"""
        versions = ["bak", "old", "backup", "orig"]
        sorted_versions = sorted(versions,
                                key=lambda v: self.manager._version_key(v, 'backup'),
                                reverse=True)
        
        # backup 应该是最新的
        self.assertEqual(sorted_versions[0], "backup")


class TestDirectoryScanning(unittest.TestCase):
    """测试目录扫描功能"""
    
    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = VersionRetentionManager()
        
        # 创建测试文件
        files = [
            "module_v1.py",
            "module_v2.py",
            "module_v3.py",
            "config_v1.0.json",
            "config_v1.1.json",
            "data_20240101.csv",
            "data_20240102.csv",
            "script.py.backup",
            "script.py.old",
            "regular_file.py",  # 非版本化
        ]
        
        for filename in files:
            (Path(self.temp_dir) / filename).write_text(f"# {filename}")
    
    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.temp_dir)
    
    def test_scan_directory(self):
        """测试扫描目录"""
        groups = self.manager.scan_directory(self.temp_dir, recursive=False)
        
        # 应该识别出 4 个版本组
        self.assertEqual(len(groups), 4)
        
        # module 组应该有 3 个版本
        module_group = groups.get(f"{self.temp_dir}/module")
        self.assertIsNotNone(module_group)
        self.assertEqual(len(module_group), 3)
        
        # config 组应该有 2 个版本
        config_group = groups.get(f"{self.temp_dir}/config")
        self.assertIsNotNone(config_group)
        self.assertEqual(len(config_group), 2)
    
    def test_extension_filter(self):
        """测试扩展名过滤"""
        groups = self.manager.scan_directory(
            self.temp_dir, 
            recursive=False,
            file_extensions=['.py']
        )
        
        # 应该只包含 .py 文件
        for group in groups.values():
            for vf in group:
                self.assertTrue(str(vf.path).endswith('.py'))
    
    def test_exclude_dirs(self):
        """测试排除目录"""
        # 创建子目录
        subdir = Path(self.temp_dir) / "__pycache__"
        subdir.mkdir()
        (subdir / "cached_v1.pyc").write_text("cached")
        
        groups = self.manager.scan_directory(self.temp_dir, recursive=True)
        
        # 不应该包含 __pycache__ 中的文件
        for group_key in groups.keys():
            self.assertNotIn("__pycache__", group_key)


class TestCleanupOperation(unittest.TestCase):
    """测试清理操作"""
    
    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = VersionRetentionManager()
        
        # 创建版本化文件
        files = [
            ("module_v1.py", "# old version 1"),
            ("module_v2.py", "# old version 2"),
            ("module_v3.py", "# latest version 3"),
            ("config_v1.0.json", '{"version": "1.0"}'),
            ("config_v2.0.json", '{"version": "2.0"}'),
        ]
        
        for filename, content in files:
            (Path(self.temp_dir) / filename).write_text(content)
    
    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.temp_dir)
    
    def test_dry_run(self):
        """测试试运行模式"""
        result = self.manager.clean_directory(
            self.temp_dir,
            recursive=False,
            dry_run=True
        )
        
        # 验证所有文件仍然存在
        self.assertTrue((Path(self.temp_dir) / "module_v1.py").exists())
        self.assertTrue((Path(self.temp_dir) / "module_v2.py").exists())
        self.assertTrue((Path(self.temp_dir) / "module_v3.py").exists())
        
        # 验证结果
        self.assertTrue(result.dry_run)
        self.assertEqual(len(result.kept_files), 2)  # 每组保留1个
        self.assertEqual(len(result.removed_files), 3)  # 总共删除3个
    
    def test_actual_cleanup(self):
        """测试实际清理"""
        result = self.manager.clean_directory(
            self.temp_dir,
            recursive=False,
            dry_run=False
        )
        
        # 验证旧版本已删除
        self.assertFalse((Path(self.temp_dir) / "module_v1.py").exists())
        self.assertFalse((Path(self.temp_dir) / "module_v2.py").exists())
        
        # 验证最新版本保留
        self.assertTrue((Path(self.temp_dir) / "module_v3.py").exists())
        self.assertTrue((Path(self.temp_dir) / "config_v2.0.json").exists())
        
        # 验证结果
        self.assertFalse(result.dry_run)
        self.assertEqual(len(result.kept_files), 2)
        self.assertEqual(len(result.removed_files), 3)
    
    def test_keep_multiple_versions(self):
        """测试保留多个版本"""
        manager = VersionRetentionManager(min_versions_to_keep=2)
        
        result = manager.clean_directory(
            self.temp_dir,
            recursive=False,
            dry_run=False
        )
        
        # 应该保留 4 个文件 (每组2个)
        self.assertEqual(len(result.kept_files), 4)
        self.assertEqual(len(result.removed_files), 1)
    
    def test_protected_patterns(self):
        """测试受保护模式"""
        manager = VersionRetentionManager(
            protected_patterns=[r'.*_v1\.py$']
        )
        
        result = manager.clean_directory(
            self.temp_dir,
            recursive=False,
            dry_run=False
        )
        
        # v1 文件应该被保护
        self.assertTrue((Path(self.temp_dir) / "module_v1.py").exists())


class TestValidation(unittest.TestCase):
    """测试验证功能"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = VersionRetentionManager()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_validate_success(self):
        """测试验证通过"""
        # 创建测试文件
        (Path(self.temp_dir) / "file_v1.py").write_text("v1")
        (Path(self.temp_dir) / "file_v2.py").write_text("v2")
        
        # 执行清理
        result = self.manager.clean_directory(
            self.temp_dir,
            dry_run=False
        )
        
        # 验证结果
        is_valid = self.manager.validate_cleanup(result)
        self.assertTrue(is_valid)
    
    def test_validate_failure_kept_not_exist(self):
        """测试验证失败 - 保留文件不存在"""
        result = CleanupResult(directory=self.temp_dir)
        
        # 添加不存在的文件到保留列表
        vf = VersionedFile(
            path=Path(self.temp_dir) / "nonexistent.py",
            base_name="nonexistent",
            version="1",
            version_type="suffix",
            modified_time=0,
            size=0
        )
        result.kept_files.append(vf)
        
        is_valid = self.manager.validate_cleanup(result)
        self.assertFalse(is_valid)
    
    def test_validate_failure_duplicate(self):
        """测试验证失败 - 文件重复"""
        test_file = Path(self.temp_dir) / "file_v1.py"
        test_file.write_text("v1")
        
        result = CleanupResult(directory=self.temp_dir)
        
        vf = VersionedFile(
            path=test_file,
            base_name="file",
            version="1",
            version_type="suffix",
            modified_time=0,
            size=10
        )
        
        # 同时添加到保留和删除列表
        result.kept_files.append(vf)
        result.removed_files.append(vf)
        
        is_valid = self.manager.validate_cleanup(result)
        self.assertFalse(is_valid)


class TestReportGeneration(unittest.TestCase):
    """测试报告生成功能"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = VersionRetentionManager()
        
        # 创建测试文件
        (Path(self.temp_dir) / "file_v1.py").write_text("v1")
        (Path(self.temp_dir) / "file_v2.py").write_text("v2")
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_save_report(self):
        """测试保存报告"""
        result = self.manager.clean_directory(
            self.temp_dir,
            dry_run=True
        )
        
        report_path = Path(self.temp_dir) / "cleanup_report.json"
        result.save_report(str(report_path))
        
        # 验证报告文件
        self.assertTrue(report_path.exists())
        
        # 验证报告内容
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        self.assertIn('directory', data)
        self.assertIn('timestamp', data)
        self.assertIn('kept_files', data)
        self.assertIn('removed_files', data)
        self.assertEqual(data['kept_count'], 1)
        self.assertEqual(data['removed_count'], 1)


class TestPreviewFunction(unittest.TestCase):
    """测试预览功能"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = VersionRetentionManager()
        
        # 创建测试文件
        for i in range(1, 4):
            (Path(self.temp_dir) / f"file_v{i}.py").write_text(f"v{i}")
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_preview_cleanup(self):
        """测试清理预览"""
        preview = self.manager.preview_cleanup(self.temp_dir)
        
        # 验证摘要
        self.assertIn('summary', preview)
        self.assertEqual(preview['summary']['total_scanned'], 3)
        self.assertEqual(preview['summary']['will_keep'], 1)
        self.assertEqual(preview['summary']['will_remove'], 2)
        self.assertGreater(preview['summary']['can_free_space'], 0)
        
        # 验证分组
        self.assertIn('groups', preview)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestVersionedFile))
    suite.addTests(loader.loadTestsFromTestCase(TestVersionParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestVersionSorting))
    suite.addTests(loader.loadTestsFromTestCase(TestDirectoryScanning))
    suite.addTests(loader.loadTestsFromTestCase(TestCleanupOperation))
    suite.addTests(loader.loadTestsFromTestCase(TestValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestReportGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestPreviewFunction))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
