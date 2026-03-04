from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from unified_interface import get_unified_analyzer  # 修改点 1：使用统一接口
from disease_analyzer import DiseaseAnalyzer
import pandas as pd
import os
from settings import CLEANED_DATA_FILE

os.environ.setdefault("OPENAI_API_KEY", "your-key-here")

# 尽量导入，但允许部分功能不可用
try:
    from gtts import gTTS

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("⚠️ gTTS 未安装，语音功能将返回文本提示")


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
            'zh': "🔬 贝叶修 SIR 分析结果\n方法：",
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
        # 处理关键词参数
        try:
            return msg_template.format(**kwargs)
        except KeyError:
            return msg_template


def get_analyzer():
    if os.path.exists(CLEANED_DATA_FILE):
        return get_unified_analyzer(CLEANED_DATA_FILE)
    return None


@tool
def get_optimization_suggestion(year: int, objective: str = 'maximize_health'):
    """
    针对特定目标（最大化健康产出或最小化不平等）提供资源优化分配建议。
    objective 可选值: 'maximize_health', 'minimize_inequality'
    """
    analyzer = get_analyzer()
    if not analyzer:
        return "数据分析器未就绪。"

    result = analyzer.optimize_resource_allocation(year, objective=objective)
    return result

@tool
def analyze_resource_gap(year: int):
    """
    计算指定年份全国各省份的医疗资源缺口。
    返回包含缺口率和严重程度分类的数据。
    """
    analyzer = get_analyzer()
    if not analyzer:
        return "错误：未找到处理后的数据文件，请先运行预处理。"

    try:
        gap_data = analyzer.compute_resource_gap(year)
        # 转换为易于 AI 阅读的格式
        summary = gap_data.reset_index().to_dict(orient='records')
        return summary
    except Exception as e:
        return f"分析失败: {str(e)}

@tool
def generate_interactive_chart(year: int, chart_type: str = "gap_bar") -> str:
    """自动生成交互式 Plotly 图表（返回完整 HTML - 多语言支持）"""
    analyzer = get_analyzer()
    gap = analyzer.compute_resource_gap(year)

    if chart_type == "gap_bar":
        fig = px.bar(gap.reset_index(), x='地区', y='相对缺口率',
                     color='缺口类别',
                     title=f"[{year} Provincial Healthcare Resource Gap Rate]",  # 英文标题
                     labels={'相对缺口率': 'Gap Rate', '地区': 'Province'})  # 英文标签
    elif chart_type == "supply_demand":
        fig = px.bar(gap.reset_index(), x='地区', y=['实际供给指数', '理论需求指数'],
                     barmode='group', title=f"[Supply vs Demand Index {year}]")  # 英文标题
    else:
        # choropleth图需要特定的数据格式
        df_to_plot = gap.reset_index()
        if '地区' in df_to_plot.columns:
            fig = px.choropleth(df_to_plot, locations='地区', color='相对缺口率',
                                title=f"[National Gap Heatmap {year}]",  # 英文标题
                                locationmode='USA-states')
        else:
            # 如果没有地区列，使用柱状图作为备选
            fig = px.bar(df_to_plot, x=df_to_plot.index, y='相对缺口率',
                         title=f"[Provincial Gap Heatmap {year}]")  # 英文标题

    fig.update_layout(height=600)
    html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    # 双语标题内容
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
    filename = f"HealthData_{year}_{timestamp}.xlsx"  # 使用英文文件名
    df.to_excel(filename)
    records_count = len(df)
    if province:
        return f"✅ Excel Exported: {filename} (Region: {province}, Records: {records_count})\n✅ 已导出：{filename}（省份：{province}，记录数：{records_count}）"
    else:
        return f"✅ Excel Exported: {filename} (Records: {records_count})\n✅ 已导出：{filename}（记录数：{records_count}）"


@tool
def speak_key_findings(year: int, province: str = None) -> str:
    """语音播报关键结论（生成 mp3 文件 - 支持双语文本）"""
    analyzer = get_analyzer()
    gap = analyzer.compute_resource_gap(year)

    if province and province in gap.index:
        row = gap.loc[province]
        zh_text = f"{province} {year}年，资源缺口率 {row['相对缺口率']:.1%}，属于 {row['缺口类别']} 省份。"
        en_text = f"For {province} in {year}, gap ratio is {row['相对缺口率']:.1%}, classified as {row['缺口类别']} province."
    else:
        avg = gap['相对缺口率'].mean()
        shortage = len(gap[gap['缺口类别'] == '短缺'])
        zh_text = f"{year}年全国平均缺口率 {avg:.1%}，共有 {shortage} 个省份处于短缺状态。建议优先向短缺省份调配资源。"
        en_text = f"In {year}, national average gap ratio is {avg:.1%}, with {shortage} provinces in shortage. Suggest prioritize resource allocation to these provinces."

    combined_text = f"{en_text}\n{zh_text}"

    if TTS_AVAILABLE:
        # 使用合并的文本生成语音（优先中文，兼容性好）
        tts = gTTS(text=zh_text, lang='zh', slow=False)
        audio_file = f"Findings_{year}.mp3"
        tts.save(audio_file)
        return f"🎤 Audio Generated: {audio_file}\n{combined_text}"
    else:
        return f"🎤 [Audio Mode] \n{combined_text}\n（Install gTTS to generate real audio）"


@tool
def analyze_spatial_spillover(province: str, year: int) -> str:
    """地理空间分析：邻近省份资源溢出效应 - 多语言输出"""
    analyzer = get_analyzer()
    gap = analyzer.compute_resource_gap(year)

    # 中国省级行政区邻接关系表
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
    zh_title = f"-calendar {year}年 {frequency} 高频数据"
    message = f"""{en_title}\n{zh_title}
Current health statistics bulletin provides annual data ONLY.
Future integration will provide monthly/quarterly panel data with this tool for finest time-series prediction.
Current suggestion is to use annual data for strategic planning."""
    return message


@tool
def get_resource_gap(year: int) -> str:
    """分析并获取指定年份医疗资源缺口情况 - 改进双语版本"""
    analyzer = get_analyzer()
    df = analyzer.compute_resource_gap(year)
    avg_gap = df['相对缺口率'].mean() if '相对缺口率' in df.columns else 0

    # 双语头
    en_header = f"[{year} National Healthcare Resource Gap]"
    zh_header = f"【{year}年全国资源缺口】"
    table_str = df[['实际供给指数', '理论需求指数', '相对缺口率', '缺口类别']].to_string()
    avg_str = f"Average gap rate: {avg_gap:.1%}"

    return f"""{zh_header}
{table_str}

{en_header}
{avg_str}"""


@tool
def optimize_allocation(year: int, objective: str = "maximize_health", budget_ratio: float = 0.3) -> str:
    """优化资源分配 - 多语言输出"""
    analyzer = get_analyzer()

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
        # 如果优化过程出错，提供默认反馈
        return f"❌ Optimization Error: {str(e)}\n❌ 优化过程遇到问题: {str(e)}"


@tool
def predict_future(years_ahead: int = 5, scenario: str = "基准") -> str:
    """未来医疗资源需求预测 - 多语言输出"""
    analyzer = get_analyzer()
    try:
        df = analyzer.predict_future(years_ahead, scenario)
        zh_pred = f"""未来预测（{scenario}情景）:
{df.head(10).to_string()}"""
        en_pred = f"""Future Prediction ({scenario} Scenario):
{df.head(10).to_string()}"""
        return f"{zh_pred}\n\n{en_pred}"""
    except Exception as e:
        return f"Prediction Error: {str(e)}\n预测出现错误：{str(e)}"


@tool
def get_province_report(province: str, year: int) -> str:
    """获取某省份某年的详细报告 - 多语言输出"""
    analyzer = get_analyzer()
    gap = analyzer.compute_resource_gap(year)
    row = gap.loc[province] if province in gap.index else None

    # 双语头
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
        filename = f"Report_{year}{'_' + province if province else ''}.pdf"  # 使用英文文件名
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
    da = DiseaseAnalyzer()
    try:
        attribution = da.get_attribution(year, province)
        interventions = da.get_intervention_list(province)
        result = attribution + "\n\n" + interventions

        # 添加英文概要
        en_summary = f"\n\n[Disease Attribution Analysis for {province if province else 'China'}, Year {year}]"
        return result + en_summary
    except Exception as e:
        return f"Disease Attribution Error: {str(e)}\n疾病归因分析失败：{str(e)}"


@tool
def predict_disease(cause: str = "Cardiovascular diseases", years: int = 5) -> str:
    """疾病趋势预测 - 支持双语关键词"""
    da = DiseaseAnalyzer()
    try:
        result = str(da.predict_disease_trend(cause, years))
        return f"""Disease Trend Prediction for '{cause}' over {years} years:\n\n{result}

疾病趋势预测（'{cause}'持续{years}年）：\n\n{result}"""
    except Exception as e:
        return f"Disease Prediction Error: {str(e)}\n疾病预测失败：{str(e)}"


@tool
def deep_analyzer_api(query: str) -> str:
    """预留 DeepAnalyzer API 接口（未来可对接外部高级分析）- 双语输出"""
    # TODO: 这里调用您的 DeepAnalyzer API
    en_msg = f"[DeepAnalyzer API Placeholder] Received Query: {query} (Interface Reserved)"
    zh_msg = f"[DeepAnalyzer API 占位] 收到查询: {query}（已预留接口）"
    return f"{en_msg}\n{zh_msg}"


@tool
def web_search(query: str) -> str:
    """使用网络搜索获取最新的医疗健康相关信息 - 双语查询支持"""
    try:
        search_tool = DuckDuckGoSearchRun()
        results = search_tool.run(query)

        # 尝试检测是否包含英语关键词
        query_lower = query.lower()
        contains_en_keywords = any(
            keyword in query_lower for keyword in ["coronavirus", "covid", "medical", "health", "data"])
        if contains_en_keywords:
            return f"""English Search Query: {query}
Search Results:
{results}"""
        else:
            return f"""中文搜索引擎查询: {query}
搜索结果:
{results}"""
    except Exception as e:
        en_error = f"Web Search Failed: {str(e)}. Try another query or retry later."
        zh_error = f"网络搜索失败：{str(e)}。请尝试其他查询或稍后再试。"
        return f"{en_error}\n{zh_error}"


# 工具列表
tools = [
    get_resource_gap,
    optimize_allocation,
    predict_future,
    get_province_report,
    generate_pdf,
    disease_attribution,
    predict_disease,
    deep_analyzer_api,
    generate_interactive_chart,
    export_data_to_excel,
    speak_key_findings,
    analyze_spatial_spillover,
    get_high_frequency_data,
    bayesian_disease_analysis,
    web_search,
]

llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),  # 请在终端执行：export DEEPSEEK_API_KEY=sk-xxx
    temperature=0.3
)


# 更新系统提示以支持更好的多语言处理
def detect_language_preference(user_input: str) -> str:
    """检测用户输入的语言偏向"""
    en_keywords = ["en", "english", "rate", "gap", "chart", "analysis", "data"]
    lower_input = user_input.lower()
    en_count = sum(1 for word in en_keywords if word in lower_input)
    return 'en' if en_count > 2 else 'zh'


class HealthResourceAgent:
    def __init__(self):
        # 推荐使用 gpt-4o-mini 或更高版本
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.tools = [analyze_resource_gap, get_optimization_suggestion]

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的中国卫生健康资源配置专家。
            你可以通过工具获取各省份的资源缺口数据和优化建议。

            回复准则：
            1. 始终提供客观的数据支持。
            2. 使用中文回答，除非用户要求英文。
            3. 如果缺口率超过 20%，请标记为“严重警示”。"""),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        self.executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)

    def ask(self, user_input: str, chat_history: list = None):
        return self.executor.invoke({
            "input": user_input,
            "chat_history": chat_history or []
        })["output"]


def ask_agent(question: str, chat_history: list = None):
    agent = HealthResourceAgent()
    return agent.ask(question, chat_history)
