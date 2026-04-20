#!/usr/bin/env python3
"""清除新闻缓存，强制重新获取中文新闻"""
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

def clear_cache():
    """清除新闻缓存"""
    loader = DataLoader()
    
    # 获取今天的缓存键
    today = datetime.now().strftime("%Y-%m-%d")
    cache_key = f"mediastack:news:{today}"
    
    print(f"正在清除缓存: {cache_key}")
    
    # 尝试从 Redis 清除
    if loader._redis_client:
        try:
            loader._redis_client.delete(cache_key)
            print("✅ Redis 缓存已清除")
        except Exception as e:
            print(f"⚠️ Redis 清除失败: {e}")
    
    # 从内存缓存清除
    if cache_key in loader._fallback_cache:
        del loader._fallback_cache[cache_key]
        del loader._cache_timestamps[cache_key]
        print("✅ 内存缓存已清除")
    
    print("\n缓存清除完成，下次请求将获取最新中文新闻")

if __name__ == "__main__":
    clear_cache()
