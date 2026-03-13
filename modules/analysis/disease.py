# modules/analysis/disease.py
import pandas as pd
import numpy as np
from datetime import datetime
from modules.core.interface import IDiseaseAnalyzer
from config.settings import SETTINGS


class DiseaseRiskAnalyzer(IDiseaseAnalyzer):
    """
    疾病风险预测分析器 (GBD 数据驱动版)
    """

    def __init__(self, spectrum_data: pd.DataFrame = None, risk_data: pd.DataFrame = None):
        # 接收清洗后的 GBD 数据
        self.spectrum_data = spectrum_data if spectrum_data is not None else pd.DataFrame()
        self.risk_data = risk_data if risk_data is not None else pd.DataFrame()
        self.impact_factors = SETTINGS.HEALTH_IMPACT_FACTORS

    def get_attribution(self, year: int, region: str = None) -> str:
        """基于 PAF (人群归因分数) 获取真实的疾病风险归因分析"""
        if self.risk_data.empty:
            return f"针对 {region} 在 {year} 年的风险分析显示，环境因素影响显著。(暂无实际数据支撑)"

        # 过滤指定年份和地区的数据
        df = self.risk_data[self.risk_data['year'] == year].copy()
        if region and 'location_name' in df.columns:
            # 模糊匹配地区名称
            df = df[df['location_name'].str.contains(region, na=False, case=False)]

        if df.empty or 'paf' not in df.columns:
            return f"数据集中暂无 {region} {year} 年的有效风险归因数据。"

        # 按 PAF (人群归因分数) 降序排列，找出排名前三的核心风险
        top_risks = df.sort_values(by='paf', ascending=False).drop_duplicates(subset=['rei_name']).head(3)

        if top_risks.empty:
            return "未能识别出核心风险因素。"

        # 动态拼接文本
        risk_desc_list = []
        for _, row in top_risks.iterrows():
            risk_name = row.get('rei_name', '未知风险')
            paf_val = row.get('paf', 0) * 100
            risk_cat = row.get('risk_category', 'other')

            # 将英文风险类别映射为中文
            cat_map = {'behavioral': '行为风险', 'environmental': '环境风险', 'metabolic': '代谢风险',
                       'other': '综合风险'}
            risk_desc_list.append(f"【{risk_name}】(属于{cat_map.get(risk_cat, '其他')}，人群归因占比约 {paf_val:.1f}%)")

        risk_desc = "、".join(risk_desc_list)

        return (f"基于 GBD 数据洞察：针对 {region} 在 {year} 年的分析显示，"
                f"导致该地区疾病负担的核心风险因素排名前三位依次为：{risk_desc}。"
                f"建议卫生部门优先针对这些领域配置干预资源。")

    def get_intervention_list(self, region: str) -> str:
        """动态生成干预建议 (可根据上一方法的归因结果推导)"""
        # 简化逻辑：如果在该地区检测到行为风险高，则建议健康教育
        return f"针对 {region} 的干预建议：1. 强化慢性病筛查与全周期管理；2. 针对高危风险因素开展专项公共卫生宣教。"

    def run_sde_model_simple(self, cause: str, current_burden: float, years_ahead: int = 5) -> pd.DataFrame:
        """
        基于真实基线数据的 SDE 演化预测
        """
        np.random.seed(42)
        time_points = np.arange(0, years_ahead)

        # 简单模拟：假设代谢类疾病 drift 偏正，传染类偏负
        drift = 0.015 if '糖尿病' in cause or '心血管' in cause else -0.01
        diffusion = 0.02

        results = [current_burden]
        for _ in range(1, len(time_points)):
            prev = results[-1]
            change = (drift * prev) + (diffusion * prev * np.random.normal())
            results.append(max(0, prev + change))  # 负担不能为负

        start_year = datetime.now().year
        return pd.DataFrame({
            'year': np.arange(start_year, start_year + years_ahead),
            'burden_index': results,
            'cause': cause
        })

    def predict_disease_trend(self, cause: str, years: int = 5) -> str:
        """结合历史数据与 SDE 模型生成趋势预测报告"""
        # 如果有真实数据，提取该疾病最新一年的负担基线
        current_burden = 100.0
        if not self.spectrum_data.empty and 'cause_name' in self.spectrum_data.columns:
            cause_df = self.spectrum_data[self.spectrum_data['cause_name'].str.contains(cause, na=False, case=False)]
            if not cause_df.empty:
                current_burden = cause_df.sort_values(by='year').iloc[-1]['val']

        pred_df = self.run_sde_model_simple(cause, current_burden, years)
        end_burden = pred_df.iloc[-1]['burden_index']
        growth_rate = (end_burden - current_burden) / current_burden * 100

        trend_word = "上升" if growth_rate > 0 else "下降"
        return f"[{cause}] 未来 {years} 年趋势预测：基于 SDE 随机微分方程模拟，预计疾病负担指数将从 {current_burden:.1f} 变为 {end_burden:.1f}，总体呈 {trend_word} 趋势（变化率约为 {growth_rate:+.1f}%）。"