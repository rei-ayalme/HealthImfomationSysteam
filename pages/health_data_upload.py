import streamlit as st
import os
from config.settings import RAW_DATA_FILE, CLEANED_DATA_FILE,UPLOAD_DIR
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
        uploaded_file = st.file_uploader(
            "上传 Excel 报表",
            type=[ext.lstrip(".") for ext in DATA_CONFIG["supported_formats"]],
            accept_multiple_files=False
        )
        if uploaded_file is not None:
            # 保存上传文件到本地
            file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.success(f"✅ 文件上传成功：{uploaded_file.name}")

            # 全链路转换
            with st.spinner("🔄 正在进行文件校验、清洗、标准化转换..."):
                convert_result = convert_data(file_path, uploaded_file.name)

            # 展示转换结果
            if convert_result.status:
                st.success("✅ 数据标准化转换完成！兼容算法/智能体输入要求")

                # 1. 展示元信息
                with st.expander("📋 数据元信息"):
                    st.json(convert_result.metadata)

                # 2. 预览标准化数据
                with st.expander("📊 标准化数据预览（前10行）"):
                    st.dataframe(convert_result.data.head(10), use_container_width=True)

                # 3. 入库选项
                if st.button("💾 将标准化数据入库", type="primary"):
                    db = SessionLocal()
                    try:
                        # 入库（适配GlobalHealthMetric表）
                        for _, row in convert_result.data.iterrows():
                            metric = GlobalHealthMetric(
                                region=row.get("country", "未知") if pd.notna(row.get("country")) else "未知",
                                indicator=row.get("indicator", "未知") if pd.notna(row.get("indicator")) else "未知",
                                value=float(row.get("value", 0)) if pd.notna(row.get("value")) else 0.0,
                                year=int(row.get("year", 0)) if pd.notna(row.get("year")) and row.get(
                                    "year") != "未知" else 0
                            )
                            db.add(metric)
                        db.commit()
                        st.success("✅ 标准化数据成功入库！")
                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ 入库失败：{str(e)[:100]}")
                    finally:
                        db.close()

                # 4. 调用DeepSeek算法选项
                if st.button("🚀 调用DeepSeek分析标准化数据", type="secondary"):
                    from modules.deepseek_client import call_deepseek_analyzer
                    with st.spinner("🔄 调用DeepSeek_Analyzer..."):
                        # 适配DeepSeek输入
                        deepseek_input = {
                            "data": convert_result.standard_format,
                            "metadata": convert_result.metadata
                        }
                        deepseek_result = call_deepseek_analyzer(deepseek_input, task_type="resource_allocation")
                        if deepseek_result["status"] == "success":
                            st.success("✅ DeepSeek分析完成！")
                            st.json(deepseek_result["result"])
                        else:
                            st.error(f"❌ DeepSeek调用失败：{deepseek_result['msg']}")

                # 5. 同步到AI智能体
                if st.button("🤖 将数据同步到AI智能体", type="secondary"):
                    # 将标准化prompt存入session_state，供智能体调用
                    st.session_state["agent_data_prompt"] = convert_result.agent_prompt
                    st.success("✅ 数据已同步到AI智能体！现在可向AI提问该数据相关问题")

            else:
                st.error(f"❌ 数据转换失败：{convert_result.error_msg}")


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

        try:
            metrics = db.query(GlobalHealthMetric).limit(100).all()
            if metrics:
                df_preview = pd.DataFrame([{
                    "region": m.region,
                    "indicator": m.indicator,
                    "value": m.value,
                    "year": m.year
                } for m in metrics])
                st.dataframe(df_preview, use_container_width=True)
            else:
                st.info("暂无已入库的标准化数据")
        finally:
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
                    "配置数据量": log.data_count,
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