from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import matplotlib.pyplot as plt
import os
from modules.health_analyzer import HealthResourceAnalyzer
from disease_analyzer import DiseaseAnalyzer

def generate_pdf_report(year: int, province: str = None):
    analyzer = HealthResourceAnalyzer("cleaned_health_data.xlsx")
    disease_analyzer = DiseaseAnalyzer()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph(f"全国卫生资源配置优化报告 - {year}年", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 20))

    gap = analyzer.compute_resource_gap(year)
    if province and province in gap.index:
        data = gap.loc[province]
        story.append(Paragraph(f"{province}分析", styles['Heading2']))
        story.append(Paragraph(f"缺口率：{data['相对缺口率']:.1%}（{data['缺口类别']}）", styles['Normal']))
    else:
        story.append(Paragraph("全国整体缺口分析", styles['Heading2']))
        story.append(Paragraph(f"平均缺口率：{gap['相对缺口率'].mean():.1%}", styles['Normal']))

    opt = analyzer.optimize_resource_allocation(year)
    story.append(Paragraph(f"AI优化改善率：{opt.get('optimization_improvement', 0):.1%}", styles['Normal']))

    if hasattr(disease_analyzer, 'get_attribution'):
        attr = disease_analyzer.get_attribution(year, province)
        story.append(Paragraph("主要疾病风险归因", styles['Heading2']))
        story.append(Paragraph(attr, styles['Normal']))

    # 生成图表
    fig, ax = plt.subplots(figsize=(8, 4))
    gap['相对缺口率'].plot(kind='bar', ax=ax, color='skyblue')
    plt.title("各地区相对缺口率")
    plt.xticks(rotation=45)
    chart_path = "temp_chart.png"
    plt.savefig(chart_path, bbox_inches='tight')
    plt.close(fig)  # 释放内存

    story.append(Image(chart_path, width=450, height=220))
    os.remove(chart_path)  # 删除临时文件

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()