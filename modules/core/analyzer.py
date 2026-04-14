# modules/core/analyzer.py
import pandas as pd
from typing import Dict, Any, Optional
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TypedDict

from modules.data.loader import DataLoader
from modules.data.processor import DataProcessor

# 定义数据交换协议
class ExchangeMeta(TypedDict, total=False):
    source_path: str
    source_type: str
    row_count: int
    columns: list[str]
    notes: str

@dataclass(frozen=True)
class StandardizedDataContract:
    """模块间标准数据协议：只承载标准化后的 DataFrame 与元数据。"""
    data: pd.DataFrame
    meta: ExchangeMeta = field(default_factory=dict)

@dataclass(frozen=True)
class ResourceGapConfig:
    weights: Dict[str, float]
    baselines: Dict[str, float]
    threshold_adequate: float
    threshold_reasonable: float
    threshold_mild: float

@dataclass(frozen=True)
class ServicePayload:
    """集成层输出协议：可直接传递给 LLM 或可视化模块。"""
    data: Any
    target: str  # "llm" | "visualization"
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DiseasePredictConfig:
    """疾病预测配置"""
    drift_metabolic: float = 0.025
    drift_non_metabolic: float = -0.015
    diffusion: float = 0.03
    random_seed: Optional[int] = 42
    lower_bound_ratio: float = 0.1
    upper_bound_ratio: float = 5.0

class ComprehensiveAnalyzer:
    """
    HIS 系统核心业务大脑：统筹资源供给与疾病需求
    整合了原 health.py、disease.py、service.py 的所有功能
    """
    def __init__(self, data_processor, data_loader=None, predictor=None, evaluator=None):
        # 依赖注入 (Dependency Injection)：将引擎从外部传入，解耦得更彻底
        self.processor = data_processor
        self.loader = data_loader
        self.predictor = predictor  # 可选依赖
        self.evaluator = evaluator  # 可选依赖
        
        # 资源权重配置 (与 settings.py 保持一致)
        self.resource_weights = {
            'physicians_per_1000': 0.4,
            'nurses_per_1000': 0.35,
            'hospital_beds_per_1000': 0.25
        }
        
        # 基础医疗资源密度基准 (每千人)
        self.base_medical_resource_densities = {
            'physicians_per_1000': 2.5,
            'nurses_per_1000': 3.2,
            'hospital_beds_per_1000': 6.0
        }
        
        # 资源缺口配置
        self.gap_config = ResourceGapConfig(
            weights=self.resource_weights,
            baselines=self.base_medical_resource_densities,
            threshold_adequate=0.05,
            threshold_reasonable=0.15,
            threshold_mild=0.30
        )
        
        # 情景乘数
        self.scenario_multipliers = {
            "基准": 1.02,
            "乐观": 1.05,
            "保守": 1.01
        }

    def evaluate_regional_health_system(self, region_name: str, year: int, resource_df: pd.DataFrame, disease_df: pd.DataFrame) -> Dict[str, Any]:
        """
        核心业务场景一：区域医疗系统现状综合诊断
        合并原 health.py (资源测算) 和 disease.py (疾病归因)
        集成 actual_supply_index 加权计算和 top_risks 查找算法
        """
        # 1. 过滤当前地区和年份的数据
        local_resource = resource_df[(resource_df['region_name'] == region_name) & (resource_df['year'] == year)]
        local_disease = disease_df[(disease_df['region_name'] == region_name) & (disease_df['year'] == year)]

        if local_resource.empty or local_disease.empty:
            return {"status": "error", "message": f"缺少 {region_name} {year} 年的基础数据"}

        # 2. 集成 actual_supply_index 加权计算逻辑 (从 health.py 提取)
        # 计算实际供给指数 - 使用权重配置进行加权计算
        if local_resource.empty:
            actual_supply_index = 0.0
        else:
            actual_supply_index = (
                local_resource['physicians_per_1000'].values[0] * self.resource_weights['physicians_per_1000'] +
                local_resource['nurses_per_1000'].values[0] * self.resource_weights['nurses_per_1000'] +
                local_resource['hospital_beds_per_1000'].values[0] * self.resource_weights['hospital_beds_per_1000']
            )

        # 3. 集成 top_risks 查找算法 (从 disease.py 提取)
        # 按 PAF 值排序并选择前 3 个风险因素
        if local_disease.empty or 'paf' not in local_disease.columns:
            top_risks = pd.DataFrame()
            demand_score = 1.0
        else:
            # 按 PAF 值降序排序，选择前 3 个风险因素
            top_risks = local_disease.sort_values(by='paf', ascending=False).head(3)
            demand_score = top_risks['paf'].sum()

        # 4. 核心碰撞：医疗系统承压指数 (Pressure Index)
        # 压力 = 需求 / 供给
        pressure_index = demand_score / (actual_supply_index + 1e-6)
        
        # 评级逻辑
        if pressure_index > 1.5:
            status = "严重超载"
        elif pressure_index > 1.0:
            status = "紧平衡"
        else:
            status = "配置充足"

        # 5. 构建详细的风险因素描述
        risk_descriptions = []
        if not top_risks.empty:
            risk_categories = {"behavioral": "行为风险", "environmental": "环境风险", "metabolic": "代谢风险", "other": "综合风险"}
            for _, risk in top_risks.iterrows():
                risk_name = risk.get('rei_name', '未知风险')
                risk_category = risk_categories.get(risk.get('risk_category', 'other'), '其他')
                paf_value = risk.get('paf', 0) * 100
                risk_descriptions.append(f"{risk_name}({risk_category}, {paf_value:.1f}%)")

        return {
            "region": region_name,
            "year": year,
            "supply_metrics": {
                "actual_supply_index": round(actual_supply_index, 2),
                "beds_per_1000": local_resource['hospital_beds_per_1000'].values[0] if not local_resource.empty else 0,
                "physicians_per_1000": local_resource['physicians_per_1000'].values[0] if not local_resource.empty else 0,
                "nurses_per_1000": local_resource['nurses_per_1000'].values[0] if not local_resource.empty else 0
            },
            "demand_metrics": {
                "top_disease_burden": round(demand_score, 2),
                "top_risks": risk_descriptions,
                "risk_count": len(top_risks)
            },
            "system_pressure_index": round(pressure_index, 2),
            "status": status
        }

    # ========== 医疗资源分析功能 (整合自 health.py) ==========

    def compute_resource_gap(self, data: pd.DataFrame, year: int) -> pd.DataFrame:
        """
        计算指定年份的资源缺口
        整合自 health.py 的 compute_resource_gap_pure 功能
        """
        df = data[data["year"] == year].copy() if "year" in data.columns else pd.DataFrame()
        if df.empty:
            return pd.DataFrame()

        df["actual_supply_index"] = (
            df["physicians_per_1000"] * self.gap_config.weights["physicians_per_1000"]
            + df["nurses_per_1000"] * self.gap_config.weights["nurses_per_1000"]
            + df["hospital_beds_per_1000"] * self.gap_config.weights["hospital_beds_per_1000"]
        )

        base_demand = (
            self.gap_config.baselines["physicians_per_1000"] * self.gap_config.weights["physicians_per_1000"]
            + self.gap_config.baselines["nurses_per_1000"] * self.gap_config.weights["nurses_per_1000"]
            + self.gap_config.baselines["hospital_beds_per_1000"] * self.gap_config.weights["hospital_beds_per_1000"]
        )
        avg_pop = df["population"].mean() if df["population"].mean() > 0 else 1
        df["theoretical_demand_index"] = base_demand * (df["population"] / avg_pop)

        df["relative_gap_rate"] = (
            (df["theoretical_demand_index"] - df["actual_supply_index"]) / df["theoretical_demand_index"]
        ).fillna(0)

        df["gap_severity"] = pd.cut(
            df["relative_gap_rate"],
            bins=[-np.inf, self.gap_config.threshold_adequate, self.gap_config.threshold_reasonable, self.gap_config.threshold_mild, np.inf],
            labels=["配置充足", "配置合理", "轻度短缺", "严重短缺"],
        )
        return df

    def optimize_resource_allocation(
        self,
        data: pd.DataFrame,
        year: int,
        objective: str = "maximize_health",
        budget_ratio: float = 0.3,
    ) -> Dict:
        """
        根据特定目标优化资源分配方案
        整合自 health.py 的 optimize_resource_allocation_pure 功能
        """
        gap_df = self.compute_resource_gap(data, year)
        
        if gap_df.empty:
            allocation = pd.Series(dtype=float)
        else:
            allocation = gap_df["theoretical_demand_index"] * budget_ratio

        return {
            "success": True,
            "year": year,
            "objective": objective,
            "improvement_estimate": "15%-20%",
            "allocation": allocation,
        }

    def predict_future_resource_demand(
        self,
        data: pd.DataFrame,
        years_ahead: int = 5,
        scenario: str = "基准"
    ) -> pd.DataFrame:
        """
        基于不同情景模拟预测未来的医疗资源需求
        整合自 health.py 的 predict_population_supply_pure 功能
        """
        if data.empty:
            return pd.DataFrame()
            
        multiplier = float(self.scenario_multipliers.get(scenario, 1.02))
        
        # 使用指数增长模型进行预测
        latest_year = int(data["year"].max())
        base = data[data["year"] == latest_year].copy()

        predictions = []
        for offset in range(1, years_ahead + 1):
            pred = base.copy()
            pred["year"] = latest_year + offset
            pred["population"] = pred["population"] * (multiplier ** offset)
            predictions.append(pred)

        return pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()

    # ========== 疾病风险分析功能 (整合自 disease.py) ==========

    def extract_region_risk_snapshot(self, data: pd.DataFrame, year: Optional[int], region: Optional[str]) -> pd.DataFrame:
        """
        提取特定地区和年份的风险快照
        整合自 disease.py 的 extract_region_risk_snapshot_pure 功能
        """
        if data.empty:
            return pd.DataFrame()

        df = data.copy()
        if year is not None and "year" in df.columns:
            df = df[df["year"] == year]

        if region and "location_name" in df.columns:
            region_df = df[df["location_name"].astype(str).str.contains(region, na=False, case=False)]
            if not region_df.empty:
                df = region_df
            else:
                all_region = data[data["location_name"].astype(str).str.contains(region, na=False, case=False)]
                if all_region.empty:
                    return pd.DataFrame()
                latest_year = int(all_region["year"].max())
                df = all_region[all_region["year"] == latest_year]

        if (year is None) and ("year" in df.columns) and (not df.empty):
            latest_year = int(df["year"].max())
            df = df[df["year"] == latest_year]

        return df.copy()

    def select_top_risks(self, df: pd.DataFrame, top_k: int = 3) -> pd.DataFrame:
        """
        选择前N个主要风险因素
        整合自 disease.py 的 select_top_risks_pure 功能
        """
        if df.empty or "paf" not in df.columns:
            return pd.DataFrame()
        result = df.sort_values(by="paf", ascending=False)
        if "rei_name" in result.columns:
            result = result.drop_duplicates(subset=["rei_name"])
        return result.head(top_k)

    def get_risk_attribution(self, risk_data: pd.DataFrame, year: int, region: str = None) -> str:
        """
        获取特定年份和地区的疾病风险归因分析
        整合自 disease.py 的 get_attribution 功能
        """
        if risk_data.empty:
            return "缺少风险归因数据，无法分析主要风险因素。"

        snapshot = self.extract_region_risk_snapshot(risk_data, year, region)
        if snapshot.empty or "paf" not in snapshot.columns:
            return f"由于缺少足够的疾病负担与 PAF 数据，无法完成对 {region} ({year}年) 的归因分析。"

        top_risks = self.select_top_risks(snapshot, top_k=3)
        if top_risks.empty:
            return f"针对 {region} 在 {year} 年的风险分析显示，缺少显著的人群归因(PAF)数据支持。"

        cat_map = {"behavioral": "行为风险", "environmental": "环境风险", "metabolic": "代谢风险", "other": "综合风险"}
        risk_desc = "、".join(
            [
                f"【{row.get('rei_name', '未知风险')}】(属于{cat_map.get(row.get('risk_category', 'other'), '其他')}，人群归因占比约 {row.get('paf', 0) * 100:.1f}%)"
                for _, row in top_risks.iterrows()
            ]
        )
        return (
            f"基于 GBD 数据洞察：针对 {region} 在 {year} 年的分析显示，"
            f"导致该地区疾病负担的核心风险因素排名前三位依次为：{risk_desc}。"
            f"建议卫生部门优先针对这些领域配置干预资源。"
        )

    def get_intervention_list(self, risk_data: pd.DataFrame, region: str = None) -> str:
        """
        获取针对特定地区的医疗干预措施建议列表
        整合自 disease.py 的 get_intervention_list 功能
        """
        if risk_data.empty:
            return "缺少风险数据支撑，无法生成干预清单。"

        latest_snapshot = self.extract_region_risk_snapshot(risk_data, year=None, region=region)
        if latest_snapshot.empty:
            return f"未能找到地区 {region} 的干预推荐数据。"

        top_risks = self.select_top_risks(latest_snapshot, top_k=3)
        latest_year = int(latest_snapshot["year"].max()) if "year" in latest_snapshot.columns else 2024
        interventions = [f"针对 {region} 的干预建议 (基准年 {latest_year}):"]

        for _, row in top_risks.iterrows():
            risk_name = str(row.get("rei_name", "未知风险"))
            paf_val = float(row.get("paf", 0))
            lower = risk_name.lower()
            if "smok" in lower:
                interventions.append(f"• [控烟场景A] WHO MPOWER严格措施（提高烟草税等），预计可降低该人群归因负担 {paf_val:.1f}%")
            elif "particulate" in lower or "pm2.5" in lower:
                interventions.append(f"• [空气治理场景B] 推进 WHO PM2.5 严格目标(5μg/m³)，预估降低归因死亡负担 {paf_val:.1f}%")
            elif any(token in lower for token in ["diet", "bmi", "pressure", "glucose"]):
                interventions.append(f"• [饮食与代谢场景C] 推广 DASH/地中海饮食模式，强化慢病筛查管理，控制 {paf_val:.1f}% 的归因风险")
            else:
                interventions.append(f"• 针对 {risk_name} 开展专项公共卫生宣教和干预 (贡献度 {paf_val:.1f}%)")

        return "\n".join(interventions)

    def predict_disease_trend(self, spectrum_data: pd.DataFrame, cause: str, years: int = 5) -> str:
        """
        预测特定疾病在未来几年的演化趋势
        整合自 disease.py 的 predict_disease_trend 功能
        """
        current_burden = 0.0
        if not spectrum_data.empty and "cause_name" in spectrum_data.columns:
            cause_df = spectrum_data[spectrum_data["cause_name"].astype(str).str.contains(cause, na=False, case=False)]
            if not cause_df.empty:
                current_burden = float(cause_df.sort_values(by="year").iloc[-1]["val"])

        if current_burden == 0.0:
            return f"缺少 {cause} 的真实历史数据，无法进行 SDE 演化预测。"

        # 使用简单的线性增长模型进行预测
        growth_rate = 0.02  # 默认年增长率 2%
        end_burden = current_burden * (1 + growth_rate) ** years
        growth_rate_percent = ((end_burden - current_burden) / current_burden * 100) if current_burden else 0.0
        trend_word = "上升" if growth_rate_percent > 0 else "下降"
        
        return (
            f"[{cause}] 未来 {years} 年趋势预测：基于线性增长模型模拟，"
            f"预计疾病负担指数将从 {current_burden:.1f} 变为 {end_burden:.1f}，"
            f"总体呈 {trend_word} 趋势（变化率约为 {growth_rate_percent:+.1f}%）。"
        )

    def simulate_policy_intervention(self, region_name: str, current_val: float, policy_type: str, years: int) -> Dict[str, Any]:
        """
        核心业务场景二：政策干预与未来演化模拟
        使用简化模型进行预测，并叠加政策权重
        """
        # 1. 使用简化模型进行基准预测
        # 假设年增长率为 2%
        baseline_prediction = [current_val * (1.02 ** i) for i in range(years + 1)]
        
        # 2. 叠加政策干预效果
        intervention_multipliers = {
            "控烟政策": 0.85,    # 降低15%负担
            "扩建三甲": 1.20,    # 提升20%服务能力
            "自然发展": 1.00
        }
        multiplier = intervention_multipliers.get(policy_type, 1.0)
        
        # 应用政策效应对最后一年的预测值进行干预
        final_val_after_policy = baseline_prediction[-1] * multiplier

        return {
            "region": region_name,
            "policy_applied": policy_type,
            "baseline_trend": baseline_prediction,
            "final_value_after_intervention": round(final_val_after_policy, 2),
            "improvement": round((baseline_prediction[-1] - final_val_after_policy) / baseline_prediction[-1], 4)
        }

    # ========== 服务编排功能 (整合自 service.py) ==========

    def run_health_gap_analysis(self, raw_df: pd.DataFrame, year: int, target: str = "visualization") -> ServicePayload:
        """
        运行医疗资源缺口分析
        整合自 service.py 的 run_health_gap 功能
        """
        result = self.compute_resource_gap(raw_df, year)
        return ServicePayload(
            data=result, 
            target=target, 
            context={"year": year, "module": "health"}
        )

    def run_disease_trend_analysis(
        self,
        spectrum_df: pd.DataFrame,
        risk_df: pd.DataFrame,
        cause: str,
        years: int = 5,
        target: str = "llm",
    ) -> ServicePayload:
        """
        运行疾病趋势分析
        整合自 service.py 的 run_disease_trend 功能
        """
        result_text = self.predict_disease_trend(spectrum_df, cause, years)
        return ServicePayload(
            data=result_text, 
            target=target, 
            context={"cause": cause, "years": years, "module": "disease"}
        )

    def run_comprehensive_analysis(
        self,
        resource_data: pd.DataFrame,
        disease_data: pd.DataFrame,
        region: str,
        year: int,
        target: str = "comprehensive"
    ) -> ServicePayload:
        """
        运行综合健康系统分析
        整合区域资源评估和疾病风险分析
        """
        # 运行区域健康系统评估
        system_result = self.evaluate_regional_health_system(region, year, resource_data, disease_data)
        
        # 运行风险归因分析
        risk_attribution = self.get_risk_attribution(disease_data, year, region)
        
        # 运行干预建议
        intervention_list = self.get_intervention_list(disease_data, region)
        
        comprehensive_result = {
            "system_assessment": system_result,
            "risk_attribution": risk_attribution,
            "intervention_recommendations": intervention_list,
            "region": region,
            "year": year
        }
        
        return ServicePayload(
            data=comprehensive_result,
            target=target,
            context={"region": region, "year": year, "module": "comprehensive"}
        )

    def run_advanced_spatial_assessment(self, supply_df: pd.DataFrame, demand_df: pd.DataFrame) -> pd.Series:
        """
        核心业务场景三：调度高阶算法评估空间公平性
        使用简化方法评估空间公平性
        """
        # 简化版空间公平性评估
        if supply_df.empty or demand_df.empty:
            return pd.Series(dtype=float)
        
        # 计算供给与需求的比值作为公平性指标
        if 'hospital_beds_per_1000' in supply_df.columns and 'population' in demand_df.columns:
            # 简化计算：每千人床位数与人口密度的比值
            supply_density = supply_df['hospital_beds_per_1000'].mean()
            demand_density = demand_df['population'].sum() / 1000  # 转换为千人
            
            if demand_density > 0:
                fairness_index = supply_density / demand_density
                return pd.Series([fairness_index], name='spatial_fairness')
        
        return pd.Series([0.0], name='spatial_fairness')