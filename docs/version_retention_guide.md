# 版本保留管理器使用指南

## 概述

版本保留管理器 (`VersionRetentionManager`) 是一个自动化工具，用于识别和清理项目中的旧版本文件，仅保留最新版本，从而防止版本混乱和存储浪费。

## 功能特性

- **多模式版本识别**: 支持后缀版本、前缀版本、日期版本、备份版本和数字版本
- **智能版本排序**: 正确排序语义版本号 (1.0.0 < 1.0.10 < 1.1.0)
- **安全清理机制**: 支持试运行模式 (dry run)，先预览再执行
- **验证机制**: 自动验证清理结果，确保数据完整性
- **报告生成**: 生成详细的清理报告，便于审计

## 支持的版本命名模式

| 模式类型 | 示例 | 说明 |
|---------|------|------|
| 后缀版本 | `file_v1.py`, `file_v2.0.0.py` | 最常用，推荐 |
| 前缀版本 | `v1_file.py`, `v2_config.json` | 版本号在前 |
| 日期版本 | `file_20240101.py`, `file_2024-01-01.py` | 按日期版本化 |
| 备份版本 | `file.py.backup`, `file.py.old` | 备份文件 |
| 数字版本 | `file.1.py`, `file.2.py` | 纯数字版本 |

## 安装

版本保留管理器已集成到项目中，无需额外安装。

```python
from utils.version_retention_manager import VersionRetentionManager
```

## 基本使用

### 1. 创建管理器实例

```python
from utils.version_retention_manager import VersionRetentionManager

# 基础配置
manager = VersionRetentionManager(
    min_versions_to_keep=1,  # 最少保留版本数
    exclude_dirs=['.git', '__pycache__', 'node_modules'],  # 排除目录
    protected_patterns=[r'.*_v1\.py$']  # 受保护模式（不会被删除）
)
```

### 2. 预览清理结果 (推荐先预览)

```python
# 预览模式 - 只查看不删除
preview = manager.preview_cleanup(
    directory='modules/data',
    recursive=True,
    file_extensions=['.py', '.json']  # 可选：限制文件类型
)

print(f"扫描文件: {preview['summary']['total_scanned']}")
print(f"将保留: {preview['summary']['will_keep']}")
print(f"将删除: {preview['summary']['will_remove']}")
print(f"可释放空间: {preview['summary']['can_free_space'] / 1024 / 1024:.2f} MB")
```

### 3. 执行清理

```python
# 实际执行清理
result = manager.clean_directory(
    directory='modules/data',
    recursive=True,
    dry_run=False,  # False = 实际删除，True = 仅预览
    keep_strategy='latest'  # 保留策略: 'latest', 'oldest', 'all'
)

print(f"保留文件: {len(result.kept_files)}")
print(f"删除文件: {len(result.removed_files)}")
```

### 4. 验证清理结果

```python
# 验证清理结果
is_valid = manager.validate_cleanup(result)

if is_valid:
    print("✅ 验证通过！清理成功")
else:
    print("❌ 验证失败，请检查日志")
```

### 5. 保存清理报告

```python
# 保存详细报告
result.save_report('cleanup_report_20240101.json')
```

## 命令行使用

### 基本命令

```bash
# 预览模式 (默认)
python utils/version_retention_manager.py modules/data

# 执行实际清理
python utils/version_retention_manager.py modules/data --execute

# 递归扫描子目录
python utils/version_retention_manager.py modules/data --execute --recursive

# 限制文件类型
python utils/version_retention_manager.py modules/data --execute --extensions .py .json

# 保留多个版本
python utils/version_retention_manager.py modules/data --execute --keep 2

# 保存报告
python utils/version_retention_manager.py modules/data --execute --report cleanup_report.json
```

### 命令行参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `directory` | - | 目标目录 | 必需 |
| `--execute` | - | 执行实际删除 | False (预览模式) |
| `--recursive` | `-r` | 递归扫描子目录 | False |
| `--extensions` | `-e` | 限制文件扩展名 | None (所有类型) |
| `--keep` | `-k` | 最少保留版本数 | 1 |
| `--report` | - | 保存报告路径 | None |

## 实际应用示例

### 示例1: 清理 Python 模块版本

假设 `modules/data` 目录有以下文件：
```
loader_v1.py
loader_v2.py
loader_v3.py
processor_v1.0.py
processor_v1.1.py
processor_v2.0.py
```

执行清理：
```python
manager = VersionRetentionManager()
result = manager.clean_directory('modules/data', dry_run=False)

# 结果：
# 保留: loader_v3.py, processor_v2.0.py
# 删除: loader_v1.py, loader_v2.py, processor_v1.0.py, processor_v1.1.py
```

### 示例2: 清理缓存文件

```python
# 清理缓存目录，保留最近2个版本
manager = VersionRetentionManager(min_versions_to_keep=2)
result = manager.clean_directory(
    'data/cache',
    recursive=True,
    dry_run=False
)
```

### 示例3: 保护特定版本

```python
# 保护所有 v1 版本不被删除
manager = VersionRetentionManager(
    protected_patterns=[r'.*_v1\.py$', r'.*_v1\.\d+\.py$']
)
result = manager.clean_directory('modules', dry_run=False)
```

## 版本排序规则

管理器使用智能排序算法确保正确识别最新版本：

### 语义版本排序
```
2.0.0 > 1.10.0 > 1.1.0 > 1.0.10 > 1.0.1 > 1.0.0
```

### 数字版本排序
```
10 > 9 > 2 > 1  (不是字符串排序的 9 > 10 > 2 > 1)
```

### 日期版本排序
```
2024-01-15 > 2024-01-01 > 2023-12-31
```

### 备份版本排序
```
backup > save > orig > old > bak
```

## 验证机制

清理完成后，管理器会自动验证：

1. **保留文件存在性**: 所有标记为保留的文件必须存在
2. **删除文件不存在性**: 所有标记为删除的文件必须不存在 (非 dry_run 模式)
3. **版本数量检查**: 每个版本组至少保留 `min_versions_to_keep` 个版本
4. **重复检查**: 同一文件不能同时出现在保留和删除列表

## 最佳实践

### 1. 始终先预览再执行

```python
# 第一步：预览
preview = manager.preview_cleanup('target_dir')
print(json.dumps(preview, indent=2))

# 第二步：确认无误后执行
input("确认执行清理? (y/n): ")
result = manager.clean_directory('target_dir', dry_run=False)
```

### 2. 定期清理

建议将版本清理加入定期维护任务：

```python
# cleanup_script.py
import schedule
import time

def cleanup_job():
    manager = VersionRetentionManager()
    result = manager.clean_directory('modules', recursive=True, dry_run=False)
    result.save_report(f'cleanup_report_{datetime.now().strftime("%Y%m%d")}.json')

# 每周日凌晨执行
schedule.every().sunday.at("00:00").do(cleanup_job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 3. 保留重要版本

```python
# 保留所有主版本 (v1.x, v2.x)
manager = VersionRetentionManager(
    protected_patterns=[
        r'.*_v\d+\.0\.py$',  # 保护 x.0 版本
        r'.*_v1\..*\.py$',   # 保护所有 v1.x 版本
    ]
)
```

## 故障排除

### 问题1: 版本未被识别

**原因**: 文件名不符合支持的命名模式  
**解决**: 检查文件名格式，参考支持的版本命名模式

### 问题2: 验证失败

**可能原因**:
- 文件在清理过程中被其他程序修改
- 权限不足导致无法删除

**解决**:
```python
# 检查错误详情
result = manager.clean_directory('target', dry_run=False)
if result.errors:
    for error in result.errors:
        print(f"错误: {error}")
```

### 问题3: 误删文件

**预防**:
1. 始终使用 dry_run=True 先预览
2. 配置 protected_patterns 保护重要文件
3. 定期备份

**恢复**:
如果启用了备份版本，可以从备份恢复：
```python
# 查找备份
backup_files = list(Path('target').glob('*.backup'))
```

## API 参考

### VersionRetentionManager

#### 构造函数

```python
VersionRetentionManager(
    protected_patterns: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None,
    min_versions_to_keep: int = 1
)
```

#### 主要方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `scan_directory()` | 扫描目录中的版本化文件 | Dict[str, List[VersionedFile]] |
| `clean_directory()` | 清理目录中的旧版本 | CleanupResult |
| `preview_cleanup()` | 预览清理结果 | Dict |
| `validate_cleanup()` | 验证清理结果 | bool |
| `parse_version()` | 解析文件名中的版本 | Optional[Tuple] |

### CleanupResult

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `directory` | str | 清理的目录 |
| `timestamp` | str | 操作时间戳 |
| `scanned_files` | int | 扫描的文件数 |
| `version_groups` | int | 版本组数 |
| `kept_files` | List[VersionedFile] | 保留的文件 |
| `removed_files` | List[VersionedFile] | 删除的文件 |
| `errors` | List[str] | 错误信息 |
| `dry_run` | bool | 是否为试运行 |

#### 方法

| 方法 | 说明 |
|------|------|
| `to_dict()` | 转换为字典 |
| `save_report(path)` | 保存报告到文件 |

## 更新日志

### v1.0.0 (2026-04-17)
- 初始版本发布
- 支持5种版本命名模式
- 实现智能版本排序
- 添加验证机制
- 提供命令行接口

---

如有问题或建议，请联系开发团队。
