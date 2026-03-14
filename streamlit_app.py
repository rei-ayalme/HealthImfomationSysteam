import os
import sys
import pandas as pd
from pathlib import Path
from modules.analysis.health import UnifiedHealthAnalyzer
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
from modules.core.interface import IDiseaseAnalyzer
from modules.analysis.disease import DiseaseRiskAnalyzer
from db.connection import init_db
from utils.auth import check_password

# 页面基础配置
st.set_page_config(page_title=PAGE_TITLE, layout="wide")

# 2. 数据库与会话状态初始化
if 'initialized' not in st.session_state:
    # 初始化数据库表结构
    init_db()
    if os.path.exists(CLEANED_DATA_FILE):
        try:
            if CLEANED_DATA_FILE.endswith('.csv'):
                df = pd.read_csv(CLEANED_DATA_FILE)
            else:
                df = pd.read_excel(CLEANED_DATA_FILE)

            st.session_state.analyzer = UnifiedHealthAnalyzer(df)
        except Exception as e:
            st.error(f"加载数据失败: {e}")
            st.session_state.analyzer = None
    else:
        st.session_state.analyzer = None

    st.session_state.disease_analyzer = DiseaseRiskAnalyzer()
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
        "📈 数据可视化": ["数据可视化（带加载动画）"],
        "⚙️ 系统管理": ["接口检查中心"]
    }

    selected_group = st.selectbox("功能分组", list(menu.keys()))
    selected_page = st.radio("功能模块", menu[selected_group])

    st.markdown("---")
    st.caption("v1.2 | 系统运行正常")

# 5. AI 智能助手悬浮
def add_ai_sidebar():
    st.markdown("""
            <style>
            /* 悬浮窗口主容器：固定在右侧，距离顶部20px，宽度320px，跟随滚动 */
            .ai-float-window {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 320px;
                height: 80vh;
                max-height: 800px;
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 16px;
                z-index: 9999;  /* 置顶，不被其他内容遮挡 */
                overflow-y: auto;  /* 聊天记录过多时滚动 */
            }
            /* 最小化按钮样式 */
            .ai-min-btn {
                position: absolute;
                top: 10px;
                right: 10px;
                background: #f0f2f6;
                border: none;
                border-radius: 4px;
                padding: 2px 8px;
                cursor: pointer;
                font-size: 14px;
            }
            /* 聊天输入框适配 */
            div[data-testid="stChatInput"] {
                margin-top: 16px;
            }
            </style>
            <!-- 悬浮窗口容器 -->
            <div class="ai-float-window" id="aiWindow">
                <button class="ai-min-btn" onclick="document.getElementById('aiWindow').style.display='none'">—</button>
                <h3 style="margin-top:0; color:#1f2937;">🤖 AI智能助手</h3>
                <hr style="margin:8px 0;">
            </div>
            <!-- 恢复窗口按钮：最小化后显示在右侧 -->
            <button style="position:fixed;top:20px;right:20px;z-index:9999;display:none;" id="resumeBtn" onclick="document.getElementById('aiWindow').style.display='block';this.style.display='none'">
                🤖 AI助手
            </button>
            <script>
            // 最小化后显示恢复按钮
            document.querySelector('.ai-min-btn').onclick = function() {
                document.getElementById('aiWindow').style.display = 'none';
                document.getElementById('resumeBtn').style.display = 'block';
            }
            </script>
        """, unsafe_allow_html=True)  # 必须开启unsafe_allow_html

    # 原有AI聊天逻辑完全保留，无任何修改
    from modules.agent.agent import ask_agent
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

    # 聊天输入框后新增代码
    #if len(st.session_state.messages) > 20:  # 保留最多20条记录
        #st.session_state.messages = st.session_state.messages[-20:]  # 只取最后20条

add_ai_sidebar()

# 6. 页面路由分发
if selected_page == "数据上传与预处理":
    import pages.health_data_upload as upload_page

    upload_page.show()
elif selected_page == "资源缺口分析":
    import pages.health_analysis as analysis_page

    analysis_page.show()
elif selected_page== "疾病风险评估":
    import pages.disease_risk_assessment as disease_page

    disease_page.show()
elif selected_page == "报告经理":
    import pages.report_manager as report_page

    report_page.show()
elif selected_page == "接口检查中心":  # 新增
    import pages.api_checker_page as api_check_page

    api_check_page.show()
elif selected_page == "数据可视化（带加载动画）":  # 新增路由
    import pages.data_visualization_with_loading as vis_page

    vis_page.show()
