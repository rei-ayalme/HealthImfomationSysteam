# modules/fallback_handler.py
import redis
import json
import logging
import functools
from datetime import timedelta
from config.settings import REDIS_CONFIG  # Redis配置

# 初始化Redis（生产环境用Redis，开发环境可用本地缓存）
redis_client = redis.Redis(
    host=REDIS_CONFIG["host"],
    port=REDIS_CONFIG["port"],
    password=REDIS_CONFIG["password"],
    db=REDIS_CONFIG["db"],
    decode_responses=True
)
# 初始化日志记录器
logger = logging.getLogger(__name__)

def set_fallback_data(key: str, data: dict, expire: int = 86400):
    """
    设置兜底数据到Redis
    :param key: 缓存键（如owid:physicians-per-1000-people:China）
    :param data: 兜底数据
    :param expire: 过期时间（秒），默认1天
    """
    redis_client.setex(key, timedelta(seconds=expire), json.dumps(data))

def get_fallback_data(key: str) -> dict:
    """获取兜底数据"""
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return {}

def fallback_wrapper(default_data: dict = None):
    """
    兜底处理装饰器：接口失败时返回兜底数据
    :param default_data: 无缓存时的默认兜底数据
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # 接口成功：更新兜底缓存
                if result.get("status") == "success":
                    # 构造缓存键（示例：根据指标/国家构造）
                    indicator_id = kwargs.get("indicator_id") or args[0] if args else "default"
                    country = kwargs.get("target_countries") or args[1] if len(args)>=2 else "default"
                    cache_key = f"fallback:{indicator_id}:{country}"
                    set_fallback_data(cache_key, result)
                return result
            except Exception as e:
                # 接口失败：获取兜底数据
                indicator_id = kwargs.get("indicator_id") or args[0] if args else "default"
                country = kwargs.get("target_countries") or args[1] if len(args)>=2 else "default"
                cache_key = f"fallback:{indicator_id}:{country}"
                fallback_data = get_fallback_data(cache_key)
                if fallback_data:
                    logger.warning(f"[{func.__name__}] 调用失败，返回兜底缓存：{e}")
                    return fallback_data
                # 无缓存：返回默认值
                logger.error(f"[{func.__name__}] 调用失败，无兜底缓存，返回默认值：{e}")
                return default_data or {"status": "error", "msg": "接口调用失败", "data": {}}
        return wrapper
    return decorator