# tests/test_dea_efficiency.py
"""
DEA 效率评估算法单元测试

测试范围:
1. HealthMathModels.calculate_dea_efficiency 核心算法
2. HealthMathModels.validate_dea_data 数据验证
3. EfficiencyEvaluator 类完整功能
4. DEAInputOutputConfig 配置类

修正验证 (2026-04-17):
- 验证人口作为投入指标而非产出指标
- 验证不同人口规模地区的效率计算正确性
- 验证数据合法性校验机制
"""

import unittest
import numpy as np
import pandas as pd
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
root = str(Path(__file__).parent.parent)
if root not in sys.path:
    sys.path.insert(0, root)

from modules.core.evaluator import (
    HealthMathModels,
    EfficiencyEvaluator,
    DEAInputOutputConfig
)


class TestDEAInputOutputConfig(unittest.TestCase):
    """测试 DEA 投入产出配置类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = DEAInputOutputConfig()
        
        # 验证默认投入指标
        self.assertIn('bed_count', config.input_columns)
        self.assertIn('physician_count', config.input_columns)
        self.assertIn('population', config.input_columns)  # 关键：人口是投入指标
        
        # 验证默认产出指标
        self.assertIn('total_outpatient_visits', config.output_columns)
        self.assertIn('discharged_patients', config.output_columns)
        
        # 验证人口不在产出指标中
        self.assertNotIn('population', config.output_columns)
    
    def test_column_mappings(self):
        """测试列名映射功能"""
        config = DEAInputOutputConfig()
        
        # 创建测试数据框
        df = pd.DataFrame({
            'beds': [100, 200, 300],
            'physicians': [50, 80, 120],
            'pop': [10000, 20000, 30000],
            'outpatient': [5000, 8000, 12000],
            'discharges': [1000, 2000, 3000]
        })
        
        available_inputs, available_outputs = config.get_available_columns(df)
        
        # 验证能正确识别投入列
        self.assertTrue(len(available_inputs) >= 3)
        
        # 验证能正确识别产出列
        self.assertTrue(len(available_outputs) >= 2)


class TestDEADataValidation(unittest.TestCase):
    """测试 DEA 数据验证功能"""
    
    def test_valid_data(self):
        """测试有效数据通过验证"""
        X = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        Y = np.array([[10, 20], [30, 40], [50, 60]])
        
        is_valid, error_msg, X_clean, Y_clean = HealthMathModels.validate_dea_data(X, Y)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "数据验证通过")
        np.testing.assert_array_equal(X, X_clean)
        np.testing.assert_array_equal(Y, Y_clean)
    
    def test_empty_data(self):
        """测试空数据验证失败"""
        X = np.array([])
        Y = np.array([[1, 2], [3, 4]])
        
        is_valid, error_msg, _, _ = HealthMathModels.validate_dea_data(X, Y)
        
        self.assertFalse(is_valid)
        self.assertIn("空", error_msg)
    
    def test_mismatched_dimensions(self):
        """测试维度不匹配验证失败"""
        X = np.array([[1, 2], [3, 4], [5, 6]])  # 3 DMUs
        Y = np.array([[10, 20], [30, 40]])       # 2 DMUs
        
        is_valid, error_msg, _, _ = HealthMathModels.validate_dea_data(X, Y)
        
        self.assertFalse(is_valid)
        self.assertIn("不匹配", error_msg)
    
    def test_nan_values(self):
        """测试 NaN 值处理"""
        X = np.array([[1, 2], [np.nan, 4], [5, 6]])
        Y = np.array([[10, 20], [30, 40], [50, 60]])
        
        is_valid, error_msg, X_clean, Y_clean = HealthMathModels.validate_dea_data(X, Y)
        
        self.assertTrue(is_valid)
        # NaN 应该被替换为列均值
        self.assertFalse(np.isnan(X_clean).any())
    
    def test_infinity_values(self):
        """测试 Infinity 值处理"""
        X = np.array([[1, 2], [np.inf, 4], [5, 6]])
        Y = np.array([[10, 20], [30, 40], [50, 60]])
        
        is_valid, error_msg, X_clean, Y_clean = HealthMathModels.validate_dea_data(X, Y)
        
        self.assertTrue(is_valid)
        # Infinity 应该被替换为有限值
        self.assertFalse(np.isinf(X_clean).any())
    
    def test_negative_values(self):
        """测试负值处理"""
        X = np.array([[1, 2], [-3, 4], [5, 6]])
        Y = np.array([[10, 20], [30, 40], [50, 60]])
        
        is_valid, error_msg, X_clean, Y_clean = HealthMathModels.validate_dea_data(X, Y)
        
        self.assertTrue(is_valid)
        # 负值应该被取绝对值
        self.assertTrue((X_clean >= 0).all())
    
    def test_zero_rows(self):
        """测试全零行处理"""
        X = np.array([[1, 2], [0, 0], [5, 6]])
        Y = np.array([[10, 20], [30, 40], [50, 60]])
        
        is_valid, error_msg, X_clean, Y_clean = HealthMathModels.validate_dea_data(X, Y)
        
        self.assertTrue(is_valid)
        # 全零行应该被替换为极小值
        # 注意：由于浮点数精度问题，使用更宽松的比较
        self.assertTrue((X_clean[1] > 0).all() or np.allclose(X_clean[1], 1e-6),
                       f"全零行处理后值应为正数或接近1e-6，实际值: {X_clean[1]}")


class TestDEAEfficiencyCalculation(unittest.TestCase):
    """测试 DEA 效率计算核心算法"""
    
    def test_basic_efficiency_calculation(self):
        """测试基本效率计算"""
        # 构造简单测试数据: 3个DMU，2个投入，1个产出
        X = np.array([[1, 2], [2, 4], [3, 6]])
        Y = np.array([[1], [2], [3]])
        
        efficiencies = HealthMathModels.calculate_dea_efficiency(X, Y)
        
        # 验证结果
        self.assertEqual(len(efficiencies), 3)
        # 所有效率值应在 [0, 1] 范围内
        self.assertTrue((efficiencies >= 0).all() and (efficiencies <= 1).all())
        # 第一个DMU应该是有效的 (效率=1)
        self.assertAlmostEqual(efficiencies[0], 1.0, places=5)
    
    def test_efficient_dmu_identification(self):
        """测试有效DMU识别"""
        # 构造数据: DMU1和DMU3在效率前沿面上
        X = np.array([[1, 1], [2, 2], [1, 2]])
        Y = np.array([[2], [3], [2]])
        
        efficiencies = HealthMathModels.calculate_dea_efficiency(X, Y)
        
        # DMU1应该是有效的
        self.assertGreaterEqual(efficiencies[0], 0.99)
    
    def test_with_dmu_names(self):
        """测试带DMU名称的计算"""
        X = np.array([[1, 2], [2, 4], [3, 6]])
        Y = np.array([[1], [2], [3]])
        dmu_names = ['Region_A', 'Region_B', 'Region_C']
        
        efficiencies = HealthMathModels.calculate_dea_efficiency(X, Y, dmu_names=dmu_names)
        
        self.assertEqual(len(efficiencies), 3)
    
    def test_return_slacks(self):
        """测试返回松弛变量"""
        X = np.array([[1, 2], [2, 4], [3, 6]])
        Y = np.array([[1], [2], [3]])
        
        result = HealthMathModels.calculate_dea_efficiency(X, Y, return_slacks=True)
        
        self.assertIn('efficiencies', result)
        self.assertIn('input_slacks', result)
        self.assertIn('output_slacks', result)
        self.assertIn('status', result)
        
        self.assertEqual(len(result['efficiencies']), 3)
        self.assertEqual(result['input_slacks'].shape, (3, 2))
        self.assertEqual(result['output_slacks'].shape, (3, 1))
    
    def test_invalid_data_handling(self):
        """测试无效数据处理"""
        X = np.array([])
        Y = np.array([[1], [2]])
        
        efficiencies = HealthMathModels.calculate_dea_efficiency(X, Y)
        
        # 应该返回空数组
        self.assertEqual(len(efficiencies), 0)


class TestPopulationAsInput(unittest.TestCase):
    """
    测试人口作为投入指标的关键修正
    
    这是问题3的核心修复验证：
    - 人口应该作为投入指标（服务基数），而非产出指标
    - 人口规模大的地区不应该因此获得虚高的效率评分
    """
    
    def test_population_as_input_vs_output(self):
        """验证人口作为投入vs产出的差异"""
        # 构造测试数据: 两个地区，投入和产出相同，但人口不同
        # 地区A: 人口10000，床位数100，医生50，诊疗5000，出院1000
        # 地区B: 人口20000，床位数100，医生50，诊疗5000，出院1000
        
        # 场景1: 人口作为产出 (错误做法)
        X_wrong = np.array([[100, 50], [100, 50]])  # 床位数, 医生数
        Y_wrong = np.array([[10000, 5000, 1000], [20000, 5000, 1000]])  # 人口, 诊疗, 出院
        
        efficiencies_wrong = HealthMathModels.calculate_dea_efficiency(X_wrong, Y_wrong)
        
        # 场景2: 人口作为投入 (正确做法)
        X_correct = np.array([[100, 50, 10000], [100, 50, 20000]])  # 床位数, 医生数, 人口
        Y_correct = np.array([[5000, 1000], [5000, 1000]])  # 诊疗, 出院
        
        efficiencies_correct = HealthMathModels.calculate_dea_efficiency(X_correct, Y_correct)
        
        # 验证: 在错误做法中，人口大的地区B可能效率虚高
        # 在正确做法中，地区B因为投入更多(人口)，但产出相同，效率应该更低
        
        # 地区B在正确做法中的效率应该 <= 地区A的效率
        # (因为投入更多但产出相同)
        self.assertLessEqual(
            efficiencies_correct[1], efficiencies_correct[0],
            "人口大的地区在投入相同、产出相同时，效率不应更高"
        )
    
    def test_large_population_no_artificial_advantage(self):
        """测试人口大的地区不会出现效率虚高"""
        # 构造数据: 5个地区，产出与投入成比例，但人口规模不同
        np.random.seed(42)
        n_regions = 5
        
        # 基础投入 - 与人口成比例增长
        beds = np.array([100, 500, 1000, 5000, 10000])  # 床位数与人口成比例
        physicians = np.array([50, 250, 500, 2500, 5000])  # 医生数与人口成比例
        populations = np.array([10000, 50000, 100000, 500000, 1000000])  # 人口差异大
        
        # 产出与投入成比例 (合理情况) - 按人均计算应该相似
        # 假设每床位产出约50次诊疗，每医生产出约100次诊疗
        outpatient_visits = beds * 50 + np.random.normal(0, 500, n_regions)
        discharged = beds * 10 + np.random.normal(0, 100, n_regions)
        
        # 正确做法: 人口作为投入
        X = np.column_stack([beds, physicians, populations])
        Y = np.column_stack([outpatient_visits, discharged])
        
        efficiencies = HealthMathModels.calculate_dea_efficiency(X, Y)
        
        # 验证: 效率分布应该合理，不会因为人口大就效率高
        # 至少应该有一些地区的效率不是1.0
        self.assertTrue((efficiencies <= 1.0).all())
        self.assertTrue((efficiencies >= 0).all())
        
        # 计算效率与人口的相关性
        # 由于投入产出都随人口成比例增长，效率应该相对稳定
        correlation = np.corrcoef(populations, efficiencies)[0, 1]
        
        # 记录相关性用于调试
        print(f"人口与效率的相关系数: {correlation:.4f}")
        print(f"效率分布: {efficiencies}")
        
        # 验证效率值在合理范围内，没有异常值
        self.assertTrue((efficiencies >= 0.5).all(), 
                       "所有地区的效率应该在一个合理的范围内")
        
        # 验证至少有一个地区不是完全有效 (效率 < 0.99)
        # 这表明算法能够区分不同地区的效率差异
        self.assertTrue((efficiencies < 0.99).any(),
                       "应该至少有一个地区不是完全有效，以证明算法能区分效率差异")


class TestEfficiencyEvaluator(unittest.TestCase):
    """测试 EfficiencyEvaluator 类"""
    
    def setUp(self):
        """设置测试数据"""
        self.evaluator = EfficiencyEvaluator()
        
        # 创建测试数据框
        self.test_df = pd.DataFrame({
            'region_name': ['Region_A', 'Region_B', 'Region_C', 'Region_D', 'Region_E'],
            'bed_count': [100, 200, 150, 300, 250],
            'physician_count': [50, 100, 75, 150, 125],
            'population': [10000, 50000, 25000, 100000, 75000],
            'total_outpatient_visits': [5000, 15000, 8000, 25000, 20000],
            'discharged_patients': [1000, 3000, 1600, 5000, 4000]
        })
    
    def test_calculate_from_df_basic(self):
        """测试从DataFrame计算效率"""
        result_df = self.evaluator.calculate_dea_efficiency_from_df(
            self.test_df,
            dmu_col='region_name'
        )
        
        # 验证结果列存在
        self.assertIn('dea_efficiency', result_df.columns)
        self.assertIn('dea_rank', result_df.columns)
        self.assertIn('is_efficient', result_df.columns)
        
        # 验证效率值范围
        self.assertTrue((result_df['dea_efficiency'] >= 0).all())
        self.assertTrue((result_df['dea_efficiency'] <= 1).all())
        
        # 验证排名
        self.assertEqual(result_df['dea_rank'].min(), 1)
        self.assertEqual(result_df['dea_rank'].max(), len(self.test_df))
    
    def test_column_validation(self):
        """测试列验证功能"""
        # 测试有效列
        is_valid, available_cols = self.evaluator.validate_columns(
            self.test_df, ['bed_count', 'physician_count'], "投入"
        )
        self.assertTrue(is_valid)
        self.assertEqual(len(available_cols), 2)
        
        # 测试无效列
        is_valid, available_cols = self.evaluator.validate_columns(
            self.test_df, ['nonexistent_col'], "投入"
        )
        self.assertFalse(is_valid)
        self.assertEqual(len(available_cols), 0)
    
    def test_get_efficiency_benchmarks(self):
        """测试获取效率标杆"""
        result_df = self.evaluator.calculate_dea_efficiency_from_df(
            self.test_df,
            dmu_col='region_name'
        )
        
        benchmarks = self.evaluator.get_efficiency_benchmarks(result_df, 'region_name')
        
        # 验证标杆结果
        self.assertIn('total_dmus', benchmarks)
        self.assertIn('efficient_dmus', benchmarks)
        self.assertIn('average_efficiency', benchmarks)
        self.assertIn('benchmark_dmus', benchmarks)
        
        self.assertEqual(benchmarks['total_dmus'], len(self.test_df))
        self.assertGreaterEqual(benchmarks['efficient_dmus'], 1)  # 至少有一个有效DMU
    
    def test_compare_scenarios(self):
        """测试情景对比"""
        # 基准情景
        baseline_df = self.evaluator.calculate_dea_efficiency_from_df(
            self.test_df,
            dmu_col='region_name'
        )
        
        # 修改后的情景 (增加产出)
        modified_df = self.test_df.copy()
        modified_df['total_outpatient_visits'] = modified_df['total_outpatient_visits'] * 1.2
        scenario_df = self.evaluator.calculate_dea_efficiency_from_df(
            modified_df,
            dmu_col='region_name'
        )
        
        comparison = self.evaluator.compare_scenarios(baseline_df, scenario_df, 'region_name')
        
        # 验证对比结果
        self.assertIn('efficiency_change', comparison.columns)
        self.assertIn('efficiency_change_pct', comparison.columns)
        
        # 产出增加，效率应该提升或保持不变
        self.assertTrue((comparison['efficiency_change'] >= -0.01).all())
    
    def test_data_preprocessing(self):
        """测试数据预处理"""
        # 创建包含异常值的数据
        df_with_issues = self.test_df.copy()
        df_with_issues.loc[0, 'bed_count'] = np.nan
        df_with_issues.loc[1, 'physician_count'] = 0
        df_with_issues.loc[2, 'population'] = -1000
        
        result_df = self.evaluator.calculate_dea_efficiency_from_df(
            df_with_issues,
            dmu_col='region_name'
        )
        
        # 验证计算仍然成功
        self.assertEqual(len(result_df), len(df_with_issues))
        self.assertTrue((result_df['dea_efficiency'] >= 0).all())


class TestEdgeCases(unittest.TestCase):
    """测试边界情况"""
    
    def test_single_dmu(self):
        """测试单个DMU"""
        X = np.array([[1, 2, 1000]])  # 床位数, 医生数, 人口
        Y = np.array([[100, 20]])      # 诊疗, 出院
        
        efficiencies = HealthMathModels.calculate_dea_efficiency(X, Y)
        
        # 单个DMU应该是有效的
        self.assertEqual(len(efficiencies), 1)
        self.assertAlmostEqual(efficiencies[0], 1.0, places=5)
    
    def test_identical_dmus(self):
        """测试完全相同的DMU"""
        X = np.array([[1, 2, 1000], [1, 2, 1000], [1, 2, 1000]])
        Y = np.array([[100, 20], [100, 20], [100, 20]])
        
        efficiencies = HealthMathModels.calculate_dea_efficiency(X, Y)
        
        # 所有DMU应该都是有效的
        self.assertTrue((efficiencies >= 0.99).all())
    
    def test_very_small_values(self):
        """测试极小值"""
        X = np.array([[1e-10, 1e-10, 1e-8], [2e-10, 2e-10, 2e-8]])
        Y = np.array([[1e-9, 1e-10], [2e-9, 2e-10]])
        
        efficiencies = HealthMathModels.calculate_dea_efficiency(X, Y)
        
        self.assertEqual(len(efficiencies), 2)
        self.assertTrue((efficiencies >= 0).all() and (efficiencies <= 1).all())
    
    def test_very_large_values(self):
        """测试极大值"""
        X = np.array([[1e6, 1e5, 1e8], [2e6, 2e5, 2e8]])
        Y = np.array([[1e7, 1e6], [2e7, 2e6]])
        
        efficiencies = HealthMathModels.calculate_dea_efficiency(X, Y)
        
        self.assertEqual(len(efficiencies), 2)
        self.assertTrue((efficiencies >= 0).all() and (efficiencies <= 1).all())


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestDEAInputOutputConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestDEADataValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestDEAEfficiencyCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestPopulationAsInput))
    suite.addTests(loader.loadTestsFromTestCase(TestEfficiencyEvaluator))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
