import streamlit as st
import os
from config.settings import RAW_DATA_FILE, CLEANED_DATA_FILE
from modules.run_analysis import main as run_prebuild


def show():
    st.header("📂 数据上传与自动化清洗")

    uploaded_file = st.file_uploader("上传卫生统计年鉴 (Excel)", type=['xlsx'])

    if uploaded_file:
        # 确保目录存在
        os.makedirs(os.path.dirname(RAW_DATA_FILE), exist_ok=True)
        with open(RAW_DATA_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("文件已暂存至 data/raw/")

    if st.button("🚀 执行清洗与标准化", type="primary"):
        with st.spinner("🔄 正在运行预处理算法..."):
            try:
                run_prebuild()  # 调用 run_analysis.py 的逻辑
                st.success("✅ 数据清洗完成！")

                # 重新加载分析器
                from modules.unified_interface import get_unified_analyzer
                st.session_state.analyzer = get_unified_analyzer(CLEANED_DATA_FILE)
            except Exception as e:
                st.error(f"处理失败: {e}")