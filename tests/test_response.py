"""
标准化响应模块测试验证脚本

验证内容：
1. 成功响应格式正确性
2. 错误响应格式正确性
3. 时间戳ISO 8601格式验证
4. HTTP状态码与业务状态码一致性
5. 空数据处理
"""

import json
import re
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.response import success_response, error_response, ResponseCode


def test_success_response():
    """测试成功响应"""
    print("=" * 60)
    print("测试1: 成功响应 - 带数据")
    print("=" * 60)
    
    data = {"users": ["Alice", "Bob"], "count": 2}
    response = success_response(data, "获取用户列表成功")
    
    print(f"响应内容: {json.dumps(response, indent=2, ensure_ascii=False)}")
    
    # 验证字段
    assert response["code"] == 200, "状态码应为200"
    assert response["message"] == "获取用户列表成功", "消息不匹配"
    assert response["data"] == data, "数据不匹配"
    assert "timestamp" in response, "缺少timestamp字段"
    assert response["timestamp"].endswith("Z"), "时间戳应包含Z时区标识"
    
    # 验证时间戳格式
    timestamp_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$'
    assert re.match(timestamp_pattern, response["timestamp"]), "时间戳格式不符合ISO 8601"
    
    print("[OK] 测试通过\n")


def test_success_response_empty_data():
    """测试成功响应 - 空数据"""
    print("=" * 60)
    print("测试2: 成功响应 - 空数据（验证默认空字典）")
    print("=" * 60)
    
    response = success_response()
    
    print(f"响应内容: {json.dumps(response, indent=2, ensure_ascii=False)}")
    
    assert response["code"] == 200, "状态码应为200"
    assert response["message"] == "success", "默认消息应为success"
    assert response["data"] == {}, "无数据时应返回空字典而非None"
    assert "timestamp" in response, "缺少timestamp字段"
    
    print("[OK] 测试通过\n")


def test_success_response_none_data():
    """测试成功响应 - None数据"""
    print("=" * 60)
    print("测试3: 成功响应 - 显式传入None数据")
    print("=" * 60)
    
    response = success_response(data=None)
    
    print(f"响应内容: {json.dumps(response, indent=2, ensure_ascii=False)}")
    
    assert response["data"] == {}, "None数据应被转换为空字典"
    
    print("[OK] 测试通过\n")


def test_error_response():
    """测试错误响应"""
    print("=" * 60)
    print("测试4: 错误响应 - 验证HTTP状态码一致性")
    print("=" * 60)
    
    from fastapi.responses import JSONResponse
    
    response = error_response(404, "资源不存在")
    
    print(f"响应类型: {type(response).__name__}")
    print(f"HTTP状态码: {response.status_code}")
    print(f"响应内容: {json.dumps(response.body.decode('utf-8'), indent=2, ensure_ascii=False)}")
    
    # 验证是JSONResponse对象
    assert isinstance(response, JSONResponse), "错误响应应为JSONResponse对象"
    
    # 验证HTTP状态码
    assert response.status_code == 404, "HTTP状态码应为404"
    
    # 解析响应体
    body = json.loads(response.body.decode('utf-8'))
    
    # 验证业务状态码与HTTP状态码一致
    assert body["code"] == 404, "业务状态码应为404"
    assert body["message"] == "资源不存在", "错误消息不匹配"
    assert body["data"] == {}, "错误响应数据应为空字典"
    assert "timestamp" in body, "缺少timestamp字段"
    assert body["timestamp"].endswith("Z"), "时间戳应包含Z时区标识"
    
    print("[OK] 测试通过\n")


def test_error_response_various_codes():
    """测试不同错误码"""
    print("=" * 60)
    print("测试5: 错误响应 - 多种HTTP状态码")
    print("=" * 60)
    
    test_cases = [
        (400, "请求参数错误"),
        (401, "未授权访问"),
        (403, "禁止访问"),
        (404, "资源不存在"),
        (500, "服务器内部错误"),
        (503, "服务不可用")
    ]
    
    for code, message in test_cases:
        response = error_response(code, message)
        body = json.loads(response.body.decode('utf-8'))
        
        assert response.status_code == code, f"HTTP状态码应为{code}"
        assert body["code"] == code, f"业务状态码应为{code}"
        assert body["message"] == message, "消息不匹配"
        
        print(f"  [OK] 状态码 {code}: {message}")
    
    print("[OK] 所有状态码测试通过\n")


def test_response_code_constants():
    """测试响应码常量"""
    print("=" * 60)
    print("测试6: 响应码常量定义")
    print("=" * 60)
    
    print(f"  SUCCESS: {ResponseCode.SUCCESS}")
    print(f"  CREATED: {ResponseCode.CREATED}")
    print(f"  BAD_REQUEST: {ResponseCode.BAD_REQUEST}")
    print(f"  UNAUTHORIZED: {ResponseCode.UNAUTHORIZED}")
    print(f"  FORBIDDEN: {ResponseCode.FORBIDDEN}")
    print(f"  NOT_FOUND: {ResponseCode.NOT_FOUND}")
    print(f"  INTERNAL_ERROR: {ResponseCode.INTERNAL_ERROR}")
    print(f"  SERVICE_UNAVAILABLE: {ResponseCode.SERVICE_UNAVAILABLE}")
    
    assert ResponseCode.SUCCESS == 200
    assert ResponseCode.CREATED == 201
    assert ResponseCode.BAD_REQUEST == 400
    assert ResponseCode.UNAUTHORIZED == 401
    assert ResponseCode.FORBIDDEN == 403
    assert ResponseCode.NOT_FOUND == 404
    assert ResponseCode.INTERNAL_ERROR == 500
    assert ResponseCode.SERVICE_UNAVAILABLE == 503
    
    print("[OK] 测试通过\n")


def test_timestamp_format():
    """测试时间戳格式"""
    print("=" * 60)
    print("测试7: 时间戳格式验证")
    print("=" * 60)
    
    response = success_response({"test": "data"})
    timestamp = response["timestamp"]
    
    print(f"生成的时间戳: {timestamp}")
    
    # 验证格式: YYYY-MM-DDTHH:MM:SS.microsecondsZ
    iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$'
    assert re.match(iso_pattern, timestamp), "时间戳不符合ISO 8601格式"
    
    # 验证可以解析
    try:
        # 移除Z后缀进行解析
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        print(f"解析成功: {dt}")
    except ValueError as e:
        assert False, f"时间戳无法解析: {e}"
    
    print("[OK] 测试通过\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("标准化响应模块 - 全面测试")
    print("=" * 60 + "\n")
    
    try:
        test_success_response()
        test_success_response_empty_data()
        test_success_response_none_data()
        test_error_response()
        test_error_response_various_codes()
        test_response_code_constants()
        test_timestamp_format()
        
        print("=" * 60)
        print("[SUCCESS] 所有测试通过！响应模块符合中台标准")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] 测试异常: {e}")
        return False


if __name__ == "__main__":
    run_all_tests()
