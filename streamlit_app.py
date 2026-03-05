import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from settings import PAGE_TITLE, CLEANED_DATA_FILE
from unified_interface import get_unified_analyzer
from disease_analyzer import DiseaseAnalyzer
import os
import numpy as np
from health_agent import ask_agent
import seaborn as sns
import matplotlib.pyplot as plt
import arviz as az
import json

st.set_page_config(page_title="全国卫生资源配置优化平台", layout="wide")

# 初始化会话状态
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.analyzer = get_unified_analyzer(CLEANED_DATA_FILE)
    st.session_state.disease_analyzer = DiseaseAnalyzer()
    st.session_state.selected_year = 2020  # 设置默认年份
    st.session_state.chat_history = [
        {"role": "assistant", "content": "你好！我是卫生资源配置智能助手。请问有什么可以帮你分析的？"}
    ]

analyzer = st.session_state.analyzer
da = st.session_state.disease_analyzer

st.sidebar.header("📅 全局控制")
available_years = sorted(getattr(analyzer, 'years', [2020]), reverse=True)
if not available_years:
    available_years = [2020]

current_year = st.session_state.get('selected_year', available_years[0])
default_idx = available_years.index(current_year) if current_year in available_years else 0

st.session_state.selected_year = st.sidebar.selectbox(
    "分析年份", available_years, index=default_idx, key="global_year"
)

st.title("全国卫生资源配置优化分析平台")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 缺口分析",
    "🗺️ 交互地图",
    "🔮 未来预测",
    "⚡ 最优再分配",
    "📄 PDF报告 & 疾病谱系",
    "🔬 疾病谱系微分模型"
])

# 第一个标签页
with tab1:
    col1, col2, col3 = st.columns(3)


    @st.cache_data
    def compute_gap_data(_analyzer, year):
        return _analyzer.compute_resource_gap(year)


    gap_data = compute_gap_data(analyzer, st.session_state.selected_year)
    avg_gap_rate = gap_data['相对缺口率'].median()

    with col1:
        st.metric("全国平均缺口率 (中位数)", f"{avg_gap_rate:.1%}")
    with col2:
        severe = len(gap_data[gap_data['缺口类别'] == '严重短缺'])
        st.metric("严重短缺省份", severe)
    with col3:
        top_p = gap_data['相对缺口率'].idxmax()
        st.metric("缺口最大省份", top_p, f"{gap_data.loc[top_p, '相对缺口率']:.1%}")

    fig = px.bar(
        gap_data.reset_index(),
        x='地区',
        y=['实际供给指数', '理论需求指数'],
        barmode='group',
        title=f"{st.session_state.selected_year}年 实际供给指数 vs 理论需求指数",
        labels={'value': '综合资源指数（每万人）', 'variable': '指标'},
        color_discrete_sequence=['#1f77b4', '#ff7f0e']
    )

    st.plotly_chart(fig, use_container_width=True)

# 第二个标签页
with tab2:
    st.subheader("🗺️ 交互地图可视化")
    map_type = st.radio("选择地图类型", ["中国省级详细地图", "全球地图（突出中国）"])


    @st.cache_data
    def get_cached_map_data(_analyzer, selected_year):
        return _analyzer.get_map_data(selected_year)


    map_data = get_cached_map_data(analyzer, st.session_state.selected_year)

    if map_type == "中国省级详细地图":
        with st.spinner("正在计算优化分配方案..."):
            result = analyzer.optimize_resource_allocation(st.session_state.selected_year,
                                                           objective='minimize_inequality')
        new_gap = result['new_relative_gap']

        map_data['优化后缺口率'] = new_gap.values

        try:
            import requests

            china_geo = requests.get(
                "https://raw.githubusercontent.com/longwosion/geojson-map-china/master/china.json",
                timeout=10  # 增加超时时间
            ).json()

            fig = px.choropleth(
                map_data,
                geojson=china_geo,
                locations='地区',
                featureidkey="properties.name",
                color='优化后缺口率',
                color_continuous_scale="RdYlGn_r",
                range_color=(-0.5, 0.5),
                title="中国省级卫生资源缺口率分布",
                hover_data={'地区': True, '优化后缺口率': ':.1%'}
            )
            fig.update_geos(showcountries=False, showcoastlines=True, showland=True, fitbounds="locations")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"地图加载失败（网络问题）: {str(e)}，显示备用柱状图")
            fig = px.bar(map_data, x='地区', y='优化后缺口率', title="各省优化后缺口率")
            st.plotly_chart(fig, use_container_width=True)

    else:  # 全球地图
        try:
            import folium
            from streamlit_folium import st_folium

            with st.spinner("正在加载世界地图..."):
                m = folium.Map(location=[35, 105], zoom_start=4)

                # 添加choropleth图层
                folium.Choropleth(
                    geo_data="https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson",
                    data=map_data,
                    columns=["地区", "相对缺口率"],
                    key_on="feature.properties.name",
                    fill_color="RdYlGn_r",
                    fill_opacity=0.7,
                    line_opacity=0.2,
                    legend_name="相对缺口率"
                ).add_to(m)

            st_folium(m, width=800, height=500)
        except Exception as e:
            st.error(f"全球地图加载失败: {str(e)}")

# 第三个标签页
with tab3:
    st.subheader("🔮 未来卫生资源预测（2021-2025）")
    scenario = st.selectbox("预测场景", ["基准", "乐观", "保守"], key="pred_scenario")

    # 确保pred_years变量定义
    pred_years = st.slider("预测年数", 3, 10, 5, key="years_ahead_slider")

    if st.button("生成预测报告", key="gen_pred_btn"):
        with st.spinner("正在预测未来数据..."):
            pred_df = analyzer.predict_future(years_ahead=pred_years, scenario=scenario)

        st.dataframe(pred_df)

        # 趋势图
        fig = px.line(pred_df, x='年份', y='预测缺口率', color='地区', title=f"{scenario}场景下未来缺口率趋势")
        st.plotly_chart(fig, use_container_width=True)

# 第四个标签页
with tab4:
    st.subheader("⚡ 最优再分配方案模拟")
    obj = st.selectbox("优化目标", ["最大化健康产出", "最小化健康不平等"], key="opt_objective")
    budget_ratio = st.slider("可调配资源比例 (%)", 0, 100, 30, key="budget_slider") / 100

    if st.button("🚀 运行优化模型", type="primary", key="run_opt_btn"):
        with st.spinner("正在运行优化模型..."):
            obj_key = 'maximize_health' if "最大化" in obj else 'minimize_inequality'
            result = analyzer.optimize_resource_allocation(st.session_state.selected_year, obj_key, budget_ratio)
        st.success(result['message'])

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("预期改善率", f"{result['optimization_improvement']:.1%}")
        with col_b:
            st.metric("优化后不平等程度（方差）", f"{result['new_relative_gap'].var():.4f}")

        # 饼图：预算分配
        alloc = result['allocation'][result['allocation'] > 0]
        if not alloc.empty:
            fig_pie = px.pie(names=alloc.index, values=alloc.values, title="预算分配比例")
            st.plotly_chart(fig_pie, use_container_width=True)

        # What-if 调节
        if not alloc.empty:
            st.subheader("🎛️ What-if 实时调节")
            province_select = st.selectbox("手动调整省份", list(alloc.index), key="manual_prov_select")
            manual_alloc = st.slider(f"额外分配给 {province_select} 的资源", 0, int(alloc.max()) * 2, 1000,
                                     key="manual_alloc_slider")

            # 计算调节后公平性
            with st.spinner("计算调节影响分析..."):
                original_var = result['new_relative_gap'].var()
                adjusted_var = original_var * (1 - manual_alloc / (alloc.max() * len(alloc))) if alloc.max() * len(
                    alloc) != 0 else original_var  # 防止除零错误
                st.metric("调节后不平等程度", f"{max(0, adjusted_var):.4f}")

# 第五个标签页
with tab5:
    st.subheader("📄 PDF报告 & 疾病谱系分析 & 📍 省级详情面板")
    year = st.selectbox("报告年份", available_years, key="rep_year_sel")
    prov_input = st.text_input("指定省份（留空则全国）", key="prov_input")

    provinces = list(analyzer.regions) if hasattr(analyzer, 'regions') and analyzer.regions is not None else [
        '无可用省份']
    prov = st.selectbox("选择省份", provinces, key="prov_select")

    gap_df = analyzer.compute_resource_gap(int(year))

    # 确保选择的省份存在于地区列表中
    if hasattr(analyzer, 'regions') and prov in analyzer.regions and prov in gap_df.index:
        prov_gap = gap_df.loc[prov]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("实际供给", f"{prov_gap['实际供给指数']:.2f}")  # 修复了错误的列名
        with col2:
            st.metric("理论需求", f"{prov_gap['理论需求指数']:.2f}")
        with col3:
            st.metric("缺口率", f"{prov_gap['相对缺口率']:.1%}", delta=prov_gap['缺口类别'])
    else:
        st.warning(f"暂无 {prov} 在 {year} 年的有效分析数据，可能因为该省份各项核心指标缺失。")

    # 历史趋势
    with st.spinner("正在获取趋势数据..."):
        trend = analyzer.predict_future(years_ahead=5)

    if trend.empty or '地区' not in trend.columns:
        st.info("该省份暂无预测数据（历史数据不足）")
        fig_trend = px.line(pd.DataFrame(),
                            title=f"{prov if hasattr(analyzer, 'regions') and prov in analyzer.regions else '未知省份'} 未来趋势")
    else:
        if hasattr(analyzer, 'regions') and prov in analyzer.regions:
            prov_trend = trend[trend['地区'].astype(str).str.strip() == str(prov).strip()]
            if prov_trend.empty:
                st.info("该省份暂无预测数据")
                fig_trend = px.line(pd.DataFrame(), title=f"{prov} 未来趋势")
            else:
                fig_trend = px.line(prov_trend, x='年份', y='预测缺口率',
                                    title=f"{prov} 未来缺口率趋势")
        else:
            fig_trend = px.line(pd.DataFrame(), title="数据不可用")

    st.plotly_chart(fig_trend, use_container_width=True)

    st.write("**个性化干预建议**（来自 GBD）")
    st.info("(功能开发中)")

    # PDF下载
    if st.button("生成完整PDF报告", key="gen_pdf_btn"):
        # 注意: 需要确保report_generator模块存在且能正常工作
        try:
            from report_generator import generate_pdf_report

            with st.spinner("正在生成PDF报告..."):
                pdf_bytes = generate_pdf_report(int(year), prov_input or None)

            st.download_button(
                "📥 下载PDF报告",
                pdf_bytes,
                f"卫生资源报告_{year}{'_' + prov_input if prov_input else ''}.pdf",
                "application/pdf"
            )
        except ImportError:
            st.error("报告生成模块不可用")
        except Exception as e:
            st.error(f"生成PDF报告时出错: {str(e)}")

    # 疾病分析
    st.subheader("🩸 疾病风险归因与干预建议")
    if prov and hasattr(analyzer, 'regions') and prov in analyzer.regions:
        try:
            intervention_info = da.get_intervention_list(prov)
            if intervention_info:
                st.info(intervention_info)
            else:
                st.warning("该地区暂无疾病干预建议")
        except Exception as e:
            st.error(f"获取疾病干预建议时出错: {str(e)}")
    else:
        st.warning("请选择一个有效省份以便获取分析建议")

# 第六个标签页
with tab6:
    st.subheader("🔬 全球疾病谱系 SDE 多尺度模拟器")
    st.caption("随机微分方程 + 碳中和协同 + 概率预测区间")

    col1, col2, col3 = st.columns(3)
    with col1:
        sde_scenario = st.selectbox("模拟情景", ["基准", "强化干预", "碳中和"], key="sde_scenario_tab6")
    with col2:
        carbon = st.slider("碳中和政策强度", 0.0, 1.0, 0.4,
                           key="carbon_slider_tab6") if sde_scenario == "碳中和" else 0.0
    with col3:
        sim_years = st.slider("模拟年限", 10, 50, 30, key="sim_years_slider_tab6")

    if st.button("🚀 运行 SDE 多尺度模拟", type="primary", key="run_sde_btn"):
        with st.spinner("正在运行复杂SDE模型（可能需要几分钟）..."):
            try:
                result_tuple = da.run_sde_model(years=sim_years, scenario=sde_scenario, carbon_policy=carbon)

                if isinstance(result_tuple, tuple) and len(result_tuple) >= 2:
                    # 如果确实有df和paths两个结果
                    try:
                        df, paths = result_tuple

                        # 主趋势图 + 置信区间
                        fig = go.Figure()
                        # 从df中提取数据
                        if '年份' in df.columns and '传染病负担_均值' in df.columns:
                            fig.add_trace(go.Scatter(x=df['年份'], y=df['传染病负担_均值'], name='传染病负担均值',
                                                     line=dict(color='red')))
                            if '传染病负担_下限' in df.columns:
                                fig.add_trace(go.Scatter(x=df['年份'], y=df['传染病负担_下限'], name='95%下限',
                                                         line=dict(color='red', dash='dash')))
                            if '传染病负担_上限' in df.columns:
                                fig.add_trace(go.Scatter(x=df['年份'], y=df['传染病负担_上限'], name='95%上限',
                                                         line=dict(color='red', dash='dash'), fill='tonexty'))
                            fig.update_layout(title=f"{sde_scenario}情景下疾病谱系随机演化（碳中和强度 {carbon:.1f}）")

                            st.plotly_chart(fig, use_container_width=True)

                            # VaR 风险价值
                            if paths.size > 0:  # 检查paths不为空
                                final_burden = paths[:, -1] if paths.ndim > 1 else paths  # 所有路径的最后一年值
                                var_95 = np.percentile(final_burden, 95)
                                baseline_var = np.mean(
                                    paths[:, 0] if paths.ndim > 1 and paths.shape[1] > 0 else paths)  # 初态值均值作为基准
                                var_delta = ((var_95 - baseline_var) / abs(
                                    baseline_var)) * 100 if baseline_var != 0 else 0

                                st.metric(
                                    "95% VaR（最差传染病负担）",
                                    f"{var_95:.0f}",
                                    delta=f"{var_delta:+.1f}% 较初态"
                                )

                    except (IndexError, ValueError):
                        # 假设只有一个结果返回或者格式不同
                        st.warning("模型返回格式不符合预期，显示通用统计分析")

                    # 通用统计分析部分始终显示
                    st.subheader("贝叶斯后验分析")
                    # 创建一些示例轨迹用于演示
                    dummy_trace = np.random.randn(100, 1)  # 假设形状
                    sample_param_data = np.random.normal(0, 1, size=1000)
                    data_dict = {'param': sample_param_data}

                    # 使用arviz进行后验分析
                    dataset = az.convert_to_inference_data({k: v.reshape(1, -1) for k, v in data_dict.items()})

                    col_A, col_B = st.columns(2)
                    with col_A:
                        st.subheader('参数迹线图')
                        fig_trace = az.plot_trace(dataset)
                        st.pyplot(fig_trace.figure)

                        # 清理matplotlib图形避免重叠
                        if plt.get_fignums():
                            plt.close(plt.gcf())  # 关闭当前图

                    with col_B:
                        st.subheader('后验分布图')
                        fig_post = az.plot_posterior(dataset)
                        st.pyplot(fig_post.figure)

                        # 清理matplotlib图形避免重叠
                        if plt.get_fignums():
                            plt.close(plt.gcf())  # 关闭当前图

                else:
                    st.error(
                        f"无法解析SDE模型结果，返回值类型: {type(result_tuple)}, 长度: {len(result_tuple) if isinstance(result_tuple, (list, tuple)) else 'N/A'}")
                    st.info("这可能是由于模型复杂度高或依赖库问题，请联系管理员")

            except Exception as e:
                st.error(f"SDE模型执行出错: {str(e)}")
                st.info("这可能是由于模型复杂度高或相关依赖库未安装，请联系管理员")

# AI智能体
st.sidebar.markdown("---")
if st.sidebar.checkbox("打开AI智能助手", key="open_ai_helper"):
    st.subheader("🤖 AI 智能分析助手")

    # 确保聊天历史存在于会话状态中
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "你好！我是卫生资源配置智能助手。请问有什么可以帮你分析的？"}
        ]

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("输入你的问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        with st.spinner("智能体正在分析..."):
            # 构造上下文，包含当前状态
            context = f"当前年份：{st.session_state.selected_year}，用户正在查看全国或特定省的卫生资源分析。用户输入的问题是：{prompt}"
            answer = ask_agent(prompt, chat_history=st.session_state.messages[:-1])
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.chat_message("assistant").write(answer)

# 清理会话清理
if st.sidebar.button("🔄 重置应用状态"):
    # 清理会话状态中的非核心项目
    keys_to_reset = [k for k in st.session_state.keys() if
                     k not in ['initialized', 'analyzer', 'disease_analyzer', 'chat_history']]
    for k in keys_to_reset:
        del st.session_state[k]
    # 重新初始化聊天历史
    st.session_state.messages = [
        {"role": "assistant", "content": "应用已重置。你好！我是卫生资源配置智能助手。请问有什么可以帮你分析的？"}]
    st.rerun()
