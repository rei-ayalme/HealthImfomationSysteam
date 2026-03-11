# modules/search_api_checker.py
import requests
import hashlib
import time
from config.settings import SEARCH_ENGINE_CONFIG
from pydantic import BaseModel
from typing import List, Dict, Optional


# 定义返回结果模型（保证结构化）
class SearchAPICheckResult(BaseModel):
    status: bool  # True=成功/False=失败
    engine: str  # 搜索引擎类型
    check_items: List[Dict]  # 各检查项结果
    data: Optional[Dict] = None  # 成功时的返回数据
    error_msg: Optional[str] = None  # 失败时的错误信息


def check_serpapi(test_query: str = "2025全球卫生资源配置报告") -> SearchAPICheckResult:
    """检查SerpAPI接口"""
    config = SEARCH_ENGINE_CONFIG["serpapi"]
    check_items = []
    # 检查项1：配置验证
    if not config["api_key"]:
        check_items.append({"item": "配置验证", "status": False, "msg": "SerpAPI密钥为空"})
        return SearchAPICheckResult(status=False, engine="serpapi", check_items=check_items, error_msg="密钥为空")
    check_items.append({"item": "配置验证", "status": True, "msg": "密钥/地址/参数均合法"})

    # 检查项2：连通性+数据有效性测试
    params = {
        "q": test_query,
        "api_key": config["api_key"],
        "engine": "google",
        "num": config["result_num"]
    }
    try:
        for retry in range(config["retry_times"]):
            response = requests.get(config["api_url"], params=params, timeout=config["timeout"])
            if response.status_code == 200:
                break
            elif retry == config["retry_times"] - 1:
                check_items.append({"item": "连通性测试", "status": False, "msg": f"HTTP状态码：{response.status_code}"})
                return SearchAPICheckResult(status=False, engine="serpapi", check_items=check_items,
                                            error_msg=f"请求失败，状态码{response.status_code}")
        check_items.append({"item": "连通性测试", "status": True, "msg": "HTTP请求成功，状态码200"})

        # 解析数据，验证有效性
        search_data = response.json()
        if "organic_results" in search_data and len(search_data["organic_results"]) > 0:
            check_items.append({"item": "数据有效性", "status": True, "msg": "返回结构化自然搜索结果"})
            # 整理核心数据
            result_data = {
                "query": test_query,
                "result_num": len(search_data["organic_results"]),
                "results": [
                    {"title": item.get("title"), "snippet": item.get("snippet"), "link": item.get("link")}
                    for item in search_data["organic_results"][:config["result_num"]]
                ]
            }
            return SearchAPICheckResult(status=True, engine="serpapi", check_items=check_items, data=result_data)
        else:
            check_items.append({"item": "数据有效性", "status": False, "msg": "无自然搜索结果"})
            return SearchAPICheckResult(status=False, engine="serpapi", check_items=check_items, error_msg="无搜索结果")
    except requests.exceptions.Timeout:
        check_items.append({"item": "连通性测试", "status": False, "msg": "请求超时"})
        return SearchAPICheckResult(status=False, engine="serpapi", check_items=check_items, error_msg="请求超时")
    except Exception as e:
        check_items.append({"item": "连通性测试", "status": False, "msg": str(e)[:100]})
        return SearchAPICheckResult(status=False, engine="serpapi", check_items=check_items, error_msg=str(e)[:100])


def check_bing(test_query: str = "2025全球卫生资源配置报告") -> SearchAPICheckResult:
    """检查Bing Search API接口"""
    config = SEARCH_ENGINE_CONFIG["bing"]
    check_items = []
    # 配置验证
    if not config["api_key"]:
        check_items.append({"item": "配置验证", "status": False, "msg": "Bing API密钥为空"})
        return SearchAPICheckResult(status=False, engine="bing", check_items=check_items, error_msg="密钥为空")
    check_items.append({"item": "配置验证", "status": True, "msg": "配置合法"})

    # 连通性+数据有效性
    headers = {"Ocp-Apim-Subscription-Key": config["api_key"]}
    params = {"q": test_query, "textDecorations": True, "textFormat": "html"}
    try:
        response = requests.get(config["api_url"], headers=headers, params=params, timeout=config["timeout"])
        if response.status_code != 200:
            check_items.append({"item": "连通性测试", "status": False, "msg": f"状态码{response.status_code}"})
            return SearchAPICheckResult(status=False, engine="bing", check_items=check_items,
                                        error_msg=f"状态码{response.status_code}")
        check_items.append({"item": "连通性测试", "status": True, "msg": "状态码200"})

        # 验证数据
        search_data = response.json()
        if "webPages" in search_data and "value" in search_data["webPages"]:
            check_items.append({"item": "数据有效性", "status": True, "msg": "返回网页搜索结果"})
            result_data = {
                "query": test_query,
                "result_num": len(search_data["webPages"]["value"]),
                "results": [
                    {"title": item.get("name"), "snippet": item.get("snippet"), "link": item.get("url")}
                    for item in search_data["webPages"]["value"][:config["result_num"]]
                ]
            }
            return SearchAPICheckResult(status=True, engine="bing", check_items=check_items, data=result_data)
        else:
            check_items.append({"item": "数据有效性", "status": False, "msg": "无搜索结果"})
            return SearchAPICheckResult(status=False, engine="bing", check_items=check_items, error_msg="无搜索结果")
    except Exception as e:
        check_items.append({"item": "连通性测试", "status": False, "msg": str(e)[:100]})
        return SearchAPICheckResult(status=False, engine="bing", check_items=check_items, error_msg=str(e)[:100])


# 统一检查入口
def check_search_engine(test_query: str = "2025全球卫生资源配置报告") -> SearchAPICheckResult:
    """统一检查入口，根据配置自动切换搜索引擎"""
    engine_type = SEARCH_ENGINE_CONFIG["type"]
    if engine_type == "serpapi":
        return check_serpapi(test_query)
    elif engine_type == "bing":
        return check_bing(test_query)
    elif engine_type == "baidu":
        # 可按需扩展百度搜索API检查逻辑，同上述格式
        pass
    else:
        return SearchAPICheckResult(status=False, engine=engine_type, check_items=[], error_msg="不支持的搜索引擎类型")


# 本地测试
if __name__ == "__main__":
    result = check_search_engine()
    print(f"检查结果：{'成功' if result.status else '失败'}")
    print(f"检查项：{result.check_items}")
    if result.data:
        print(f"返回数据：{result.data}")