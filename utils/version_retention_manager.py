# utils/version_retention_manager.py
"""
版本保留管理器 - Version Retention Manager

功能说明:
    自动识别并清理旧版本文件，仅保留最新版本，防止版本混乱和存储浪费。
    
    支持的版本命名模式:
    1. 后缀版本: file_v1.py, file_v2.py, file_v1.0.0.py
    2. 前缀版本: v1_file.py, v2_file.py
    3. 日期版本: file_20240101.py, file_2024-01-01.py
    4. 备份版本: file.py.backup, file.py.old, file.py.bak
    5. 数字版本: file.1.py, file.2.py
    
使用示例:
    >>> from utils.version_retention_manager import VersionRetentionManager
    >>> 
    >>> # 创建管理器实例
    >>> manager = VersionRetentionManager()
    >>> 
    >>> # 扫描并清理特定目录
    >>> result = manager.clean_directory('modules/data', dry_run=False)
    >>> print(f"清理完成: 保留 {result['kept']} 个, 删除 {result['removed']} 个")
    >>> 
    >>> # 仅查看不删除 (dry run)
    >>> preview = manager.clean_directory('modules/data', dry_run=True)
    >>> 
    >>> # 验证清理结果
    >>> is_valid = manager.validate_cleanup(result)

作者: AI Assistant
日期: 2026-04-17
版本: 1.0.0
"""

import os
import re
import shutil
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class VersionedFile:
    """版本化文件信息"""
    path: Path
    base_name: str  # 基础文件名 (不含版本号)
    version: str    # 版本标识
    version_type: str  # 版本类型: suffix, prefix, date, backup, numeric
    modified_time: float
    size: int
    checksum: Optional[str] = None
    
    def __post_init__(self):
        if self.checksum is None:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """计算文件MD5校验和"""
        try:
            hash_md5 = hashlib.md5()
            with open(self.path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.warning(f"计算校验和失败 {self.path}: {e}")
            return ""
    
    def to_dict(self) -> Dict:
        return {
            'path': str(self.path),
            'base_name': self.base_name,
            'version': self.version,
            'version_type': self.version_type,
            'modified_time': datetime.fromtimestamp(self.modified_time).isoformat(),
            'size': self.size,
            'checksum': self.checksum
        }


@dataclass
class CleanupResult:
    """清理操作结果"""
    directory: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    scanned_files: int = 0
    version_groups: int = 0
    kept_files: List[VersionedFile] = field(default_factory=list)
    removed_files: List[VersionedFile] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'directory': self.directory,
            'timestamp': self.timestamp,
            'scanned_files': self.scanned_files,
            'version_groups': self.version_groups,
            'kept_count': len(self.kept_files),
            'removed_count': len(self.removed_files),
            'kept_files': [f.to_dict() for f in self.kept_files],
            'removed_files': [f.to_dict() for f in self.removed_files],
            'errors': self.errors,
            'dry_run': self.dry_run
        }
    
    def save_report(self, report_path: str):
        """保存清理报告"""
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"清理报告已保存: {report_path}")


class VersionRetentionManager:
    """
    版本保留管理器
    
    自动识别版本化文件，保留最新版本，清理旧版本。
    """
    
    # 版本模式定义
    VERSION_PATTERNS = {
        'suffix': [
            # file_v1.py, file_v2.py, file_v1.0.0.py
            (r'^(.*?)_v(\d+(?:\.\d+)*)\.(\w+)$', lambda m: (m.group(1), m.group(2), m.group(3))),
            # file_v1, file_v2 (无扩展名)
            (r'^(.*?)_v(\d+(?:\.\d+)*)$', lambda m: (m.group(1), m.group(2), '')),
        ],
        'prefix': [
            # v1_file.py, v2_file.py
            (r'^v(\d+(?:\.\d+)*)_(.*?)\.(\w+)$', lambda m: (m.group(2), m.group(1), m.group(3))),
        ],
        'date': [
            # file_20240101.py, file_2024-01-01.py
            (r'^(.*?)_(\d{4}-?\d{2}-?\d{2})\.(\w+)$', lambda m: (m.group(1), m.group(2), m.group(3))),
            # file_202401.py (年月)
            (r'^(.*?)_(\d{4}-?\d{2})\.(\w+)$', lambda m: (m.group(1), m.group(2), m.group(3))),
        ],
        'backup': [
            # file.py.backup, file.py.old, file.py.bak
            (r'^(.*?)\.(\w+)\.(backup|old|bak|orig|save)$', lambda m: (f"{m.group(1)}.{m.group(2)}", m.group(3), m.group(2))),
            # file.backup.py
            (r'^(.*?)\.(backup|old|bak)\.(\w+)$', lambda m: (m.group(1), m.group(2), m.group(3))),
        ],
        'numeric': [
            # file.1.py, file.2.py
            (r'^(.*?)\.(\d+)\.(\w+)$', lambda m: (m.group(1), m.group(2), m.group(3))),
        ],
    }
    
    def __init__(self, 
                 protected_patterns: Optional[List[str]] = None,
                 exclude_dirs: Optional[List[str]] = None,
                 min_versions_to_keep: int = 1):
        """
        初始化版本保留管理器
        
        Args:
            protected_patterns: 受保护的模式列表 (不会被删除)
            exclude_dirs: 排除的目录列表
            min_versions_to_keep: 最少保留版本数 (默认1)
        """
        self.protected_patterns = protected_patterns or []
        self.exclude_dirs = set(exclude_dirs or ['.git', '__pycache__', 'node_modules', '.venv', 'venv'])
        self.min_versions_to_keep = max(1, min_versions_to_keep)
        
        logger.info(f"版本保留管理器初始化完成 (最少保留 {self.min_versions_to_keep} 个版本)")
    
    def parse_version(self, filename: str) -> Optional[Tuple[str, str, str]]:
        """
        解析文件名中的版本信息
        
        Args:
            filename: 文件名
            
        Returns:
            (base_name, version, extension) 或 None
        """
        for version_type, patterns in self.VERSION_PATTERNS.items():
            for pattern, extractor in patterns:
                match = re.match(pattern, filename)
                if match:
                    try:
                        base_name, version, ext = extractor(match)
                        return (base_name, version, ext, version_type)
                    except Exception as e:
                        logger.debug(f"解析失败 {filename}: {e}")
                        continue
        return None
    
    def _version_key(self, version: str, version_type: str) -> Tuple:
        """
        生成版本排序键
        
        支持多种版本格式排序:
        - 数字版本: 1, 2, 10 (正确排序)
        - 语义版本: 1.0.0, 1.0.1, 1.1.0
        - 日期版本: 20240101, 2024-01-01
        """
        try:
            if version_type == 'date':
                # 日期版本: 20240101 或 2024-01-01
                clean_date = version.replace('-', '').replace('_', '')
                if len(clean_date) >= 6:
                    return (0, int(clean_date[:8]) if len(clean_date) >= 8 else int(clean_date[:6]))
            
            elif version_type == 'backup':
                # 备份类型按时间排序 (假设backup比old新)
                priority = {'bak': 0, 'old': 1, 'orig': 2, 'save': 3, 'backup': 4}
                return (1, priority.get(version.lower(), 0))
            
            else:
                # 数字/语义版本: 1, 1.0, 1.0.0
                parts = version.split('.')
                numeric_parts = []
                for part in parts:
                    try:
                        numeric_parts.append(int(part))
                    except ValueError:
                        numeric_parts.append(0)
                # 补齐到4位以便比较
                while len(numeric_parts) < 4:
                    numeric_parts.append(0)
                return (2, tuple(numeric_parts))
        
        except Exception as e:
            logger.debug(f"版本排序键生成失败 {version}: {e}")
        
        # 默认按字符串排序
        return (3, version)
    
    def scan_directory(self, directory: str, 
                       recursive: bool = True,
                       file_extensions: Optional[List[str]] = None) -> Dict[str, List[VersionedFile]]:
        """
        扫描目录中的版本化文件
        
        Args:
            directory: 目标目录
            recursive: 是否递归扫描子目录
            file_extensions: 限制的文件扩展名列表 (如 ['.py', '.json'])
            
        Returns:
            按基础文件名分组的版本化文件字典
        """
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")
        
        version_groups = defaultdict(list)
        scanned_count = 0
        
        # 确定扫描路径
        if recursive:
            files = directory.rglob('*')
        else:
            files = directory.iterdir()
        
        for file_path in files:
            # 跳过目录
            if file_path.is_dir():
                continue
            
            # 跳过排除的目录
            if any(excluded in str(file_path) for excluded in self.exclude_dirs):
                continue
            
            # 检查扩展名限制
            if file_extensions and file_path.suffix not in file_extensions:
                continue
            
            scanned_count += 1
            
            # 解析版本信息
            version_info = self.parse_version(file_path.name)
            if version_info:
                base_name, version, ext, version_type = version_info
                
                # 获取文件信息
                stat = file_path.stat()
                
                vf = VersionedFile(
                    path=file_path,
                    base_name=base_name,
                    version=version,
                    version_type=version_type,
                    modified_time=stat.st_mtime,
                    size=stat.st_size
                )
                
                # 按基础文件名分组
                group_key = f"{file_path.parent}/{base_name}"
                version_groups[group_key].append(vf)
        
        logger.info(f"扫描完成: {scanned_count} 个文件, 发现 {len(version_groups)} 个版本组")
        return dict(version_groups)
    
    def clean_directory(self, directory: str,
                       recursive: bool = True,
                       file_extensions: Optional[List[str]] = None,
                       dry_run: bool = True,
                       keep_strategy: str = 'latest') -> CleanupResult:
        """
        清理目录中的旧版本文件
        
        Args:
            directory: 目标目录
            recursive: 是否递归扫描
            file_extensions: 限制的文件扩展名
            dry_run: 是否为试运行模式 (只查看不删除)
            keep_strategy: 保留策略 ('latest', 'oldest', 'all')
            
        Returns:
            CleanupResult 清理结果
        """
        result = CleanupResult(
            directory=str(directory),
            dry_run=dry_run
        )
        
        try:
            # 扫描版本化文件
            version_groups = self.scan_directory(directory, recursive, file_extensions)
            result.scanned_files = sum(len(files) for files in version_groups.values())
            result.version_groups = len(version_groups)
            
            for group_key, files in version_groups.items():
                if len(files) <= self.min_versions_to_keep:
                    # 版本数不足，全部保留
                    result.kept_files.extend(files)
                    continue
                
                # 按版本排序
                sorted_files = sorted(
                    files,
                    key=lambda f: self._version_key(f.version, f.version_type),
                    reverse=True  # 最新版本在前
                )
                
                # 根据策略决定保留哪些
                if keep_strategy == 'latest':
                    keep_files = sorted_files[:self.min_versions_to_keep]
                    remove_files = sorted_files[self.min_versions_to_keep:]
                elif keep_strategy == 'oldest':
                    keep_files = sorted_files[-self.min_versions_to_keep:]
                    remove_files = sorted_files[:-self.min_versions_to_keep]
                else:  # keep all
                    keep_files = sorted_files
                    remove_files = []
                
                result.kept_files.extend(keep_files)
                
                # 删除旧版本
                for vf in remove_files:
                    try:
                        if not dry_run:
                            # 检查是否受保护
                            if any(re.match(pattern, str(vf.path)) for pattern in self.protected_patterns):
                                logger.info(f"跳过受保护文件: {vf.path}")
                                result.kept_files.append(vf)
                                continue
                            
                            # 执行删除
                            if vf.path.exists():
                                vf.path.unlink()
                                logger.info(f"已删除: {vf.path}")
                        
                        result.removed_files.append(vf)
                        
                    except Exception as e:
                        error_msg = f"删除失败 {vf.path}: {e}"
                        logger.error(error_msg)
                        result.errors.append(error_msg)
                        result.kept_files.append(vf)  # 删除失败的保留
            
            logger.info(f"清理完成: 保留 {len(result.kept_files)} 个, 删除 {len(result.removed_files)} 个")
            
        except Exception as e:
            error_msg = f"清理过程出错: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
        
        return result
    
    def validate_cleanup(self, result: CleanupResult) -> bool:
        """
        验证清理结果
        
        验证项:
        1. 所有保留文件都存在
        2. 所有删除的文件都不存在 (非 dry_run 模式)
        3. 每个版本组至少保留了 min_versions_to_keep 个版本
        4. 没有重复删除同一文件
        
        Args:
            result: 清理结果
            
        Returns:
            验证是否通过
        """
        logger.info("开始验证清理结果...")
        
        validation_errors = []
        
        # 1. 验证保留文件存在
        for vf in result.kept_files:
            if not vf.path.exists():
                validation_errors.append(f"保留文件不存在: {vf.path}")
        
        # 2. 验证删除的文件不存在 (非 dry_run 模式)
        if not result.dry_run:
            for vf in result.removed_files:
                if vf.path.exists():
                    validation_errors.append(f"应删除的文件仍存在: {vf.path}")
        
        # 3. 验证版本组保留数量
        group_counts = defaultdict(int)
        for vf in result.kept_files:
            group_key = f"{vf.path.parent}/{vf.base_name}"
            group_counts[group_key] += 1
        
        for group_key, count in group_counts.items():
            if count < self.min_versions_to_keep:
                validation_errors.append(f"版本组 {group_key} 保留数量不足: {count} < {self.min_versions_to_keep}")
        
        # 4. 检查重复
        kept_paths = {str(vf.path) for vf in result.kept_files}
        removed_paths = {str(vf.path) for vf in result.removed_files}
        duplicates = kept_paths & removed_paths
        if duplicates:
            validation_errors.append(f"文件同时出现在保留和删除列表: {duplicates}")
        
        if validation_errors:
            logger.error("验证失败:")
            for error in validation_errors:
                logger.error(f"  - {error}")
            return False
        
        logger.info("验证通过!")
        return True
    
    def preview_cleanup(self, directory: str, 
                       recursive: bool = True,
                       file_extensions: Optional[List[str]] = None) -> Dict:
        """
        预览清理结果 (dry run)
        
        Args:
            directory: 目标目录
            recursive: 是否递归
            file_extensions: 限制的文件扩展名
            
        Returns:
            预览结果字典
        """
        result = self.clean_directory(
            directory=directory,
            recursive=recursive,
            file_extensions=file_extensions,
            dry_run=True
        )
        
        return {
            'summary': {
                'total_scanned': result.scanned_files,
                'version_groups': result.version_groups,
                'will_keep': len(result.kept_files),
                'will_remove': len(result.removed_files),
                'can_free_space': sum(f.size for f in result.removed_files)
            },
            'groups': self._group_by_base_name(result.kept_files, result.removed_files)
        }
    
    def _group_by_base_name(self, kept_files: List[VersionedFile], 
                           removed_files: List[VersionedFile]) -> Dict:
        """按基础名分组显示结果"""
        groups = defaultdict(lambda: {'keep': [], 'remove': []})
        
        for vf in kept_files:
            key = f"{vf.path.parent}/{vf.base_name}"
            groups[key]['keep'].append(vf.to_dict())
        
        for vf in removed_files:
            key = f"{vf.path.parent}/{vf.base_name}"
            groups[key]['remove'].append(vf.to_dict())
        
        return dict(groups)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='版本保留管理器')
    parser.add_argument('directory', help='目标目录')
    parser.add_argument('--execute', action='store_true', help='执行实际删除 (默认仅预览)')
    parser.add_argument('--recursive', '-r', action='store_true', help='递归扫描子目录')
    parser.add_argument('--extensions', '-e', nargs='+', help='限制的文件扩展名 (如 .py .json)')
    parser.add_argument('--keep', '-k', type=int, default=1, help='最少保留版本数 (默认1)')
    parser.add_argument('--report', help='保存报告的文件路径')
    
    args = parser.parse_args()
    
    # 创建管理器
    manager = VersionRetentionManager(min_versions_to_keep=args.keep)
    
    # 执行清理
    result = manager.clean_directory(
        directory=args.directory,
        recursive=args.recursive,
        file_extensions=args.extensions,
        dry_run=not args.execute
    )
    
    # 打印结果
    print("\n" + "="*60)
    print(f"{'预览模式' if result.dry_run else '执行模式'} - 清理结果")
    print("="*60)
    print(f"扫描文件数: {result.scanned_files}")
    print(f"版本组数: {result.version_groups}")
    print(f"保留文件: {len(result.kept_files)}")
    print(f"删除文件: {len(result.removed_files)}")
    print(f"释放空间: {sum(f.size for f in result.removed_files) / 1024 / 1024:.2f} MB")
    
    if result.errors:
        print(f"\n错误 ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error}")
    
    # 验证结果
    if args.execute:
        is_valid = manager.validate_cleanup(result)
        print(f"\n验证结果: {'通过' if is_valid else '失败'}")
    
    # 保存报告
    if args.report:
        result.save_report(args.report)
    
    # 打印详细列表
    print("\n保留的最新版本:")
    for vf in sorted(result.kept_files, key=lambda x: str(x.path))[:10]:
        print(f"  ✓ {vf.path.name} (v{vf.version})")
    if len(result.kept_files) > 10:
        print(f"  ... 还有 {len(result.kept_files) - 10} 个")
    
    if result.removed_files:
        print("\n删除的旧版本:")
        for vf in sorted(result.removed_files, key=lambda x: str(x.path))[:10]:
            print(f"  ✗ {vf.path.name} (v{vf.version})")
        if len(result.removed_files) > 10:
            print(f"  ... 还有 {len(result.removed_files) - 10} 个")


if __name__ == '__main__':
    main()
