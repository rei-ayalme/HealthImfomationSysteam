#!/usr/bin/env python3
"""清除缓存并重新获取新闻"""
import os
import sys
from datetime import datetime

# 加载环境变量
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.data.loader import DataLoader

def clear_and_test():
    """清除缓存并测试获取新闻"""
    loader = DataLoader()
    
    # 获取今天的缓存键
    today = datetime.now().strftime("%Y-%m-%d")
    cache_key = f"mediastack:news:{today}"
    
    print(f"清除缓存: {cache_key}")
    
    # 从 Redis 清除
    if loader._redis_client:
        try:
            loader._redis_client.delete(cache_key)
            print("[OK] Redis 缓存已清除")
        except Exception as e:
            print(f"[WARN] Redis 清除失败: {e}")
    
    # 从内存缓存清除
    if cache_key in loader._fallback_cache:
        del loader._fallback_cache[cache_key]
        if cache_key in loader._cache_timestamps:
            del loader._cache_timestamps[cache_key]
        print("[OK] 内存缓存已清除")
    
    print("\n重新获取新闻...")
    news = loader.fetch_health_news(limit=5)
    
    print(f"\n获取到 {len(news)} 条新闻:")
    for i, item in enumerate(news, 1):
        print(f"{i}. {item['title']}")
        print(f"   来源: {item['source']}")
        print()

if __name__ == "__main__":
    clear_and_test()
