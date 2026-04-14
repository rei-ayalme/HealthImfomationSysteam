"""
疾病预测API标准化改造测试

验证内容：
1. 正常流程响应格式是否符合中台标准
2. 异常场景错误处理是否正确
3. 响应字段完整性验证
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.responses import JSONResponse
from utils.response import success_response, error_response


def test_success_response_structure():
    """测试成功响应结构是否符合标准"""
    print("=" * 60)
    print("测试1: 成功响应结构验证")
    print("=" * 60)
    
    # 模拟接口返回的数据结构
    response_data = {
        "labels": ["2023", "2027", "2031", "2035", "2038"],
        "datasets": [
            {
                "label": "心血管疾病 (SDE 动力学预测)",
                "data": [100.5, 110.2, 125.8, 140.3, 155.6],
                "borderColor": "#2b6cb0",
                "borderWidth": 3
            }
        ]
    }
    
    # 调用标准响应函数
    response = success_response(data=response_data, message="China 疾病演化测算完成")
    
    print(f"响应内容:\n{json.dumps(response, indent=2, ensure_ascii=False)}")
    
    # 验证字段
    assert "code" in response, "缺少code字段"
    assert "message" in response, "缺少message字段"
    assert "data" in response, "缺少data字段"
    assert "timestamp" in response, "缺少timestamp字段"
    
    assert response["code"] == 200, "成功状态码应为200"
    assert response["message"] == "China 疾病演化测算完成", "消息不匹配"
    assert response["data"] == response_data, "数据不匹配"
    assert response["timestamp"].endswith("Z"), "时间戳应包含Z时区标识"
    
    print("[OK] 成功响应结构符合中台标准\n")


def test_error_response_structure():
    """测试错误响应结构是否符合标准"""
    print("=" * 60)
    print("测试2: 错误响应结构验证")
    print("=" * 60)
    
    # 测试400错误
    response = error_response(code=400, message="未能找到 TestRegion 的基线数据，无法进行 SDE 预测")
    
    print(f"响应类型: {type(response).__name__}")
    print(f"HTTP状态码: {response.status_code}")
    
    body = json.loads(response.body.decode('utf-8'))
    print(f"响应体:\n{json.dumps(body, indent=2, ensure_ascii=False)}")
    
    # 验证字段
    assert isinstance(response, JSONResponse), "错误响应应为JSONResponse对象"
    assert response.status_code == 400, "HTTP状态码应为400"
    assert body["code"] == 400, "业务状态码应为400"
    assert body["message"] == "未能找到 TestRegion 的基线数据，无法进行 SDE 预测"
    assert body["data"] == {}, "错误响应data应为空字典"
    assert body["timestamp"].endswith("Z"), "时间戳应包含Z时区标识"
    
    print("[OK] 错误响应结构符合中台标准\n")


def test_500_error_response():
    """测试500服务器错误响应"""
    print("=" * 60)
    print("测试3: 500错误响应验证")
    print("=" * 60)
    
    response = error_response(code=500, message="中台算力引擎异常，请联系管理员")
    body = json.loads(response.body.decode('utf-8'))
    
    print(f"HTTP状态码: {response.status_code}")
    print(f"响应体:\n{json.dumps(body, indent=2, ensure_ascii=False)}")
    
    assert response.status_code == 500, "HTTP状态码应为500"
    assert body["code"] == 500, "业务状态码应为500"
    assert body["message"] == "中台算力引擎异常，请联系管理员"
    
    print("[OK] 500错误响应符合中台标准\n")


def test_response_comparison():
    """对比改造前后的响应格式差异"""
    print("=" * 60)
    print("测试4: 改造前后响应格式对比")
    print("=" * 60)
    
    # 改造前的旧格式
    old_format = {
        "status": "success",
        "chart_data": {
            "labels": ["2023", "2027"],
            "datasets": []
        }
    }
    
    # 改造后的新格式
    response_data = {
        "labels": ["2023", "2027"],
        "datasets": []
    }
    new_format = success_response(data=response_data, message="China 疾病演化测算完成")
    
    print("改造前格式:")
    print(json.dumps(old_format, indent=2, ensure_ascii=False))
    print("\n改造后格式:")
    print(json.dumps(new_format, indent=2, ensure_ascii=False))
    
    # 验证新格式包含所有必要字段
    assert "code" in new_format
    assert "message" in new_format
    assert "data" in new_format
    assert "timestamp" in new_format
    
    print("\n[OK] 改造后格式符合中台标准协议\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("疾病预测API标准化改造 - 功能测试")
    print("=" * 60 + "\n")
    
    try:
        test_success_response_structure()
        test_error_response_structure()
        test_500_error_response()
        test_response_comparison()
        
        print("=" * 60)
        print("[SUCCESS] 所有测试通过！API改造符合中台标准")
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
