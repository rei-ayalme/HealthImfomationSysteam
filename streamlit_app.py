# streamlit_app.py
import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 1. 路径注入：确保模块能被正确找到
root_path = str(Path(__file__).parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from db.connection import init_db
if 'db_initialized' not in st.session_state:
    init_db()  # 程序启动时自动创建 health_system.db 文件和表
    st.session_state.db_initialized = True

# 2. 环境配置
load_dotenv()
from config.settings import PAGE_TITLE, CLEANED_DATA_FILE
from modules.unified_interface import get_unified_analyzer
from modules.disease_analyzer import DiseaseAnalyzer

st.set_page_config(page_title=PAGE_TITLE, layout="wide")

# 3. 初始化会话状态
if 'initialized' not in st.session_state:
    if os.path.exists(CLEANED_DATA_FILE):
        st.session_state.analyzer = get_unified_analyzer(CLEANED_DATA_FILE)
    else:
        st.session_state.analyzer = None
    st.session_state.disease_analyzer = DiseaseAnalyzer()
    st.session_state.initialized = True

st.title("🏥 卫生资源配置优化分析平台")
st.info("请从左侧侧边栏选择具体的分析页面。")

# 4. 全局 AI 助手 (侧边栏)
with st.sidebar:
    st.header("🤖 AI 智能分析")
    if st.checkbox("开启 AI 助手"):
        from modules.health_agent import ask_agent

        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "你好！我是分析助手。请问需要什么帮助？"}]

        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])

        if prompt := st.chat_input("输入问题..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            with st.spinner("思考中..."):
                answer = ask_agent(prompt, chat_history=st.session_state.messages[:-1])
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.chat_message("assistant").write(answer)