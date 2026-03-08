import streamlit as st
import plotly.graph_objects as go
from modules.disease_analyzer import DiseaseAnalyzer

st.title("🔬 疾病风险归因与 SDE 模拟")

da = st.session_state.get('disease_analyzer', DiseaseAnalyzer())
prov = st.text_input("输入分析省份", "北京市")

if st.button("运行多尺度模拟"):
    result_df, paths = da.run_sde_model(years=30, scenario="碳中和", carbon_policy=0.5)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=result_df['年份'], y=result_df['传染病负担_均值'], name='趋势均值'))
    st.plotly_chart(fig)

    # 获取建议
    st.info(da.get_intervention_list(prov))