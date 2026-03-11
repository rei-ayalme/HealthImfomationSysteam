# pages/data_visualization_with_loading.py
import streamlit as st
import pandas as pd
import plotly.express as px
import time
import numpy as np
from db.connection import SessionLocal
from db.models import GlobalHealthMetric


# ====================== 1. 自定义加载动画CSS（独立封装） ======================
def init_loading_css():
    """初始化加载动画样式（独立页面专用）"""
    st.markdown("""
        <style>
        /* 全局Spinner样式：医疗主题配色 */
        div[data-testid="stSpinner"] > div {
            border-top-color: #2a9d8f !important; /* 医疗绿 */
            border-right-color: #2a9d8f !important;
            border-bottom-color: transparent !important;
            border-left-color: transparent !important;
            width: 2rem !important;
            height: 2rem !important;
        }

        /* DataFrame骨架屏：加载占位动画 */
        .df-skeleton {
            width: 100%;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 16px;
            border: 1px solid #e9ecef;
        }
        .skeleton-row {
            display: flex;
            margin-bottom: 8px;
            animation: pulse 1.5s infinite ease-in-out;
        }
        .skeleton-cell {
            height: 24px;
            background: #e9ecef;
            border-radius: 4px;
            margin-right: 8px;
            flex: 1;
        }
        .skeleton-cell.short { flex: 0.2; }
        .skeleton-cell.medium { flex: 0.5; }

        /* Plotly图表淡入动画 */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        div[data-testid="stPlotlyChart"] {
            animation: fadeIn 0.8s ease-out;
        }

        /* 页面整体样式优化 */
        .main-header { color: #264653; border-bottom: 2px solid #2a9d8f; padding-bottom: 10px; }
        .stDataFrame { border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        </style>

        <!-- DataFrame骨架屏模板 -->
        <div class="df-skeleton" id="df-skeleton-template" style="display: none;">
            <div class="skeleton-row">
                <div class="skeleton-cell short"></div>
                <div class="skeleton-cell medium"></div>
                <div class="skeleton-cell"></div>
                <div class="skeleton-cell short"></div>
            </div>
            <div class="skeleton-row">
                <div class="skeleton-cell short"></div>
                <div class="skeleton-cell medium"></div>
                <div class="skeleton-cell"></div>
                <div class="skeleton-cell short"></div>
            </div>
            <div class="skeleton-row">
                <div class="skeleton-cell short"></div>
                <div class="skeleton-cell medium"></div>
                <div class="skeleton-cell"></div>
                <div class="skeleton-cell short"></div>
            </div>
            <div class="skeleton-row">
                <div class="skeleton-cell short"></div>
                <div class="skeleton-cell medium"></div>
                <div class="skeleton-cell"></div>
                <div class="skeleton-cell short"></div>
            </div>
            <div class="skeleton-row">
                <div class="skeleton-cell short"></div>
                <div class="skeleton-cell medium"></div>
                <div class="skeleton-cell"></div>
                <div class="skeleton-cell short"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# ====================== 2. 数据加载逻辑（独立封装） ======================
def load_health_resource_data() -> pd.DataFrame:
    """加载卫生资源数据（模拟/真实数据库读取）"""
    # 模拟数据加载延迟（实际项目可删除，保留真实数据库查询）
    time.sleep(2)

    # 真实场景：从数据库读取标准化数据
    db = SessionLocal()
    try:
        # 查询数据库中的卫生资源数据
        metrics = db.query(GlobalHealthMetric).limit(100).all()
        df = pd.DataFrame([{
            "地区": m.region,
            "指标": m.indicator,
            "数值": m.value,
            "年份": m.year
        } for m in metrics])

        # 无数据库数据时返回模拟数据
        if df.empty:
            df = pd.DataFrame({
                "地区": ["北京市", "上海市", "广东省", "江苏省", "浙江省"] * 4,
                "指标": ["医生密度", "护士密度", "病床数", "卫生支出占比"] * 5,
                "数值": np.random.uniform(1.2, 8.5, 20),
                "年份": [2020] * 5 + [2021] * 5 + [2022] * 5 + [2023] * 5
            })
        return df
    finally:
        db.close()


def create_health_inx_chart(df: pd.DataFrame) -> px.bar:
    """生成卫生资源对比px.bar图表"""
    # 筛选2023年数据做可视化
    time.sleep(1.5)  # 模拟加载延迟
    df_inx = df[df["年份"] == 2023].groupby("指标")["数值"].sum().reset_index()
    df_bar=df_inx
    df_pie = df_inx


    # 构建Plotly柱状图
    fig = px.bar(
        df_bar,
        x="地区",
        y="数值",
        color="指标",
        title="2023年各地区卫生资源配置对比",
        color_discrete_map={
            "医生密度": "#2a9d8f",
            "护士密度": "#e9c46a",
            "病床数": "#f4a261",
            "卫生支出占比": "#e76f51"
        },
        template="plotly_white",
        hover_data={"数值": ":,.2f"}
    )

    fig = px.pie(
        df_pie,
        values="数值",
        names="指标",
        title="2023年卫生资源类型占比",
        color_discrete_map={
            "医生密度": "#2a9d8f",
            "护士密度": "#e9c46a",
            "病床数": "#f4a261",
            "卫生支出占比": "#e76f51"
        },
        hole=0.3  # 环形图更美观
    )

    # 优化图表样式
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        title_x=0.5,
        title_font={"size": 18, "color": "#264653"},
        xaxis_title="地区",
        yaxis_title="数值（标准化）",
        legend_title="资源指标"
    )
    return fig


# ====================== 3. 页面核心逻辑（加载动画+可视化） ======================
def show():
    """独立页面入口函数"""
    # 页面基础配置
    st.set_page_config(
        page_title="数据可视化（带加载动画）",
        layout="wide",
        page_icon="📊"
    )

    # 初始化加载动画样式
    init_loading_css()

    # 页面标题
    st.title("📊 卫生资源数据可视化（带加载动画）", anchor=False)
    st.markdown('<div class="main-header"></div>', unsafe_allow_html=True)
    st.markdown("---")

    # ========== 第一部分：px.bar图表加载动画 ==========
    st.subheader("🧮 地区卫生资源配置对比（px.bar）", anchor=False)

    # 1. 显示Spinner加载提示
    with st.spinner("🔄 正在加载柱状图数据..."):
        # 2. 加载数据并生成图表
        health_df = load_health_resource_data()
        bar_chart = create_health_inx_chart(health_df)
        pie_chart = create_health_inx_chart(health_df)
    # 3. 渲染图表（自动触发淡入动画）
    st.plotly_chart(bar_chart, use_container_width=True)

    st.markdown("---")

    # ========== 第二部分：st.dataframe骨架屏加载动画 ==========
    st.subheader("📋 标准化卫生资源数据表（st.dataframe）", anchor=False)

    # 1. 创建空占位符（用于切换骨架屏/真实表格）
    df_placeholder = st.empty()

    # 2. 先渲染骨架屏（加载中状态）
    df_placeholder.markdown("""
        <div id="df-skeleton-container">
            <div class="df-skeleton">
                <div class="skeleton-row">
                    <div class="skeleton-cell short"></div>
                    <div class="skeleton-cell medium"></div>
                    <div class="skeleton-cell"></div>
                    <div class="skeleton-cell short"></div>
                </div>
                <div class="skeleton-row">
                    <div class="skeleton-cell short"></div>
                    <div class="skeleton-cell medium"></div>
                    <div class="skeleton-cell"></div>
                    <div class="skeleton-cell short"></div>
                </div>
                <div class="skeleton-row">
                    <div class="skeleton-cell short"></div>
                    <div class="skeleton-cell medium"></div>
                    <div class="skeleton-cell"></div>
                    <div class="skeleton-cell short"></div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 3. 模拟数据加载延迟（实际项目删除）
    with st.spinner("🔄 正在加载表格数据..."):
        time.sleep(1.5)

    # 4. 替换骨架屏为真实DataFrame
    df_placeholder.dataframe(
        health_df,
        use_container_width=True,
        column_config={
            "地区": st.column_config.TextColumn("地区", width="small"),
            "指标": st.column_config.SelectboxColumn("资源指标", width="medium"),
            "数值": st.column_config.NumberColumn("数值", format="%.2f", width="small"),
            "年份": st.column_config.NumberColumn("统计年份", width="small")
        },
        hide_index=True
    )

    # ========== 数据概览（可选） ==========
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📈 数据总行数", len(health_df))
    with col2:
        st.metric("🌍 覆盖地区数", health_df["地区"].nunique())
    with col3:
        st.metric("📅 覆盖年份数", health_df["年份"].nunique())


# 页面入口
if __name__ == "__main__":
    show()