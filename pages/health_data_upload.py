import streamlit as st
import os
from config.settings import RAW_DATA_FILE, CLEANED_DATA_FILE
from modules.run_analysis import main as run_prebuild
from db.connection import SessionLocal
from db.models import GlobalHealthMetric
from modules.data_cleaner import HealthDataCleaner
from modules.owid_data_fetcher import batch_fetch_owid, owid_data_2_db

def show():
    st.header("📂 数据上传与自动化清洗")

    tab1, tab2, tab3 = st.tabs(["数据导入", "库内数据查看", "OWID爬取日志"])

    uploaded_file = st.file_uploader("上传卫生统计年鉴 (Excel)", type=['xlsx'])

    with tab1:
        uploaded_file = st.file_uploader("上传 Excel 报表", type=['xlsx'])
        if uploaded_file:
            # 确保 data/raw 目录存在
            target_dir = os.path.dirname(RAW_DATA_FILE)
            os.makedirs(target_dir, exist_ok=True)

            with open(RAW_DATA_FILE, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("文件已成功上传")

        st.markdown("---")
        st.subheader("🌐 OWID全球数据一键拉取")  # 新增OWID拉取区域
        target_countries = st.text_input("输入拉取的国家（英文,分隔）", "China,United States,India,Germany,Nigeria")
        if st.button("🚀 拉取OWID健康数据并入库", type="secondary"):
            with st.spinner("🔄 正在从OWID拉取数据并标准化入库..."):
                try:
                    batch_fetch_owid(target_countries=[c.strip() for c in target_countries.split(",")])
                    st.success(f"✅ OWID数据拉取完成！已存入WHOGlobalHealth表")
                except Exception as e:
                    st.error(f"❌ OWID数据拉取失败：{e}")


    with tab2:
        db = SessionLocal()
        data = db.query(GlobalHealthMetric).limit(100).all()
        st.table([{"地区": d.region, "指标": d.indicator, "数值": d.value} for d in data])
        db.close()

        view_type = st.radio("查看数据类型", ["本地卫生数据", "OWID全球健康数据"])
        if view_type == "本地卫生数据":
            data = db.query(GlobalHealthMetric).limit(100).all()
            st.table([{"地区": d.region, "指标": d.indicator, "数值": d.value, "年份": d.year} for d in data])
        else:
            from db.models import WHOGlobalHealth
            data = db.query(WHOGlobalHealth).limit(100).all()
            st.table(
                [{"国家": d.country_name, "指标": d.indicator_name, "数值": d.value, "年份": d.year} for d in data])
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

    with tab3:
        st.subheader("📜 OWID爬取日志")
        db = SessionLocal()
        try:
            # 分页查询日志
            page = st.number_input("页码", min_value=1, value=1)
            page_size = 10
            offset = (page - 1) * page_size

            logs = db.query(OWIDFetchLog).order_by(OWIDFetchLog.fetch_time.desc()).offset(offset).limit(page_size).all()
            if not logs:
                st.info("暂无爬取日志")
                return

            # 格式化日志数据
            log_data = []
            for log in logs:
                log_data.append({
                    "指标ID": log.indicator_id,
                    "爬取时间": log.fetch_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "目标国家": json.loads(log.target_countries) if log.target_countries else [],
                    "状态": "成功" if log.status else "失败",
                    "新增数据量": log.data_count,
                    "错误信息": log.error_msg if log.error_msg else "无"
                })
            st.dataframe(log_data, use_container_width=True)

            # 导出日志
            if st.button("📥 导出所有日志"):
                all_logs = db.query(OWIDFetchLog).all()
                all_log_data = pd.DataFrame([{
                    "indicator_id": log.indicator_id,
                    "target_countries": log.target_countries,
                    "fetch_time": log.fetch_time,
                    "status": log.status,
                    "data_count": log.data_count,
                    "error_msg": log.error_msg
                } for log in all_logs])
                st.download_button(
                    label="下载CSV日志",
                    data=all_log_data.to_csv(index=False, encoding="utf-8-sig"),
                    file_name=f"owid_fetch_log_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"加载日志失败：{e}")
        finally:
            db.close()