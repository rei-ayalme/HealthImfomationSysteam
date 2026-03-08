import streamlit as st
import plotly.express as px


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