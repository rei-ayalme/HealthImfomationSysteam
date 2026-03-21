# modules/deepseek_client.py
import requests
import json
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Any, Optional
from config.settings import DEEPSEEK_CONFIG
from modules.agent.adapter import owid_2_deepseek_input
from utils.logger import logger
from modules.core.fallback_handler import fallback_wrapper

# -------------------------- 定义标准化返回模型 --------------------------
class AnalysisResponse(BaseModel):
    status: str
    task_type: Optional[str] = None
    result: Optional[Any] = None
    metadata: Optional[Dict] = None
    msg: Optional[str] = None

# -------------------------- 本地库调用 --------------------------
def call_deepseek_local(owid_adapted_data: dict, task_type: str = "disease_risk") -> AnalysisResponse:
    try:
        import deepseek_analyzer as dsa
        input_data = owid_adapted_data["data"]
        metadata = owid_adapted_data["metadata"]
        model_params = DEEPSEEK_CONFIG["model_params"]

        if task_type == "disease_risk":
            result = dsa.disease_risk_analysis(
                input_data=input_data,
                risk_indicators=["pm2-5-air-pollution-exposure", "share-of-adults-who-smoke"],
                disease_indicator="share-of-deaths-from-non-communicable-diseases",
                **model_params
            )
        elif task_type == "resource_allocation":
            result = dsa.resource_allocation_optimization(
                input_data=input_data,
                resource_indicator="physicians-per-1000-people",
                disease_burden_indicator="share-of-deaths-from-non-communicable-diseases",
                **model_params
            )
        elif task_type == "disease_burden":
            result = dsa.disease_burden_prediction(
                input_data=input_data,
                predict_years=20,
                **model_params
            )
        else:
            return AnalysisResponse(status="error", msg=f"不支持的任务类型：{task_type}")

        return AnalysisResponse(status="success", task_type=task_type, result=result, metadata=metadata)
    except ImportError:
        logger.exception("未检测到本地 deepseek_analyzer 库")
        return AnalysisResponse(status="error", msg="未检测到本地deepseek_analyzer库，请检查部署")
    except Exception as e:
        logger.exception("本地调用 DeepSeek 失败")
        return AnalysisResponse(status="error", msg=f"本地调用DeepSeek失败：{str(e)[:500]}")

# -------------------------- 远程API调用 --------------------------
@fallback_wrapper(default_data={"status": "error", "msg": "API 调用失败，已降级返回默认值", "result": None, "metadata": {}})
def call_deepseek_api(owid_adapted_data: dict, task_type: str = "disease_risk") -> AnalysisResponse:
    try:
        request_data = {
            "api_key": DEEPSEEK_CONFIG["api_key"],
            "task_type": task_type,
            "input_data": owid_adapted_data["data"],
            "metadata": owid_adapted_data["metadata"],
            "model_params": DEEPSEEK_CONFIG["model_params"]
        }

        for retry in range(DEEPSEEK_CONFIG["retry_times"]):
            response = requests.post(
                url=DEEPSEEK_CONFIG["api_url"],
                json=request_data,
                timeout=DEEPSEEK_CONFIG["timeout"],
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                return AnalysisResponse(
                    status="success",
                    task_type=task_type,
                    result=response.json(),
                    metadata=owid_adapted_data["metadata"]
                )
            elif retry == DEEPSEEK_CONFIG["retry_times"] - 1:
                # 抛出异常以触发降级装饰器
                raise RuntimeError(f"API调用失败，状态码：{response.status_code}，信息：{response.text[:500]}")
    except requests.exceptions.Timeout:
        logger.exception("DeepSeek API 调用超时")
        raise  # 抛出异常触发降级
    except Exception as e:
        logger.exception("API 调用异常")
        raise  # 抛出异常触发降级

def save_analysis_result(result: AnalysisResponse):
    """单独的 Repository 层：负责将分析结果落库"""
    if result.status != "success":
        return
        
    from db.connection import SessionLocal
    from db.models import DeepSeekAnalysisResult
    db = SessionLocal()
    try:
        db.add(DeepSeekAnalysisResult(
            task_type=result.task_type,
            input_metadata=json.dumps(result.metadata),
            analysis_result=json.dumps(result.result),
            create_time=datetime.now()
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("DeepSeek结果入库失败")
    finally:
        db.close()

def deepseek_analyze(
    indicator_ids: list,
    countries: list,
    start_year: int,
    end_year: int,
    task_type: str = "disease_risk"
) -> AnalysisResponse:
    """
    纯粹的服务层函数：适配数据 -> 调用模型 -> 返回模型，不再耦合数据库
    """
    owid_input = owid_2_deepseek_input(indicator_ids, countries, start_year, end_year)
    if owid_input["status"] != "success":
        return AnalysisResponse(status="error", msg=owid_input.get("msg", "适配失败"))

    if DEEPSEEK_CONFIG["call_type"] == "local":
        return call_deepseek_local(owid_input, task_type)
    else:
        return call_deepseek_api(owid_input, task_type)