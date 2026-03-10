import os
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.express as px
from dotenv import load_dotenv
from langchain.tools import tool
from db.connection import SessionLocal
from db.models import WHOGlobalHealth
from modules.data_cleaner import HealthDataCleaner
from utils.helpers import parse_text_to_df

load_dotenv()


try:
    from langchain_openai import ChatOpenAI
    from langchain.agents import create_tool_calling_agent, AgentExecutor
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.tools import tool
except ImportError as e:
    print(f"⚠️ LangChain 核心组件导入失败: {e}")



    def tool(func):
        return func

    class AgentExecutor:
        def __init__(self, *args, **kwargs): pass
        def invoke(self, *args, **kwargs):
            return {"output": "Agent 引擎未就绪，请检查 langchain 安装或版本。"}

    class ChatPromptTemplate:
        @classmethod
        def from_messages(cls, *args, **kwargs): return None

    def create_tool_calling_agent(*args, **kwargs):
        return None




try:
    from modules.unified_interface import get_unified_analyzer
    from modules.disease_analyzer import DiseaseAnalyzer
    from config.settings import CLEANED_DATA_FILE
except ImportError as e:
    print(f"⚠️ 内部业务模块导入失败: {e}")

    # 定义 get_unified_analyzer 的占位函数
    def get_unified_analyzer(*args, **kwargs):
        return None

    # 定义 DiseaseAnalyzer 的占位类
    class DiseaseAnalyzer:
        def get_attribution(self, *args, **kwargs): return "分析不可用"

        def get_intervention_list(self, *args, **kwargs): return "建议不可用"


    CLEANED_DATA_FILE = "data/processed/cleaned_health_data.xlsx"


# --- ADDED MISSING IMPORT FOR WEB SEARCH ---
try:
    from langchain_community.tools import DuckDuckGoSearchRun
    search_tool = DuckDuckGoSearchRun()
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False
    class DuckDuckGoSearchRun:
        def run(self, *args, **kwargs):
            return "网络搜索功能不可用，请安装 duckduckgo-search 库。"
    search_tool = DuckDuckGoSearchRun()
    print("⚠️ duckduckgo-search 未安装，网络搜索功能不可用")

def get_analyzer():
    """获取数据分析器实例"""
    if os.path.exists(CLEANED_DATA_FILE):
        return get_unified_analyzer(CLEANED_DATA_FILE)
    return None


class MultilingualManager:
    """多语言资源管理器"""
    TRANSLATIONS = {
        'resource_gap_summary': {
            'zh': "【{year}年全国资源缺口】",
            'en': "[{year} National Healthcare Resource Gap]",
        },
        'average_gap_rate': {
            'zh': "平均缺口率: ",
            'en': "Average gap rate: ",
        },
        'province_report': {
            'zh': "【{province} {year}年报告】",
            'en': "[Report for {province}, {year}]",
        },
        'opti_success': {
            'zh': "✅ 优化成功！改善率 ",
            'en': "✅ Optimization successful! Improvement rate ",
        },
        'choropleth_map': {
            'zh': "{year}年 全国缺口热力图",
            'en': "National Gap Heatmap {year}",
        },
        'interactive_viz': {
            'zh': "📊 {year}年交互式可视化",
            'en': "📊 {year} Interactive Visualization",
        },
        'chart_supply_demand': {
            'zh': "{year}年 供给 vs 需求指数",
            'en': "Supply vs Demand Index {year}",
        },
        'bayesian_result': {
            'zh': "🔬 贝叶斯 SIR 分析结果\n方法：",
            'en': "🔬 Bayesian SIR Analysis Result\nMethod: ",
        },
        'high_freq_data': {
            'zh': "📅 {year}年 {frequency} 高频数据",
            'en': "📅 {year} {frequency} High-Frequency Data",
        },
        'resource_gap_year': {
            'zh': "【{year}年全国资源缺口】",
            'en': "[{year} National Resource Gap]",
        }
    }

    @classmethod
    def get_message(cls, key: str, lang: str = 'zh', **kwargs):
        """获取翻译后的消息"""
        msg_template = cls.TRANSLATIONS.get(key, {}).get(lang, '')
        try:
            return msg_template.format(**kwargs)
        except KeyError:
            return msg_template


def get_analyzer():
    """获取数据分析器实例"""
    if os.path.exists(CLEANED_DATA_FILE):
        return get_unified_analyzer(CLEANED_DATA_FILE)
    return None


# --- CONSOLIDATED AND FIXED TOOLS ---

@tool
def optimize_allocation(year: int, objective: str = "maximize_health", budget_ratio: float = 0.3) -> str:
    """优化资源分配 - 多语言输出"""
    analyzer = get_analyzer()
    if not analyzer:
        return "错误：未找到处理后的数据文件，请先运行预处理。"

    try:
        result = analyzer.optimize_resource_allocation(year, objective, budget_ratio)
        if result['success']:
            top_allocations = result['allocation'].sort_values(ascending=False).head(3)
            zh_msg = f"✅ 优化成功！改善率 {result['optimization_improvement']:.1%}\n新分配方案前3名：\n{top_allocations.to_string()}"
            en_msg = f"✅ Optimization Successful! Improvement rate {result['optimization_improvement']:.1%}\nTop 3 Allocation Plans:\n{top_allocations.to_string()}"
        else:
            zh_msg = result['message']
            en_msg = f"Optimization Error: {result['message']}"
        return f"{zh_msg}\n\n{en_msg}"
    except Exception as e:
        return f"❌ Optimization Error: {str(e)}\n❌ 优化过程遇到问题: {str(e)}"


@tool
def get_global_health_data(country: str, year: int) -> str:
    """查询全球卫生数据。优先从本地库查询，无数据则提示。"""
    db = SessionLocal()
    # 简单的本地库查询
    res = db.query(WHOGlobalHealth).filter(
        WHOGlobalHealth.country_code == country,
        WHOGlobalHealth.year == year
    ).first()
    db.close()

    if res:
        return f"本地库记录：{country} 在 {year} 年的指标值为 {res.value}"
    else:
        return f"本地库暂无 {country} {year} 年数据，请尝试使用搜索工具获取。"

@tool
def analyze_resource_gap(year: int) -> str:
    """
    计算指定年份全国各省份的医疗资源缺口。
    返回包含缺口率和严重程度分类的格式化字符串。
    """
    analyzer = get_analyzer()
    if not analyzer:
        return "错误：未找到处理后的数据文件，请先运行预处理。"

    try:
        gap_data = analyzer.compute_resource_gap(year)
        avg_gap = gap_data['相对缺口率'].mean()
        return f"【{year}年分析】全国平均缺口率: {avg_gap:.1%}"
    except Exception as e:
        return f"分析失败: {str(e)}"


@tool
def generate_interactive_chart(year: int, chart_type: str = "gap_bar") -> str:
    """自动生成交互式 Plotly 图表（返回完整 HTML - 多语言支持）"""
    analyzer = get_analyzer()
    gap = analyzer.compute_resource_gap(year)

    if chart_type == "gap_bar":
        fig = px.bar(gap.reset_index(), x='地区', y='相对缺口率',
                     color='缺口类别',
                     title=f"[{year} Provincial Healthcare Resource Gap Rate]",
                     labels={'相对缺口率': 'Gap Rate', '地区': 'Province'})
    elif chart_type == "supply_demand":
        fig = px.bar(gap.reset_index(), x='地区', y=['实际供给指数', '理论需求指数'],
                     barmode='group', title=f"[Supply vs Demand Index {year}]")
    else:
        df_to_plot = gap.reset_index()
        if '地区' in df_to_plot.columns:
            fig = px.choropleth(df_to_plot, locations='地区', color='相对缺口率',
                                title=f"[National Gap Heatmap {year}]",
                                locationmode='USA-states')
        else:
            fig = px.bar(df_to_plot, x=df_to_plot.index, y='相对缺口率',
                         title=f"[Provincial Gap Heatmap {year}]")

    fig.update_layout(height=600)
    html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    zh_title = f"📊 {year}年交互式可视化"
    en_title = f"📊 {year} Interactive Visualization"
    return f"""<h3>{zh_title}<br/>{en_title}</h3>{html}"""


@tool
def export_data_to_excel(year: int, province: str = None) -> str:
    """导出 Excel 数据表（支持全国/单省 - 多语言提示）"""
    analyzer = get_analyzer()
    gap = analyzer.compute_resource_gap(year)

    if province and province in gap.index:
        df = gap.loc[[province]]
    else:
        df = gap

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"HealthData_{year}_{timestamp}.xlsx"
    df.to_excel(filename)
    records_count = len(df)
    if province:
        return f"✅ Excel Exported: {filename} (Region: {province}, Records: {records_count})\n✅ 已导出：{filename}（省份：{province}，记录数：{records_count}）"
    else:
        return f"✅ Excel Exported: {filename} (Records: {records_count})\n✅ 已导出：{filename}（记录数：{records_count}）"



@tool
def analyze_spatial_spillover(province: str, year: int) -> str:
    """地理空间分析：邻近省份资源溢出效应 - 多语言输出"""
    analyzer = get_analyzer()
    gap = analyzer.compute_resource_gap(year)

    neighbors = {
        '北京市': ['天津市', '河北省'],
        '天津市': ['北京市', '河北省'],
        '上海市': ['江苏省', '浙江省'],
        '重庆市': ['四川省', '贵州省', '湖北省', '湖南省', '陕西省'],
        '河北省': ['北京市', '天津市', '山西省', '内蒙古自治区', '辽宁省', '山东省'],
        '山西省': ['河北省', '内蒙古自治区', '陕西省', '河南省'],
        '辽宁省': ['河北省', '内蒙古自治区', '吉林省'],
        '吉林省': ['辽宁省', '内蒙古自治区', '黑龙江省'],
        '黑龙江省': ['吉林省', '内蒙古自治区'],
        '江苏省': ['上海市', '安徽省', '山东省', '浙江省'],
        '浙江省': ['上海市', '江苏省', '安徽省', '福建省', '江西省'],
        '安徽省': ['江苏省', '浙江省', '江西省', '湖北省', '河南省', '山东省'],
        '福建省': ['浙江省', '江西省', '广东省', '台湾省（隔海）'],
        '江西省': ['安徽省', '浙江省', '福建省', '广东省', '湖南省', '湖北省'],
        '山东省': ['河北省', '江苏省', '安徽省', '河南省'],
        '河南省': ['河北省', '山西省', '陕西省', '湖北省', '安徽省', '山东省'],
        '湖北省': ['河南省', '陕西省', '重庆市', '湖南省', '江西省', '安徽省'],
        '湖南省': ['湖北省', '重庆市', '贵州省', '广西壮族自治区', '广东省', '江西省'],
        '广东省': ['湖南省', '江西省', '福建省', '广西壮族自治区', '香港特别行政区', '澳门特别行政区'],
        '海南省': ['广东省（隔海）'],
        '四川省': ['重庆市', '贵州省', '云南省', '西藏自治区', '青海省', '甘肃省', '陕西省'],
        '贵州省': ['重庆市', '四川省', '云南省', '广西壮族自治区', '湖南省'],
        '云南省': ['四川省', '贵州省', '广西壮族自治区', '西藏自治区'],
        '陕西省': ['山西省', '内蒙古自治区', '宁夏回族自治区', '甘肃省', '四川省', '重庆市', '河南省', '湖北省'],
        '甘肃省': ['内蒙古自治区', '宁夏回族自治区', '陕西省', '四川省', '青海省', '新疆维吾尔自治区'],
        '青海省': ['甘肃省', '四川省', '西藏自治区', '新疆维尔自治区'],
        '台湾省': ['福建省（隔海）'],
        '内蒙古自治区': ['黑龙江省', '吉林省', '辽宁省', '河北省', '山西省', '陕西省', '宁夏回族自治区', '甘肃省'],
        '广西壮族自治区': ['云南省', '贵州省', '湖南省', '广东省'],
        '西藏自治区': ['四川省', '云南省', '青海省', '新疆维吾尔自治区'],
        '宁夏回族自治区': ['内蒙古自治区', '甘肃省', '陕西省'],
        '新疆维吾尔自治区': ['甘肃省', '青海省', '西藏自治区'],
        '香港特别行政区': ['广东省'],
        '澳门特别行政区': ['广东省']
    }

    if province not in neighbors:
        return f"No neighbor data available for {province}\n暂无 {province} 的邻接数据"

    neigh_list = neighbors[province]
    available_neighbors = [n for n in neigh_list if n in gap.index]
    spillover = gap.loc[available_neighbors]['相对缺口率'].mean() if available_neighbors else 0

    own_gap = gap.loc[province]['相对缺口率'] if province in gap.index else 0
    effect = "Positive Spillover (Can Leverage)" if spillover > own_gap * 0.8 else "Negative Pressure"

    return f"""🗺️ Spatial Spillover Analysis for {province} in {year} 🗺️
Neighbor Average Gap Rate: {spillover:.1%}
Own Gap Rate: {own_gap:.1%}
Spillover Effect: {effect}
Recommendation: Strengthen resource sharing mechanisms with neighboring provinces

🗺️ {province} {year}年空间溢出分析 🗺️
邻省平均缺口率：{spillover:.1%}
本省缺口率：{own_gap:.1%}
溢出效应：{effect}
建议：加强与邻省的资源共享机制"""


@tool
def bayesian_disease_analysis(province: str = None, years_obs: int = 5) -> str:
    """贝叶斯参数估计 + 不确定性量化 - 多语言输出"""
    try:
        da = DiseaseAnalyzer()
        result = da.bayesian_calibrate_sir(province, years_obs)
        return f"""🔬 Bayesian SIR Analysis Result 🔬
Method: {result['method']}
R₀ Posterior Mean: {result['R0_mean']:.2f}

🔬 贝叶斯 SIR 分析结果 🔬
方法：{result['method']}
R₀ 后验均值：{result['R0_mean']:.2f}
{result['message']}"""
    except Exception as e:
        return f"Bayesian Analysis Error: {str(e)}\n贝叶斯分析出现错误：{str(e)}"


@tool
def get_high_frequency_data(year: int, frequency: str = "quarterly") -> str:
    """季度/月度高频数据接口（当前数据为年度，未来可无缝升级）- 多语言输出"""
    en_title = f"📅 {year} {frequency} High-Frequency Data"
    zh_title = f"📅 {year}年 {frequency} 高频数据"
    message = f"""{en_title}\n{zh_title}
Current health statistics bulletin provides annual data ONLY.
Future integration will provide monthly/quarterly panel data with this tool for finest time-series prediction.
Current suggestion is to use annual data for strategic planning."""
    return message


@tool
def predict_future(years_ahead: int = 5, scenario: str = "基准") -> str:
    """未来医疗资源需求预测 - 多语言输出"""
    analyzer = get_analyzer()
    if not analyzer: return "错误：未找到数据文件。"
    try:
        df = analyzer.predict_future(years_ahead, scenario)
        return f"未来{years_ahead}年预测 ({scenario}情景):\n{df.head().to_string()}"
    except Exception as e:
        return f"预测失败: {str(e)}"

@tool
def get_province_report(province: str, year: int) -> str:
    """获取某省份某年的详细报告 - 多语言输出"""
    analyzer = get_analyzer()
    gap = analyzer.compute_resource_gap(year)
    row = gap.loc[province] if province in gap.index else None

    en_header = f"[Report for {province}, {year}]"
    zh_header = f"【{province} {year}年报告】"
    if row is not None:
        content = row.to_dict()
        report = f"{zh_header}\n{content}\n\n{en_header}\n{content}"
    else:
        report = f"{zh_header}\nNo data available\n\n{en_header}\n无数据"

    return report


@tool
def generate_pdf(year: int, province: str = None) -> str:
    """生成PDF报告 - 多语言输出"""
    try:
        from report_generator import generate_pdf_report
        pdf_bytes = generate_pdf_report(year, province)
        filename = f"Report_{year}{'_' + province if province else ''}.pdf"
        with open(filename, "wb") as f:
            f.write(pdf_bytes)
        if province:
            return f"✅ PDF Report Generated: {filename} (Region: {province})\n✅ PDF报告已生成：{filename}（省份：{province}）"
        else:
            return f"✅ PDF Report Generated: {filename}\n✅ PDF报告已生成：{filename}"
    except ImportError:
        return "⚠️ Report Generator Module Not Found\n⚠️ report_generator 模块未找到，请确保已安装相应依赖。"
    except Exception as e:
        return f"PDF Generation Failed: {str(e)}\nPDF生成失败：{str(e)}"


@tool
def disease_attribution(year: int, province: str = None) -> str:
    """疾病归因分析 - 双语增强"""
    try:
        da = DiseaseAnalyzer()
        attribution = da.get_attribution(year, province)
        interventions = da.get_intervention_list(province)
        result = attribution + "\n\n" + interventions

        en_summary = f"\n\n[Disease Attribution Analysis for {province if province else 'China'}, Year {year}]"
        return result + en_summary
    except Exception as e:
        return f"Disease Attribution Error: {str(e)}\n疾病归因分析失败：{str(e)}"


@tool
def predict_disease(cause: str = "Cardiovascular diseases", years: int = 5) -> str:
    """疾病趋势预测 - 支持双语关键词"""
    try:
        da = DiseaseAnalyzer()
        result = str(da.predict_disease_trend(cause, years))
        return f"""Disease Trend Prediction for '{cause}' over {years} years:\n\n{result}

疾病趋势预测（'{cause}'持续{years}年）：\n\n{result}"""
    except Exception as e:
        return f"Disease Prediction Error: {str(e)}\n疾病预测失败：{str(e)}"


@tool
def process_searched_data(raw_search_content: str):
    """处理搜索引擎返回的杂乱文本数据并标准化"""
    df = parse_text_to_df(raw_search_content)

    if df.empty:
        return "未能从搜索结果中提取到结构化数据。"

    cleaner = HealthDataCleaner()
    df = cleaner.handle_missing_values(df)
    mapping = {"国家": "country_code", "年份": "year", "数值": "value"}
    df = cleaner.standardize_indicators(df, mapping)
    df = cleaner.calculate_core_metrics(df)

    return df.to_dict(orient='records')

@tool
def deep_analyzer_api(query: str) -> str:
    """预留 DeepAnalyzer API 接口（未来可对接外部高级分析）- 双语输出"""
    en_msg = f"[DeepAnalyzer API Placeholder] Received Query: {query} (Interface Reserved)"
    zh_msg = f"[DeepAnalyzer API 占位] 收到查询: {query}（已预留接口）"
    return f"{en_msg}\n{zh_msg}"


@tool
def web_search(query: str) -> str:
    """使用网络搜索获取最新的医疗健康相关信息 - 双语查询支持"""
    if not SEARCH_AVAILABLE:
        return "Web Search Unavailable. Please install duckduckgo-search.\n网络搜索不可用，请安装 duckduckgo-search。"
    try:
        results = search_tool.run(query)

        query_lower = query.lower()
        contains_en_keywords = any(
            keyword in query_lower for keyword in ["coronavirus", "covid", "medical", "health", "data"])
        if contains_en_keywords:
            return f"""English Search Query: {query}\nSearch Results:\n{results}"""
        else:
            return f"""中文搜索引擎查询: {query}\n搜索结果:\n{results}"""
    except Exception as e:
        en_error = f"Web Search Failed: {str(e)}. Try another query or retry later."
        zh_error = f"网络搜索失败：{str(e)}。请尝试其他查询或稍后再试。"
        return f"{en_error}\n{zh_error}"


@tool
def search_and_save_data(query: str):
    """搜索外部卫生数据并保存到基础平台库中"""
    raw_content = search_tool.run(query)
    # 使用之前定义的解析函数
    df = parse_text_to_df(raw_content)
    clean_df = HealthDataCleaner.quick_clean(df)

    # 存入数据库逻辑...
    return f"已成功从互联网抓取并储存了 {len(clean_df)} 条关于 '{query}' 的新数据。"

# --- AGENT CONFIGURATION ---

# 统一工具列表
ALL_TOOLS = [
    analyze_resource_gap,
    optimize_allocation,
    predict_future,
    get_province_report,
    generate_pdf,
    disease_attribution,
    predict_disease,
    deep_analyzer_api,
    generate_interactive_chart,
    export_data_to_excel,
    analyze_spatial_spillover,
    get_high_frequency_data,
    bayesian_disease_analysis,
    web_search,
    get_global_health_data,
    process_searched_data,
    search_and_save_data
]


def detect_language_preference(user_input: str) -> str:
    """检测用户输入的语言偏向"""
    en_keywords = ["en", "english", "rate", "gap", "chart", "analysis", "data"]
    lower_input = user_input.lower()
    en_count = sum(1 for word in en_keywords if word in lower_input)
    return 'en' if en_count > 2 else 'zh'


class HealthResourceAgent:
    def __init__(self, model_name="gpt-4o-mini"):#记得换模型
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.tools = ALL_TOOLS

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的中国卫生健康资源配置专家。
            你可以通过工具获取各省份的资源缺口数据、优化建议和其他高级分析。

            回复准则：
            1. 始终提供客观的数据支持。
            2. 使用中文回答，除非用户要求英文。
            3. 如果缺口率超过 20%，请标记为“严重警示”。"""),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)

        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True
        )

    def ask(self, user_input: str, chat_history: list = None):
        return self.executor.invoke({
            "input": user_input,
            "chat_history": chat_history or []
        })["output"]


def ask_agent(question: str, chat_history: list = None):
    agent = HealthResourceAgent()
    return agent.ask(question, chat_history)