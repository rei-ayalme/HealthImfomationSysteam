"""
SystemGuard 模块单元测试与集成测试
测试覆盖：
1. 安全防护模块 (SecurityGuard)
2. 基础设施检查模块 (InfrastructureGuard)
3. 外部 API 检查模块 (ExternalAPIGuard)
4. DPIO 硬件检查模块 (DPIOGuard)
5. 统一入口 (SystemGuard)
"""

import time
import unittest
from unittest.mock import MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.core.guard import (
    SystemGuard,
    SecurityGuard,
    InfrastructureGuard,
    ExternalAPIGuard,
    DPIOGuard,
    CheckStatus,
    CheckItem,
    GuardCheckResult,
    create_guard
)


class TestSecurityGuard(unittest.TestCase):
    """安全防护模块测试"""

    def setUp(self):
        self.security = SecurityGuard()

    def test_rate_limit_configuration(self):
        """测试限流配置"""
        self.security.configure_rate_limit(limit=5, window=30)
        allowed, msg = self.security.check_rate_limit("test_client")
        self.assertTrue(allowed)
        self.assertEqual(msg, "")

    def test_rate_limit_enforcement(self):
        """测试限流执行"""
        self.security.configure_rate_limit(limit=2, window=60)

        # 前两次应该通过
        self.assertTrue(self.security.check_rate_limit("client1")[0])
        self.assertTrue(self.security.check_rate_limit("client1")[0])

        # 第三次应该被限流
        allowed, msg = self.security.check_rate_limit("client1")
        self.assertFalse(allowed)
        self.assertIn("限流触发", msg)

    def test_api_key_registration_and_verification(self):
        """测试 API 密钥注册和验证"""
        self.security.register_api_key("test_api", "secret_key_123")

        # 正确密钥
        self.assertTrue(self.security.verify_api_key("test_api", "secret_key_123"))

        # 错误密钥
        self.assertFalse(self.security.verify_api_key("test_api", "wrong_key"))

        # 未注册 API
        self.assertFalse(self.security.verify_api_key("unknown_api", "secret_key_123"))

    def test_api_protector_decorator(self):
        """测试 API 保护装饰器"""
        call_count = 0

        @self.security.api_protector("test_endpoint")
        def test_endpoint():
            nonlocal call_count
            call_count += 1
            return {"status": "success"}

        result = test_endpoint()
        self.assertEqual(result["status"], "success")
        self.assertEqual(call_count, 1)

    def test_api_protector_with_auth(self):
        """测试带鉴权的装饰器"""
        self.security.register_api_key("protected_api", "valid_key")

        @self.security.api_protector("protected_api", require_auth=True)
        def protected_endpoint(api_key=None):
            return {"status": "success"}

        # 无密钥
        result = protected_endpoint()
        self.assertEqual(result["status"], "error")
        self.assertIn("鉴权失败", result["msg"])

        # 错误密钥
        result = protected_endpoint(api_key="invalid_key")
        self.assertEqual(result["status"], "error")

        # 正确密钥
        result = protected_endpoint(api_key="valid_key")
        self.assertEqual(result["status"], "success")

    def test_security_status_check(self):
        """测试安全状态检查"""
        result = self.security.check_security_status()

        self.assertEqual(result.module, "security")
        self.assertIsInstance(result.overall_status, CheckStatus)
        self.assertGreater(len(result.items), 0)

        # 检查是否包含关键检查项
        item_names = [item.name for item in result.items]
        self.assertIn("rate_limit_config", item_names)


class TestInfrastructureGuard(unittest.TestCase):
    """基础设施检查模块测试"""

    def setUp(self):
        self.infrastructure = InfrastructureGuard()

    def test_database_check_without_engine(self):
        """测试无数据库引擎时的检查"""
        result = self.infrastructure.check_database()

        self.assertEqual(result.name, "database")
        self.assertEqual(result.status, CheckStatus.WARNING)
        self.assertIn("未配置", result.message)

    def test_redis_check_without_client(self):
        """测试无 Redis 客户端时的检查"""
        result = self.infrastructure.check_redis()

        self.assertEqual(result.name, "redis")
        self.assertEqual(result.status, CheckStatus.WARNING)
        self.assertIn("未配置", result.message)

    @patch("modules.core.guard.os.path.exists")
    @patch("modules.core.guard.os.access")
    def test_file_system_check(self, mock_access, mock_exists):
        """测试文件系统检查"""
        mock_exists.return_value = True
        mock_access.return_value = True

        result = self.infrastructure.check_file_system()

        self.assertEqual(result.name, "file_system")
        self.assertEqual(result.status, CheckStatus.OK)

    def test_full_infrastructure_check(self):
        """测试完整基础设施检查"""
        result = self.infrastructure.check_infrastructure()

        self.assertEqual(result.module, "infrastructure")
        self.assertIsInstance(result.overall_status, CheckStatus)
        self.assertEqual(len(result.items), 3)


class TestExternalAPIGuard(unittest.TestCase):
    """外部 API 检查模块测试"""

    def setUp(self):
        self.external_api = ExternalAPIGuard()

    @patch("modules.core.guard.requests.get")
    def test_serpapi_check_without_key(self, mock_get):
        """测试无 SerpAPI 密钥时的检查"""
        result = self.external_api.check_serpapi()

        self.assertEqual(result.name, "serpapi")
        self.assertEqual(result.status, CheckStatus.WARNING)
        self.assertIn("未配置", result.message)
        mock_get.assert_not_called()

    @patch("modules.core.guard.requests.get")
    def test_bing_check_without_key(self, mock_get):
        """测试无 Bing API 密钥时的检查"""
        result = self.external_api.check_bing()

        self.assertEqual(result.name, "bing")
        self.assertEqual(result.status, CheckStatus.WARNING)
        self.assertIn("未配置", result.message)
        mock_get.assert_not_called()

    def test_full_external_api_check(self):
        """测试完整外部 API 检查"""
        result = self.external_api.check_external_apis()

        self.assertEqual(result.module, "external_api")
        self.assertIsInstance(result.overall_status, CheckStatus)
        self.assertGreaterEqual(len(result.items), 2)


class TestDPIOGuard(unittest.TestCase):
    """DPIO 硬件检查模块测试"""

    def setUp(self):
        self.hardware = DPIOGuard()

    @patch("modules.core.guard.os.path.exists")
    def test_dpio_hardware_check(self, mock_exists):
        """测试 DPIO 硬件检查"""
        mock_exists.return_value = False

        result = self.hardware.check_dpio_hardware()

        self.assertEqual(result.name, "dpio_hardware")
        self.assertEqual(result.status, CheckStatus.WARNING)

    @patch("modules.core.guard.os.path.exists")
    def test_dpio_frame_io_without_device(self, mock_exists):
        """测试无设备节点时的帧收发检查"""
        mock_exists.return_value = False

        result = self.hardware.check_dpio_frame_io()

        self.assertEqual(result.name, "dpio_frame_io")
        self.assertEqual(result.status, CheckStatus.WARNING)
        self.assertIn("不存在", result.message)

    def test_full_dpio_check(self):
        """测试完整 DPIO 硬件检查"""
        result = self.hardware.check_dpio()

        self.assertEqual(result.module, "hardware")
        self.assertIsInstance(result.overall_status, CheckStatus)
        self.assertEqual(len(result.items), 3)


class TestSystemGuard(unittest.TestCase):
    """统一系统卫士入口测试"""

    def setUp(self):
        self.guard = SystemGuard()

    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.guard.security)
        self.assertIsNotNone(self.guard.infrastructure)
        self.assertIsNotNone(self.guard.external_api)
        self.assertIsNotNone(self.guard.hardware)

    def test_verify_request_safety(self):
        """测试请求安全验证"""
        # 首次请求应该通过
        self.assertTrue(self.guard.verify_request_safety("127.0.0.1", "token123"))

    def test_check_internal_health(self):
        """测试内部健康检查"""
        result = self.guard.check_internal_health()

        self.assertEqual(result.module, "infrastructure")
        self.assertIsInstance(result.overall_status, CheckStatus)

    def test_check_external_apis(self):
        """测试外部 API 检查"""
        result = self.guard.check_external_apis()

        self.assertEqual(result.module, "external_api")
        self.assertIsInstance(result.overall_status, CheckStatus)

    def test_check_hardware(self):
        """测试硬件检查"""
        result = self.guard.check_hardware()

        self.assertEqual(result.module, "hardware")
        self.assertIsInstance(result.overall_status, CheckStatus)

    def test_system_ready(self):
        """测试系统就绪检查"""
        ready, message = self.guard.system_ready()

        # 应该返回布尔值和字符串
        self.assertIsInstance(ready, bool)
        self.assertIsInstance(message, str)

    def test_full_system_check(self):
        """测试完整系统检查"""
        results = self.guard.full_system_check()

        self.assertIn("security", results)
        self.assertIn("infrastructure", results)
        self.assertIn("external_api", results)
        self.assertIn("hardware", results)

        for key, result in results.items():
            self.assertIsInstance(result, GuardCheckResult)
            self.assertIsInstance(result.to_dict(), dict)

    def test_get_decorator(self):
        """测试获取装饰器"""
        decorator = self.guard.get_decorator("test_api")
        self.assertTrue(callable(decorator))

    def test_create_guard_factory(self):
        """测试工厂函数"""
        guard = create_guard()
        self.assertIsInstance(guard, SystemGuard)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_end_to_end_system_check(self):
        """端到端系统检查流程"""
        guard = create_guard()

        # 1. 检查安全状态
        security_result = guard.security.check_security_status()
        self.assertIsNotNone(security_result)

        # 2. 检查基础设施
        infra_result = guard.check_internal_health()
        self.assertIsNotNone(infra_result)

        # 3. 检查外部 API
        api_result = guard.check_external_apis()
        self.assertIsNotNone(api_result)

        # 4. 检查硬件
        hw_result = guard.check_hardware()
        self.assertIsNotNone(hw_result)

        # 5. 系统就绪检查
        ready, message = guard.system_ready()
        self.assertIsInstance(ready, bool)
        self.assertIsInstance(message, str)

    def test_decorator_integration(self):
        """装饰器集成测试"""
        guard = create_guard()
        guard.security.register_api_key("integration_api", "test_key")

        call_count = 0

        @guard.get_decorator("integration_api", require_auth=True)
        def protected_function(api_key=None):
            nonlocal call_count
            call_count += 1
            return {"data": "protected"}

        # 错误密钥
        result = protected_function(api_key="wrong_key")
        self.assertEqual(result["status"], "error")
        self.assertEqual(call_count, 0)

        # 正确密钥
        result = protected_function(api_key="test_key")
        self.assertEqual(result["data"], "protected")
        self.assertEqual(call_count, 1)

    def test_rate_limit_integration(self):
        """限流集成测试"""
        guard = create_guard()
        guard.security.configure_rate_limit(limit=3, window=60)

        call_count = 0

        @guard.get_decorator("rate_limited_api")
        def rate_limited_function():
            nonlocal call_count
            call_count += 1
            return {"status": "success"}

        # 前3次应该成功
        success_count = 0
        for _ in range(3):
            result = rate_limited_function()
            if isinstance(result, dict) and result.get("status") == "success":
                success_count += 1

        # call_count 应该为 3（函数被调用了3次）
        self.assertEqual(call_count, 3)
        self.assertEqual(success_count, 3)

        # 第4次应该被限流（函数不会被调用）
        result = rate_limited_function()
        self.assertEqual(result["status"], "error")
        self.assertIn("限流", result["msg"])
        # call_count 仍然为 3（函数没有被调用）
        self.assertEqual(call_count, 3)


class TestDataModels(unittest.TestCase):
    """数据模型测试"""

    def test_check_item_creation(self):
        """测试 CheckItem 创建"""
        item = CheckItem(
            name="test",
            status=CheckStatus.OK,
            message="Test message",
            details={"key": "value"}
        )

        self.assertEqual(item.name, "test")
        self.assertEqual(item.status, CheckStatus.OK)
        self.assertEqual(item.message, "Test message")
        self.assertEqual(item.details, {"key": "value"})

    def test_guard_check_result_to_dict(self):
        """测试结果转换为字典"""
        item = CheckItem(name="test", status=CheckStatus.OK, message="OK")
        result = GuardCheckResult(
            module="test_module",
            overall_status=CheckStatus.OK,
            items=[item]
        )

        dict_result = result.to_dict()

        self.assertEqual(dict_result["module"], "test_module")
        self.assertEqual(dict_result["overall_status"], "ok")
        self.assertEqual(len(dict_result["items"]), 1)

    def test_check_status_enum(self):
        """测试 CheckStatus 枚举"""
        self.assertEqual(CheckStatus.OK.value, "ok")
        self.assertEqual(CheckStatus.ERROR.value, "error")
        self.assertEqual(CheckStatus.WARNING.value, "warning")
        self.assertEqual(CheckStatus.TIMEOUT.value, "timeout")
        self.assertEqual(CheckStatus.UNKNOWN.value, "unknown")


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
