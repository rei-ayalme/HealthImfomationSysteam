# modules/deepseek_client.py
import requests
import json
from config.settings import DEEPSEEK_CONFIG  # 新增DeepSeek配置
from modules.agent.agent import owid_2_deepseek_input

# 配置示例（config/settings.py）：
# DEEPSEEK_CONFIG = {
#     "api_url": "http://localhost:8000/deepseek/analyze",
#     "api_key": "your_deepseek_api_key",
#     "timeout": 60,
#     "retry_times": 3
# }

# -------------------------- 本地库调用（核心：按DeepSeek的Python库函数修改） --------------------------
def call_deepseek_local(owid_adapted_data: dict, task_type: str = "disease_risk") -> dict:
    """
    调用本地部署的deepseek_analyzer Python库
    :param owid_adapted_data: owid_2_deepseek返回的适配数据
    :param task_type: 分析任务类型（贴合你的项目）：
        - disease_risk：疾病风险归因分析
        - resource_allocation：卫生资源配置优化
        - disease_burden：疾病负担趋势预测
    :return: DeepSeek的分析结果
    """
    try:
        # 导入本地deepseek_analyzer（按实际库名/函数名修改！）
        import deepseek_analyzer as dsa

        # 提取适配后的输入数据和元信息
        input_data = owid_adapted_data["data"]
        metadata = owid_adapted_data["metadata"]
        model_params = DEEPSEEK_CONFIG["model_params"]

        # 按任务类型调用DeepSeek的对应函数（核心：和DeepSeek的功能函数匹配）
        if task_type == "disease_risk":
            # 示例：疾病风险归因→分析各风险因素对疾病的贡献度
            result = dsa.disease_risk_analysis(
                input_data=input_data,
                risk_indicators=["pm2-5-air-pollution-exposure", "share-of-adults-who-smoke"],
                disease_indicator="share-of-deaths-from-non-communicable-diseases",
                **model_params
            )
        elif task_type == "resource_allocation":
            # 示例：卫生资源配置→计算最优资源分配方案
            result = dsa.resource_allocation_optimization(
                input_data=input_data,
                resource_indicator="physicians-per-1000-people",
                disease_burden_indicator="share-of-deaths-from-non-communicable-diseases",
                **model_params
            )
        elif task_type == "disease_burden":
            # 示例：疾病负担预测→预测未来20年疾病负担变化
            result = dsa.disease_burden_prediction(
                input_data=input_data,
                predict_years=20,
                **model_params
            )
        else:
            return {"status": "error", "msg": f"不支持的任务类型：{task_type}"}

        # 返回结构化结果
        return {
            "status": "success",
            "task_type": task_type,
            "result": result,  # DeepSeek的原始分析结果
            "metadata": metadata  # 元信息，方便后续可视化
        }
    except ImportError:
        return {"status": "error", "msg": "未检测到本地deepseek_analyzer库，请检查部署"}
    except Exception as e:
        return {"status": "error", "msg": f"本地调用DeepSeek失败：{str(e)[:500]}"}

# -------------------------- 远程API调用（核心：按DeepSeek的接口规范修改） --------------------------
def call_deepseek_api(owid_adapted_data: dict, task_type: str = "disease_risk") -> dict:
    """调用远程部署的deepseek_analyzer API接口"""
    try:
        # 构造接口请求参数
        request_data = {
            "api_key": DEEPSEEK_CONFIG["api_key"],
            "task_type": task_type,
            "input_data": owid_adapted_data["data"],
            "metadata": owid_adapted_data["metadata"],
            "model_params": DEEPSEEK_CONFIG["model_params"]
        }

        # 带重试的接口请求
        for retry in range(DEEPSEEK_CONFIG["retry_times"]):
            response = requests.post(
                url=DEEPSEEK_CONFIG["api_url"],
                json=request_data,
                timeout=DEEPSEEK_CONFIG["timeout"],
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                api_result = response.json()
                return {
                    "status": "success",
                    "task_type": task_type,
                    "result": api_result,
                    "metadata": owid_adapted_data["metadata"]
                }
            elif retry == DEEPSEEK_CONFIG["retry_times"] - 1:
                return {"status": "error", "msg": f"API调用失败，状态码：{response.status_code}，信息：{response.text[:500]}"}
    except requests.exceptions.Timeout:
        return {"status": "error", "msg": "DeepSeek API调用超时"}
    except Exception as e:
        return {"status": "error", "msg": f"API调用异常：{str(e)[:500]}"}


def deepseek_analyze(
    indicator_ids: list,
    countries: list,
    start_year: int,
    end_year: int,
    task_type: str = "disease_risk",
    output_format: str = "dict"
) -> dict:
    """
    封装：OWID数据适配 + DeepSeek调用 + 结果返回
    """
    # 1. 适配OWID数据
    owid_input = owid_2_deepseek_input(indicator_ids, countries, start_year, end_year)
    if owid_input["status"] != "success":
        return owid_input

    # 2. 调用DeepSeek
    if DEEPSEEK_CONFIG["call_type"] == "local":
        return call_deepseek_local(owid_input, task_type)
    else:
        return call_deepseek_api(owid_input, task_type)

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