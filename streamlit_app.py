import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from db.connection import init_db, SessionLocal, seed_db
init_db()  # 创建表结构
db = SessionLocal()
seed_db(db) # 填充预设数据
db.close()

# 1. 路径注入：确保模块能从项目根目录被正确加载
root_path = str(Path(__file__).parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)
current_dir = Path(__file__).parent.absolute()
# 将根目录添加到 sys.path
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
import streamlit as st
# 加载环境变量（API密钥等）
load_dotenv()

from config.settings import PAGE_TITLE, CLEANED_DATA_FILE
from modules.unified_interface import get_unified_analyzer
from modules.disease_analyzer import DiseaseAnalyzer
from db.connection import init_db
from utils.auth import check_password

# 页面基础配置
st.set_page_config(page_title=PAGE_TITLE, layout="wide")

# 2. 数据库与会话状态初始化
if 'initialized' not in st.session_state:
    # 初始化数据库表结构
    init_db()

    # 初始化分析器实例
    if os.path.exists(CLEANED_DATA_FILE):
        st.session_state.analyzer = get_unified_analyzer(CLEANED_DATA_FILE)
    else:
        st.session_state.analyzer = None

    st.session_state.disease_analyzer = DiseaseAnalyzer()
    st.session_state.initialized = True

# 3. 登录校验 (可选)
#if not check_password():
    #st.stop()

# 4. 侧边栏：业务流程导向导航
with st.sidebar:
    st.title("🏥 卫生资源配置平台")
    st.markdown("---")

    st.subheader("📊 导航菜单")
    menu = {
        "📊 数据管理": ["数据上传与预处理"],
        "🔍 核心分析": ["资源缺口分析", "疾病风险评估"],
        "📋 输出管理": ["报告经理"]
    }

    selected_group = st.selectbox("功能分组", list(menu.keys()))
    page = st.radio("功能模块", menu[selected_group])

    st.markdown("---")
    st.caption("v1.2 | 系统运行正常")


# 5. AI 智能助手悬浮/侧边栏入口
def add_ai_sidebar():
    with st.sidebar.expander(" AI 智能助手", expanded=False):
        from modules.health_agent import ask_agent
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "你好！我是卫生资源助手。建议您先上传数据。"}]

        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])

        if prompt := st.chat_input("询问关于资源配置的问题...", key="ai_chat_input"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            with st.spinner("AI 思考中..."):
                answer = ask_agent(prompt, chat_history=st.session_state.messages[:-1])
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.chat_message("assistant").write(answer)


add_ai_sidebar()

# 6. 页面路由分发
if page == "数据上传与预处理":
    import pages.health_data_upload as upload_page

    upload_page.show()
elif page == "资源缺口分析":
    import pages.health_analysis as analysis_page

    analysis_page.show()
elif page == "疾病风险评估":
    import pages.disease_risk_assessment as disease_page

    disease_page.show()
elif page == "报告经理":
    import pages.report_manager as report_page

    report_page.show()