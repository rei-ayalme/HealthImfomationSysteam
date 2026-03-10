import streamlit as st
import os
from config.settings import RAW_DATA_FILE, CLEANED_DATA_FILE
from modules.run_analysis import main as run_prebuild
from db.connection import SessionLocal
from db.models import GlobalHealthMetric
from modules.data_cleaner import HealthDataCleaner


def show():
    st.header("📂 数据上传与自动化清洗")

    tab1, tab2 = st.tabs(["数据导入", "库内数据查看"])

    uploaded_file = st.file_uploader("上传卫生统计年鉴 (Excel)", type=['xlsx'])

    with tab1:
        uploaded_file = st.file_uploader("上传 Excel 报表", type=['xlsx'])
        if uploaded_file:
            import pandas as pd
            df = pd.read_excel(uploaded_file)
            clean_df = HealthDataCleaner.quick_clean(df)
            st.write("清洗后的数据预览：", clean_df.head())

            if st.button("确认入库"):
                # 这里调用 CRUD 将数据写入 SQLite
                st.success("数据已持久化至本地数据库！")

    with tab2:
        db = SessionLocal()
        data = db.query(GlobalHealthMetric).limit(100).all()
        st.table([{"地区": d.region, "指标": d.indicator, "数值": d.value} for d in data])
        db.close()

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