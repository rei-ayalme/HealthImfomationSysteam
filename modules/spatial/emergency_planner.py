from typing import Dict


class EmergencySpacePlanner:
    @staticmethod
    def simulate_emergency_demand(total_pop: int, current_beds: int, initial_cases: int = 10, days: int = 60) -> Dict:
        """
        于涛：SIR模型推演应急空间与床位缺口
        """
        beta, gamma = 0.3, 0.1  # 传染率与康复率基线
        S, I, R = total_pop - initial_cases, initial_cases, 0
        peak_infected = 0

        for _ in range(days):
            dS = -beta * I * S / total_pop
            dI = beta * I * S / total_pop - gamma * I
            dR = gamma * I
            S += dS;
            I += dI;
            R += dR
            if I > peak_infected:
                peak_infected = I

        # 假设 15% 的感染者需要实体医疗空间/方舱隔离
        emergency_beds_needed = max(0, int(peak_infected * 0.15) - current_beds)

        return {
            "peak_infected": int(peak_infected),
            "emergency_beds_gap": emergency_beds_needed,
            "status": "🔴 严重超载" if emergency_beds_needed > current_beds else "🟢 承载力安全",
            "planning_advice": f"峰值预计{int(peak_infected)}人感染，需保障征用并改造约 {emergency_beds_needed * 15} 平方米的城市大型公共空间（如体育馆、会展中心）作为应急方舱储备。"
        }