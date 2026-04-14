"""
SpatialUtils 单元测试

测试覆盖：
1. 距离计算函数
2. 坐标转换函数
3. 多边形操作函数
4. 便捷函数接口
"""

import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.spatial_utils import SpatialUtils, haversine_distance, euclidean_distance


class TestHaversineDistance(unittest.TestCase):
    """Haversine距离计算测试"""

    def test_basic_distance_calculation(self):
        """测试基本距离计算"""
        # 北京到上海的大致距离
        dist = SpatialUtils.haversine_distance(39.9042, 116.4074, 31.2304, 121.4737)
        # 实际距离约1067公里，允许1%误差
        self.assertAlmostEqual(dist, 1067, delta=20)

    def test_same_point_zero_distance(self):
        """测试同一点距离为0"""
        dist = SpatialUtils.haversine_distance(39.9, 116.4, 39.9, 116.4)
        self.assertEqual(dist, 0.0)

    def test_array_input(self):
        """测试数组输入"""
        lat1 = np.array([39.9, 31.2])
        lon1 = np.array([116.4, 121.5])
        lat2 = np.array([31.2, 39.9])
        lon2 = np.array([121.5, 116.4])

        distances = SpatialUtils.haversine_distance(lat1, lon1, lat2, lon2)

        self.assertEqual(len(distances), 2)
        self.assertAlmostEqual(distances[0], distances[1], delta=0.1)

    def test_symmetry(self):
        """测试距离对称性"""
        dist1 = SpatialUtils.haversine_distance(39.9, 116.4, 31.2, 121.5)
        dist2 = SpatialUtils.haversine_distance(31.2, 121.5, 39.9, 116.4)
        self.assertAlmostEqual(dist1, dist2, places=10)

    def test_known_distance(self):
        """测试已知距离"""
        # 赤道上一度的距离约为111.32公里
        dist = SpatialUtils.haversine_distance(0, 0, 0, 1)
        self.assertAlmostEqual(dist, 111.32, delta=1)


class TestEuclideanDistance(unittest.TestCase):
    """欧几里得距离计算测试"""

    def test_basic_calculation(self):
        """测试基本计算"""
        dist = SpatialUtils.euclidean_distance(0, 0, 3, 4)
        self.assertEqual(dist, 5.0)

    def test_same_point(self):
        """测试同一点"""
        dist = SpatialUtils.euclidean_distance(1, 1, 1, 1)
        self.assertEqual(dist, 0.0)

    def test_array_input(self):
        """测试数组输入"""
        x1 = np.array([0, 1, 2])
        y1 = np.array([0, 1, 2])
        x2 = np.array([3, 4, 5])
        y2 = np.array([4, 5, 6])

        distances = SpatialUtils.euclidean_distance(x1, y1, x2, y2)

        self.assertEqual(len(distances), 3)
        self.assertAlmostEqual(distances[0], 5.0)


class TestManhattanDistance(unittest.TestCase):
    """曼哈顿距离计算测试"""

    def test_basic_calculation(self):
        """测试基本计算"""
        dist = SpatialUtils.manhattan_distance(0, 0, 3, 4)
        self.assertEqual(dist, 7.0)

    def test_same_point(self):
        """测试同一点"""
        dist = SpatialUtils.manhattan_distance(1, 1, 1, 1)
        self.assertEqual(dist, 0.0)


class TestPointInPolygon(unittest.TestCase):
    """点在多边形内测试"""

    def test_point_inside(self):
        """测试点在内部"""
        polygon = [(0, 0), (0, 10), (10, 10), (10, 0)]
        self.assertTrue(SpatialUtils.is_point_in_polygon(5, 5, polygon))

    def test_point_outside(self):
        """测试点在外部"""
        polygon = [(0, 0), (0, 10), (10, 10), (10, 0)]
        self.assertFalse(SpatialUtils.is_point_in_polygon(15, 15, polygon))

    def test_point_on_vertex(self):
        """测试点在顶点上"""
        polygon = [(0, 0), (0, 10), (10, 10), (10, 0)]
        # 点在顶点上通常被认为在内部或边界上
        result = SpatialUtils.is_point_in_polygon(0, 0, polygon)
        self.assertIsInstance(result, bool)

    def test_invalid_polygon(self):
        """测试无效多边形"""
        polygon = [(0, 0), (10, 10)]  # 少于3个点
        self.assertFalse(SpatialUtils.is_point_in_polygon(5, 5, polygon))


class TestBearing(unittest.TestCase):
    """方位角计算测试"""

    def test_north_bearing(self):
        """测试正北方位"""
        bearing = SpatialUtils.calculate_bearing(0, 0, 10, 0)
        self.assertAlmostEqual(bearing, 0.0, delta=1)

    def test_east_bearing(self):
        """测试正东方位"""
        bearing = SpatialUtils.calculate_bearing(0, 0, 0, 10)
        self.assertAlmostEqual(bearing, 90.0, delta=1)

    def test_south_bearing(self):
        """测试正南方位"""
        bearing = SpatialUtils.calculate_bearing(10, 0, 0, 0)
        self.assertAlmostEqual(bearing, 180.0, delta=1)

    def test_west_bearing(self):
        """测试正西方位"""
        bearing = SpatialUtils.calculate_bearing(0, 10, 0, 0)
        self.assertAlmostEqual(bearing, 270.0, delta=1)

    def test_bearing_range(self):
        """测试方位角范围"""
        bearing = SpatialUtils.calculate_bearing(39.9, 116.4, 31.2, 121.5)
        self.assertGreaterEqual(bearing, 0)
        self.assertLess(bearing, 360)


class TestDestinationPoint(unittest.TestCase):
    """目标点计算测试"""

    def test_north_destination(self):
        """测试向北移动"""
        lat2, lon2 = SpatialUtils.destination_point(0, 0, 0, 111.32)
        self.assertAlmostEqual(lat2, 1.0, delta=0.1)
        self.assertAlmostEqual(lon2, 0.0, delta=0.1)

    def test_east_destination(self):
        """测试向东移动"""
        lat2, lon2 = SpatialUtils.destination_point(0, 0, 90, 111.32)
        self.assertAlmostEqual(lat2, 0.0, delta=0.1)
        self.assertAlmostEqual(lon2, 1.0, delta=0.1)

    def test_zero_distance(self):
        """测试零距离"""
        lat2, lon2 = SpatialUtils.destination_point(39.9, 116.4, 90, 0)
        self.assertAlmostEqual(lat2, 39.9, places=5)
        self.assertAlmostEqual(lon2, 116.4, places=5)


class TestCoordinateConversion(unittest.TestCase):
    """坐标转换测试"""

    def test_roundtrip_conversion(self):
        """测试往返转换"""
        lat, lon = 39.9, 116.4
        x, y, z = SpatialUtils.coordinate_to_cartesian(lat, lon)
        lat2, lon2 = SpatialUtils.cartesian_to_coordinate(x, y, z)

        self.assertAlmostEqual(lat, lat2, places=5)
        self.assertAlmostEqual(lon, lon2, places=5)

    def test_unit_sphere(self):
        """测试单位球面上的点"""
        x, y, z = SpatialUtils.coordinate_to_cartesian(0, 0, radius=1.0)
        self.assertAlmostEqual(x, 1.0)
        self.assertAlmostEqual(y, 0.0)
        self.assertAlmostEqual(z, 0.0)

    def test_poles(self):
        """测试极点"""
        # 北极
        x, y, z = SpatialUtils.coordinate_to_cartesian(90, 0)
        self.assertAlmostEqual(z, 1.0, places=5)

        # 南极
        x, y, z = SpatialUtils.coordinate_to_cartesian(-90, 0)
        self.assertAlmostEqual(z, -1.0, places=5)


class TestGCJ02WGS84(unittest.TestCase):
    """GCJ-02与WGS-84转换测试"""

    def test_outside_china_no_change(self):
        """测试中国范围外坐标不变"""
        lat, lon = 40.7, -74.0  # 纽约
        lat2, lon2 = SpatialUtils.gcj02_to_wgs84(lat, lon)
        self.assertEqual(lat, lat2)
        self.assertEqual(lon, lon2)

    def test_inside_china_conversion(self):
        """测试中国范围内转换"""
        lat, lon = 39.9, 116.4  # 北京
        lat2, lon2 = SpatialUtils.gcj02_to_wgs84(lat, lon)
        # 应该有偏移
        self.assertNotEqual((lat, lon), (lat2, lon2))

    def test_roundtrip_conversion(self):
        """测试往返转换"""
        lat_orig, lon_orig = 31.2304, 121.4737  # 上海

        # GCJ-02 -> WGS-84 -> GCJ-02
        lat_wgs, lon_wgs = SpatialUtils.gcj02_to_wgs84(lat_orig, lon_orig)
        lat_gcj, lon_gcj = SpatialUtils.wgs84_to_gcj02(lat_wgs, lon_wgs)

        # 允许小误差（约1e-5度，约1米精度）
        self.assertAlmostEqual(lat_orig, lat_gcj, delta=1e-4)
        self.assertAlmostEqual(lon_orig, lon_gcj, delta=1e-4)


class TestPolygonArea(unittest.TestCase):
    """多边形面积测试"""

    def test_square_area(self):
        """测试正方形面积"""
        # 在赤道附近1度x1度的正方形
        polygon = [(0, 0), (0, 1), (1, 1), (1, 0)]
        area = SpatialUtils.calculate_polygon_area(polygon)
        # 约12364平方公里
        self.assertGreater(area, 10000)
        self.assertLess(area, 15000)

    def test_invalid_polygon(self):
        """测试无效多边形"""
        polygon = [(0, 0), (10, 10)]
        area = SpatialUtils.calculate_polygon_area(polygon)
        self.assertEqual(area, 0.0)


class TestCentroid(unittest.TestCase):
    """重心计算测试"""

    def test_two_points(self):
        """测试两点重心"""
        points = [(0, 0), (10, 0)]
        lat, lon = SpatialUtils.calculate_centroid(points)
        self.assertAlmostEqual(lat, 5.0, delta=0.5)
        self.assertAlmostEqual(lon, 0.0, delta=0.1)

    def test_empty_list(self):
        """测试空列表"""
        lat, lon = SpatialUtils.calculate_centroid([])
        self.assertEqual(lat, 0.0)
        self.assertEqual(lon, 0.0)


class TestDistanceMatrix(unittest.TestCase):
    """距离矩阵测试"""

    def test_basic_matrix(self):
        """测试基本矩阵计算"""
        points1 = np.array([[39.9, 116.4], [31.2, 121.5]])
        points2 = np.array([[30.5, 114.3], [23.1, 113.2]])

        matrix = SpatialUtils.distance_matrix(points1, points2)

        self.assertEqual(matrix.shape, (2, 2))
        self.assertTrue(np.all(matrix >= 0))

    def test_haversine_metric(self):
        """测试Haversine度量"""
        points1 = np.array([[0, 0], [0, 1]])
        points2 = np.array([[0, 0], [0, 1]])

        matrix = SpatialUtils.distance_matrix(points1, points2, metric="haversine")

        # 对角线应该接近0
        self.assertAlmostEqual(matrix[0, 0], 0, delta=1)
        self.assertAlmostEqual(matrix[1, 1], 0, delta=1)

    def test_euclidean_metric(self):
        """测试欧几里得度量"""
        points1 = np.array([[0, 0], [3, 4]])
        points2 = np.array([[0, 0], [3, 4]])

        matrix = SpatialUtils.distance_matrix(points1, points2, metric="euclidean")

        self.assertAlmostEqual(matrix[0, 1], 5.0)
        self.assertAlmostEqual(matrix[1, 0], 5.0)

    def test_invalid_metric(self):
        """测试无效度量"""
        points1 = np.array([[0, 0]])
        points2 = np.array([[0, 0]])

        with self.assertRaises(ValueError):
            SpatialUtils.distance_matrix(points1, points2, metric="invalid")


class TestConvenienceFunctions(unittest.TestCase):
    """便捷函数测试"""

    def test_haversine_convenience(self):
        """测试Haversine便捷函数"""
        dist1 = haversine_distance(39.9, 116.4, 31.2, 121.5)
        dist2 = SpatialUtils.haversine_distance(39.9, 116.4, 31.2, 121.5)
        self.assertEqual(dist1, dist2)

    def test_euclidean_convenience(self):
        """测试欧几里得便捷函数"""
        dist1 = euclidean_distance(0, 0, 3, 4)
        dist2 = SpatialUtils.euclidean_distance(0, 0, 3, 4)
        self.assertEqual(dist1, dist2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
