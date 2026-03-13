# run_gbd_analysis.py
import pandas as pd
import warnings
import os
from modules.data.gbd_preprocessor import GlobalHealthDataCleaner
from modules.analysis.disease import DiseaseRiskAnalyzer

warnings.filterwarnings('ignore')


def main():
    print("=== 开始 GBD 疾病负担与风险归因洞察 ===")

    # 1. 模拟加载原始数据（在实际中，这里读取你的 GBD CSV 文件）
    # 这里我们构造几条伪造的原始数据来测试清洗管道和分析逻辑是否通畅
    print("\n[1/3] 加载并清洗 GBD 数据...")
    raw_risk_data = pd.DataFrame({
        'Location': ['China', 'China', 'China', 'USA'],
        'Year': [2019, 2019, 2019, 2019],
        'Risk Name': ['Smoking', 'High fasting plasma glucose', 'Ambient particulate matter pollution', 'High BMI'],
        'PAF': [0.15, 0.12, 0.08, 0.20]  # 归因分数
    })

    raw_spectrum_data = pd.DataFrame({
        'Location': ['China', 'China'],
        'Year': [2019, 2019],
        'Cause Name': ['Cardiovascular diseases', 'Neoplasms'],
        'Value': [5000.5, 3200.0]  # DALYs
    })

    raw_data_dict = {
        'disease_spectrum': raw_spectrum_data,
        'risk_attribution': raw_risk_data
    }

    # 2. 调用你设计的清洗器
    cleaner = GlobalHealthDataCleaner()
    cleaned_dict = cleaner.run_cleaning_pipeline(raw_data_dict)
    print("数据清洗与特征工程完成！")

    # 3. 将清洗后的数据喂给疾病分析模块
    print("\n[2/3] 初始化疾病风险分析器...")
    disease_analyzer = DiseaseRiskAnalyzer(
        spectrum_data=cleaned_dict.get('disease_spectrum'),
        risk_data=cleaned_dict.get('risk_attribution')
    )

    # 4. 执行业务分析
    print("\n[3/3] 生成分析洞察报告：")

    # 测试问题 2：归因分析
    attribution_report = disease_analyzer.get_attribution(year=2019, region='China')
    print("-" * 50)
    print("【归因分析结论】")
    print(attribution_report)
    print("-" * 50)

    # 测试问题 1：趋势预测
    trend_report = disease_analyzer.predict_disease_trend(cause='Cardiovascular', years=5)
    print("【趋势预测结论】")
    print(trend_report)
    print("-" * 50)

    print("\n=== 分析流程圆满结束 ===")


if __name__ == "__main__":
    main()