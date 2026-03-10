import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db.connection import SessionLocal
from db.models import WHOGlobalHealth


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
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_indicator = st.selectbox(
            "选择OWID指标",
            ["physicians-per-1000-people", "life-expectancy", "health-expenditure-share-of-gdp",
             "share-of-deaths-from-communicable-diseases", "share-of-deaths-from-non-communicable-diseases"],
            format_func=lambda x: {"physicians-per-1000-people": "医生密度(每千人)",
                                   "life-expectancy": "人均预期寿命",
                                   "health-expenditure-share-of-gdp": "卫生支出占GDP%",
                                   "share-of-deaths-from-communicable-diseases": "传疾病死亡占比%",
                                   "share-of-deaths-from-non-communicable-diseases": "非传疾病死亡占比%"
                                   }[x]
        )
    with col2:
        year_s = st.slider("起始年份", 1990, 2020, 2000)
    with col3:
        selected_countries = st.multiselect("选择对比国家", ["China", "United States", "India", "Germany", "Nigeria"],
                                            default=["China", "United States"])

    # 可视化1：OWID风格——多国家指标趋势折线图（OWID最经典的可视化）
    st.subheader("📈 国家间指标趋势对比（OWID风格）")
    df_owid = get_owid_db_data([selected_indicator], year_s, 2020)
    if not df_owid.empty:
        df_filter = df_owid[df_owid["country"].isin(selected_countries)]
        fig_trend = px.line(df_filter, x="year", y="value", color="country",
                            title=f"{{'physicians-per-1000-people':'医生密度(每千人)',
                                  'life-expectancy':'人均预期寿命',
        'health-expenditure-share-of-gdp': '卫生支出占GDP%',
        'share-of-deaths-from-communicable-diseases': '传疾病死亡占比%'
        'share-of-deaths-from-non-communicable-diseases': '非传疾病死亡占比%'
        }[selected_indicator]} 趋势对比
        ",
        color_discrete_map = OWID_COLORS,
        markers = True,  # OWID风格：加数据点
        hover_data = {"value": ":,.2f", "year": ":d"})  # 悬停格式化
        # OWID风格优化：隐藏图例标题、网格线更柔和、字体适配
        fig_trend.update_layout(
            legend_title=None,
            plot_bgcolor="white",
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
            hovermode="x unified"  # OWID风格：x轴统一悬停
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        # 可视化2：OWID风格——全球卫生指标热力图（时空分布，适配疾病谱系/资源分布）
        st.subheader("🌍 全球指标热力图（OWID风格）")
        if st.checkbox("显示全球热力图"):
            df_map = get_owid_db_data([selected_indicator], 2020, 2020)  # 取最新年份
        if not df_map.empty:
            fig_map = px.choropleth(
                df_map,
                locations="code",  # ISO国家代码，适配Plotly地图
                color="value",
                hover_name="country",
                title=f"2020年全球{ {'physicians-per-1000-people': '医生密度(每千人)',
                                     'life-expectancy': '人均预期寿命',
                                     'health-expenditure-share-of-gdp': '卫生支出占GDP%',
                                     'share-of-deaths-from-communicable-diseases': '传疾病死亡占比%',
                                     'share-of-deaths-from-non-communicable-diseases': '非传疾病死亡占比%'
                                     }[selected_indicator]} 分布",
                color_continuous_scale=px.colors.sequential.Blues,  # OWID经典蓝调配色
                projection="natural earth"  # OWID地图投影方式
            )
        fig_map.update_layout(plot_bgcolor="white")
        st.plotly_chart(fig_map, use_container_width=True)

        # 可视化3：OWID风格——堆叠面积图（全球疾病谱系变迁，适配你的核心研究维度）
        st.subheader("📊 全球疾病谱系时空变迁（OWID风格）")
        if st.checkbox("显示疾病谱系堆叠面积图"):
            df_disease = get_owid_db_data(["share-of-deaths-from-communicable-diseases",
        "share-of-deaths-from-non-communicable-diseases"], 1990, 2020)
        if not df_disease.empty:
        # 聚合全球数据（OWID的全球平均逻辑）
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

# 原有WHO数据对比：保留，可作为补充
st.markdown("---")
st.subheader("📋 传统WHO国际数据对比")
if st.checkbox("开启 WHO 国际数据对比"):
# 原有代码完全保留，无需修改
    db = SessionLocal()
try:
    query_res = db.query(WHOGlobalHealth).filter(WHOGlobalHealth.year == 2020).all()
    if not query_res:
        st.info("💡 本地库中暂无 WHO 数据。请先拉取OWID数据，或通过 AI 助手搜索添加。")
    else:
        who_data = pd.DataFrame([
            {"国家代码": item.country_code, "指标名称": item.indicator_name, "数值": item.value, "年份": item.year}
            for item in query_res
        ])
        col1, col2 = st.columns([1, 2])
        with col1:
            st.write("📋 WHO/OWID 指标数据预览")
            st.dataframe(who_data, use_container_width=True)
        with col2:
            fig = px.bar(who_data, x="国家代码", y="数值", color="国家代码",
                         title="WHO/OWID 核心卫生指标国际对比 (2020)", labels={"数值": "指标值"})
            st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"查询数据时出错: {e}")
finally:
    db.close()

st.info("🧐 对OWID数据感兴趣？在左侧 AI 助手输入：'拉取日本2010-2020年的医疗支出数据'")

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