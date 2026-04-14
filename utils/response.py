"""
标准化数据中台架构 - 统一接口响应格式模块

本模块提供工业级中台标准响应格式，确保所有API接口返回一致的响应结构。
"""

from fastapi.responses import JSONResponse
import datetime


def success_response(data: dict = None, message: str = "success"):
    """中台标准成功响应格式
    
    Args:
        data: 业务数据字典，默认为空字典
        message: 响应描述信息，默认为"success"
        
    Returns:
        dict: 符合中台标准的成功响应结构
        
    Example:
        >>> success_response({"users": ["Alice", "Bob"]}, "获取用户列表成功")
        {
            "code": 200,
            "message": "获取用户列表成功",
            "data": {"users": ["Alice", "Bob"]},
            "timestamp": "2024-01-15T08:30:00.000000Z"
        }
    """
    return {
        "code": 200,
        "message": message,
        "data": data if data is not None else {},
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }


def error_response(code: int, message: str):
    """中台标准错误响应格式
    
    Args:
        code: 业务错误状态码，需与HTTP状态码保持一致
        message: 错误描述信息
        
    Returns:
        JSONResponse: 符合中台标准的错误响应对象
        
    Example:
        >>> error_response(404, "用户不存在")
        JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "message": "用户不存在",
                "data": {},
                "timestamp": "2024-01-15T08:30:00.000000Z"
            }
        )
    """
    return JSONResponse(
        status_code=code,  # HTTP状态码与业务状态码保持一致
        content={
            "code": code,  # 业务状态码
            "message": message,
            "data": {},
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
    )


# 常用HTTP状态码常量定义（可选使用）
class ResponseCode:
    """标准HTTP状态码与业务状态码映射"""
    SUCCESS = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_ERROR = 500
    SERVICE_UNAVAILABLE = 503
