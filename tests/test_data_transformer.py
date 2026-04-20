"""
中台数据口径 - 数据转换模块测试

测试数据转换、校验和响应构建功能的正确性。
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_transformer import (
    DataTransformer, DataValidator, ResponseBuilder,
    transform_to_chart, transform_to_prediction, build_standard_response
)


class TestDataTransformer:
    """测试数据转换功能"""
    
    def test_to_chart_format_basic(self):
        """测试基本图表格式转换"""
        df = pd.DataFrame({
            'year': [2020, 2021, 2022],
            'value': [100, 120, 130]
        })
        
        result = DataTransformer.to_chart_format(df, 'year', 'value')
        
        assert "labels" in result
        assert "datasets" in result
        assert result["labels"] == ["2020", "2021", "2022"]
        assert len(result["datasets"]) == 1
        assert result["datasets"][0]["label"] == "value"
        assert result["datasets"][0]["data"] == [100, 120, 130]
    
    def test_to_chart_format_multiple_y(self):
        """测试多Y轴图表格式转换"""
        df = pd.DataFrame({
            'year': [2020, 2021, 2022],
            'value1': [100, 120, 130],
            'value2': [200, 220, 240]
        })
        
        result = DataTransformer.to_chart_format(df, 'year', ['value1', 'value2'])
        
        assert len(result["datasets"]) == 2
        assert result["datasets"][0]["label"] == "value1"
        assert result["datasets"][1]["label"] == "value2"
    
    def test_to_chart_format_empty_df(self):
        """测试空DataFrame处理"""
        df = pd.DataFrame()
        result = DataTransformer.to_chart_format(df, 'year', 'value')
        
        assert result == {"labels": [], "datasets": []}
    
    def test_to_chart_format_group_by(self):
        """测试分组图表格式转换"""
        df = pd.DataFrame({
            'year': [2020, 2020, 2021, 2021],
            'disease': ['A', 'B', 'A', 'B'],
            'value': [100, 200, 110, 220]
        })
        
        result = DataTransformer.to_chart_format(df, 'year', 'value', group_by='disease')
        
        assert len(result["datasets"]) == 2
    
    def test_to_prediction_format(self):
        """测试预测数据格式转换"""
        df = pd.DataFrame({
            'year': [2020, 2020, 2021, 2021, 2022, 2022],
            'cause_name': ['Cardiovascular diseases', 'Neoplasms'] * 3,
            'val': [100, 80, 110, 82, 120, 85]
        })
        
        result = DataTransformer.to_prediction_format(df)
        
        assert "labels" in result
        assert "datasets" in result
        assert len(result["datasets"]) == 2
        # 检查疾病名称是否正确映射为中文
        labels = [d["label"] for d in result["datasets"]]
        assert "心血管疾病" in labels
        assert "肿瘤" in labels
    
    def test_to_list_format(self):
        """测试列表格式转换"""
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['A', 'B', 'C'],
            'value': [10.5, 20.3, 30.7]
        })
        
        result = DataTransformer.to_list_format(df)
        
        assert len(result) == 3
        assert result[0]["id"] == 1
        assert result[0]["name"] == "A"
    
    def test_convert_value_nan(self):
        """测试NaN值转换"""
        assert DataTransformer._convert_value(None) is None
        assert DataTransformer._convert_value(np.nan) is None
        assert DataTransformer._convert_value(pd.NaT) is None
    
    def test_convert_value_numeric(self):
        """测试数值类型转换"""
        # 测试numpy类型
        assert DataTransformer._convert_value(np.int64(10)) == 10
        assert DataTransformer._convert_value(np.float64(3.14159)) == 3.1416
        # 测试float精度
        assert DataTransformer._convert_value(3.1415926, decimal_places=2) == 3.14
    
    def test_convert_value_datetime(self):
        """测试日期时间转换"""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = DataTransformer._convert_value(dt)
        assert result == "2024-01-15 10:30:00"
    
    def test_normalize_field_names(self):
        """测试字段名标准化"""
        data = {
            'cause_name': '心脏病',
            'location_name': '中国',
            'val': 100
        }
        
        result = DataTransformer.normalize_field_names(data)
        
        assert "disease_name" in result
        assert "region" in result
        assert "value" in result


class TestDataValidator:
    """测试数据校验功能"""
    
    def test_validate_response_success(self):
        """测试成功响应校验"""
        data = {
            "code": 200,
            "data": {"test": "value"},
            "message": "success"
        }
        
        result = DataValidator.validate_response(data)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_response_missing_fields(self):
        """测试缺少字段的响应校验"""
        data = {
            "data": {"test": "value"}
        }
        
        result = DataValidator.validate_response(data)
        
        assert result["valid"] is False
        assert any("code" in err for err in result["errors"])
    
    def test_validate_response_invalid_code(self):
        """测试无效状态码校验"""
        data = {
            "code": 600,
            "data": {}
        }
        
        result = DataValidator.validate_response(data)
        
        assert result["valid"] is False
        assert any("状态码" in err for err in result["errors"])
    
    def test_validate_chart_data_success(self):
        """测试图表数据校验成功"""
        data = {
            "labels": ["2020", "2021"],
            "datasets": [
                {"label": "A", "data": [100, 200]}
            ]
        }
        
        result = DataValidator.validate_chart_data(data)
        
        assert result["valid"] is True
    
    def test_validate_chart_data_missing_fields(self):
        """测试图表数据缺少字段"""
        data = {
            "labels": ["2020", "2021"]
        }
        
        result = DataValidator.validate_chart_data(data)
        
        assert result["valid"] is False
        assert any("datasets" in err for err in result["errors"])
    
    def test_validate_chart_data_length_mismatch(self):
        """测试图表数据长度不匹配"""
        data = {
            "labels": ["2020", "2021", "2022"],
            "datasets": [
                {"label": "A", "data": [100, 200]}  # 长度不匹配
            ]
        }
        
        result = DataValidator.validate_chart_data(data)
        
        assert result["valid"] is False
    
    def test_validate_dataframe_success(self):
        """测试DataFrame校验成功"""
        df = pd.DataFrame({
            'year': [2020, 2021],
            'value': [100, 200]
        })
        
        result = DataValidator.validate_dataframe(df, ['year', 'value'])
        
        assert result["valid"] is True
    
    def test_validate_dataframe_missing_columns(self):
        """测试DataFrame缺少列"""
        df = pd.DataFrame({
            'year': [2020, 2021]
        })
        
        result = DataValidator.validate_dataframe(df, ['year', 'value'])
        
        assert result["valid"] is False
        assert any("value" in err for err in result["errors"])


class TestResponseBuilder:
    """测试响应构建功能"""
    
    def test_build_basic(self):
        """测试基本响应构建"""
        result = ResponseBuilder.build(
            code=200,
            data={"test": "value"},
            message="success"
        )
        
        assert result["code"] == 200
        assert result["data"]["test"] == "value"
        assert result["message"] == "success"
        assert "timestamp" in result
    
    def test_build_with_extra(self):
        """测试带额外字段的响应构建"""
        result = ResponseBuilder.build(
            code=200,
            data={},
            message="success",
            extra={"request_id": "12345"}
        )
        
        assert result["request_id"] == "12345"
    
    def test_build_chart_response(self):
        """测试图表响应构建"""
        df = pd.DataFrame({
            'year': [2020, 2021, 2022],
            'value': [100, 120, 130]
        })
        
        result = ResponseBuilder.build_chart_response(
            df, 'year', 'value', message="图表数据获取成功"
        )
        
        assert result["code"] == 200
        assert "labels" in result["data"]
        assert "datasets" in result["data"]
        assert result["message"] == "图表数据获取成功"
    
    def test_build_prediction_response(self):
        """测试预测响应构建"""
        df = pd.DataFrame({
            'year': [2020, 2021],
            'cause_name': ['Cardiovascular diseases', 'Neoplasms'],
            'val': [100, 80]
        })
        
        result = ResponseBuilder.build_prediction_response(df)
        
        assert result["code"] == 200
        assert "datasets" in result["data"]
    
    def test_build_error_response(self):
        """测试错误响应构建"""
        result = ResponseBuilder.build_error_response(
            code=404,
            message="数据不存在",
            details={"resource": "user"}
        )
        
        assert result["code"] == 404
        assert result["message"] == "数据不存在"
        assert result["data"]["error_details"]["resource"] == "user"


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    def test_transform_to_chart(self):
        """测试图表转换便捷函数"""
        df = pd.DataFrame({
            'x': [1, 2, 3],
            'y': [10, 20, 30]
        })
        
        result = transform_to_chart(df, 'x', 'y')
        
        assert "labels" in result
        assert "datasets" in result
    
    def test_transform_to_prediction(self):
        """测试预测转换便捷函数"""
        df = pd.DataFrame({
            'year': [2020, 2021],
            'cause_name': ['A', 'B'],
            'val': [100, 200]
        })
        
        result = transform_to_prediction(df)
        
        assert "labels" in result
        assert "datasets" in result
    
    def test_build_standard_response(self):
        """测试标准响应构建便捷函数"""
        result = build_standard_response(
            code=200,
            data={"test": "value"},
            message="success"
        )
        
        assert result["code"] == 200
        assert result["data"]["test"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
