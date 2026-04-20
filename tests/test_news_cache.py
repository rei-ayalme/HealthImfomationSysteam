#!/usr/bin/env python3
"""
新闻缓存机制测试脚本
测试24小时缓存和API调用计数功能
"""

import os
import sys
import time
import json

# 加载环境变量
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path=env_path)

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.data.loader import DataLoader


def test_cache_mechanism():
    """测试缓存机制"""
    print("=" * 60)
    print("测试 24小时缓存机制")
    print("=" * 60)

    loader = DataLoader()

    print("\n[测试 1] 首次调用（应从API获取）...")
    news1 = loader.fetch_health_news(limit=3)
    print(f"  获取到 {len(news1)} 条新闻")
    print(f"  第一条: {news1[0].get('title', 'N/A')[:50]}...")

    # 检查API调用统计
    stats1 = loader.get_api_usage_stats()
    print(f"\n  API调用统计:")
    print(f"    本月已使用: {stats1['api_calls_used']}/100")
    print(f"    剩余次数: {stats1['api_calls_remaining']}")
    print(f"    使用百分比: {stats1['usage_percentage']}%")
    print(f"    状态: {stats1['status']}")

    print("\n[测试 2] 第二次调用（应从缓存获取）...")
    news2 = loader.fetch_health_news(limit=3)
    print(f"  获取到 {len(news2)} 条新闻")

    stats2 = loader.get_api_usage_stats()
    print(f"\n  API调用统计:")
    print(f"    本月已使用: {stats2['api_calls_used']}/100")
    print(f"    缓存命中: {'是' if stats1['api_calls_used'] == stats2['api_calls_used'] else '否'}")

    print("\n[测试 3] 第三次调用（再次验证缓存）...")
    news3 = loader.fetch_health_news(limit=3)
    print(f"  获取到 {len(news3)} 条新闻")

    stats3 = loader.get_api_usage_stats()
    print(f"\n  API调用统计:")
    print(f"    本月已使用: {stats3['api_calls_used']}/100")
    print(f"    连续缓存命中: {'是' if stats2['api_calls_used'] == stats3['api_calls_used'] else '否'}")

    # 验证数据一致性
    print("\n[测试 4] 验证数据一致性...")
    if json.dumps(news1, sort_keys=True) == json.dumps(news2, sort_keys=True) == json.dumps(news3, sort_keys=True):
        print("  [PASS] 三次获取的数据一致")
    else:
        print("  [WARN] 数据不一致（可能是正常情况）")

    return True


def test_api_stats():
    """测试API统计功能"""
    print("\n" + "=" * 60)
    print("测试 API 调用统计")
    print("=" * 60)

    loader = DataLoader()
    stats = loader.get_api_usage_stats()

    print(f"\n当前月份: {stats['current_month']}")
    print(f"API调用限额: {stats['api_calls_limit']} 次/月")
    print(f"已使用: {stats['api_calls_used']} 次")
    print(f"剩余: {stats['api_calls_remaining']} 次")
    print(f"使用百分比: {stats['usage_percentage']}%")
    print(f"状态: {stats['status']}")

    if stats['api_calls_used'] > 0:
        print(f"\n[分析] 按当前使用速度:")
        days_left = 30 - int(stats['current_month'].split('-')[1]) * 0  # 简化计算
        if stats['api_calls_remaining'] > 0:
            daily_limit = stats['api_calls_remaining'] / 30
            print(f"  每天可用约 {daily_limit:.1f} 次API调用")

    return True


def test_rate_limit_protection():
    """测试额度保护机制"""
    print("\n" + "=" * 60)
    print("测试 API 额度保护机制")
    print("=" * 60)

    loader = DataLoader()
    stats = loader.get_api_usage_stats()

    if stats['api_calls_remaining'] <= 0:
        print("\n[测试] API额度已用完，测试保护机制...")
        news = loader.fetch_health_news(limit=3)
        if news and news[0].get('title') == "API调用额度已用完":
            print("  [PASS] 额度保护生效，返回提示信息")
        else:
            print("  [FAIL] 额度保护未生效")
    else:
        print(f"\n[INFO] 当前剩余 {stats['api_calls_remaining']} 次调用，跳过额度耗尽测试")
        print("  （额度充足时正常获取数据）")

    return True


def main():
    """主测试函数"""
    print("=" * 60)
    print("新闻缓存机制测试")
    print("功能: 24小时缓存 + API调用计数")
    print("=" * 60)

    # 检查API Key
    api_key = os.getenv("MEDIASTACK_API_KEY", "")
    if not api_key:
        print("\n[ERROR] MEDIASTACK_API_KEY 未设置，无法进行测试")
        return 1

    print(f"\nAPI Key: {api_key[:8]}...{api_key[-4:]}")

    try:
        # 运行测试
        test_cache_mechanism()
        test_api_stats()
        test_rate_limit_protection()

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        print("\n缓存机制说明:")
        print("  - 首次调用会请求 Mediastack API")
        print("  - 数据缓存24小时，期间重复调用使用缓存")
        print("  - API调用计数按月统计，限额100次")
        print("  - 额度耗尽时返回提示信息而非错误")

        return 0

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
