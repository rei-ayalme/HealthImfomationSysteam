import time
import streamlit as st
from modules.disease_analyzer import DiseaseAnalyzer

def show():
    st.title("🔬 疾病风险归因与 SDE 模拟")

da = st.session_state.get('disease_analyzer', DiseaseAnalyzer())
prov = st.text_input("输入分析省份", "北京市")


def run_simulation():
    st.subheader("🔬 多尺度演化模拟")
    if st.button("🚀 开始模拟计算"):
        # 显示自定义加载状态
        with st.empty():
            st.markdown("![Loading...](https://loading.io/asset/634628)")  # 建议替换为本地 static/loading.gif
            st.write("正在求解随机微分方程 (SDE)...")

            # 模拟计算耗时
            from modules.disease_analyzer import DiseaseAnalyzer
            da = DiseaseAnalyzer()
            res = da.run_sde_model(years=30)
            time.sleep(2)

        st.success("✅ 模拟完成！")
        st.plotly_chart(res[0])
    # 获取建议
    st.info(da.get_intervention_list(prov))