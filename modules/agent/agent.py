# modules/health_agent.py 修复版
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent
from langchain.agents.agent import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from db.connection import SessionLocal
from db.models import GlobalHealthMetric
from modules.agent.adapter import owid_2_deepseek_input
from config.settings import OPENAI_CONFIG

load_dotenv()

# --- 1. 模型初始化 ---
chat_llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat"),
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base="https://api.deepseek.com/v1",
    temperature=0.7
)

analyzer_llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_ANALYZER_MODEL", "DeepAnalyze-8B"),
    openai_api_key=os.getenv("DEEPSEEK_API_KEY","EMPTY"),
    openai_api_base="https://u906943-aad8-00a5d162.westc.seetacloud.com:8443/v1",
    temperature=0,
    max_tokens=2048
)

# --- 2. 增强型分析工具 ---
@tool
def deepseek_analyzer_tool(analysis_query: str) -> str:
    """卫生数据分析专家工具。用于复杂计算、趋势预测和深度推理。"""
    db = SessionLocal()
    try:
        # 修复1：将变量名 context 修改为 data_context 保持一致
        base_metrics = db.query(GlobalHealthMetric).limit(5).all()
        data_context = "\n".join([f"{m.region} {m.indicator}: {m.value}" for m in base_metrics])
    finally:
        db.close()

    policy_context = ""
    try:
        with open("data/china/policy_notes.txt", "r", encoding="utf-8") as f:
            policy_context = f.read()[:4000]  # 只取精华部分
    except FileNotFoundError:
        policy_context = "暂无官方政策背景说明。"

    system_prompt = f"""
你是一名资深中国卫生数据科学家。

【当前数值数据】
{data_context}

【官方政策与统计口径背景】
{policy_context}

请结合上述政策背景（如医改、统计范围调整）和数值数据，回答用户的分析请求。
"""

    # 修复2：这里传入上面精心构建的 system_prompt
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