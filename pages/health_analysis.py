import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
import json
from streamlit_folium import st_folium
from db.connection import SessionLocal
from db.models import WHOGlobalHealth
from db.models import DeepSeekAnalysisResult
from modules.agent.client import deepseek_analyze

# === 配置：导入城市规划与空间分析模块 ===
try:
    from modules.spatial.urban_accessibility import SpatialAccessibilityModel
    from modules.spatial.layout_optimizer import LayoutAndFairnessOptimizer
except ImportError:
    st.error("请确保已在 modules/spatial/ 目录下创建了 urban_accessibility.py 和 layout_optimizer.py")

OWID_COLORS = {
    "China": "#e63946",
    "United States": "#457b9d",
    "India": "#fca311",
    "Germany": "#1d3557",
    "Nigeria": "#2a9d8f",
    "World": "#707070",
    "communicable": "#ff6b6b",
    "non-communicable": "#4ecdc4"
}


# 获取OWID入库数据的封装函数
def get_owid_db_data(indicator_names: list, year_start: int = 1990, year_end: int = 2020):
    db = SessionLocal()
    try:
        query = db.query(WHOGlobalHealth).filter(
            WHOGlobalHealth.indicator_name.in_(indicator_names),
            WHOGlobalHealth.year.between(year_start, year_end)
        )
        df = pd.DataFrame([{
            "country": item.country_name,
            "code": item.country_code,
            "year": item.year,
            "indicator": item.indicator_name,
            "value": item.value
        } for item in query.all()])
        return df
    except Exception as e:
        st.error(f"获取OWID数据失败：{e}")
        return pd.DataFrame()
    finally:
        db.close()


def show():
    st.header("🔍 卫生资源缺口分析")

    analyzer = st.session_state.get('analyzer')
    if not analyzer:
        st.warning("⚠️ 未检测到有效数据，请先前往『数据管理』页面。")
        st.stop()

    available_years = sorted(getattr(analyzer, 'years', [2020]), reverse=True)
    selected_year = st.selectbox("选择分析年份", available_years)

    # 计算缺口数据 (你原有的基础数据)
    gap_data = analyzer.compute_resource_gap(selected_year)

    # === 关键改动：使用选项卡将“常规宏观分析”与“城市空间规划”解耦 ===
    tab1, tab2, tab3 = st.tabs([
        "📊 宏观资源评估 (常规)",
        "🗺️ 空间可达性地图 (规划视角)",
        "🎯 智能选址与公平性 (优化)"
    ])

    # ==========================================
    # Tab 1: 完全保留你原有的全部宏观数据与API调用逻辑
    # ==========================================
    with tab1:
        # 展示核心指标
        c1, c2, c3 = st.columns(3)
        c1.metric("全国平均缺口率", f"{gap_data['相对缺口率'].mean():.1%}" if not gap_data.empty else "N/A")
        c2.metric("严重短缺省份", len(gap_data[gap_data['相对缺口率'] > 0.2]) if not gap_data.empty else 0)

        # 交互式柱状图
        if not gap_data.empty:
            fig = px.bar(gap_data.reset_index(), x='地区', y='相对缺口率', color='缺口类别',
                         title=f"{selected_year}年各省份资源缺口分布")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("🌐 WHO 国际卫生指标对比")
        col1, col2, col3 = st.columns(3)

        indicator_map = {
            "physicians-per-1000-people": "医生密度(每千人)",
            "life-expectancy": "人均预期寿命",
            "health-expenditure-share-of-gdp": "卫生支出占GDP%",
            "share-of-deaths-from-communicable-diseases": "传疾病死亡占比%",
            "share-of-deaths-from-non-communicable-diseases": "非传疾病死亡占比%"
        }

        with col1:
            selected_indicator = st.selectbox(
                "选择OWID指标",
                list(indicator_map.keys()),
                format_func=lambda x: indicator_map[x]
            )
        with col2:
            year_s = st.slider("起始年份", 1990, 2020, 2000)
        with col3:
            selected_countries = st.multiselect("选择对比国家",
                                                ["China", "United States", "India", "Germany", "Nigeria"],
                                                default=["China", "United States"])

        # 可视化1：OWID风格——多国家指标趋势折线图
        st.subheader("📈 国家间指标趋势对比（OWID风格）")
        df_owid = get_owid_db_data([selected_indicator], year_s, 2020)
        if not df_owid.empty:
            df_filter = df_owid[df_owid["country"].isin(selected_countries)]
            title_str = f"{indicator_map[selected_indicator]} 趋势对比"

            fig_trend = px.line(df_filter, x="year", y="value", color="country",
                                title=title_str,
                                color_discrete_map=OWID_COLORS,
                                markers=True,
                                hover_data={"value": ":,.2f", "year": ":d"})
            fig_trend.update_layout(
                legend_title=None,
                plot_bgcolor="white",
                xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
                yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
                hovermode="x unified"
            )
            st.plotly_chart(fig_trend, use_container_width=True)

            # 可视化2：OWID风格——全球卫生指标热力图
            st.subheader("🌍 全球指标热力图（OWID风格）")
            if st.checkbox("显示全球热力图"):
                df_map = get_owid_db_data([selected_indicator], 2020, 2020)
                if not df_map.empty:
                    fig_map = px.choropleth(
                        df_map,
                        locations="code",
                        color="value",
                        hover_name="country",
                        title=f"2020年全球 {indicator_map[selected_indicator]} 分布",
                        color_continuous_scale=px.colors.sequential.Blues,
                        projection="natural earth"
                    )
                    fig_map.update_layout(plot_bgcolor="white")
                    st.plotly_chart(fig_map, use_container_width=True)

            # 可视化3：OWID风格——堆叠面积图
            st.subheader("📊 全球疾病谱系时空变迁（OWID风格）")
            if st.checkbox("显示疾病谱系堆叠面积图"):
                df_disease = get_owid_db_data([
                    "share-of-deaths-from-communicable-diseases",
                    "share-of-deaths-from-non-communicable-diseases"
                ], 1990, 2020)
                if not df_disease.empty:
                    df_world = df_disease[df_disease["country"] == "World"].pivot(index="year", columns="indicator",
                                                                                  values="value")
                    df_world = df_world.reset_index()
                    fig_stack = go.Figure(data=[
                        go.Scatter(x=df_world["year"], y=df_world["share-of-deaths-from-communicable-diseases"],
                                   name="传染性疾病", stackgroup="one", color=OWID_COLORS["communicable"]),
                        go.Scatter(x=df_world["year"], y=df_world["share-of-deaths-from-non-communicable-diseases"],
                                   name="非传染性疾病", stackgroup="one", color=OWID_COLORS["non-communicable"])
                    ])
                    fig_stack.update_layout(
                        title="1990-2020全球死亡疾病谱系变迁（OWID全球数据）",
                        yaxis_title="死亡占比（%）",
                        plot_bgcolor="white",
                        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
                        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig_stack, use_container_width=True)

        st.markdown("---")
        st.subheader("🧠 DeepSeek 卫生资源配置优化（基于OWID全球数据）")
        st.markdown("**分析逻辑**：OWID提供卫生资源+疾病负担数据 → DeepSeek计算最优资源分配方案")

        col1, col2 = st.columns(2)
        with col1:
            opt_countries = st.multiselect("选择优化国家", ["China", "India", "Nigeria", "Brazil"],
                                           default=["China", "India"])
        with col2:
            opt_year = st.number_input("分析年份", min_value=2015, max_value=2020, value=2020)

        opt_indicators = ["physicians-per-1000-people", "share-of-deaths-from-non-communicable-diseases"]

        if st.button("🚀 运行DeepSeek资源配置优化", type="primary"):
            with st.spinner("🔄 正在调用DeepSeek做资源优化计算..."):
                try:
                    # 注意：确保 deepseek_analyze 函数在你的环境中可用
                    ds_opt_result = deepseek_analyze(
                        indicator_ids=opt_indicators,
                        countries=opt_countries,
                        start_year=opt_year,
                        end_year=opt_year,
                        task_type="resource_allocation",
                        output_format="dict"
                    )
                    if ds_opt_result.get("status") == "success":
                        st.success("✅ DeepSeek资源配置优化完成！")

                        # 数据入库 (如无对应Model可先注释此处)
                        db = SessionLocal()
                        db.add(DeepSeekAnalysisResult(
                             task_type="resource_allocation",
                             indicator_ids=",".join(opt_indicators),
                             countries=",".join(opt_countries),
                             time_range=f"{opt_year}-{opt_year}",
                             analysis_result=ds_opt_result["result"],
                             metadata=ds_opt_result["metadata"]
                         ))
                        db.commit()
                        db.close()

                        st.subheader("📊 卫生资源最优配置方案（DeepSeek）")
                        df_opt = pd.DataFrame([
                                                  {"country": c, "type": "现有资源", "value": v["current"]}
                                                  for c, v in ds_opt_result["result"]["resource_optimization"].items()
                                              ] + [
                                                  {"country": c, "type": "最优资源", "value": v["optimal"]}
                                                  for c, v in ds_opt_result["result"]["resource_optimization"].items()
                                              ])
                        fig_opt = px.bar(
                            df_opt, x="country", y="value", color="type", barmode="group",
                            title=f"{opt_year}年医生密度最优配置对比（每千人）",
                            color_discrete_map={"现有资源": "#fca311", "最优资源": "#2a9d8f"},
                            hover_data={"value": ":,.2f"}
                        )
                        fig_opt.update_layout(plot_bgcolor="white", yaxis_title="医生密度（每千人）")
                        st.plotly_chart(fig_opt, use_container_width=True)
                        st.info(f"💡 DeepSeek优化建议：{ds_opt_result['result']['optimization_suggestion']}")
                    else:
                        st.error(f"❌ 优化失败：{ds_opt_result.get('msg', '未知错误')}")
                except NameError:
                    st.error("未找到 deepseek_analyze 函数，请确保已经正确导入该 AI 辅助函数。")
                except Exception as e:
                    st.error(f"分析出错: {str(e)}")

        st.markdown("---")
        st.subheader("📋 传统WHO国际数据对比")
        if st.checkbox("开启 WHO 国际数据对比"):
            db = SessionLocal()
            try:
                query_res = db.query(WHOGlobalHealth).filter(WHOGlobalHealth.year == 2020).all()
                if not query_res:
                    st.info("💡 本地库中暂无 WHO 数据。请确保已运行同步脚本，或通过 AI 助手搜索添加。")
                else:
                    who_data = pd.DataFrame([
                        {"国家代码": item.country_code, "指标名称": item.indicator_name, "数值": item.value,
                         "年份": item.year}
                        for item in query_res
                    ])
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.write("📋 WHO 指标数据预览")
                        st.dataframe(who_data, use_container_width=True)
                    with col2:
                        fig = px.bar(who_data, x="国家代码", y="数值", color="国家代码",
                                     title="WHO 核心卫生指标国际对比 (2020)", labels={"数值": "指标值"})
                        st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"查询数据时出错: {e}")
            finally:
                db.close()

        st.info("🧐 对数据感兴趣？在左侧 AI 助手输入：'搜索并添加 [国家] [年份] 的人均医疗支出数据'")

    # ==========================================
    # Tab 2: 城市医疗空间盲区识别（融合汤君友、刘承承多模式等时圈理论）
    # ==========================================
    with tab2:
        st.subheader("📍 城市医疗空间盲区识别 (高斯衰减 2SFCA)")
        st.markdown("基于 **多模式两步移动搜索法(2SFCA)** 与 **引力模型**，测算不同区域到医疗设施的真实阻抗可达性。")

        if not gap_data.empty:
            import os

            spatial_df = gap_data.copy().reset_index()
            # 兼容列名
            if '地区' in spatial_df.columns:
                spatial_df['region_name'] = spatial_df['地区']
            else:
                spatial_df['region_name'] = [f"网格_{i}" for i in range(len(spatial_df))]

            # ---------------------------------------------------------
            # ⭐ 核心修改点：读取真实的 CSV 坐标数据并进行合并
            # ---------------------------------------------------------
            coords_path = "data/全国省会经纬坐标.csv"
            if os.path.exists(coords_path):
                coords_df = pd.read_csv(coords_path)

                # 写一个清洗函数，去掉“省/市/自治区”后缀，保证年鉴的“北京”能和CSV的“北京市”成功匹配
                def clean_name(name):
                    if not isinstance(name, str): return ""
                    return name.replace('省', '').replace('市', '').replace('维吾尔', '').replace('回族', '').replace(
                        '壮族', '').replace('自治区', '')

                coords_df['match_key'] = coords_df['省份'].apply(clean_name)
                spatial_df['match_key'] = spatial_df['region_name'].apply(clean_name)

                # 关联经纬度
                spatial_df = pd.merge(spatial_df, coords_df[['match_key', '经度', '纬度']], on='match_key', how='left')
                spatial_df['longitude'] = spatial_df['经度'].fillna(116.4)  # 匹配失败的兜底：北京经度
                spatial_df['latitude'] = spatial_df['纬度'].fillna(39.9)  # 匹配失败的兜底：北京纬度
            else:
                st.warning(f"未找到真实坐标文件 {coords_path}，使用模拟坐标。")
                spatial_df['longitude'] = np.random.uniform(116.1, 116.6, len(spatial_df))
                spatial_df['latitude'] = np.random.uniform(39.7, 40.1, len(spatial_df))

            # 老龄化率目前由于没有入库，暂时保留随机模拟（以测试算法弱势群体权重）
            spatial_df['elderly_ratio'] = np.random.uniform(0.05, 0.35, len(spatial_df))

            # 准备算法需要的字段
            spatial_df['population'] = spatial_df.get('population', np.random.randint(2000, 10000, len(spatial_df)))
            spatial_df['physicians'] = spatial_df.get('actual_supply_index', 10) * 10
            spatial_df['beds'] = spatial_df.get('actual_supply_index', 10) * 50

            demand_df = spatial_df[['longitude', 'latitude', 'population', 'elderly_ratio', 'region_name']]
            facility_df = spatial_df[['longitude', 'latitude', 'physicians', 'beds', 'region_name']].rename(
                columns={'region_name': 'hospital_name'})

            try:
                # 运行空间模型
                spatial_model = SpatialAccessibilityModel(demand_df, facility_df)
                result_df = spatial_model.compute_enhanced_2sfca(threshold_dist=5.0)  # 大约8-10km阈值

                # 渲染 folium 热力地图
                center_lat, center_lon = 35.86, 104.19
                m = folium.Map(location=[center_lat, center_lon], zoom_start=4, tiles="CartoDB positron")

                from config.settings import SETTINGS
                geojson_path = os.path.join(SETTINGS.BASE_DIR, SETTINGS.GEOJSON_PATH_CHINA)
                if not os.path.exists(geojson_path):
                    # 回退到我们已知的存在文件
                    geojson_path = os.path.join(SETTINGS.BASE_DIR, "data", "geojson", "中华人民共和国.geojson")
                    
                with open(geojson_path, "r", encoding="utf-8") as f:
                    geo_data = json.load(f)

                # 将边界添加到地图上
                folium.GeoJson(
                    geo_data,
                    name="中国边界",
                    style_function=lambda feature: {
                        'fillColor': '#ffffff',  # 填充颜色
                        'color': '#666666',  # 边界线颜色
                        'weight': 1,  # 边界线粗细
                        'fillOpacity': 0.1  # 填充透明度
                    }
                ).add_to(m)

                for _, row in result_df.iterrows():
                    access_score = row.get('enhanced_2sfca_index', 0)

                    # 动态颜色：按分数赋红黄绿
                    if access_score < result_df['enhanced_2sfca_index'].quantile(0.33):
                        color = "red"
                    elif access_score < result_df['enhanced_2sfca_index'].quantile(0.66):
                        color = "orange"
                    else:
                        color = "green"

                    folium.CircleMarker(
                        location=[row['latitude'], row['longitude']],
                        radius=max(5, row['population'] / 1000),  # 气泡大小反映人口基数
                        color=color, fill=True, fill_opacity=0.7,
                        tooltip=f"<b>区域：</b>{row['region_name']}<br><b>老龄化率：</b>{row['elderly_ratio']:.1%}<br><b>空间可及性指数：</b>{access_score:.4f}"
                    ).add_to(m)

                st_folium(m, width=800, height=500)
                st.caption(
                    "🔴 **红色警示**：代表弱势群体密集且跨省医疗资源空间辐射极弱的区域；🟢 **绿色代表**：资源可达性良好。")
            except Exception as e:
                st.error(f"渲染空间地图失败: {str(e)}\n请检查是否已正确创建 modules/spatial 模块。")
            else:
                st.info("暂无数据可供进行空间映射分析。")

    # ==========================================
    # Tab 3: 设施选址优化与机会公平补偿（融合马超、刘承承选址模型）
    # ==========================================
    with tab3:
        st.subheader("🎯 机会不平等分解与 P-median 靶向选址")
        st.markdown("通过空间基尼系数分解医疗资源配置的**环境不公**，并利用选址算法自动输出新建资源点的最佳坐标储备库。")

        if not gap_data.empty and 'result_df' in locals():
            try:
                optimizer = LayoutAndFairnessOptimizer(result_df)

                col1, col2 = st.columns([1, 1.2])
                with col1:
                    fairness_res = optimizer.decompose_opportunity_inequality()
                    st.metric("空间分配基尼系数 (Gini)", fairness_res.get("gini_coefficient", "N/A"))
                    st.caption(
                        f"环境因素(如户籍/地域交通)不平等贡献率: **{fairness_res.get('opportunity_contribution', 'N/A')}**")
                    st.info(fairness_res.get("insight", "计算中..."))

                with col2:
                    st.markdown("**🤖 AI 靶向选址推荐 (Top 2 急需干预网格)**")
                    new_locations = optimizer.recommend_new_locations(max_new=2)
                    # 格式化展示数据
                    display_df = new_locations[
                        ['region_name', 'longitude', 'latitude', 'population', 'elderly_ratio']].copy()
                    display_df['elderly_ratio'] = display_df['elderly_ratio'].apply(lambda x: f"{x:.1%}")
                    display_df.rename(columns={'region_name': '建议选址区域', 'population': '覆盖人口',
                                               'elderly_ratio': '老龄化水平'}, inplace=True)

                    st.dataframe(display_df, use_container_width=True)
                    st.success(
                        "🎯 **规划建议**：已优先锚定老龄化严重、可达性极低的底端区域作为下一年度医疗设施扩建的储备点。")
            except Exception as e:
                st.error(f"优化器运行失败: {str(e)}")
        else:
            st.info("需要先计算基础数据才能进行选址优化。")