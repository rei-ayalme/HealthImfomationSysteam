import streamlit as st
import os
from config.settings import RAW_DATA_FILE, CLEANED_DATA_FILE
from modules.run_analysis import main as run_prebuild

st.title("📂 数据上传与预处理")

uploaded_file = st.file_uploader("上传年度卫生统计 Excel 文件", type=['xlsx'])

if uploaded_file:
    # 保存到 raw 目录
    with open(RAW_DATA_FILE, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success("原始文件已保存到 data/raw/")

if st.button("🚀 执行数据清洗与标准化", type="primary"):
    with st.spinner("正在运行预处理算法..."):
        try:
            run_prebuild() # 调用现有的 main 函数
            st.success("清洗完成！数据已就绪。")
            if os.path.exists(CLEANED_DATA_FILE):
                from modules.unified_interface import get_unified_analyzer
                st.session_state.analyzer = get_unified_analyzer(CLEANED_DATA_FILE)
        except Exception as e:
            st.error(f"预处理失败: {e}")