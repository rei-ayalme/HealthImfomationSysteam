#!/usr/bin/env python3
"""
Redis 连接测试脚本
用于验证 Redis 服务是否正常运行以及应用是否能成功连接
"""

import sys
import os

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

def test_redis_connection():
    """测试 Redis 连接"""
    print("=" * 60)
    print("Redis 连接测试")
    print("=" * 60)
    print()
    
    # 1. 测试直接连接
    print("[步骤 1] 测试直接 Redis 连接...")
    try:
        import redis
        client = redis.Redis(
            host='127.0.0.1',
            port=6379,
            db=0,
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0
        )
        client.ping()
        print("[成功] Redis 直接连接成功！")
        
        # 测试基本操作
        client.set('test_key', 'Hello Redis!')
        value = client.get('test_key')
        print(f"[成功] 测试读写操作正常: {value}")
        client.delete('test_key')
        print()
        
    except ImportError:
        print("[错误] 未安装 redis 库，请运行: pip install redis")
        return False
    except redis.ConnectionError as e:
        print(f"[错误] Redis 连接失败: {e}")
        print("[提示] 请确保 Redis 服务已启动")
        print("[提示] 可以运行 scripts/start_redis.bat 启动服务")
        return False
    except Exception as e:
        print(f"[错误] 未知错误: {e}")
        return False
    
    # 2. 测试通过 DataLoader 连接
    print("[步骤 2] 测试通过 DataLoader 连接...")
    try:
        from modules.data.loader import DataLoader
        loader = DataLoader()
        
        if hasattr(loader, 'use_redis') and loader.use_redis:
            print("[成功] DataLoader 成功连接到 Redis！")
            print(f"[信息] use_redis = {loader.use_redis}")
            print(f"[信息] _redis_client = {loader._redis_client}")
        else:
            print("[警告] DataLoader 未能使用 Redis，已降级到内存缓存")
            print(f"[信息] use_redis = {getattr(loader, 'use_redis', '未设置')}")
            print(f"[信息] _redis_client = {loader._redis_client}")
        print()
        
    except Exception as e:
        print(f"[错误] DataLoader 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("=" * 60)
    print("[成功] 所有测试通过！")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_redis_connection()
    sys.exit(0 if success else 1)
