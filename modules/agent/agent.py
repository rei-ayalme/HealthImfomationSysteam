# modules/health_agent.py 修复版
import os
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent
from langchain.agents.agent import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from db.connection import SessionLocal
from db.models import GlobalHealthMetric
from modules.agent.adapter import owid_2_deepseek_input
from config.settings import OPENAI_CONFIG
import logging

logger = logging.getLogger(__name__)

# --- 1. 模型初始化 (懒加载) ---
_chat_llm_instance = None
_analyzer_llm_instance = None

def get_chat_llm():
    global _chat_llm_instance
    if _chat_llm_instance is None:
        _chat_llm_instance = ChatOpenAI(
            model=os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat"),
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base="https://api.deepseek.com/v1",
            temperature=0.7
        )
    return _chat_llm_instance

def get_analyzer_llm():
    global _analyzer_llm_instance
    if _analyzer_llm_instance is None:
        _analyzer_llm_instance = ChatOpenAI(
            model=os.getenv("DEEPSEEK_ANALYZER_MODEL", "DeepAnalyze-8B"),
            openai_api_key=os.getenv("DEEPSEEK_API_KEY", "EMPTY"),
            openai_api_base="https://u906943-aad8-00a5d162.westc.seetacloud.com:8443/v1",
            temperature=0,
            max_tokens=2048
        )
    return _analyzer_llm_instance

# --- 2. 增强型分析工具 ---
@tool
def deepseek_analyzer_tool(analysis_query: str, keyword: str = "") -> str:
    """卫生数据分析专家工具。用于复杂计算、趋势预测和深度推理。"""
    db = SessionLocal()
    try:
        query = db.query(GlobalHealthMetric)
        if keyword:
            # 基于关键词进行模糊查询（地区或指标名称匹配）
            query = query.filter(
                (GlobalHealthMetric.region.ilike(f"%{keyword}%")) | 
                (GlobalHealthMetric.indicator.ilike(f"%{keyword}%"))
            )
        
        # 限制返回的数据量以防超过 token 限制，但不再是固定的无条件 limit 5
        base_metrics = query.limit(50).all()
        
        if not base_metrics:
            data_context = f"未找到与关键词 '{keyword}' 相关的健康数据。"
        else:
            # 增加 year 字段以便 LLM 执行时序分析
            data_context = "\n".join([f"{m.region} ({m.year}年) {m.indicator}: {m.value}" for m in base_metrics])
    finally:
        db.close()

    policy_context = ""
    try:
        from pathlib import Path
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        file_path = BASE_DIR / "data" / "china" / "policy_notes.txt"
        with open(file_path, "r", encoding="utf-8") as f:
            policy_context = f.read()[:4000]  # 只取精华部分
    except FileNotFoundError:
        policy_context = "暂无官方政策背景说明。"

    system_prompt = f"""
你是一名资深中国卫生数据科学家。

【当前数值数据】
{data_context}

【官方政策与统计口径背景】
{policy_context}

请结合上述政策背景和时序数据，回答用户的分析请求。
要求：
1. **时序分析**：如果数据包含不同年份，请主动进行同比/环比分析，指出数据的增长或下降趋势。
2. **政策对比分析**：将数据表现与【官方政策与统计口径背景】进行深度对比，评估现有数据是否符合政策预期或目标，指出政策落地效果或潜在问题。
3. **深度推理**：不要仅仅罗列数据，要给出专业的数据洞察和可行的优化建议。
"""

    # 修复2：这里传入上面精心构建的 system_prompt
    analyzer_llm = get_analyzer_llm()
    response = analyzer_llm.invoke([
        ("system", system_prompt),
        ("human", analysis_query)
    ])
    return f"--- 深度分析报告 ---\n{response.content}"

@tool
def query_local_db(region: str) -> str:
    """查询本地数据库卫生指标。"""
    db = SessionLocal()
    try:
        res = db.query(GlobalHealthMetric).filter(GlobalHealthMetric.region == region).limit(3).all()
        return "\n".join([f"{r.year} {r.indicator}: {r.value}" for r in res]) or "本地库暂无数据"
    finally:
        db.close()

# --- 3. 智能体构建 ---
class HealthResourceAgent:
    def __init__(self):
        self.tools = [deepseek_analyzer_tool, query_local_db]
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个卫生信息助手。对于复杂的计算、预测或深度评估，请务必调用 deepseek_analyzer_tool。"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        # 创建 Agent
        chat_llm = get_chat_llm()
        self.agent = create_openai_functions_agent(chat_llm, self.tools, self.prompt)
        self.executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)

    def ask(self, user_input: str, chat_history: list = None):
        response = self.executor.invoke({
            "input": user_input,
            "chat_history": chat_history or []
        })
        return response["output"]

def ask_agent(user_input: str, chat_history: list = None):
    agent_inst = HealthResourceAgent()
    return agent_inst.ask(user_input, chat_history)