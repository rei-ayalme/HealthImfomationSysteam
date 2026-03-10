import streamlit as st
import pandas as pd
import plotly.express as px
from db.connection import SessionLocal
from db.models import WHOGlobalHealth

def show():
    st.header("🔍 卫生资源缺口分析")

    analyzer = st.session_state.get('analyzer')
    if not analyzer:
        st.warning("⚠️ 未检测到有效数据，请先前往『数据管理』页面。")
        st.stop()

    available_years = sorted(getattr(analyzer, 'years', [2020]), reverse=True)
    selected_year = st.selectbox("选择分析年份", available_years)

    # 计算缺口数据
    gap_data = analyzer.compute_resource_gap(selected_year)

    # 展示核心指标
    c1, c2, c3 = st.columns(3)
    c1.metric("全国平均缺口率", f"{gap_data['相对缺口率'].mean():.1%}")
    c2.metric("严重短缺省份", len(gap_data[gap_data['相对缺口率'] > 0.2]))


    # 交互式柱状图
    fig = px.bar(gap_data.reset_index(), x='地区', y='相对缺口率', color='缺口类别',
                 title=f"{selected_year}年各省份资源缺口分布")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("🌐 WHO 国际卫生指标对比")

    # 用户勾选后才显示对比
    if st.checkbox("开启 WHO 国际数据对比"):
        db = SessionLocal()
        try:
            # 1. 从数据库获取数据
            # 假设我们要对比的是 2020 年的数据
            query_res = db.query(WHOGlobalHealth).filter(WHOGlobalHealth.year == 2020).all()

            if not query_res:
                st.info("💡 本地库中暂无 WHO 数据。请确保已运行同步脚本，或通过 AI 助手搜索添加。")
            else:
                # 2. 将查询结果转化为 DataFrame
                who_data = pd.DataFrame([
                    {
                        "国家代码": item.country_code,
                        "指标名称": item.indicator_name,
                        "数值": item.value,
                        "年份": item.year
                    } for item in query_res
                ])

                col1, col2 = st.columns([1, 2])

                with col1:
                    st.write("📋 WHO 指标数据预览")
                    st.dataframe(who_data, use_container_width=True)

                with col2:
                    fig = px.bar(
                        who_data,
                        x="国家代码",
                        y="数值",
                        color="国家代码",
                        title="WHO 核心卫生指标国际对比 (2020)",
                        labels={"数值": "指标值"}
                    )
                    st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"查询 WHO 数据时出错: {e}")
        finally:
            db.close()

    st.info("🧐 对数据感兴趣？在左侧 AI 助手输入：'搜索并添加 [国家] [年份] 的人均医疗支出数据'")