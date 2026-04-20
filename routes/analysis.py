"""
AI 驱动的动态分析报告生成模块 (Dynamic Report Generator)

功能说明：
- 调用本地 Ollama 服务 (Qwen 3.5 9B) 生成专业健康信息学分析报告
- 支持智能降级策略，确保服务高可用性
- 提供标准化 API 接口供前端调用

"""

import httpx
from fastapi import APIRouter, Query
from typing import Optional

# 创建 APIRouter 实例
router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# Ollama 默认服务地址
OLLAMA_API_URL = "http://localhost:11434/api/generate"


@router.get("/report/auto")
async def generate_ai_report(
    region: Optional[str] = Query(default="china", description="分析地区名称"),
    metric: Optional[str] = Query(default="dalys", description="核心健康指标"),
    start_year: Optional[int] = Query(default=1990, description="起始年份"),
    end_year: Optional[int] = Query(default=2024, description="结束年份")
):
    """
    调用本地 Ollama (Qwen 3.5 9B) 生成专业健康信息学分析报告
    
    当本地 AI 服务不可用时，自动降级返回警告信息。
    
    Args:
        region: 分析地区名称，如 "china", "chengdu", "global"
        metric: 核心健康指标，如 "dalys", "deaths", "prevalence"
        start_year: 数据起始年份
        end_year: 数据结束年份
        
    Returns:
        包含 AI 生成报告或警告信息的标准响应
    """
    # 构造专业提示词
    prompt = (
        f"你是一位健康信息学专家。请分析 {region} 地区从 {start_year} 到 {end_year} 的 {metric} 数据趋势。"
        f"目前系统检测到风险波动，请给出 100 字内的专业干预建议。"
    )
    
    try:
        async with httpx.AsyncClient() as client:
            # 调用本地 Ollama 服务
            response = await client.post(
                OLLAMA_API_URL,
                json={"model": "qwen:9b", "prompt": prompt, "stream": False},
                timeout=30.0
            )
            ai_content = response.json().get("response", "AI 推理未返回结果")
            return {"status": "success", "report": ai_content}
    except Exception as e:
        return {"status": "warning", "report": "AI 模块离线，请检查本地 Ollama 服务状态。"}


# ==================== 模块测试 ====================

if __name__ == "__main__":
    import asyncio
    import uvicorn
    from fastapi import FastAPI

    # 创建测试应用
    app = FastAPI(title="AI Report Generator Test")
    app.include_router(router)

    print("启动 AI 报告生成器测试服务器...")
    print(f"API 端点: http://127.0.0.1:8000/api/analysis/report/auto")
    print("确保本地 Ollama 服务已启动: ollama serve")
    uvicorn.run(app, host="127.0.0.1", port=8000)
