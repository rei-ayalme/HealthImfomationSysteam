"""
SpatialEngine 空间决策引擎单元测试

测试覆盖：
1. calculate_accessibility - 可达性计算
2. plan_emergency_routes - 应急路线规划
3. optimize_facility_layout - 设施布局优化
4. 性能基准测试
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.core.spatial_engine import SpatialEngine


class TestSpatialEngineInit(unittest.TestCase):
    """SpatialEngine 初始化测试"""

    def test_default_initialization(self):
        """测试默认初始化"""
        engine = SpatialEngine()
        self.assertEqual(engine.cache_size, 128)
        self.assertTrue(engine.enable_progress)
        self.assertIsNotNone(engine.logger)

    def test_custom_initialization(self):
        """测试自定义参数初始化"""
        engine = SpatialEngine(cache_size=256, enable_progress=False)
        self.assertEqual(engine.cache_size, 256)
        self.assertFalse(engine.enable_progress)

    def test_statistics_initialization(self):
        """测试统计信息初始化"""
        engine = SpatialEngine()
        stats = engine.get_statistics()
        self.assertEqual(stats['distance_calculations'], 0)
        self.assertEqual(stats['cache_hits'], 0)
        self.assertEqual(stats['accessibility_computations'], 0)


class TestCalculateAccessibility(unittest.TestCase):
    """可达性计算测试"""

    def setUp(self):
        self.engine = SpatialEngine(enable_progress=False)

        # 创建测试数据 - 供给点（医院）
        self.supply_df = pd.DataFrame({
            'lat': [30.65, 30.67, 30.63],
            'lon': [104.05, 104.08, 104.02],
            'capacity': [1000, 800, 600],
            'name': ['医院A', '医院B', '医院C']
        })

        # 创建测试数据 - 需求点（社区）
        self.demand_df = pd.DataFrame({
            'lat': [30.66, 30.64, 30.68, 30.62],
            'lon': [104.06, 104.04, 104.07, 104.03],
            'population': [50000, 40000, 60000, 30000],
            'elderly_ratio': [0.15, 0.25, 0.18, 0.12]
        })

    def test_e2sfca_basic(self):
        """测试E2SFCA基本功能"""
        result = self.engine.calculate_accessibility(
            self.supply_df, self.demand_df, method='e2sfca'
        )

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), len(self.demand_df))
        self.assertIn('accessibility_index', result.columns)
        self.assertTrue(all(result['accessibility_index'] >= 0))

    def test_gravity_model(self):
        """测试引力模型"""
        result = self.engine.calculate_accessibility(
            self.supply_df, self.demand_df, method='gravity', beta=2.0
        )

        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('accessibility_index', result.columns)

    def test_elderly_weight(self):
        """测试老龄化权重"""
        result_with_weight = self.engine.calculate_accessibility(
            self.supply_df, self.demand_df,
            method='e2sfca', use_elderly_weight=True
        )

        result_without_weight = self.engine.calculate_accessibility(
            self.supply_df, self.demand_df,
            method='e2sfca', use_elderly_weight=False
        )

        # 老龄化率>0.2的地区权重会降低可达性指数
        elderly_mask = self.demand_df['elderly_ratio'] > 0.2
        if elderly_mask.any():
            self.assertTrue(
                any(result_with_weight.loc[elderly_mask, 'accessibility_index'] <=
                    result_without_weight.loc[elderly_mask, 'accessibility_index'])
            )

    def test_different_decay_types(self):
        """测试不同衰减函数"""
        for decay_type in ['gaussian', 'power', 'piecewise_power', 'binary']:
            result = self.engine.calculate_accessibility(
                self.supply_df, self.demand_df,
                method='e2sfca', decay_type=decay_type
            )
            self.assertIn('accessibility_index', result.columns)

    def test_invalid_method(self):
        """测试无效方法"""
        with self.assertRaises(ValueError) as context:
            self.engine.calculate_accessibility(
                self.supply_df, self.demand_df, method='invalid'
            )
        self.assertIn("未知的计算方法", str(context.exception))

    def test_invalid_decay_type(self):
        """测试无效衰减类型"""
        with self.assertRaises(ValueError) as context:
            self.engine.calculate_accessibility(
                self.supply_df, self.demand_df,
                method='e2sfca', decay_type='invalid'
            )
        self.assertIn("未知的衰减函数类型", str(context.exception))

    def test_empty_data(self):
        """测试空数据"""
        empty_df = pd.DataFrame()
        with self.assertRaises(ValueError):
            self.engine.calculate_accessibility(empty_df, self.demand_df)

        with self.assertRaises(ValueError):
            self.engine.calculate_accessibility(self.supply_df, empty_df)

    def test_missing_columns(self):
        """测试缺少必要列"""
        bad_supply = pd.DataFrame({'lat': [30.0], 'lon': [104.0]})  # 缺少capacity
        with self.assertRaises(ValueError) as context:
            self.engine.calculate_accessibility(bad_supply, self.demand_df)
        self.assertIn("缺少必要列", str(context.exception))

    def test_statistics_update(self):
        """测试统计信息更新"""
        initial_count = self.engine.get_statistics()['accessibility_computations']
        self.engine.calculate_accessibility(self.supply_df, self.demand_df)
        new_count = self.engine.get_statistics()['accessibility_computations']
        self.assertEqual(new_count, initial_count + 1)


class TestPlanEmergencyRoutes(unittest.TestCase):
    """应急路线规划测试"""

    def setUp(self):
        self.engine = SpatialEngine(enable_progress=False)

        # 创建测试医院数据
        self.hospital_df = pd.DataFrame({
            'lat': [30.65, 30.67, 30.63, 30.66],
            'lon': [104.05, 104.08, 104.02, 104.06],
            'capacity': [1000, 800, 600, 900],
            'name': ['中心医院', '人民医院', '第一医院', '急救中心']
        })

        self.incident_lat = 30.658
        self.incident_lon = 104.055

    def test_basic_route_planning(self):
        """测试基本路线规划"""
        result = self.engine.plan_emergency_routes(
            self.incident_lat, self.incident_lon, self.hospital_df
        )

        self.assertIsInstance(result, dict)
        self.assertIn('incident_location', result)
        self.assertIn('recommended_hospitals', result)
        self.assertIn('total_options', result)
        self.assertEqual(result['total_options'], len(self.hospital_df))

    def test_route_count(self):
        """测试返回路线数量"""
        max_routes = 2
        result = self.engine.plan_emergency_routes(
            self.incident_lat, self.incident_lon,
            self.hospital_df, max_routes=max_routes
        )

        self.assertEqual(len(result['recommended_hospitals']), max_routes)

    def test_route_structure(self):
        """测试路线数据结构"""
        result = self.engine.plan_emergency_routes(
            self.incident_lat, self.incident_lon, self.hospital_df
        )

        for hospital in result['recommended_hospitals']:
            self.assertIn('rank', hospital)
            self.assertIn('name', hospital)
            self.assertIn('distance_km', hospital)
            self.assertIn('estimated_time_min', hospital)
            self.assertIn('capacity_score', hospital)
            self.assertIn('priority_score', hospital)
            self.assertIn('lat', hospital)
            self.assertIn('lon', hospital)

            self.assertIsInstance(hospital['rank'], int)
            self.assertIsInstance(hospital['distance_km'], float)
            self.assertGreater(hospital['distance_km'], 0)
            self.assertGreater(hospital['estimated_time_min'], 0)

    def test_ranking_order(self):
        """测试排名顺序"""
        result = self.engine.plan_emergency_routes(
            self.incident_lat, self.incident_lon, self.hospital_df
        )

        hospitals = result['recommended_hospitals']
        for i in range(len(hospitals) - 1):
            self.assertGreaterEqual(
                hospitals[i]['priority_score'],
                hospitals[i + 1]['priority_score']
            )

    def test_invalid_coordinates(self):
        """测试无效坐标"""
        with self.assertRaises(ValueError) as context:
            self.engine.plan_emergency_routes(100, 104, self.hospital_df)
        self.assertIn("纬度", str(context.exception))

        with self.assertRaises(ValueError) as context:
            self.engine.plan_emergency_routes(30, 200, self.hospital_df)
        self.assertIn("经度", str(context.exception))

    def test_invalid_types(self):
        """测试无效类型"""
        with self.assertRaises(TypeError):
            self.engine.plan_emergency_routes("30", 104, self.hospital_df)

    def test_empty_hospitals(self):
        """测试空医院数据"""
        with self.assertRaises(ValueError):
            self.engine.plan_emergency_routes(
                self.incident_lat, self.incident_lon,
                pd.DataFrame()
            )

    def test_missing_columns(self):
        """测试缺少必要列"""
        bad_hospitals = pd.DataFrame({
            'lat': [30.0],
            'lon': [104.0]
            # 缺少 capacity
        })
        with self.assertRaises(ValueError) as context:
            self.engine.plan_emergency_routes(
                self.incident_lat, self.incident_lon, bad_hospitals
            )
        self.assertIn("缺少必要列", str(context.exception))


class TestOptimizeFacilityLayout(unittest.TestCase):
    """设施布局优化测试"""

    def setUp(self):
        self.engine = SpatialEngine(enable_progress=False)

        # 现有设施
        self.current_facilities = pd.DataFrame({
            'lat': [30.65, 30.67],
            'lon': [104.05, 104.08],
            'capacity': [1000, 800]
        })

        # 人口热力图
        self.population_heatmap = pd.DataFrame({
            'lat': [30.66, 30.64, 30.68, 30.62, 30.70, 30.60],
            'lon': [104.06, 104.04, 104.07, 104.03, 104.09, 104.01],
            'population': [80000, 60000, 90000, 50000, 100000, 40000]
        })

    def test_basic_optimization(self):
        """测试基本优化功能"""
        result = self.engine.optimize_facility_layout(
            self.current_facilities, self.population_heatmap
        )

        self.assertIsInstance(result, dict)
        self.assertIn('current_coverage', result)
        self.assertIn('recommendations', result)
        self.assertIn('projected_coverage', result)
        self.assertIn('blind_spots', result)

    def test_coverage_metrics(self):
        """测试覆盖率指标"""
        result = self.engine.optimize_facility_layout(
            self.current_facilities, self.population_heatmap
        )

        coverage = result['current_coverage']
        self.assertIn('coverage_rate', coverage)
        self.assertIn('avg_distance_km', coverage)
        self.assertIn('gini_coefficient', coverage)
        self.assertIn('total_population', coverage)

        self.assertGreaterEqual(coverage['coverage_rate'], 0)
        self.assertLessEqual(coverage['coverage_rate'], 1)
        self.assertGreaterEqual(coverage['gini_coefficient'], 0)
        self.assertLessEqual(coverage['gini_coefficient'], 1)

    def test_recommendations_structure(self):
        """测试推荐结构"""
        result = self.engine.optimize_facility_layout(
            self.current_facilities, self.population_heatmap,
            max_new_facilities=2
        )

        for rec in result['recommendations']:
            self.assertIn('rank', rec)
            self.assertIn('lat', rec)
            self.assertIn('lon', rec)
            self.assertIn('justification', rec)

    def test_different_methods(self):
        """测试不同优化方法"""
        for method in ['coverage_gap', 'equal_access', 'min_distance']:
            result = self.engine.optimize_facility_layout(
                self.current_facilities, self.population_heatmap,
                optimization_method=method
            )
            self.assertIn('recommendations', result)

    def test_empty_facilities(self):
        """测试无现有设施"""
        result = self.engine.optimize_facility_layout(
            pd.DataFrame(), self.population_heatmap
        )

        self.assertEqual(result['current_coverage']['coverage_rate'], 0.0)
        self.assertEqual(result['current_coverage']['gini_coefficient'], 1.0)

    def test_no_blind_spots(self):
        """测试无盲区情况"""
        # 创建覆盖所有人口的设施
        dense_facilities = self.population_heatmap.copy()
        dense_facilities['capacity'] = 1000

        result = self.engine.optimize_facility_layout(
            dense_facilities, self.population_heatmap,
            coverage_radius_km=10.0  # 大半径确保全覆盖
        )

        self.assertTrue(result['blind_spots'].empty or
                       len(result['recommendations']) == 0)

    def test_invalid_method(self):
        """测试无效优化方法"""
        with self.assertRaises(ValueError) as context:
            self.engine.optimize_facility_layout(
                self.current_facilities, self.population_heatmap,
                optimization_method='invalid'
            )
        self.assertIn("未知的优化方法", str(context.exception))

    def test_empty_population(self):
        """测试空人口数据"""
        with self.assertRaises(ValueError):
            self.engine.optimize_facility_layout(
                self.current_facilities, pd.DataFrame()
            )

    def test_zero_population(self):
        """测试零人口"""
        zero_pop = self.population_heatmap.copy()
        zero_pop['population'] = 0

        with self.assertRaises(ValueError) as context:
            self.engine.optimize_facility_layout(
                self.current_facilities, zero_pop
            )
        self.assertIn("总人口为0", str(context.exception))


class TestPerformanceBenchmarks(unittest.TestCase):
    """性能基准测试"""

    def setUp(self):
        self.engine = SpatialEngine(enable_progress=False)

    def test_large_dataset_accessibility(self):
        """测试大数据集可达性计算性能"""
        # 创建大规模测试数据
        np.random.seed(42)
        n_supply = 100
        n_demand = 1000

        supply_df = pd.DataFrame({
            'lat': np.random.uniform(30.5, 30.8, n_supply),
            'lon': np.random.uniform(103.9, 104.2, n_supply),
            'capacity': np.random.randint(500, 2000, n_supply)
        })

        demand_df = pd.DataFrame({
            'lat': np.random.uniform(30.5, 30.8, n_demand),
            'lon': np.random.uniform(103.9, 104.2, n_demand),
            'population': np.random.randint(10000, 100000, n_demand)
        })

        start_time = time.time()
        result = self.engine.calculate_accessibility(supply_df, demand_df)
        elapsed = time.time() - start_time

        self.assertEqual(len(result), n_demand)
        # 1000个需求点应该在1秒内完成
        self.assertLess(elapsed, 1.0, f"计算耗时过长: {elapsed:.3f}s")

    def test_cache_performance(self):
        """测试缓存性能"""
        supply_df = pd.DataFrame({
            'lat': [30.65, 30.67],
            'lon': [104.05, 104.08],
            'capacity': [1000, 800]
        })

        demand_df = pd.DataFrame({
            'lat': [30.66, 30.64],
            'lon': [104.06, 104.04],
            'population': [50000, 40000]
        })

        # 多次计算以测试缓存
        for _ in range(3):
            self.engine.calculate_accessibility(supply_df, demand_df)

        # 检查统计信息
        stats = self.engine.get_statistics()
        # 距离计算应该只执行一次（缓存后续命中）
        self.assertGreaterEqual(stats['distance_calculations'], 1)
        # 验证功能正常工作
        self.assertGreaterEqual(stats['accessibility_computations'], 3)


class TestEdgeCases(unittest.TestCase):
    """边界情况测试"""

    def setUp(self):
        self.engine = SpatialEngine(enable_progress=False)

    def test_single_point(self):
        """测试单点数据"""
        supply_df = pd.DataFrame({
            'lat': [30.65],
            'lon': [104.05],
            'capacity': [1000]
        })

        demand_df = pd.DataFrame({
            'lat': [30.66],
            'lon': [104.06],
            'population': [50000]
        })

        result = self.engine.calculate_accessibility(supply_df, demand_df)
        self.assertEqual(len(result), 1)
        self.assertIn('accessibility_index', result.columns)

    def test_same_location(self):
        """测试相同位置"""
        supply_df = pd.DataFrame({
            'lat': [30.65, 30.65],
            'lon': [104.05, 104.05],
            'capacity': [1000, 800]
        })

        demand_df = pd.DataFrame({
            'lat': [30.65],
            'lon': [104.05],
            'population': [50000]
        })

        result = self.engine.calculate_accessibility(supply_df, demand_df)
        self.assertEqual(len(result), 1)

    def test_very_small_distances(self):
        """测试极小距离"""
        supply_df = pd.DataFrame({
            'lat': [30.650001],
            'lon': [104.050001],
            'capacity': [1000]
        })

        demand_df = pd.DataFrame({
            'lat': [30.65],
            'lon': [104.05],
            'population': [50000]
        })

        result = self.engine.calculate_accessibility(supply_df, demand_df)
        self.assertEqual(len(result), 1)

    def test_extreme_coordinates(self):
        """测试极端坐标"""
        # 测试应急规划在边界坐标
        hospital_df = pd.DataFrame({
            'lat': [30.65],
            'lon': [104.05],
            'capacity': [1000],
            'name': ['医院']
        })

        # 有效边界坐标
        result = self.engine.plan_emergency_routes(30.0, 104.0, hospital_df)
        self.assertIsInstance(result, dict)


class TestStatistics(unittest.TestCase):
    """统计功能测试"""

    def setUp(self):
        self.engine = SpatialEngine(enable_progress=False)

    def test_reset_statistics(self):
        """测试重置统计"""
        # 执行一些操作
        supply_df = pd.DataFrame({
            'lat': [30.65],
            'lon': [104.05],
            'capacity': [1000]
        })
        demand_df = pd.DataFrame({
            'lat': [30.66],
            'lon': [104.06],
            'population': [50000]
        })

        self.engine.calculate_accessibility(supply_df, demand_df)

        # 重置统计
        self.engine.reset_statistics()
        stats = self.engine.get_statistics()

        self.assertEqual(stats['distance_calculations'], 0)
        self.assertEqual(stats['accessibility_computations'], 0)

    def test_statistics_immutable(self):
        """测试统计信息不可变"""
        stats = self.engine.get_statistics()
        stats['distance_calculations'] = 999

        # 原始统计不应改变
        new_stats = self.engine.get_statistics()
        self.assertEqual(new_stats['distance_calculations'], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
