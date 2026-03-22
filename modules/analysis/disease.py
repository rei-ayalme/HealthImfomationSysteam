# modules/analysis/disease.py
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional
from modules.core.interface import IDiseaseAnalyzer
from config.settings import SETTINGS


class DiseaseRiskAnalyzer(IDiseaseAnalyzer):
    """
    疾病风险预测分析器 (GBD 数据驱动版)
    """

    def __init__(self, spectrum_data: Optional[pd.DataFrame] = None, risk_data: Optional[pd.DataFrame] = None):
        """
        初始化时接收两个 DataFrame
        risk_data: 风险归因数据，必须包含 ['year', 'location_name', 'paf', 'rei_name', 'risk_category']
        spectrum_data: 疾病谱基线数据，必须包含 ['year', 'cause_name', 'val']
        """
        self.spectrum_data = spectrum_data if spectrum_data is not None else pd.DataFrame()
        self.risk_data = risk_data if risk_data is not None else pd.DataFrame()
        self.impact_factors = SETTINGS.HEALTH_IMPACT_FACTORS

    def get_attribution(self, year: int, region: str = None) -> str:
        """基于 PAF (人群归因分数) 获取真实的疾病风险归因分析"""
        # 如果基础数据或风险数据缺失，不应使用硬编码数据兜底
        if self.spectrum_data.empty:
            from utils.logger import log_missing_data
            log_missing_data("DiseaseRiskAnalyzer", "Disease Burden", 2023, "China", "缺少疾病谱系数据")
            return "缺少疾病谱系基线数据，无法生成真实的归因报告。"
            
        if self.risk_data.empty:
            from utils.logger import log_missing_data
            log_missing_data("DiseaseRiskAnalyzer", "Risk Attribution", 2023, "China", "缺少风险归因数据")
            return "缺少风险归因数据，无法分析主要风险因素。"

        df = self.risk_data[self.risk_data['year'] == year].copy()
        if region and 'location_name' in df.columns:
            # 模糊匹配地区名称
            df = df[df['location_name'].str.contains(region, na=False, case=False)]
            
            if df.empty:
                # 尝试不用年份过滤，找最新的
                df = self.risk_data[self.risk_data['location_name'].str.contains(region, na=False, case=False)].copy()
                if not df.empty:
                    latest_year = df['year'].max()
                    df = df[df['year'] == latest_year]
                else:
                    return f"未能找到地区 {region} 的风险归因数据。"

        if df.empty or 'paf' not in df.columns:
            from utils.logger import log_missing_data
            log_missing_data("DiseaseRiskAnalyzer", "Risk Attribution PAF", year, region, "没有 PAF 列或该地区年份数据为空")
            return f"由于缺少足够的疾病负担与 PAF 数据，无法完成对 {region} ({year}年) 的归因分析。"

        # 按 PAF (人群归因分数) 降序排列，找出排名前三的核心风险
        top_risks = df.sort_values(by='paf', ascending=False).drop_duplicates(subset=['rei_name']).head(3)

        if top_risks.empty:
            return f"针对 {region} 在 {year} 年的风险分析显示，缺少显著的人群归因(PAF)数据支持。"

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

    def get_intervention_list(self, region: str = None) -> str:
        """返回基于核心风险的政策干预场景清单 (针对 2024-2044 模拟)"""
        # 获取当前地区的主要风险
        if self.risk_data.empty:
            from utils.logger import log_missing_data
            log_missing_data("DiseaseRiskAnalyzer", "Intervention List", 2024, region or "Global", "无风险数据用于生成干预清单")
            return "缺少风险数据支撑，无法生成干预清单。"
            
        target_df = self.risk_data[self.risk_data['location_name'].str.contains(region, case=False, na=False)].copy()
        if target_df.empty:
            return f"未能找到地区 {region} 的干预推荐数据。"
            
        latest_year = target_df['year'].max()
        df = target_df[target_df['year'] == latest_year]
        
        # 简单模拟成本效益干预匹配
        top_risks = df.sort_values(by='paf', ascending=False).head(3)
        interventions = [f"针对 {region} 的干预建议 (基准年 {latest_year}):"]
        
        for idx, row in top_risks.iterrows():
            risk_name = row.get('rei_name', '未知风险')
            paf_val = row.get('paf', 0)
            
            # 根据风险类别匹配政策场景
            if 'smok' in risk_name.lower():
                interventions.append(f"• [控烟场景A] WHO MPOWER严格措施（提高烟草税等），预计可降低该人群归因负担 {paf_val:.1f}%")
            elif 'particulate' in risk_name.lower() or 'pm2.5' in risk_name.lower():
                interventions.append(f"• [空气治理场景B] 推进 WHO PM2.5 严格目标(5μg/m³)，预估降低归因死亡负担 {paf_val:.1f}%")
            elif 'diet' in risk_name.lower() or 'bmi' in risk_name.lower() or 'pressure' in risk_name.lower() or 'glucose' in risk_name.lower():
                interventions.append(f"• [饮食与代谢场景C] 推广 DASH/地中海饮食模式，强化慢病筛查管理，控制 {paf_val:.1f}% 的归因风险")
            else:
                interventions.append(f"• 针对 {risk_name} 开展专项公共卫生宣教和干预 (贡献度 {paf_val:.1f}%)")
                
        return "\n".join(interventions)

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
        current_burden = 0.0
        if not self.spectrum_data.empty and 'cause_name' in self.spectrum_data.columns:
            cause_df = self.spectrum_data[self.spectrum_data['cause_name'].str.contains(cause, na=False, case=False)]
            if not cause_df.empty:
                current_burden = cause_df.sort_values(by='year').iloc[-1]['val']

        if current_burden == 0.0:
            from utils.logger import log_missing_data
            log_missing_data("DiseaseRiskAnalyzer", f"{cause} Trend", 2024, "Global", "缺少用于趋势预测的历史疾病基线数据")
            return f"缺少 {cause} 的真实历史数据，无法进行 SDE 演化预测。"

        pred_df = self.run_sde_model_simple(cause, current_burden, years)
        end_burden = pred_df.iloc[-1]['burden_index']
        growth_rate = (end_burden - current_burden) / current_burden * 100

        trend_word = "上升" if growth_rate > 0 else "下降"
        return f"[{cause}] 未来 {years} 年趋势预测：基于 SDE 随机微分方程模拟，预计疾病负担指数将从 {current_burden:.1f} 变为 {end_burden:.1f}，总体呈 {trend_word} 趋势（变化率约为 {growth_rate:+.1f}%）。"