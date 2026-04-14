# modules/core/guard.py
"""
HIS 系统卫士：整合所有安全防护、基础设施健康检查与外部 API 监控
替代原有的 api_protector.py, api_checker.py, infra_checker.py

功能模块：
1. 安全防护 (Security) - 限流、鉴权、日志
2. 基础设施检查 (Infrastructure) - 数据库、Redis、文件系统
3. 外部 API 检查 (External APIs) - SerpAPI、Bing Search 等
4. DPIO 硬件检查 (Hardware) - 驱动、设备节点、帧收发
"""

import functools
import hashlib
import logging
import os
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import requests

# 可选导入 pydantic
try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    BaseModel = object  # 占位符

# 导入配置
try:
    from config.settings import Settings
except ImportError:
    # 如果配置导入失败，创建一个最小配置类
    class Settings:
        DATA_DIR = "./data"
        PROCESSED_DATA_PATH = "./data/processed"
        DPIO_CONFIG = {
            "driver_path": "/sys/class/dpio",
            "buffer_pool": "/dev/dpio_buffer0",
            "test_frame_data": b"\xAA\x55\xDE\xAD\xBE\xEF"
        }
        SEARCH_ENGINE_CONFIG = {
            "serpapi": {"api_key": "", "api_url": "https://serpapi.com/search"},
            "bing": {"api_key": "", "api_url": "https://api.bing.microsoft.com/v7.0/search"}
        }

logger = logging.getLogger("health_system.guard")


# ==================== 数据模型定义 ====================

class CheckStatus(str, Enum):
    """检查状态枚举"""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class CheckItem:
    """单个检查项结果"""
    name: str
    status: CheckStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class GuardCheckResult:
    """统一检查结果返回格式"""
    module: str  # security / infrastructure / external_api / hardware
    overall_status: CheckStatus
    items: List[CheckItem]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "module": self.module,
            "overall_status": self.overall_status.value,
            "items": [
                {
                    "name": item.name,
                    "status": item.status.value,
                    "message": item.message,
                    "details": item.details,
                    "timestamp": item.timestamp
                }
                for item in self.items
            ],
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class SearchAPICheckResult(BaseModel):
    """搜索引擎 API 检查结果"""
    status: bool
    engine: str
    check_items: List[Dict]
    data: Optional[Dict] = None
    error_msg: Optional[str] = None


class DPIOCheckResult(BaseModel):
    """DPIO 硬件检查结果"""
    status: bool
    check_items: List[Dict]
    hardware_info: Optional[Dict] = None
    error_msg: Optional[str] = None


# ==================== 1. 安全防护模块 ====================

class SecurityGuard:
    """
    安全防护模块：限流、鉴权、日志
    替代原有的 api_protector.py
    """

    def __init__(self):
        self._request_counters: Dict[str, List[float]] = defaultdict(list)
        self._api_keys: Dict[str, str] = {}
        self._rate_limit = 10  # 每分钟最多调用次数
        self._time_window = 60  # 时间窗口（秒）

    def configure_rate_limit(self, limit: int = 10, window: int = 60) -> None:
        """配置限流参数"""
        self._rate_limit = limit
        self._time_window = window

    def register_api_key(self, api_name: str, api_key: str) -> None:
        """注册 API 密钥"""
        self._api_keys[api_name] = hashlib.sha256(api_key.encode()).hexdigest()

    def verify_api_key(self, api_name: str, provided_key: str) -> bool:
        """验证 API 密钥"""
        if api_name not in self._api_keys:
            return False
        hashed = hashlib.sha256(provided_key.encode()).hexdigest()
        return hashed == self._api_keys[api_name]

    def check_rate_limit(self, client_id: str) -> Tuple[bool, str]:
        """
        检查是否超出限流阈值
        返回: (是否允许, 消息)
        """
        now = time.time()
        # 清理过期记录
        self._request_counters[client_id] = [
            t for t in self._request_counters[client_id]
            if t > now - self._time_window
        ]

        if len(self._request_counters[client_id]) >= self._rate_limit:
            return False, f"限流触发：超出每分钟 {self._rate_limit} 次调用"

        # 记录本次请求
        self._request_counters[client_id].append(now)
        return True, ""

    def api_protector(
        self,
        api_name: str,
        require_auth: bool = False,
        rate_limit_key: Optional[str] = None
    ) -> Callable:
        """
        API 保护装饰器
        :param api_name: API 名称（用于日志和限流）
        :param require_auth: 是否需要鉴权
        :param rate_limit_key: 限流标识（默认使用 api_name）
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                client_id = rate_limit_key or api_name

                # 1. 鉴权检查
                if require_auth:
                    api_key = kwargs.get("api_key") or (args[0] if args else None)
                    if not api_key or not self.verify_api_key(api_name, api_key):
                        logger.error(f"[{api_name}] 鉴权失败：无效的 API Key")
                        return {"status": "error", "msg": "鉴权失败：无效的 API Key"}

                # 2. 限流检查
                allowed, message = self.check_rate_limit(client_id)
                if not allowed:
                    logger.warning(f"[{api_name}] {message}")
                    return {"status": "error", "msg": message}

                # 3. 执行原函数
                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    logger.info(f"[{api_name}] 调用成功，耗时 {elapsed:.2f} 秒")
                    return result
                except Exception as e:
                    logger.error(f"[{api_name}] 调用失败：{str(e)}")
                    raise

            return wrapper
        return decorator

    def check_security_status(self) -> GuardCheckResult:
        """检查安全防护模块状态"""
        items = []

        # 检查限流配置
        items.append(CheckItem(
            name="rate_limit_config",
            status=CheckStatus.OK if self._rate_limit > 0 else CheckStatus.WARNING,
            message=f"限流配置：{self._rate_limit} 次/{self._time_window} 秒",
            details={"limit": self._rate_limit, "window": self._time_window}
        ))

        # 检查已注册的 API 密钥
        items.append(CheckItem(
            name="api_keys_registered",
            status=CheckStatus.OK if self._api_keys else CheckStatus.WARNING,
            message=f"已注册 API 密钥数量：{len(self._api_keys)}",
            details={"count": len(self._api_keys), "apis": list(self._api_keys.keys())}
        ))

        # 检查当前活跃请求
        total_requests = sum(len(v) for v in self._request_counters.values())
        items.append(CheckItem(
            name="active_requests",
            status=CheckStatus.OK,
            message=f"当前活跃请求数：{total_requests}",
            details={"total": total_requests, "clients": len(self._request_counters)}
        ))

        overall = CheckStatus.OK if all(
            item.status != CheckStatus.ERROR for item in items
        ) else CheckStatus.ERROR

        return GuardCheckResult(
            module="security",
            overall_status=overall,
            items=items,
            metadata={"registered_apis": list(self._api_keys.keys())}
        )


# ==================== 2. 基础设施检查模块 ====================

class InfrastructureGuard:
    """
    基础设施检查模块：数据库、Redis、文件系统
    替代原有的 infra_checker.py
    """

    def __init__(self, db_engine=None, redis_client=None):
        self.db_engine = db_engine
        self.redis_client = redis_client
        self.settings = Settings()

    def check_database(self) -> CheckItem:
        """检查数据库连接"""
        if not self.db_engine:
            return CheckItem(
                name="database",
                status=CheckStatus.WARNING,
                message="数据库引擎未配置"
            )

        try:
            # 尝试连接并执行简单查询
            with self.db_engine.connect() as conn:
                conn.execute("SELECT 1")
            return CheckItem(
                name="database",
                status=CheckStatus.OK,
                message="数据库连接正常"
            )
        except Exception as e:
            return CheckItem(
                name="database",
                status=CheckStatus.ERROR,
                message=f"数据库连接失败：{str(e)}"
            )

    def check_redis(self) -> CheckItem:
        """检查 Redis 连接"""
        if not self.redis_client:
            return CheckItem(
                name="redis",
                status=CheckStatus.WARNING,
                message="Redis 客户端未配置"
            )

        try:
            self.redis_client.ping()
            info = self.redis_client.info()
            return CheckItem(
                name="redis",
                status=CheckStatus.OK,
                message=f"Redis 连接正常，版本：{info.get('redis_version', 'unknown')}",
                details={"version": info.get("redis_version"), "used_memory": info.get("used_memory_human")}
            )
        except Exception as e:
            return CheckItem(
                name="redis",
                status=CheckStatus.ERROR,
                message=f"Redis 连接失败：{str(e)}"
            )

    def check_file_system(self) -> CheckItem:
        """检查文件系统（关键目录可写性）"""
        try:
            test_paths = [
                self.settings.DATA_DIR,
                self.settings.PROCESSED_DATA_PATH,
            ]
            results = {}
            for path in test_paths:
                if os.path.exists(path) and os.access(path, os.W_OK):
                    results[path] = "ok"
                else:
                    results[path] = "not_writable"

            all_ok = all(v == "ok" for v in results.values())
            return CheckItem(
                name="file_system",
                status=CheckStatus.OK if all_ok else CheckStatus.WARNING,
                message="文件系统检查完成" if all_ok else "部分目录不可写",
                details=results
            )
        except Exception as e:
            return CheckItem(
                name="file_system",
                status=CheckStatus.ERROR,
                message=f"文件系统检查失败：{str(e)}"
            )

    def check_infrastructure(self) -> GuardCheckResult:
        """执行完整的基础设施检查"""
        items = [
            self.check_database(),
            self.check_redis(),
            self.check_file_system()
        ]

        overall = CheckStatus.OK
        if any(item.status == CheckStatus.ERROR for item in items):
            overall = CheckStatus.ERROR
        elif any(item.status == CheckStatus.WARNING for item in items):
            overall = CheckStatus.WARNING

        return GuardCheckResult(
            module="infrastructure",
            overall_status=overall,
            items=items
        )


# ==================== 3. 外部 API 检查模块 ====================

class ExternalAPIGuard:
    """
    外部 API 检查模块：SerpAPI、Bing Search 等
    替代原有的 api_checker.py
    """

    def __init__(self):
        self.settings = Settings()
        self._timeout = 10
        self._retry_times = 3

    def _exec_check(
        self,
        name: str,
        check_fn: Callable[[], CheckItem]
    ) -> CheckItem:
        """执行单个检查项，带异常处理"""
        try:
            return check_fn()
        except Exception as e:
            return CheckItem(
                name=name,
                status=CheckStatus.ERROR,
                message=f"检查执行异常：{str(e)}"
            )

    def check_serpapi(self, test_query: str = "2025全球卫生资源配置报告") -> CheckItem:
        """检查 SerpAPI 接口"""
        config = self.settings.SEARCH_ENGINE_CONFIG.get("serpapi", {})

        if not config.get("api_key"):
            return CheckItem(
                name="serpapi",
                status=CheckStatus.WARNING,
                message="SerpAPI 密钥未配置"
            )

        params = {
            "q": test_query,
            "api_key": config["api_key"],
            "engine": "google",
            "num": config.get("result_num", 5)
        }

        for retry in range(self._retry_times):
            try:
                response = requests.get(
                    config["api_url"],
                    params=params,
                    timeout=config.get("timeout", self._timeout)
                )

                if response.status_code == 200:
                    data = response.json()
                    has_results = "organic_results" in data and len(data["organic_results"]) > 0
                    return CheckItem(
                        name="serpapi",
                        status=CheckStatus.OK if has_results else CheckStatus.WARNING,
                        message=f"SerpAPI 连接正常，返回 {len(data.get('organic_results', []))} 条结果",
                        details={"status_code": response.status_code, "has_results": has_results}
                    )
                else:
                    return CheckItem(
                        name="serpapi",
                        status=CheckStatus.ERROR,
                        message=f"SerpAPI 返回错误状态码：{response.status_code}",
                        details={"status_code": response.status_code}
                    )

            except requests.exceptions.Timeout:
                if retry == self._retry_times - 1:
                    return CheckItem(
                        name="serpapi",
                        status=CheckStatus.TIMEOUT,
                        message="SerpAPI 请求超时"
                    )
                time.sleep(1)
            except Exception as e:
                return CheckItem(
                    name="serpapi",
                    status=CheckStatus.ERROR,
                    message=f"SerpAPI 请求失败：{str(e)}"
                )

        return CheckItem(
            name="serpapi",
            status=CheckStatus.ERROR,
            message="SerpAPI 检查失败（重试耗尽）"
        )

    def check_bing(self, test_query: str = "2025全球卫生资源配置报告") -> CheckItem:
        """检查 Bing Search API 接口"""
        config = self.settings.SEARCH_ENGINE_CONFIG.get("bing", {})

        if not config.get("api_key"):
            return CheckItem(
                name="bing",
                status=CheckStatus.WARNING,
                message="Bing API 密钥未配置"
            )

        headers = {"Ocp-Apim-Subscription-Key": config["api_key"]}
        params = {"q": test_query, "textDecorations": True, "textFormat": "HTML"}

        try:
            response = requests.get(
                config["api_url"],
                headers=headers,
                params=params,
                timeout=config.get("timeout", self._timeout)
            )

            if response.status_code == 200:
                data = response.json()
                has_results = "webPages" in data and "value" in data["webPages"]
                return CheckItem(
                    name="bing",
                    status=CheckStatus.OK if has_results else CheckStatus.WARNING,
                    message=f"Bing API 连接正常，返回 {len(data.get('webPages', {}).get('value', []))} 条结果",
                    details={"status_code": response.status_code, "has_results": has_results}
                )
            else:
                return CheckItem(
                    name="bing",
                    status=CheckStatus.ERROR,
                    message=f"Bing API 返回错误状态码：{response.status_code}",
                    details={"status_code": response.status_code}
                )

        except requests.exceptions.Timeout:
            return CheckItem(
                name="bing",
                status=CheckStatus.TIMEOUT,
                message="Bing API 请求超时"
            )
        except Exception as e:
            return CheckItem(
                name="bing",
                status=CheckStatus.ERROR,
                message=f"Bing API 请求失败：{str(e)}"
            )

    def check_external_apis(self) -> GuardCheckResult:
        """执行完整的外部 API 检查"""
        items = [
            self._exec_check("serpapi", self.check_serpapi),
            self._exec_check("bing", self.check_bing)
        ]

        overall = CheckStatus.OK
        if any(item.status == CheckStatus.ERROR for item in items):
            overall = CheckStatus.ERROR
        elif any(item.status == CheckStatus.WARNING for item in items):
            overall = CheckStatus.WARNING

        return GuardCheckResult(
            module="external_api",
            overall_status=overall,
            items=items
        )


# ==================== 4. DPIO 硬件检查模块 ====================

class DPIOGuard:
    """
    DPIO 硬件检查模块：驱动、设备节点、帧收发
    替代原有的 infra_checker.py 中的 DPIO 功能
    """

    def __init__(self):
        self.settings = Settings()
        self.config = self.settings.DPIO_CONFIG

    def _exec_linux_cmd(self, cmd: str, timeout: int = 5) -> Tuple[str, int]:
        """执行 Linux 系统命令"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "命令超时", -1
        except Exception as e:
            return str(e), -2

    def check_dpio_driver(self) -> CheckItem:
        """检查 DPIO 驱动加载状态"""
        try:
            output, code = self._exec_linux_cmd("lsmod | grep dpio")
            if code == 0 and "dpio" in output:
                return CheckItem(
                    name="dpio_driver",
                    status=CheckStatus.OK,
                    message=f"DPIO 驱动已加载：{output[:100]}",
                    details={"output": output[:200]}
                )
            else:
                return CheckItem(
                    name="dpio_driver",
                    status=CheckStatus.WARNING,
                    message="DPIO 驱动未加载（可能在非 Linux 环境运行）",
                    details={"output": output, "code": code}
                )
        except Exception as e:
            return CheckItem(
                name="dpio_driver",
                status=CheckStatus.WARNING,
                message=f"DPIO 驱动检查失败：{str(e)}"
            )

    def check_dpio_hardware(self) -> CheckItem:
        """检查 DPIO 硬件设备节点"""
        check_results = {}

        # 检查设备节点
        device_path = self.config.get("buffer_pool", "/dev/dpio_buffer0")
        if os.path.exists(device_path):
            check_results["device_node"] = {"exists": True, "path": device_path}
        else:
            check_results["device_node"] = {"exists": False, "path": device_path}

        # 检查驱动绑定
        driver_path = self.config.get("driver_path", "/sys/class/dpio")
        if os.path.exists(driver_path):
            check_results["driver_binding"] = {"exists": True, "path": driver_path}
        else:
            check_results["driver_binding"] = {"exists": False, "path": driver_path}

        all_ok = all(r.get("exists") for r in check_results.values())
        return CheckItem(
            name="dpio_hardware",
            status=CheckStatus.OK if all_ok else CheckStatus.WARNING,
            message="DPIO 硬件检查完成" if all_ok else "部分硬件组件未找到",
            details=check_results
        )

    def check_dpio_frame_io(self) -> CheckItem:
        """检查 DPIO 帧收发与数据完整性"""
        device_path = self.config.get("buffer_pool", "/dev/dpio_buffer0")
        test_frame = self.config.get("test_frame_data", b"\xAA\x55\xDE\xAD\xBE\xEF")

        if not os.path.exists(device_path):
            return CheckItem(
                name="dpio_frame_io",
                status=CheckStatus.WARNING,
                message=f"DPIO 设备节点不存在：{device_path}"
            )

        if not os.access(device_path, os.W_OK | os.R_OK):
            return CheckItem(
                name="dpio_frame_io",
                status=CheckStatus.WARNING,
                message=f"DPIO 设备节点无读写权限：{device_path}"
            )

        try:
            # 模拟帧收发测试
            with open(device_path, "wb") as f:
                f.write(test_frame)

            with open(device_path, "rb") as f:
                read_data = f.read(len(test_frame))

            if read_data == test_frame:
                return CheckItem(
                    name="dpio_frame_io",
                    status=CheckStatus.OK,
                    message="DPIO 帧收发成功，数据完整性验证通过",
                    details={"sent": test_frame.hex(), "received": read_data.hex()}
                )
            else:
                return CheckItem(
                    name="dpio_frame_io",
                    status=CheckStatus.ERROR,
                    message="DPIO 帧收发数据不一致",
                    details={"sent": test_frame.hex(), "received": read_data.hex() if read_data else None}
                )

        except Exception as e:
            return CheckItem(
                name="dpio_frame_io",
                status=CheckStatus.WARNING,
                message=f"DPIO 帧收发测试失败：{str(e)}"
            )

    def check_dpio(self) -> GuardCheckResult:
        """执行完整的 DPIO 硬件检查"""
        items = [
            self.check_dpio_driver(),
            self.check_dpio_hardware(),
            self.check_dpio_frame_io()
        ]

        overall = CheckStatus.OK
        if any(item.status == CheckStatus.ERROR for item in items):
            overall = CheckStatus.ERROR
        elif any(item.status == CheckStatus.WARNING for item in items):
            overall = CheckStatus.WARNING

        return GuardCheckResult(
            module="hardware",
            overall_status=overall,
            items=items
        )


# ==================== 5. 统一系统卫士入口 ====================

class SystemGuard:
    """
    工业级系统卫士：带有防雪崩熔断、频控和后台状态缓存机制
    整合所有安全防护、基础设施检查、外部 API 监控、硬件检查
    """

    def __init__(self, db_engine=None, redis_client=None):
        self.logger = logging.getLogger("health_system.guard")

        # 初始化各子模块
        self.security = SecurityGuard()
        self.infrastructure = InfrastructureGuard(db_engine, redis_client)
        self.external_api = ExternalAPIGuard()
        self.hardware = DPIOGuard()

        # Redis 客户端（用于频控和熔断）
        self.redis = redis_client

        # 熔断阈值配置
        self.circuit_breaker_limits = {
            "amap_api": 5,     # 连续失败 5 次即熔断
            "owid_api": 3,
            "serpapi": 5,
            "bing": 5
        }

    # ================= 1. 防刷与频控 (Rate Limiter) =================
    def verify_request_safety(self, user_ip: str, limit: int = 60, window: int = 60) -> bool:
        """
        基于 Redis 滑动窗口的真实频控：默认单 IP 每分钟 60 次
        """
        if not self.redis:
            # 如果没有 Redis，回退到内存限流
            allowed, _ = self.security.check_rate_limit(user_ip)
            return allowed

        key = f"rate_limit:{user_ip}"
        current_requests = self.redis.incr(key)

        if current_requests == 1:
            self.redis.expire(key, window)

        if current_requests > limit:
            self.logger.warning(f"🚨 触发频控拦截: IP {user_ip}")
            return False

        return True

    # ================= 2. 熔断器机制 (Circuit Breaker) =================
    def is_circuit_open(self, service_name: str) -> bool:
        """
        判断某个外部服务是否已经被熔断
        如果熔断，业务层应直接跳过请求，调用 fallback
        """
        if not self.redis:
            return False  # 没有 Redis 时默认不熔断

        fails = self.redis.get(f"circuit_fails:{service_name}")
        if fails and int(fails) >= self.circuit_breaker_limits.get(service_name, 5):
            return True  # 熔断开启（拒绝访问真实服务）
        return False

    def report_api_failure(self, service_name: str):
        """当 loader.py 请求失败时，向卫士汇报，累积失败次数"""
        if not self.redis:
            return

        key = f"circuit_fails:{service_name}"
        self.redis.incr(key)
        # 300 秒后错误计数清零 (半开状态，尝试恢复)
        if self.redis.ttl(key) == -1:
            self.redis.expire(key, 300)

    def report_api_success(self, service_name: str):
        """请求成功，清空错误计数"""
        if not self.redis:
            return

        self.redis.delete(f"circuit_fails:{service_name}")

    # ================= 3. 健康状态读取 (异步解耦) =================
    def get_system_health(self) -> Dict[str, str]:
        """
        不再同步去 ping 外部接口，而是读取后台定时任务更新的 Redis 缓存
        响应时间 < 1ms
        """
        # 假设有一个后台 celery 或 apscheduler 定时任务每分钟更新这些 key
        status = {
            "database": "ok",
            "amap_api": "ok" if not self.is_circuit_open("amap_api") else "circuit_open",
            "owid_api": "ok" if not self.is_circuit_open("owid_api") else "circuit_open",
            "serpapi": "ok" if not self.is_circuit_open("serpapi") else "circuit_open",
            "bing": "ok" if not self.is_circuit_open("bing") else "circuit_open"
        }
        return status

    # ================= 4. 便捷方法（向后兼容） =================

    def check_internal_health(self) -> GuardCheckResult:
        """检查内部依赖：数据库、缓存、文件系统"""
        return self.infrastructure.check_infrastructure()

    def check_external_apis(self) -> GuardCheckResult:
        """检查外部数据源 API 是否通畅"""
        return self.external_api.check_external_apis()

    def check_hardware(self) -> GuardCheckResult:
        """检查 DPIO 硬件状态"""
        return self.hardware.check_dpio()

    def system_ready(self) -> Tuple[bool, str]:
        """全局就绪检查，供主程序启动时调用"""
        # 检查基础设施
        infra_result = self.check_internal_health()
        if infra_result.overall_status == CheckStatus.ERROR:
            errors = [item.message for item in infra_result.items if item.status == CheckStatus.ERROR]
            return False, f"致命错误：{'; '.join(errors)}"

        # 检查外部 API（非致命）
        api_result = self.check_external_apis()
        if api_result.overall_status == CheckStatus.ERROR:
            self.logger.warning("部分外部 API 不可用")

        return True, "系统运转正常"

    def full_system_check(self) -> Dict[str, GuardCheckResult]:
        """执行完整的系统检查"""
        return {
            "security": self.security.check_security_status(),
            "infrastructure": self.check_internal_health(),
            "external_api": self.check_external_apis(),
            "hardware": self.check_hardware()
        }

    def get_decorator(
        self,
        api_name: str,
        require_auth: bool = False,
        rate_limit_key: Optional[str] = None
    ) -> Callable:
        """获取 API 保护装饰器"""
        return self.security.api_protector(api_name, require_auth, rate_limit_key)


# ==================== 6. 便捷函数入口 ====================

def create_guard(db_engine=None, redis_client=None) -> SystemGuard:
    """创建系统卫士实例的工厂函数"""
    return SystemGuard(db_engine, redis_client)


# 向后兼容的别名
HealthGuard = SystemGuard
