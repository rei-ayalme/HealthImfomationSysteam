# modules/api_protector.py
import time
import functools
import logging
from collections import defaultdict
from config.settings import API_LIMIT_CONFIG  # 限流配置

# 配置示例（config/settings.py）：
# API_LIMIT_CONFIG = {
#     "rate_limit": 10,  # 每分钟最多调用10次
#     "time_window": 60  # 时间窗口（秒）
# }

# 限流计数器（内存级，生产环境建议用Redis）
request_counter = defaultdict(list)
# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_protector")


def api_protector(api_name: str, api_key: str = None):
    """
    接口保护装饰器：鉴权 + 限流 + 超时重试 + 日志
    :param api_name: 接口名称（用于限流/日志）
    :param api_key: 接口密钥（鉴权用）
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 1. 鉴权（可选）
            if api_key:
                req_api_key = kwargs.get("api_key") or args[0] if args else None
                if req_api_key != api_key:
                    logger.error(f"[{api_name}] 鉴权失败：无效的API Key")
                    return {"status": "error", "msg": "鉴权失败：无效的API Key"}

            # 2. 限流（固定窗口）
            now = time.time()
            # 清理过期请求记录
            request_counter[api_name] = [t for t in request_counter[api_name] if
                                         t > now - API_LIMIT_CONFIG["time_window"]]
            if len(request_counter[api_name]) >= API_LIMIT_CONFIG["rate_limit"]:
                logger.warning(f"[{api_name}] 限流触发：超出每分钟{API_LIMIT_CONFIG['rate_limit']}次调用")
                return {"status": "error", "msg": "接口调用过于频繁，请稍后再试"}
            # 记录本次请求时间
            request_counter[api_name].append(now)

            # 3. 执行原函数 + 日志
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"[{api_name}] 调用成功，耗时{elapsed:.2f}秒")
                return result
            except Exception as e:
                logger.error(f"[{api_name}] 调用失败：{str(e)}")
                raise e

        return wrapper

    return decorator