from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler

from modules.core.analyzer import DiseasePredictConfig

# 忽略 sklearn 的收敛警告，保持终端清爽
warnings.filterwarnings("ignore", category=ConvergenceWarning)


@dataclass
class Predictor:
    """
    HIS 系统核心预测引擎
    集成了传统线性预测、SDE (随机微分方程) 演化模拟、以及基于神经网络的时序预测
    """

    disease_config: DiseasePredictConfig = DiseasePredictConfig()
    scaler: MinMaxScaler = field(default_factory=MinMaxScaler)

    def project_exponential(
        self,
        latest_data: pd.DataFrame,
        years_ahead: int,
        year_col: str,
        value_col: str,
        multiplier: float,
    ) -> pd.DataFrame:
        if latest_data.empty:
            return pd.DataFrame()

        latest_year = int(latest_data[year_col].max())
        base = latest_data[latest_data[year_col] == latest_year].copy()

        predictions = []
        for offset in range(1, years_ahead + 1):
            pred = base.copy()
            pred[year_col] = latest_year + offset
            pred[value_col] = pred[value_col] * (multiplier ** offset)
            predictions.append(pred)

        return pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()

    def simulate_sde_burden(
        self,
        cause: str,
        current_burden: float,
        years_ahead: int,
        start_year: int,
    ) -> pd.DataFrame:
        cfg = self.disease_config
        rng = np.random.default_rng(cfg.random_seed)

        cause_lower = cause.lower()
        is_metabolic = any(
            keyword in cause_lower
            for keyword in ["diabetes", "cardiovascular", "糖尿病", "心血管", "neoplasms", "肿瘤"]
        )

        drift = cfg.drift_metabolic if is_metabolic else cfg.drift_non_metabolic
        diffusion = cfg.diffusion

        results = [float(current_burden)]
        for _ in range(1, years_ahead + 1):
            prev = results[-1]
            dt = 1.0
            dW = float(rng.normal(0.0, np.sqrt(dt)))
            change = (drift * prev * dt) + (diffusion * prev * dW)
            new_val = prev + change
            floor = current_burden * cfg.lower_bound_ratio
            ceil = current_burden * cfg.upper_bound_ratio
            results.append(float(max(floor, min(new_val, ceil))))

        return pd.DataFrame(
            {
                "year": np.arange(start_year, start_year + years_ahead + 1),
                "burden_index": results,
                "cause": cause,
            }
        )

    # ================= 神经网络预测模块 (平替 MATLAB NARNET) =================

    def _create_lagged_dataset(self, series: np.ndarray, lags: int) -> tuple[np.ndarray, np.ndarray]:
        """
        内部方法：构建滑动窗口数据集

        将时间序列转换为监督学习格式：用过去 lags 个时刻预测下一个时刻
        对应 MATLAB NARNET 的 preparets() 功能

        Args:
            series: 时间序列数据
            lags: 延迟阶数，即依赖过去多少个值

        Returns:
            X: 特征矩阵，形状 (n_samples, lags)
            Y: 目标向量，形状 (n_samples,)
        """
        X, Y = [], []
        for i in range(len(series) - lags):
            X.append(series[i:(i + lags)])      # 过去 lags 个时刻
            Y.append(series[i + lags])          # 下一个时刻
        return np.array(X), np.array(Y)

    def predict_neural_autoregression(
        self,
        historical_data: List[float],
        predict_steps: int,
        lags: int = 10,
        hidden_neurons: int = 10,
    ) -> Dict[str, Any]:
        """
        复刻 MATLAB NARNET 逻辑：非线性自回归神经网络预测

        使用 MLPRegressor + 滑动窗口技术实现 NAR (Nonlinear AutoRegressive) 预测。
        核心思想：用过去 lags 个时刻的历史数据，预测下一个时刻的值。

        Args:
            historical_data: 历史时间序列数据 (如压力、发病率等连续数值)
            predict_steps: 需要向未来预测的步数 (如 5 年)
            lags: 延迟阶数，即依赖过去多少个值 (对应 MATLAB 的 feedback_delays = 1:10)
            hidden_neurons: 隐含层节点数 (对应 MATLAB 的 num_hd_neuron = 10)

        Returns:
            包含预测结果和模型状态的字典:
            {
                "status": "success",
                "method": "neural_network_autoregression",
                "future_predictions": [pred1, pred2, ...],  # 反归一化后的真实值
                "lags": lags,
                "hidden_neurons": hidden_neurons
            }

        Raises:
            ValueError: 当历史数据长度不足时抛出

        示例:
            >>> predictor = Predictor()
            >>> pressure_data = [100.5, 101.2, 100.8, 101.5, 102.0, ...]  # 历史压力数据
            >>> result = predictor.predict_neural_autoregression(
            ...     historical_data=pressure_data,
            ...     predict_steps=5,
            ...     lags=10
            ... )
            >>> print(result["future_predictions"])  # 未来5期的预测值
        """
        if len(historical_data) <= lags:
            raise ValueError(
                f"历史数据长度 ({len(historical_data)}) 必须大于延迟阶数 ({lags})"
            )

        # 1. 数据归一化 (神经网络对输入范围非常敏感)
        data_array = np.array(historical_data).reshape(-1, 1)
        scaled_data = self.scaler.fit_transform(data_array).flatten()

        # 2. 构建滑动窗口特征矩阵 (X) 和目标向量 (Y)
        X, Y = self._create_lagged_dataset(scaled_data, lags)

        # 3. 构建并训练 MLP 回归器
        # solver='lbfgs' 对小数据集拟合效果更好，相当于 MATLAB 中的 trainlm (Levenberg-Marquardt)
        model = MLPRegressor(
            hidden_layer_sizes=(hidden_neurons,),
            activation='relu',
            solver='lbfgs',
            max_iter=1000,
            random_state=42
        )
        model.fit(X, Y)

        # 4. 滚动预测未来值 (Autoregressive Prediction)
        # 取历史数据最后的 `lags` 个值作为初始输入
        current_input = scaled_data[-lags:].tolist()
        future_scaled_preds = []

        for _ in range(predict_steps):
            # 将当前窗口转为模型需要的二维格式
            x_input = np.array(current_input).reshape(1, -1)
            # 预测下一步
            next_pred = model.predict(x_input)[0]
            future_scaled_preds.append(next_pred)

            # 窗口向前滑动：去掉最旧的值，加入最新预测的值
            current_input.pop(0)
            current_input.append(next_pred)

        # 5. 反归一化，还原为真实的业务数值
        future_real_preds = self.scaler.inverse_transform(
            np.array(future_scaled_preds).reshape(-1, 1)
        ).flatten().tolist()

        return {
            "status": "success",
            "method": "neural_network_autoregression",
            "future_predictions": [round(val, 4) for val in future_real_preds],
            "lags": lags,
            "hidden_neurons": hidden_neurons,
        }

    # ================= 数据驱动的随机逻辑斯蒂模型 =================

    @staticmethod
    def _calibrate_logistic_sde(historical_data: List[float], capacity_k: Optional[float] = None) -> tuple:
        """
        内部方法：从历史数据中反推内生增长率(r)和波动率(sigma)
        """
        data = np.array(historical_data)
        if len(data) < 2:
            return 0.02, 0.03, capacity_k or data[0] * 1.5  # 默认回退值

        # 计算对数收益率
        log_returns = np.log(data[1:] / data[:-1])

        # 1. 计算历史波动率 (sigma)
        sigma = np.std(log_returns, ddof=1) if len(log_returns) > 1 else 0.03

        # 2. 计算内生增长率 (r)
        # 考虑到早期基数小增长快，取对数收益率的均值并做 Ito 修正
        r = np.mean(log_returns) + (sigma ** 2) / 2.0

        # 3. 确定承载力上限 (K)
        # 如果业务没有传入明确上限，默认设为历史最大值的 1.5 倍（假定处于发展期中期）
        k = capacity_k if capacity_k is not None else np.max(data) * 1.5

        return r, sigma, k

    @staticmethod
    def _simulate_logistic_sde(current_val: float, years_ahead: int,
                               r: float, sigma: float, k: float) -> List[float]:
        """
        内部方法：使用欧拉-丸山方法 (Euler-Maruyama) 离散化求解 SDE
        """
        np.random.seed(42)  # 固定种子保证可复现
        results = [current_val]
        dt = 1.0

        for _ in range(1, years_ahead + 1):
            prev = results[-1]
            dW = np.random.normal(0, np.sqrt(dt))

            # 漂移项：受承载力 K 压制的逻辑斯蒂增长
            drift_term = r * prev * (1 - prev / k) * dt
            # 扩散项：随机波动
            diffusion_term = sigma * prev * dW

            new_val = prev + drift_term + diffusion_term

            # 物理意义约束：不能跌穿底线，也不能大幅突破天花板 (加上 5% 的弹性溢出空间)
            clamped_val = max(0.01, min(new_val, k * 1.05))
            results.append(clamped_val)

        return results[1:]

    @classmethod
    def run_data_driven_logistic_sde(cls,
                                     historical_data: List[float],
                                     years_ahead: int,
                                     capacity_k: Optional[float] = None) -> Dict[str, Any]:
        """
        对外暴露的核心接口：完全由数据驱动的 SDE 预测
        """
        if not historical_data:
            raise ValueError("历史数据不能为空，无法校准模型参数。")

        # 第一步：校准参数 (学)
        r, sigma, k = cls._calibrate_logistic_sde(historical_data, capacity_k)

        # 第二步：演化模拟 (推)
        current_val = historical_data[-1]
        preds = cls._simulate_logistic_sde(current_val, years_ahead, r, sigma, k)

        return {
            "status": "success",
            "method": "stochastic_logistic_growth",
            "parameters": {
                "intrinsic_growth_rate_r": round(r, 4),
                "volatility_sigma": round(sigma, 4),
                "carrying_capacity_K": round(k, 2)
            },
            "future_predictions": [round(v, 4) for v in preds]
        }
