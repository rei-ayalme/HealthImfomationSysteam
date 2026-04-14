#!/usr/bin/env python3
"""
.gitignore 验证脚本
用于验证 .gitignore 规则是否正确配置
"""

import os
import subprocess
import sys
from pathlib import Path

def run_git_check():
    """运行 Git 命令检查忽略状态"""
    print("=" * 70)
    print("Git Ignore 验证工具")
    print("=" * 70)
    print()
    
    # 检查是否在 Git 仓库中
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        if result.returncode != 0:
            print("[警告] 当前目录不是 Git 仓库，无法验证 Git 跟踪状态")
            print("[提示] 如需验证，请先初始化 Git 仓库: git init")
            return False
    except FileNotFoundError:
        print("[错误] 未找到 Git 命令，请确保 Git 已安装并添加到 PATH")
        return False
    
    print("[OK] Git 仓库检测通过")
    print()
    
    # 测试应该被忽略的文件
    test_patterns = [
        # 环境配置
        ('.env', '环境变量文件'),
        ('.env.local', '本地环境变量'),
        
        # Python 缓存
        ('__pycache__/', 'Python 缓存目录'),
        ('test.py[cod]', 'Python 编译文件'),
        
        # 虚拟环境
        ('.venv/', '虚拟环境目录'),
        ('venv/', '虚拟环境目录'),
        
        # 数据文件
        ('data/raw/test.csv', '原始数据文件'),
        ('data/processed/output.xlsx', '处理后数据文件'),
        
        # 数据库
        ('health_system.db', 'SQLite 数据库'),
        ('test.sqlite3', 'SQLite 数据库'),
        
        # 日志
        ('app.log', '日志文件'),
        ('logs/debug.log', '日志文件'),
        
        # Redis
        ('Redis-x64-5.0.14.1/', 'Redis 服务目录'),
        
        # 压缩文件
        ('archive.zip', '压缩文件'),
        ('backup.tar.gz', '压缩文件'),
        
        # 生成的文档
        ('report.pdf', 'PDF 报告'),
        ('data.xlsx', 'Excel 文件'),
        
        # IDE
        ('.idea/', 'PyCharm 配置'),
        ('.vscode/', 'VS Code 配置'),
        
        # 操作系统文件
        ('.DS_Store', 'macOS 系统文件'),
        ('Thumbs.db', 'Windows 系统文件'),
    ]
    
    # 测试不应该被忽略的文件
    whitelist_patterns = [
        ('.env.example', '环境变量示例'),
        ('data/geojson/china.json', '地理数据文件'),
        ('requirements.txt', '依赖清单'),
        ('README.md', '项目说明文档'),
        ('main.py', '主程序文件'),
        ('.gitignore', 'Git 忽略文件'),
    ]
    
    print("-" * 70)
    print("测试应该被忽略的文件/目录")
    print("-" * 70)
    
    ignored_count = 0
    not_ignored = []
    
    for pattern, description in test_patterns:
        # 使用 git check-ignore 检查
        result = subprocess.run(
            ['git', 'check-ignore', '-q', pattern],
            capture_output=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            print(f"[OK] {description}: {pattern} - 正确被忽略")
            ignored_count += 1
        else:
            print(f"[WARN] {description}: {pattern} - 未被忽略")
            not_ignored.append((pattern, description))
    
    print()
    print("-" * 70)
    print("测试不应该被忽略的文件/目录")
    print("-" * 70)
    
    whitelisted_count = 0
    incorrectly_ignored = []
    
    for pattern, description in whitelist_patterns:
        result = subprocess.run(
            ['git', 'check-ignore', '-q', pattern],
            capture_output=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode != 0:
            print(f"[OK] {description}: {pattern} - 正确未被忽略")
            whitelisted_count += 1
        else:
            print(f"[ERROR] {description}: {pattern} - 被错误忽略")
            incorrectly_ignored.append((pattern, description))
    
    print()
    print("=" * 70)
    print("验证结果汇总")
    print("=" * 70)
    print(f"应该被忽略的文件: {ignored_count}/{len(test_patterns)} 通过")
    print(f"不应该被忽略的文件: {whitelisted_count}/{len(whitelist_patterns)} 通过")
    
    if not_ignored:
        print()
        print("[注意] 以下文件应该被忽略但未被忽略:")
        for pattern, description in not_ignored:
            print(f"  - {pattern} ({description})")
    
    if incorrectly_ignored:
        print()
        print("[错误] 以下文件被错误地忽略了:")
        for pattern, description in incorrectly_ignored:
            print(f"  - {pattern} ({description})")
    
    print()
    
    # 检查实际存在的被忽略文件
    print("-" * 70)
    print("检查实际存在的被忽略文件")
    print("-" * 70)
    
    result = subprocess.run(
        ['git', 'status', '--ignored', '--short'],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    ignored_files = [line for line in result.stdout.split('\n') if line.startswith('!!')]
    
    if ignored_files:
        print(f"[信息] 发现 {len(ignored_files)} 个被忽略的文件/目录:")
        for line in ignored_files[:10]:  # 只显示前10个
            print(f"  {line}")
        if len(ignored_files) > 10:
            print(f"  ... 还有 {len(ignored_files) - 10} 个文件")
    else:
        print("[信息] 当前没有已跟踪的被忽略文件")
    
    print()
    print("=" * 70)
    
    if not incorrectly_ignored:
        print("[SUCCESS] 验证通过！.gitignore 配置正确")
        return True
    else:
        print("[WARNING] 验证未通过，请检查 .gitignore 配置")
        return False

def check_gitignore_syntax():
    """检查 .gitignore 语法"""
    print()
    print("=" * 70)
    print("检查 .gitignore 语法")
    print("=" * 70)
    print()
    
    gitignore_path = Path(__file__).parent.parent / '.gitignore'
    
    with open(gitignore_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"[OK] 文件共 {len(lines)} 行")
    
    # 统计规则类型
    comments = sum(1 for line in lines if line.strip().startswith('#'))
    blank_lines = sum(1 for line in lines if not line.strip())
    negations = sum(1 for line in lines if line.strip().startswith('!'))
    directories = sum(1 for line in lines if line.strip().endswith('/'))
    
    print(f"[OK] 注释行: {comments}")
    print(f"[OK] 空行: {blank_lines}")
    print(f"[OK] 否定规则: {negations}")
    print(f"[OK] 目录规则: {directories}")
    print(f"[OK] 普通规则: {len(lines) - comments - blank_lines - negations}")
    
    return True

if __name__ == '__main__':
    syntax_ok = check_gitignore_syntax()
    check_ok = run_git_check()
    
    sys.exit(0 if (syntax_ok and check_ok) else 1)
