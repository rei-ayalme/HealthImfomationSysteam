import streamlit as st
from modules.report_generator import generate_pdf_report

st.title("📄 报告管理中心")

year = st.number_input("报告年份", value=2020)
province = st.text_input("指定省份 (可选)")

if st.button("生成 PDF 分析报告"):
    try:
        pdf_bytes = generate_pdf_report(year, province if province else None)
        st.download_button("📥 下载报告", pdf_bytes, file_name=f"Health_Report_{year}.pdf")
    except Exception as e:
        st.error(f"报告生成失败: {e}")