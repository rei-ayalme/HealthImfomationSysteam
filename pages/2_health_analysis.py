import streamlit as st
import plotly.express as px
from config.settings import CLEANED_DATA_FILE

st.title("📊 卫生资源缺口分析")

if 'analyzer' not in st.session_state or st.session_state.analyzer is None:
    st.warning("请先前往『数据上传』页面处理数据")
    st.stop()

analyzer = st.session_state.analyzer
year = st.selectbox("选择分析年份", analyzer.years)

# 缺口分析逻辑
gap_data = analyzer.compute_resource_gap(year)
st.dataframe(gap_data.style.background_gradient(subset=['相对缺口率'], cmap='RdYlGn_r'))

# 绘制图表
fig = px.bar(gap_data.reset_index(), x='地区', y='相对缺口率', color='缺口类别', title=f"{year}年各地区资源缺口")
st.plotly_chart(fig, use_container_width=True)