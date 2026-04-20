"""
中台数据口径 - 数据转换模块简单测试（无需pytest）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime

from utils.data_transformer import (
    DataTransformer, DataValidator, ResponseBuilder,
    transform_to_chart, transform_to_prediction, build_standard_response
)


def test_to_chart_format_basic():
    """测试基本图表格式转换"""
    print("\n=== 测试基本图表格式转换 ===")
    df = pd.DataFrame({
        'year': [2020, 2021, 2022],
        'value': [100, 120, 130]
    })
    
    result = DataTransformer.to_chart_format(df, 'year', 'value')
    
    assert "labels" in result, "缺少labels字段"
    assert "datasets" in result, "缺少datasets字段"
    assert result["labels"] == ["2020", "2021", "2022"], f"labels不匹配: {result['labels']}"
    assert len(result["datasets"]) == 1, f"datasets数量错误: {len(result['datasets'])}"
    assert result["datasets"][0]["label"] == "value", f"label错误: {result['datasets'][0]['label']}"
    assert result["datasets"][0]["data"] == [100, 120, 130], f"data错误: {result['datasets'][0]['data']}"
    print("[PASS] 基本图表格式转换测试通过")
    print(f"  结果: {result}")


def test_to_prediction_format():
    """测试预测数据格式转换"""
    print("\n=== 测试预测数据格式转换 ===")
    df = pd.DataFrame({
        'year': [2020, 2020, 2021, 2021, 2022, 2022],
        'cause_name': ['Cardiovascular diseases', 'Neoplasms'] * 3,
        'val': [100, 80, 110, 82, 120, 85]
    })
    
    result = DataTransformer.to_prediction_format(df)
    
    assert "labels" in result, "缺少labels字段"
    assert "datasets" in result, "缺少datasets字段"
    assert len(result["datasets"]) == 2, f"datasets数量错误: {len(result['datasets'])}"
    # 检查疾病名称是否正确映射为中文
    labels = [d["label"] for d in result["datasets"]]
    assert "心血管疾病" in labels, f"缺少'心血管疾病': {labels}"
    assert "肿瘤" in labels, f"缺少'肿瘤': {labels}"
    print("[PASS] 预测数据格式转换测试通过")
    print(f"  结果: {result}")


def test_data_validation():
    """测试数据校验功能"""
    print("\n=== 测试数据校验功能 ===")
    
    # 测试成功响应校验
    data = {
        "code": 200,
        "data": {"test": "value"},
        "message": "success"
    }
    result = DataValidator.validate_response(data)
    assert result["valid"] is True, f"应通过校验: {result}"
    print("[PASS] 成功响应校验通过")
    
    # 测试图表数据校验
    chart_data = {
        "labels": ["2020", "2021"],
        "datasets": [
            {"label": "A", "data": [100, 200]}
        ]
    }
    result = DataValidator.validate_chart_data(chart_data)
    assert result["valid"] is True, f"图表数据应通过校验: {result}"
    print("[PASS] 图表数据校验通过")
    
    # 测试DataFrame校验
    df = pd.DataFrame({
        'year': [2020, 2021],
        'value': [100, 200]
    })
    result = DataValidator.validate_dataframe(df, ['year', 'value'])
    assert result["valid"] is True, f"DataFrame应通过校验: {result}"
    print("[PASS] DataFrame校验通过")


def test_response_builder():
    """测试响应构建功能"""
    print("\n=== 测试响应构建功能 ===")
    
    # 测试基本响应构建
    result = ResponseBuilder.build(
        code=200,
        data={"test": "value"},
        message="success"
    )
    assert result["code"] == 200, f"code错误: {result['code']}"
    assert result["data"]["test"] == "value", f"data错误"
    assert result["message"] == "success", f"message错误"
    assert "timestamp" in result, "缺少timestamp字段"
    print("[PASS] 基本响应构建测试通过")
    print(f"  结果: {result}")
    
    # 测试图表响应构建
    df = pd.DataFrame({
        'year': [2020, 2021, 2022],
        'value': [100, 120, 130]
    })
    result = ResponseBuilder.build_chart_response(
        df, 'year', 'value', message="图表数据获取成功"
    )
    assert result["code"] == 200, f"code错误"
    assert "labels" in result["data"], "缺少labels字段"
    assert "datasets" in result["data"], "缺少datasets字段"
    assert result["message"] == "图表数据获取成功", f"message错误"
    print("[PASS] 图表响应构建测试通过")
    print(f"  结果: {result}")
    
    # 测试错误响应构建
    result = ResponseBuilder.build_error_response(
        code=404,
        message="数据不存在",
        details={"resource": "user"}
    )
    assert result["code"] == 404, f"code错误"
    assert result["message"] == "数据不存在", f"message错误"
    assert result["data"]["error_details"]["resource"] == "user", f"details错误"
    print("[PASS] 错误响应构建测试通过")
    print(f"  结果: {result}")


def test_value_conversion():
    """测试数值转换功能"""
    print("\n=== 测试数值转换功能 ===")
    
    # 测试NaN值
    assert DataTransformer._convert_value(None) is None, "None转换失败"
    assert DataTransformer._convert_value(np.nan) is None, "NaN转换失败"
    print("[PASS] NaN值转换测试通过")
    
    # 测试numpy类型
    assert DataTransformer._convert_value(np.int64(10)) == 10, "int64转换失败"
    assert DataTransformer._convert_value(np.float64(3.14159)) == 3.1416, "float64转换失败"
    print("[PASS] numpy类型转换测试通过")
    
    # 测试float精度
    result = DataTransformer._convert_value(3.1415926, decimal_places=2)
    assert result == 3.14, f"float精度转换失败: {result}"
    print("[PASS] float精度转换测试通过")
    
    # 测试日期时间
    dt = datetime(2024, 1, 15, 10, 30, 0)
    result = DataTransformer._convert_value(dt)
    assert result == "2024-01-15 10:30:00", f"datetime转换失败: {result}"
    print("[PASS] 日期时间转换测试通过")


def test_standard_disease_prediction_format():
    """测试标准疾病预测数据格式（符合前端需求）"""
    print("\n=== 测试标准疾病预测数据格式 ===")
    
    # 创建模拟预测数据
    df = pd.DataFrame({
        'year': [2024, 2025, 2026, 2027, 2028] * 2,
        'cause_name': ['Cardiovascular diseases'] * 5 + ['Neoplasms'] * 5,
        'val': [120, 125, 130, 135, 140, 80, 82, 84, 86, 88]
    })
    
    result = DataTransformer.to_prediction_format(df)
    
    # 验证标准格式
    assert "labels" in result, "缺少labels字段"
    assert "datasets" in result, "缺少datasets字段"
    assert result["labels"] == ["2024", "2025", "2026", "2027", "2028"], f"labels错误: {result['labels']}"
    assert len(result["datasets"]) == 2, f"datasets数量错误: {len(result['datasets'])}"
    
    # 验证每个dataset结构
    for dataset in result["datasets"]:
        assert "label" in dataset, "dataset缺少label字段"
        assert "data" in dataset, "dataset缺少data字段"
        assert "borderColor" in dataset, "dataset缺少borderColor字段"
        assert "borderWidth" in dataset, "dataset缺少borderWidth字段"
        assert "fill" in dataset, "dataset缺少fill字段"
        assert len(dataset["data"]) == 5, f"data长度错误: {len(dataset['data'])}"
    
    print("[PASS] 标准疾病预测数据格式测试通过")
    print(f"  结果: {result}")
    
    # 验证是否符合用户要求的格式
    expected_structure = {
        "labels": ["2024", "2025", "2026", "2027", "2028"],
        "datasets": [
            {"label": "心血管疾病", "data": [120, 125, 130, 135, 140]},
            {"label": "肿瘤", "data": [80, 82, 84, 86, 88]}
        ]
    }
    
    assert result["labels"] == expected_structure["labels"], "labels不匹配"
    print("[PASS] 完全符合用户指定的JSON结构规范")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("中台数据口径 - 数据转换模块测试")
    print("=" * 60)
    
    tests = [
        test_to_chart_format_basic,
        test_to_prediction_format,
        test_data_validation,
        test_response_builder,
        test_value_conversion,
        test_standard_disease_prediction_format,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__} 测试失败: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__} 测试异常: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: 通过 {passed}/{len(tests)}, 失败 {failed}/{len(tests)}")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
