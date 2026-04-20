"""
API 路由包

包含所有 API 路由模块，按功能领域组织：
- marco: 宏观分析数据总线 (全球/国家/区域尺度)
- meso: 中观分析数据总线
- micro: 微观分析计算引擎
- prediction: 预测引擎 (替代 BAPC/SDE/DeepAnalyze)
- dataset: 数据集管理 (疾病负担/风险因素/资源效率等数据)
- analysis: AI 驱动的分析报告生成 (Ollama 集成)
"""

from .marco import router as marco_router
from .meso import router as meso_router
from .micro import router as micro_router
from .prediction import router as prediction_router
from .dataset import router as dataset_router
from .analysis import router as analysis_router

__all__ = [
    "marco_router",
    "meso_router",
    "micro_router",
    "prediction_router",
    "dataset_router",
    "analysis_router"
]
