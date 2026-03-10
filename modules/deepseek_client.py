# modules/deepseek_client.py
import requests
import json
from config.settings import DEEPSEEK_CONFIG  # 新增DeepSeek配置


# 配置示例（config/settings.py）：
# DEEPSEEK_CONFIG = {
#     "api_url": "http://localhost:8000/deepseek/analyze",
#     "api_key": "your_deepseek_api_key",
#     "timeout": 60,
#     "retry_times": 3
# }

def call_deepseek_analyzer(input_data: dict, task_type: str = "disease_risk") -> dict:
    """
    调用DeepSeek_Analyzer接口
    :param input_data: 适配后的OWID数据（owid_2_deepseek_input返回的data）
    :param task_type: 分析任务类型（disease_risk/resource_allocation/trend_prediction）
    :return: DeepSeek分析结果
    """
    # 构造请求参数
    request_data = {
        "api_key": DEEPSEEK_CONFIG["api_key"],
        "task_type": task_type,
        "input_data": input_data["data"],
        "metadata": input_data["metadata"]
    }

    # 带重试的接口调用
    for retry in range(DEEPSEEK_CONFIG["retry_times"]):
        try:
            response = requests.post(
                url=DEEPSEEK_CONFIG["api_url"],
                json=request_data,
                timeout=DEEPSEEK_CONFIG["timeout"],
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            return {"status": "success", "result": result}
        except requests.exceptions.Timeout:
            if retry == DEEPSEEK_CONFIG["retry_times"] - 1:
                return {"status": "error", "msg": "接口调用超时"}
            continue
        except requests.exceptions.HTTPError as e:
            return {"status": "error", "msg": f"HTTP错误：{e}"}
        except Exception as e:
            if retry == DEEPSEEK_CONFIG["retry_times"] - 1:
                return {"status": "error", "msg": f"调用失败：{str(e)}"}
            continue


def deepseek_analysis_wrapper(indicator_ids: list, countries: list, start_year: int, end_year: int,
                              task_type: str) -> dict:
    """
    封装：OWID数据适配 + DeepSeek调用 + 结果返回
    """
    # 1. 适配OWID数据
    owid_input = owid_2_deepseek_input(indicator_ids, countries, start_year, end_year)
    if owid_input["status"] != "success":
        return owid_input

    # 2. 调用DeepSeek
    deepseek_result = call_deepseek_analyzer(owid_input, task_type)

    # 3. 结果处理（存入数据库，可选）
    if deepseek_result["status"] == "success":
        from db.connection import SessionLocal
        from db.models import DeepSeekAnalysisResult  # 新增结果表
        db = SessionLocal()
        try:
            # 存入分析结果
            db.add(DeepSeekAnalysisResult(
                task_type=task_type,
                input_metadata=json.dumps(owid_input["metadata"]),
                analysis_result=json.dumps(deepseek_result["result"]),
                create_time=datetime.now()
            ))
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"DeepSeek结果入库失败：{e}")
        finally:
            db.close()

    return deepseek_result