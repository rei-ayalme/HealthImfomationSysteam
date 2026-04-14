#!/usr/bin/env python3
"""
验证 README.md 和 requirements.txt 文件格式
"""

import os
import sys

def validate_requirements():
    """验证 requirements.txt 格式"""
    print("=" * 60)
    print("验证 requirements.txt 格式")
    print("=" * 60)

    with open('requirements.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print(f"[OK] 文件共 {len(lines)} 行")

    # 统计各类包
    packages = []
    comments = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            packages.append(line)
        elif line.startswith('#'):
            comments.append(line)

    print(f"[OK] 共 {len(packages)} 个依赖包")
    print(f"[OK] 共 {len(comments)} 个注释行")

    # 检查包名格式
    invalid_packages = []
    for pkg in packages:
        # 基本格式检查：包名==版本号 或 包名>=版本号
        if '==' not in pkg and '>=' not in pkg:
            if not pkg.startswith('-e'):  # 排除 editable install
                invalid_packages.append(pkg)

    if invalid_packages:
        print(f"[WARN] 以下包可能格式不正确: {invalid_packages}")
    else:
        print("[OK] 所有包格式正确")

    # 检查重复包
    pkg_names = [p.split('==')[0].split('>=')[0].strip() for p in packages]
    duplicates = set([x for x in pkg_names if pkg_names.count(x) > 1])
    if duplicates:
        print(f"[WARN] 发现重复包: {duplicates}")
    else:
        print("[OK] 无重复包")

    return True

def validate_readme():
    """验证 README.md 格式"""
    print("\n" + "=" * 60)
    print("验证 README.md 格式")
    print("=" * 60)

    with open('README.md', 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查基本结构
    checks = [
        ('# 健康信息系统', '主标题'),
        ('## 一、项目简介', '项目简介'),
        ('## 二、预测引擎升级', '预测引擎'),
        ('## 三、多智能体', '多智能体模拟'),
        ('## 四、标准化数据中台', '数据中台'),
        ('## 五、环境要求', '环境要求'),
        ('## 六、快速启动', '快速启动'),
        ('## 七、目录结构', '目录结构'),
        ('## 八、核心功能', '核心功能'),
        ('```bash', '代码块'),
        ('### 核心特性', '核心特性'),
    ]

    all_passed = True
    for pattern, name in checks:
        if pattern in content:
            print(f"[OK] {name}: 存在")
        else:
            print(f"[FAIL] {name}: 缺失")
            all_passed = False

    # 统计章节数量
    sections = content.count('## ')
    print(f"\n[OK] 共 {sections} 个二级章节")

    # 检查代码块
    code_blocks = content.count('```')
    print(f"[OK] 共 {code_blocks // 2} 个代码块")

    # 检查链接格式
    links = content.count('](')
    print(f"[OK] 共 {links} 个链接")

    # 检查表格
    tables = content.count('|---')
    print(f"[OK] 共 {tables} 个表格")

    return all_passed

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("文件验证工具")
    print("=" * 60 + "\n")

    req_valid = validate_requirements()
    readme_valid = validate_readme()

    print("\n" + "=" * 60)
    if req_valid and readme_valid:
        print("[SUCCESS] 所有验证通过！")
    else:
        print("[WARNING] 部分验证未通过，请检查")
    print("=" * 60)

    return 0 if (req_valid and readme_valid) else 1

if __name__ == '__main__':
    sys.exit(main())
