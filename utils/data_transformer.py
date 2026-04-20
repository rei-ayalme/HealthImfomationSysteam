"""
中台数据口径 - 数据转换模块

本模块提供标准化的数据转换功能，将各类复杂数据结构（DataFrame、统计结果等）
转换为符合前端需求的标准化JSON格式。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
import json


class DataTransformer:
    """数据中台标准数据转换器"""
    
    # 标准字段命名映射（蛇形命名法）
    FIELD_MAPPINGS = {
        # 常见数据源字段 -> 标准字段
        'cause_name': 'disease_name',
        'location_name': 'region',
        'val': 'value',
        'rei_name': 'risk_factor',
        'paf': 'risk_value',
        'dea_efficiency': 'efficiency_score',
        'year': 'year',
        'metric': 'indicator',
    }
    
    @staticmethod
    def to_chart_format(
        df: pd.DataFrame,
        x_column: str,
        y_columns: Union[str, List[str]],
        label_mapping: Optional[Dict[str, str]] = None,
        group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        将DataFrame转换为前端图表标准格式
        
        Args:
            df: 输入数据DataFrame
            x_column: X轴数据列名（通常是年份）
            y_columns: Y轴数据列名或列名列表
            label_mapping: 列名到显示标签的映射
            group_by: 分组列名（用于多系列数据）
            
        Returns:
            标准图表格式: {"labels": [...], "datasets": [...]}
            
        Example:
            >>> df = pd.DataFrame({
            ...     'year': [2020, 2021, 2022],
            ...     'value': [100, 120, 130]
            ... })
            >>> DataTransformer.to_chart_format(df, 'year', 'value')
            {
                "labels": ["2020", "2021", "2022"],
                "datasets": [{"label": "value", "data": [100, 120, 130]}]
            }
        """
        if df is None or df.empty:
            return {"labels": [], "datasets": []}
        
        # 确保y_columns是列表
        if isinstance(y_columns, str):
            y_columns = [y_columns]
        
        # 获取X轴标签
        labels = df[x_column].astype(str).tolist() if x_column in df.columns else []
        
        # 构建datasets
        datasets = []
        colors = ["#2b6cb0", "#c53030", "#d69e2e", "#319795", "#805ad5", 
                  "#dd6b20", "#38a169", "#718096", "#d53f8c", "#3182ce"]
        
        if group_by and group_by in df.columns:
            # 分组模式：每个分组一个dataset
            groups = df[group_by].unique()
            for idx, group in enumerate(groups):
                group_df = df[df[group_by] == group]
                label = label_mapping.get(str(group), str(group)) if label_mapping else str(group)
                
                # 获取该组的数据（按X轴排序）
                group_df = group_df.sort_values(by=x_column)
                data_values = []
                for y_col in y_columns:
                    if y_col in group_df.columns:
                        data_values = group_df[y_col].tolist()
                        break
                
                datasets.append({
                    "label": label,
                    "data": [DataTransformer._convert_value(v) for v in data_values],
                    "borderColor": colors[idx % len(colors)],
                    "borderWidth": 2,
                    "fill": False
                })
        else:
            # 非分组模式：每个y_column一个dataset
            for idx, y_col in enumerate(y_columns):
                if y_col in df.columns:
                    label = label_mapping.get(y_col, y_col) if label_mapping else y_col
                    datasets.append({
                        "label": label,
                        "data": [DataTransformer._convert_value(v) for v in df[y_col].tolist()],
                        "borderColor": colors[idx % len(colors)],
                        "borderWidth": 2,
                        "fill": False
                    })
        
        return {
            "labels": labels,
            "datasets": datasets
        }
    
    @staticmethod
    def to_prediction_format(
        df: pd.DataFrame,
        year_column: str = 'year',
        disease_column: str = 'cause_name',
        value_column: str = 'val',
        disease_labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        将DataFrame转换为疾病预测标准格式
        
        输出格式严格遵循:
        {
            "labels": ["2024", "2025", ...],
            "datasets": [
                {"label": "心血管疾病", "data": [120, 125, ...]},
                {"label": "肿瘤", "data": [80, 82, ...]}
            ]
        }
        
        Args:
            df: 输入数据DataFrame
            year_column: 年份列名
            disease_column: 疾病名称列名
            value_column: 数值列名
            disease_labels: 疾病名称到显示标签的映射
            
        Returns:
            标准预测数据格式
        """
        if df is None or df.empty:
            return {"labels": [], "datasets": []}
        
        # 默认疾病标签映射
        default_labels = {
            "Cardiovascular diseases": "心血管疾病",
            "Neoplasms": "肿瘤",
            "Diabetes": "糖尿病",
            "Mental disorders": "精神疾病",
            "Chronic respiratory diseases": "慢性呼吸系统疾病",
            "Digestive diseases": "消化系统疾病",
            "Neurological disorders": "神经系统疾病",
        }
        disease_labels = disease_labels or default_labels
        
        # 获取所有年份（排序）
        years = sorted(df[year_column].unique()) if year_column in df.columns else []
        labels = [str(y) for y in years]
        
        # 获取所有疾病类型
        diseases = df[disease_column].unique() if disease_column in df.columns else []
        
        # 构建datasets
        colors = ["#2b6cb0", "#c53030", "#d69e2e", "#319795", "#805ad5", 
                  "#dd6b20", "#38a169", "#718096"]
        
        datasets = []
        for idx, disease in enumerate(diseases):
            disease_df = df[df[disease_column] == disease]
            
            # 按年份排序并获取数值
            disease_df = disease_df.sort_values(by=year_column)
            
            # 构建年份到数值的映射
            year_value_map = {}
            for _, row in disease_df.iterrows():
                year = row[year_column]
                value = row[value_column] if value_column in row else None
                year_value_map[year] = value
            
            # 按年份顺序填充数据
            data = []
            for year in years:
                val = year_value_map.get(year)
                data.append(DataTransformer._convert_value(val))
            
            # 获取显示标签
            display_label = disease_labels.get(str(disease), str(disease))
            
            datasets.append({
                "label": display_label,
                "data": data,
                "borderColor": colors[idx % len(colors)],
                "borderWidth": 2,
                "fill": False
            })
        
        return {
            "labels": labels,
            "datasets": datasets
        }
    
    @staticmethod
    def to_list_format(
        df: pd.DataFrame,
        field_mapping: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        将DataFrame转换为标准列表格式
        
        Args:
            df: 输入数据DataFrame
            field_mapping: 字段名映射（源字段 -> 目标字段）
            
        Returns:
            标准列表格式
        """
        if df is None or df.empty:
            return []
        
        field_mapping = field_mapping or {}
        result = []
        
        for _, row in df.iterrows():
            item = {}
            for col in df.columns:
                target_key = field_mapping.get(col, col)
                item[target_key] = DataTransformer._convert_value(row[col])
            result.append(item)
        
        return result
    
    @staticmethod
    def to_stats_format(
        stats_dict: Dict[str, Any],
        decimal_places: int = 4
    ) -> Dict[str, Any]:
        """
        将统计数据转换为标准统计格式
        
        Args:
            stats_dict: 统计数据字典
            decimal_places: 小数位数
            
        Returns:
            标准统计格式
        """
        if not stats_dict:
            return {}
        
        result = {}
        for key, value in stats_dict.items():
            result[key] = DataTransformer._convert_value(value, decimal_places)
        
        return result
    
    @staticmethod
    def _convert_value(value: Any, decimal_places: int = 4) -> Any:
        """
        将值转换为JSON可序列化的格式
        
        Args:
            value: 原始值
            decimal_places: 浮点数小数位数
            
        Returns:
            转换后的值
        """
        if pd.isna(value) or value is None:
            return None
        elif isinstance(value, (np.integer, np.floating)):
            if isinstance(value, np.floating):
                return round(float(value), decimal_places)
            return int(value)
        elif isinstance(value, np.ndarray):
            return value.tolist()
        elif isinstance(value, pd.Timestamp):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, (datetime, date)):
            return value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime) else value.strftime("%Y-%m-%d")
        elif isinstance(value, float):
            return round(value, decimal_places)
        else:
            return value
    
    @staticmethod
    def normalize_field_names(
        data: Union[Dict, List[Dict]],
        mapping: Optional[Dict[str, str]] = None
    ) -> Union[Dict, List[Dict]]:
        """
        标准化字段命名（转换为蛇形命名法）
        
        Args:
            data: 输入数据
            mapping: 字段映射字典
            
        Returns:
            字段名标准化后的数据
        """
        mapping = mapping or DataTransformer.FIELD_MAPPINGS
        
        if isinstance(data, dict):
            return {mapping.get(k, k): v for k, v in data.items()}
        elif isinstance(data, list):
            return [DataTransformer.normalize_field_names(item, mapping) for item in data]
        else:
            return data


class DataValidator:
    """数据口径校验器"""
    
    # 标准响应格式schema
    STANDARD_SCHEMA = {
        "required_fields": ["code", "data"],
        "optional_fields": ["message", "timestamp"],
        "code_range": [200, 599]
    }
    
    # 图表数据格式schema
    CHART_SCHEMA = {
        "required_fields": ["labels", "datasets"],
        "dataset_required": ["label", "data"]
    }
    
    @staticmethod
    def validate_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        校验响应数据是否符合标准格式
        
        Args:
            data: 响应数据
            
        Returns:
            校验结果 {"valid": bool, "errors": List[str]}
        """
        errors = []
        
        # 检查必需字段
        for field in DataValidator.STANDARD_SCHEMA["required_fields"]:
            if field not in data:
                errors.append(f"缺少必需字段: {field}")
        
        # 检查code范围
        if "code" in data:
            code = data["code"]
            min_code, max_code = DataValidator.STANDARD_SCHEMA["code_range"]
            if not (min_code <= code <= max_code):
                errors.append(f"状态码 {code} 超出有效范围 [{min_code}, {max_code}]")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    @staticmethod
    def validate_chart_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        校验图表数据格式
        
        Args:
            data: 图表数据
            
        Returns:
            校验结果 {"valid": bool, "errors": List[str]}
        """
        errors = []
        
        # 检查必需字段
        for field in DataValidator.CHART_SCHEMA["required_fields"]:
            if field not in data:
                errors.append(f"缺少必需字段: {field}")
        
        # 检查datasets结构
        if "datasets" in data:
            datasets = data["datasets"]
            if not isinstance(datasets, list):
                errors.append("datasets 必须是列表类型")
            else:
                for idx, dataset in enumerate(datasets):
                    for field in DataValidator.CHART_SCHEMA["dataset_required"]:
                        if field not in dataset:
                            errors.append(f"dataset[{idx}] 缺少必需字段: {field}")
        
        # 检查labels和data长度一致性
        if "labels" in data and "datasets" in data:
            labels_len = len(data["labels"])
            for idx, dataset in enumerate(data["datasets"]):
                if "data" in dataset:
                    data_len = len(dataset["data"])
                    if data_len != labels_len:
                        errors.append(f"dataset[{idx}] data长度({data_len})与labels长度({labels_len})不一致")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> Dict[str, Any]:
        """
        校验DataFrame是否包含必需的列
        
        Args:
            df: 输入DataFrame
            required_columns: 必需列名列表
            
        Returns:
            校验结果 {"valid": bool, "errors": List[str]}
        """
        errors = []
        
        if df is None:
            errors.append("DataFrame为None")
        elif df.empty:
            errors.append("DataFrame为空")
        else:
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                errors.append(f"缺少必需列: {missing_cols}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


class ResponseBuilder:
    """标准响应构建器"""
    
    @staticmethod
    def build(
        code: int = 200,
        data: Any = None,
        message: str = "success",
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        构建标准响应格式
        
        Args:
            code: 状态码
            data: 业务数据
            message: 响应消息
            extra: 额外字段
            
        Returns:
            标准响应格式
        """
        response = {
            "code": code,
            "message": message,
            "data": data if data is not None else {},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if extra and isinstance(extra, dict):
            response.update(extra)
        
        return response
    
    @staticmethod
    def build_chart_response(
        df: pd.DataFrame,
        x_column: str,
        y_columns: Union[str, List[str]],
        message: str = "数据获取成功",
        **kwargs
    ) -> Dict[str, Any]:
        """
        构建图表数据标准响应
        
        Args:
            df: 输入数据DataFrame
            x_column: X轴列名
            y_columns: Y轴列名
            message: 响应消息
            **kwargs: 传递给to_chart_format的额外参数
            
        Returns:
            标准响应格式
        """
        chart_data = DataTransformer.to_chart_format(df, x_column, y_columns, **kwargs)
        return ResponseBuilder.build(code=200, data=chart_data, message=message)
    
    @staticmethod
    def build_prediction_response(
        df: pd.DataFrame,
        message: str = "预测数据获取成功",
        **kwargs
    ) -> Dict[str, Any]:
        """
        构建预测数据标准响应
        
        Args:
            df: 输入数据DataFrame
            message: 响应消息
            **kwargs: 传递给to_prediction_format的额外参数
            
        Returns:
            标准响应格式
        """
        prediction_data = DataTransformer.to_prediction_format(df, **kwargs)
        return ResponseBuilder.build(code=200, data=prediction_data, message=message)
    
    @staticmethod
    def build_error_response(
        code: int,
        message: str,
        details: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        构建错误响应格式
        
        Args:
            code: 错误状态码
            message: 错误消息
            details: 错误详情
            
        Returns:
            标准错误响应格式
        """
        data = {"error_details": details} if details else {}
        return ResponseBuilder.build(code=code, data=data, message=message)


# 便捷函数

def transform_to_chart(
    df: pd.DataFrame,
    x_column: str,
    y_columns: Union[str, List[str]],
    **kwargs
) -> Dict[str, Any]:
    """便捷函数：转换为图表格式"""
    return DataTransformer.to_chart_format(df, x_column, y_columns, **kwargs)


def transform_to_prediction(
    df: pd.DataFrame,
    **kwargs
) -> Dict[str, Any]:
    """便捷函数：转换为预测格式"""
    return DataTransformer.to_prediction_format(df, **kwargs)


def validate_response_format(data: Dict[str, Any]) -> Dict[str, Any]:
    """便捷函数：校验响应格式"""
    return DataValidator.validate_response(data)


def build_standard_response(
    code: int = 200,
    data: Any = None,
    message: str = "success"
) -> Dict[str, Any]:
    """便捷函数：构建标准响应"""
    return ResponseBuilder.build(code, data, message)
