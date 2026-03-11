import time
import streamlit as st
import pandas as pd
import plotly.express as px
from modules.disease_analyzer import DiseaseAnalyzer
from modules.deepseek_client import deepseek_analysis_wrapper
from pages.health_analysis import get_owid_db_data, OWID_COLORS
from db.connection import SessionLocal
from db.models import DeepSeekAnalysisResult

def show():
    st.title("🔬 疾病风险归因与 SDE 模拟")

    da = st.session_state.get('disease_analyzer', DiseaseAnalyzer())
    prov = st.text_input("输入分析省份", "北京市")

    st.subheader("📊 OWID 全球风险因素归因分析（参考基准）")
    risk_indicator = st.selectbox("选择风险因素", ["pm2-5-air-pollution-exposure", "share-of-adults-who-smoke"],
                                  format_func=lambda x: {"pm2-5-air-pollution-exposure": "PM2.5暴露水平",
                                                         "share-of-adults-who-smoke": "成人吸烟率"}[x])
    disease_indicator = st.selectbox("选择关联疾病", ["share-of-deaths-from-non-communicable-diseases",
                                                      "share-of-deaths-from-communicable-diseases"],
                                     format_func=lambda x:
                                     {"share-of-deaths-from-non-communicable-diseases": "非传疾病死亡占比%",
                                      "share-of-deaths-from-communicable-diseases": "传疾病死亡占比%"}[x])

    st.subheader("🧠 DeepSeek 智能分析（基于OWID数据）")
    st.markdown("**分析逻辑**：OWID提供风险因素+疾病数据 → DeepSeek计算各风险因素对疾病的贡献度")
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_countries = st.multiselect("选择国家", ["China", "United States", "India"], default=["China"])
    with col2:
        start_year = st.number_input("起始年份", min_value=2000, max_value=2020, value=2010)
    with col3:
        end_year = st.number_input("结束年份", min_value=2001, max_value=2020, value=2020)

    # 选择分析指标（疾病风险+风险因素）[可拓展疾病指标]
    indicator_ids = [
        "share-of-deaths-from-non-communicable-diseases",
        "pm2-5-air-pollution-exposure"
    ]

    if st.button("🚀 运行DeepSeek分析"):
        with st.spinner("🔄 调用DeepSeek_Analyzer进行疾病风险归因分析..."):
            # 调用DeepSeek
            ds_result = deepseek_analysis_wrapper(
                indicator_ids=indicator_ids,
                countries=selected_countries,
                start_year=start_year,
                end_year=end_year,
                task_type="disease_risk"
            )

            # 展示结果
            if ds_result["status"] == "success":
                st.success("✅ DeepSeek分析完成！")
                # 提取结果和元信息
                result_data = ds_result["result"]
                metadata = ds_result["metadata"]
                indicator_map = metadata["indicator_map"]

                # --- 结果入库（持久化） ---
                db = SessionLocal()
                db.add(DeepSeekAnalysisResult(
                    task_type="disease_risk",
                    indicator_ids=",".join(indicator_ids),
                    countries=",".join(selected_countries),
                    time_range=f"{start_year}-{end_year}",
                    analysis_result=result_data,
                    metadata=metadata
                ))
                db.commit()
                db.close()
                # 可视化分析结果（适配Plotly）
                st.subheader("📊 DeepSeek分析结果可视化")
                # 示例：提取风险贡献度数据
                risk_contribution = result["result"].get("risk_contribution", {})
                if risk_contribution:
                    df_risk = pd.DataFrame(risk_contribution).T.reset_index()
                    df_risk.columns = [
                    {"country": c, "risk_factor": k, "contribution": v}
                    for c, factors in result_data["risk_contribution"].items()
                    for k, v in factors.items()
                ]
                    fig = px.bar(
                        df_risk,
                        x="country",
                        y="contribution",
                        title="不同国家疾病风险因素贡献度",
                        color_discrete_map=OWID_COLORS,
                        hover_data={"contribution": ":,.2f"}
                    )
                    fig.update_layout(plot_bgcolor="white", legend_title="风险因素", yaxis_title="贡献度")
                    st.plotly_chart(fig, use_container_width=True)
                # 展示原始结果
                with st.expander("📝 查看详细分析结果"):
                    st.json(result["result"])
            else:
                st.error(f"❌ 分析失败：{result['msg']}")

    # 获取OWID数据并做相关性分析
    df_risk = get_owid_db_data([risk_indicator, disease_indicator], 2000, 2020)
    if not df_risk.empty:
        # 数据透视：一个国家一行，包含风险因素和疾病指标
        df_pivot = df_risk.pivot_table(index=["country", "year"], columns="indicator", values="value").reset_index()
        df_pivot = df_pivot.dropna()
        # 可视化：风险因素与疾病的相关性散点图（OWID风格）
        fig_corr = px.scatter(df_pivot, x=risk_indicator, y=disease_indicator,
                              color="country", hover_name="country",
                              title=f"{ {'pm2-5-air-pollution-exposure': 'PM2.5暴露水平',
                                         'share-of-adults-who-smoke': '成人吸烟率'}[risk_indicator]
                              } 与 { {'share-of-deaths-from-non-communicable-diseases': '非传疾病死亡占比%',
                                      'share-of-deaths-from-communicable-diseases': '传疾病死亡占比%'}[disease_indicator]
                              } 相关性",
                              color_discrete_map=OWID_COLORS,
                              trendline="ols")  # OWID风格：加趋势线，显示相关性
        fig_corr.update_layout(plot_bgcolor="white", legend_title=None)
        st.plotly_chart(fig_corr, use_container_width=True)
        # 显示相关系数
        from scipy import stats
        corr, p = stats.pearsonr(df_pivot[risk_indicator], df_pivot[disease_indicator])
        st.info(f"📌 皮尔逊相关系数：{corr:.2f}，P值：{p:.4f}（P<0.05为显著相关）")

    st.markdown("---")


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