from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Tuple


class IHealthAnalyzer(ABC):
    """
    医疗资源分析统一接口
    定义了资源缺口计算、优化分配和未来预测的核心标准
    """

    @abstractmethod
    def compute_resource_gap(self, year: int) -> pd.DataFrame:
        """
        计算指定年份的资源缺口
        返回包含实际供给、理论需求、缺口率及严重程度的 DataFrame
        """
        pass

    @abstractmethod
    def optimize_resource_allocation(self, year: int,
                                     objective: str = 'maximize_health',
                                     budget_ratio: float = 0.3) -> Dict:
        """
        根据特定目标（如健康最大化）优化资源分配方案
        """
        pass

    @abstractmethod
    def predict_future(self, years_ahead: int = 5,
                       scenario: str = "基准") -> pd.DataFrame:
        """
        基于不同情景模拟预测未来的医疗资源需求
        """
        pass


class IPreprocessor(ABC):
    """
    数据预处理统一接口
    规范了从原始文件读取到标准化清洗的完整流程
    """

    @abstractmethod
    def preprocess_health_data(self, file_path: str) -> Tuple[pd.DataFrame, Dict]:
        """
        对单个原始文件进行初步读取和格式校验
        """
        pass

    @abstractmethod
    def clean_health_data(self, input_file: str, output_file: str) -> None:
        """
        执行标准清洗逻辑并输出为系统可直接加载的 Excel 文件
        """
        pass


class IDiseaseAnalyzer(ABC):
    """
    疾病分析器抽象接口
    负责疾病风险归因、干预建议及趋势预测
    """

    @abstractmethod
    def get_attribution(self, year: int, region: str = None) -> str:
        """获取特定年份和地区的疾病风险归因分析"""
        pass

    @abstractmethod
    def get_intervention_list(self, region: str) -> str:
        """获取针对特定地区的医疗干预措施建议列表"""
        pass

    @abstractmethod
    def predict_disease_trend(self, cause: str, years: int) -> str:
        """预测特定疾病在未来几年的演化趋势"""
        pass