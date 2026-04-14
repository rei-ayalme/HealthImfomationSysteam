"""
空间计算工具模块 (Spatial Utilities)

纯粹的数学与地理空间计算工具集，专注于提供基础空间度量与转换功能。
不包含任何特定业务领域（如医疗、教育等）的逻辑或依赖。

设计原则：
- 高内聚：所有函数都是纯粹的空间计算
- 低耦合：不依赖业务模块，仅使用基础数学库
- 通用性：可被项目中任何需要空间计算的模块直接调用

依赖：
    - numpy: 数值计算
    - typing: 类型注解

坐标系转换使用示例:
    >>> from utils.spatial_utils import SpatialUtils
    >>> 
    >>> # WGS84坐标系 -> 百度坐标系(BD-09)
    >>> lat, lon = 39.90923, 116.397428  # 天安门WGS84坐标
    >>> bd_lat, bd_lon = SpatialUtils.wgs84_to_bd09(lat, lon)
    >>> print(f"BD-09: {bd_lon:.6f}, {bd_lat:.6f}")
    
    >>> # 百度坐标系(BD-09) -> WGS84坐标系
    >>> wgs_lat, wgs_lon = SpatialUtils.bd09_to_wgs84(bd_lat, bd_lon)
    >>> print(f"WGS84: {wgs_lon:.6f}, {wgs_lat:.6f}")
    
    >>> # 火星坐标系(GCJ-02) <-> 百度坐标系(BD-09)
    >>> gcj_lat, gcj_lon = 31.2304, 121.4737  # 上海GCJ-02坐标
    >>> bd_lat, bd_lon = SpatialUtils.gcj02_to_bd09(gcj_lat, gcj_lon)
    >>> gcj_back_lat, gcj_back_lon = SpatialUtils.bd09_to_gcj02(bd_lat, bd_lon)
    
    >>> # WGS84 <-> 火星坐标系(GCJ-02)
    >>> gcj_lat, gcj_lon = SpatialUtils.wgs84_to_gcj02(wgs_lat, wgs_lon)
    >>> wgs_back_lat, wgs_back_lon = SpatialUtils.gcj02_to_wgs84(gcj_lat, gcj_lon)

    >>> # 便捷函数（模块级别直接调用）
    >>> from utils.spatial_utils import wgs84_to_bd09, bd09_to_wgs84
    >>> bd_lat, bd_lon = wgs84_to_bd09(39.90923, 116.397428)

中文地址转坐标（使用数据加载器）:
    >>> from modules.data.loader import DataLoader
    >>> loader = DataLoader()
    >>> # 需要配置高德地图API Key
    >>> coords = loader.fetch_coordinates_by_address("北京市朝阳区朝阳公园")
    >>> print(coords)  # "116.4890,39.9350" (GCJ-02火星坐标系)
    >>> 
    >>> # 如需WGS84坐标，进行转换
    >>> from utils.spatial_utils import gcj02_to_wgs84
    >>> lon, lat = map(float, coords.split(','))
    >>> wgs_lat, wgs_lon = gcj02_to_wgs84(lat, lon)

坐标系说明:
    - WGS84: 国际标准坐标系，GPS设备返回的坐标
    - GCJ-02: 火星坐标系，高德、谷歌等中国地图使用
    - BD-09: 百度坐标系，百度地图使用
    
    注意: 中国境内地图服务使用GCJ-02或BD-09（均经过加密偏移）
"""

from typing import Union, Tuple, List, Optional
import numpy as np


class SpatialUtils:
    """
    纯粹的空间与几何计算工具箱

    提供标准化的空间度量与转换功能，像一把标准化的卷尺，
    专注于基础计算而不涉及业务逻辑。
    """

    # 地球平均半径（公里）
    EARTH_RADIUS_KM: float = 6371.0

    @staticmethod
    def haversine_distance(
        lat1: Union[float, np.ndarray],
        lon1: Union[float, np.ndarray],
        lat2: Union[float, np.ndarray],
        lon2: Union[float, np.ndarray]
    ) -> Union[float, np.ndarray]:
        """
        计算地球上两点间的球面距离（Haversine公式）

        使用Haversine公式计算球面上两点间的最短距离（大圆距离）。
        适用于短距离和长距离计算，精度在0.5%以内。

        公式：
            a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlon/2)
            c = 2 * atan2(√a, √(1-a))
            distance = R * c

        参数:
            lat1: 第一点纬度（度），范围[-90, 90]
            lon1: 第一点经度（度），范围[-180, 180]
            lat2: 第二点纬度（度），范围[-90, 90]
            lon2: 第二点经度（度），范围[-180, 180]

        返回:
            两点间距离（公里），支持标量或数组输入

        示例:
            >>> # 计算两点距离
            >>> dist = SpatialUtils.haversine_distance(39.9042, 116.4074, 31.2304, 121.4737)
            >>> print(f"北京到上海距离: {dist:.2f} km")
            
            >>> # 批量计算
            >>> lat1 = np.array([39.9, 31.2])
            >>> lon1 = np.array([116.4, 121.5])
            >>> lat2 = np.array([31.2, 39.9])
            >>> lon2 = np.array([121.5, 116.4])
            >>> distances = SpatialUtils.haversine_distance(lat1, lon1, lat2, lon2)
        """
        R = SpatialUtils.EARTH_RADIUS_KM

        # 转换为弧度
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Haversine公式
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return R * c

    @staticmethod
    def euclidean_distance(
        x1: Union[float, np.ndarray],
        y1: Union[float, np.ndarray],
        x2: Union[float, np.ndarray],
        y2: Union[float, np.ndarray]
    ) -> Union[float, np.ndarray]:
        """
        计算欧几里得距离（平面距离）

        适用于投影坐标系下的距离计算，或平面几何问题。

        公式:
            distance = √((x2-x1)² + (y2-y1)²)

        参数:
            x1: 第一点x坐标
            y1: 第一点y坐标
            x2: 第二点x坐标
            y2: 第二点y坐标

        返回:
            欧几里得距离，支持标量或数组输入

        示例:
            >>> dist = SpatialUtils.euclidean_distance(0, 0, 3, 4)
            >>> print(dist)  # 5.0
        """
        return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    @staticmethod
    def manhattan_distance(
        x1: Union[float, np.ndarray],
        y1: Union[float, np.ndarray],
        x2: Union[float, np.ndarray],
        y2: Union[float, np.ndarray]
    ) -> Union[float, np.ndarray]:
        """
        计算曼哈顿距离（城市街区距离）

        适用于网格状路径规划，如城市街道导航。

        公式:
            distance = |x2-x1| + |y2-y1|

        参数:
            x1: 第一点x坐标
            y1: 第一点y坐标
            x2: 第二点x坐标
            y2: 第二点y坐标

        返回:
            曼哈顿距离，支持标量或数组输入

        示例:
            >>> dist = SpatialUtils.manhattan_distance(0, 0, 3, 4)
            >>> print(dist)  # 7.0
        """
        return np.abs(x2 - x1) + np.abs(y2 - y1)

    @staticmethod
    def is_point_in_polygon(
        lat: float,
        lon: float,
        polygon_coords: List[Tuple[float, float]]
    ) -> bool:
        """
        判断一个经纬度坐标是否在多边形内（射线法）

        从点向右发射射线，计算与多边形边界的交点数量。
        奇数个交点在内部，偶数个在外部。

        参数:
            lat: 点纬度（度）
            lon: 点经度（度）
            polygon_coords: 多边形顶点坐标列表 [(lat1, lon1), (lat2, lon2), ...]

        返回:
            True如果在多边形内部，False在外部

        示例:
            >>> polygon = [(0, 0), (0, 10), (10, 10), (10, 0)]
            >>> SpatialUtils.is_point_in_polygon(5, 5, polygon)
            True
            >>> SpatialUtils.is_point_in_polygon(15, 15, polygon)
            False
        """
        n = len(polygon_coords)
        if n < 3:
            return False

        inside = False
        j = n - 1

        for i in range(n):
            xi, yi = polygon_coords[i][1], polygon_coords[i][0]
            xj, yj = polygon_coords[j][1], polygon_coords[j][0]

            if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside

    @staticmethod
    def calculate_bearing(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        计算从点1到点2的方位角（前进方向）

        方位角是从正北方向顺时针旋转到目标方向的角度。

        参数:
            lat1: 起点纬度（度）
            lon1: 起点经度（度）
            lat2: 终点纬度（度）
            lon2: 终点经度（度）

        返回:
            方位角（度），范围[0, 360)

        示例:
            >>> bearing = SpatialUtils.calculate_bearing(39.9, 116.4, 31.2, 121.5)
            >>> print(f"方位角: {bearing:.2f}°")
        """
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(np.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2_rad - lon1_rad

        x = np.sin(dlon) * np.cos(lat2_rad)
        y = np.cos(lat1_rad) * np.sin(lat2_rad) - np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(dlon)

        bearing_rad = np.arctan2(x, y)
        bearing_deg = np.degrees(bearing_rad)
        return (bearing_deg + 360) % 360

    @staticmethod
    def destination_point(
        lat: float,
        lon: float,
        bearing: float,
        distance_km: float
    ) -> Tuple[float, float]:
        """
        根据起点、方位角和距离计算目标点坐标

        参数:
            lat: 起点纬度（度）
            lon: 起点经度（度）
            bearing: 方位角（度），从正北顺时针
            distance_km: 距离（公里）

        返回:
            (目标纬度, 目标经度) 元组

        示例:
            >>> lat2, lon2 = SpatialUtils.destination_point(39.9, 116.4, 90, 100)
            >>> print(f"向东100公里后的坐标: ({lat2:.4f}, {lon2:.4f})")
        """
        R = SpatialUtils.EARTH_RADIUS_KM
        lat_rad, lon_rad = np.radians(lat), np.radians(lon)
        bearing_rad = np.radians(bearing)

        lat2_rad = np.arcsin(
            np.sin(lat_rad) * np.cos(distance_km / R) +
            np.cos(lat_rad) * np.sin(distance_km / R) * np.cos(bearing_rad)
        )
        lon2_rad = lon_rad + np.arctan2(
            np.sin(bearing_rad) * np.sin(distance_km / R) * np.cos(lat_rad),
            np.cos(distance_km / R) - np.sin(lat_rad) * np.sin(lat2_rad)
        )

        return np.degrees(lat2_rad), np.degrees(lon2_rad)

    @staticmethod
    def coordinate_to_cartesian(
        lat: float,
        lon: float,
        radius: float = 1.0
    ) -> Tuple[float, float, float]:
        """
        将经纬度转换为三维笛卡尔坐标

        参数:
            lat: 纬度（度）
            lon: 经度（度）
            radius: 球体半径，默认为1（单位球）

        返回:
            (x, y, z) 笛卡尔坐标元组

        示例:
            >>> x, y, z = SpatialUtils.coordinate_to_cartesian(0, 0)
            >>> print(f"笛卡尔坐标: ({x:.4f}, {y:.4f}, {z:.4f})")
        """
        lat_rad, lon_rad = np.radians(lat), np.radians(lon)
        x = radius * np.cos(lat_rad) * np.cos(lon_rad)
        y = radius * np.cos(lat_rad) * np.sin(lon_rad)
        z = radius * np.sin(lat_rad)
        return x, y, z

    @staticmethod
    def cartesian_to_coordinate(
        x: float,
        y: float,
        z: float
    ) -> Tuple[float, float]:
        """
        将三维笛卡尔坐标转换为经纬度

        参数:
            x: x坐标
            y: y坐标
            z: z坐标

        返回:
            (纬度, 经度) 元组（度）

        示例:
            >>> lat, lon = SpatialUtils.cartesian_to_coordinate(1, 0, 0)
            >>> print(f"经纬度: ({lat:.4f}, {lon:.4f})")
        """
        radius = np.sqrt(x**2 + y**2 + z**2)
        lat = np.degrees(np.arcsin(z / radius))
        lon = np.degrees(np.arctan2(y, x))
        return lat, lon

    @staticmethod
    def gcj02_to_wgs84(lat: float, lon: float) -> Tuple[float, float]:
        """
        将火星坐标系（GCJ-02）转换为WGS-84坐标系

        中国国内地图（如高德、腾讯）使用GCJ-02坐标系，
        需要转换为国际标准WGS-84坐标系。

        参数:           lat: GCJ-02纬度（度）
            lon: GCJ-02经度（度）

        返回:
            (WGS-84纬度, WGS-84经度) 元组

        示例:
            >>> wgs_lat, wgs_lon = SpatialUtils.gcj02_to_wgs84(31.2304, 121.4737)
            >>> print(f"WGS-84坐标: ({wgs_lat:.6f}, {wgs_lon:.6f})")
        """
        if not SpatialUtils._is_in_china(lat, lon):
            return lat, lon

        dlat, dlon = SpatialUtils._delta_lat_lon(lat, lon)
        return lat - dlat, lon - dlon

    @staticmethod
    def wgs84_to_gcj02(lat: float, lon: float) -> Tuple[float, float]:
        """
        将WGS-84坐标系转换为火星坐标系（GCJ-02）

        参数:
            lat: WGS-84纬度（度）
            lon: WGS-84经度（度）

        返回:
            (GCJ-02纬度, GCJ-02经度) 元组

        示例:
            >>> gcj_lat, gcj_lon = SpatialUtils.wgs84_to_gcj02(31.2304, 121.4737)
            >>> print(f"GCJ-02坐标: ({gcj_lat:.6f}, {gcj_lon:.6f})")
        """
        if not SpatialUtils._is_in_china(lat, lon):
            return lat, lon

        dlat, dlon = SpatialUtils._delta_lat_lon(lat, lon)
        return lat + dlat, lon + dlon

    @staticmethod
    def _delta_lat_lon(lat: float, lon: float) -> Tuple[float, float]:
        """
        计算GCJ-02与WGS-84之间的偏移量（内部辅助函数）

        参数:           lat: 纬度（度）
            lon: 经度（度）

        返回:
            (纬度偏移量, 经度偏移量) 元组
        """
        # 常量定义
        a = 6378245.0  # 长半轴
        ee = 0.00669342162296594323  # 偏心率平方

        lat_rad = np.radians(lat)
        magic = np.sin(lat_rad)
        magic = 1 - ee * magic * magic
        sqrt_magic = np.sqrt(magic)

        dlat = SpatialUtils._transform_lat(lon - 105.0, lat - 35.0)
        dlon = SpatialUtils._transform_lon(lon - 105.0, lat - 35.0)

        dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrt_magic) * np.pi)
        dlon = (dlon * 180.0) / (a / sqrt_magic * np.cos(lat_rad) * np.pi)

        return dlat, dlon

    @staticmethod
    def _transform_lat(x: float, y: float) -> float:
        """纬度转换辅助函数"""
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * np.sqrt(np.abs(x))
        ret += (20.0 * np.sin(6.0 * x * np.pi) + 20.0 * np.sin(2.0 * x * np.pi)) * 2.0 / 3.0
        ret += (20.0 * np.sin(y * np.pi) + 40.0 * np.sin(y / 3.0 * np.pi)) * 2.0 / 3.0
        ret += (160.0 * np.sin(y / 12.0 * np.pi) + 320 * np.sin(y * np.pi / 30.0)) * 2.0 / 3.0
        return ret

    @staticmethod
    def _transform_lon(x: float, y: float) -> float:
        """经度转换辅助函数"""
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * np.sqrt(np.abs(x))
        ret += (20.0 * np.sin(6.0 * x * np.pi) + 20.0 * np.sin(2.0 * x * np.pi)) * 2.0 / 3.0
        ret += (20.0 * np.sin(x * np.pi) + 40.0 * np.sin(x / 3.0 * np.pi)) * 2.0 / 3.0
        ret += (150.0 * np.sin(x / 12.0 * np.pi) + 300.0 * np.sin(x / 30.0 * np.pi)) * 2.0 / 3.0
        return ret

    @staticmethod
    def _is_in_china(lat: float, lon: float) -> bool:
        """
        粗略判断坐标是否在中国范围内（内部辅助函数）

        参数:
            lat: 纬度（度）
            lon: 经度（度）

        返回:
            True如果在中国范围内
        """
        return 0.83 < lat < 55.0 and 72.0 < lon < 138.0

    # ========== 百度坐标系(BD-09)转换方法 ==========

    @staticmethod
    def gcj02_to_bd09(lat: float, lon: float) -> Tuple[float, float]:
        """
        火星坐标系(GCJ-02)转百度坐标系(BD-09)

        高德、谷歌等使用GCJ-02坐标系，百度地图使用BD-09坐标系。
        此函数用于将GCJ-02坐标转换为百度坐标。

        参数:
            lat: GCJ-02纬度（度）
            lon: GCJ-02经度（度）

        返回:
            (BD-09纬度, BD-09经度) 元组

        示例:
            >>> bd_lat, bd_lon = SpatialUtils.gcj02_to_bd09(31.2304, 121.4737)
            >>> print(f"百度坐标: ({bd_lat:.6f}, {bd_lon:.6f})")
        """
        x_pi = 3.14159265358979324 * 3000.0 / 180.0

        z = np.sqrt(lon * lon + lat * lat) + 0.00002 * np.sin(lat * x_pi)
        theta = np.arctan2(lat, lon) + 0.000003 * np.cos(lon * x_pi)
        bd_lon = z * np.cos(theta) + 0.0065
        bd_lat = z * np.sin(theta) + 0.006

        return bd_lat, bd_lon

    @staticmethod
    def bd09_to_gcj02(lat: float, lon: float) -> Tuple[float, float]:
        """
        百度坐标系(BD-09)转火星坐标系(GCJ-02)

        将百度坐标转换为GCJ-02坐标（高德、谷歌等使用）。

        参数:
            lat: BD-09纬度（度）
            lon: BD-09经度（度）

        返回:
            (GCJ-02纬度, GCJ-02经度) 元组

        示例:
            >>> gcj_lat, gcj_lon = SpatialUtils.bd09_to_gcj02(31.2304, 121.4737)
            >>> print(f"GCJ-02坐标: ({gcj_lat:.6f}, {gcj_lon:.6f})")
        """
        x_pi = 3.14159265358979324 * 3000.0 / 180.0

        x = lon - 0.0065
        y = lat - 0.006
        z = np.sqrt(x * x + y * y) - 0.00002 * np.sin(y * x_pi)
        theta = np.arctan2(y, x) - 0.000003 * np.cos(x * x_pi)
        gg_lon = z * np.cos(theta)
        gg_lat = z * np.sin(theta)

        return gg_lat, gg_lon

    @staticmethod
    def bd09_to_wgs84(lat: float, lon: float) -> Tuple[float, float]:
        """
        百度坐标系(BD-09)转WGS-84坐标系

        通过中间转换：BD-09 -> GCJ-02 -> WGS-84

        参数:
            lat: BD-09纬度（度）
            lon: BD-09经度（度）

        返回:
            (WGS-84纬度, WGS-84经度) 元组

        示例:
            >>> wgs_lat, wgs_lon = SpatialUtils.bd09_to_wgs84(31.2304, 121.4737)
            >>> print(f"WGS-84坐标: ({wgs_lat:.6f}, {wgs_lon:.6f})")
        """
        # BD-09 -> GCJ-02
        gcj_lat, gcj_lon = SpatialUtils.bd09_to_gcj02(lat, lon)
        # GCJ-02 -> WGS-84
        return SpatialUtils.gcj02_to_wgs84(gcj_lat, gcj_lon)

    @staticmethod
    def wgs84_to_bd09(lat: float, lon: float) -> Tuple[float, float]:
        """
        WGS-84坐标系转百度坐标系(BD-09)

        通过中间转换：WGS-84 -> GCJ-02 -> BD-09

        参数:
            lat: WGS-84纬度（度）
            lon: WGS-84经度（度）

        返回:
            (BD-09纬度, BD-09经度) 元组

        示例:
            >>> bd_lat, bd_lon = SpatialUtils.wgs84_to_bd09(31.2304, 121.4737)
            >>> print(f"百度坐标: ({bd_lat:.6f}, {bd_lon:.6f})")
        """
        # WGS-84 -> GCJ-02
        gcj_lat, gcj_lon = SpatialUtils.wgs84_to_gcj02(lat, lon)
        # GCJ-02 -> BD-09
        return SpatialUtils.gcj02_to_bd09(gcj_lat, gcj_lon)

    @staticmethod
    def calculate_polygon_area(polygon_coords: List[Tuple[float, float]]) -> float:
        """
        计算多边形面积（使用球面几何）

        使用球面多边形面积公式，适用于地球表面的多边形。

        参数:           polygon_coords: 多边形顶点坐标列表 [(lat1, lon1), (lat2, lon2), ...]

        返回:
            多边形面积（平方公里）

        示例:
            >>> polygon = [(0, 0), (0, 1), (1, 1), (1, 0)]
            >>> area = SpatialUtils.calculate_polygon_area(polygon)
            >>> print(f"面积: {area:.2f} km²")
        """
        n = len(polygon_coords)
        if n < 3:
            return 0.0

        R = SpatialUtils.EARTH_RADIUS_KM
        area = 0.0

        for i in range(n):
            lat1, lon1 = np.radians(polygon_coords[i])
            lat2, lon2 = np.radians(polygon_coords[(i + 1) % n])
            area += (lon2 - lon1) * (2 + np.sin(lat1) + np.sin(lat2))

        area = abs(area) * R * R / 2.0
        return area

    @staticmethod
    def calculate_centroid(coords: List[Tuple[float, float]]) -> Tuple[float, float]:
        """
        计算一组坐标的重心（几何中心）

        参数:
            coords: 坐标列表 [(lat1, lon1), (lat2, lon2), ...]

        返回:
            (重心纬度, 重心经度) 元组

        示例:
            >>> points = [(39.9, 116.4), (31.2, 121.5), (30.5, 114.3)]
            >>> center_lat, center_lon = SpatialUtils.calculate_centroid(points)
            >>> print(f"重心: ({center_lat:.4f}, {center_lon:.4f})")
        """
        if not coords:
            return 0.0, 0.0

        # 转换为笛卡尔坐标求平均
        x_sum, y_sum, z_sum = 0.0, 0.0, 0.0

        for lat, lon in coords:
            x, y, z = SpatialUtils.coordinate_to_cartesian(lat, lon)
            x_sum += x
            y_sum += y
            z_sum += z

        n = len(coords)
        return SpatialUtils.cartesian_to_coordinate(x_sum / n, y_sum / n, z_sum / n)

    @staticmethod
    def distance_matrix(
        points1: np.ndarray,
        points2: np.ndarray,
        metric: str = "haversine"
    ) -> np.ndarray:
        """
        计算两组点之间的距离矩阵

        参数:
            points1: 第一组点，形状 (n, 2)，每行 [lat, lon]
            points2: 第二组点，形状 (m, 2)，每行 [lat, lon]
            metric: 距离度量方式 ("haversine", "euclidean", "manhattan")

        返回:
            距离矩阵，形状 (n, m)

        示例:
            >>> points_a = np.array([[39.9, 116.4], [31.2, 121.5]])
            >>> points_b = np.array([[30.5, 114.3], [23.1, 113.2]])
            >>> dist_mat = SpatialUtils.distance_matrix(points_a, points_b)
            >>> print(dist_mat.shape)  # (2, 2)
        """
        n = len(points1)
        m = len(points2)
        matrix = np.zeros((n, m))

        for i in range(n):
            for j in range(m):
                lat1, lon1 = points1[i]
                lat2, lon2 = points2[j]

                if metric == "haversine":
                    matrix[i, j] = SpatialUtils.haversine_distance(lat1, lon1, lat2, lon2)
                elif metric == "euclidean":
                    matrix[i, j] = SpatialUtils.euclidean_distance(lat1, lon1, lat2, lon2)
                elif metric == "manhattan":
                    matrix[i, j] = SpatialUtils.manhattan_distance(lat1, lon1, lat2, lon2)
                else:
                    raise ValueError(f"不支持的距离度量: {metric}")

        return matrix


# 便捷函数接口（模块级别直接调用）
def haversine_distance(
    lat1: Union[float, np.ndarray],
    lon1: Union[float, np.ndarray],
    lat2: Union[float, np.ndarray],
    lon2: Union[float, np.ndarray]
) -> Union[float, np.ndarray]:
    """便捷函数：计算Haversine距离"""
    return SpatialUtils.haversine_distance(lat1, lon1, lat2, lon2)


def euclidean_distance(
    x1: Union[float, np.ndarray],
    y1: Union[float, np.ndarray],
    x2: Union[float, np.ndarray],
    y2: Union[float, np.ndarray]
) -> Union[float, np.ndarray]:
    """便捷函数：计算欧几里得距离"""
    return SpatialUtils.euclidean_distance(x1, y1, x2, y2)


def is_point_in_polygon(
    lat: float,
    lon: float,
    polygon_coords: List[Tuple[float, float]]
) -> bool:
    """便捷函数：判断点是否在多边形内"""
    return SpatialUtils.is_point_in_polygon(lat, lon, polygon_coords)


def gcj02_to_wgs84(lat: float, lon: float) -> Tuple[float, float]:
    """便捷函数：GCJ-02转WGS-84"""
    return SpatialUtils.gcj02_to_wgs84(lat, lon)


def wgs84_to_gcj02(lat: float, lon: float) -> Tuple[float, float]:
    """便捷函数：WGS-84转GCJ-02"""
    return SpatialUtils.wgs84_to_gcj02(lat, lon)


def gcj02_to_bd09(lat: float, lon: float) -> Tuple[float, float]:
    """便捷函数：GCJ-02转BD-09（火星坐标系转百度坐标系）"""
    return SpatialUtils.gcj02_to_bd09(lat, lon)


def bd09_to_gcj02(lat: float, lon: float) -> Tuple[float, float]:
    """便捷函数：BD-09转GCJ-02（百度坐标系转火星坐标系）"""
    return SpatialUtils.bd09_to_gcj02(lat, lon)


def bd09_to_wgs84(lat: float, lon: float) -> Tuple[float, float]:
    """便捷函数：BD-09转WGS-84（百度坐标系转WGS-84）"""
    return SpatialUtils.bd09_to_wgs84(lat, lon)


def wgs84_to_bd09(lat: float, lon: float) -> Tuple[float, float]:
    """便捷函数：WGS-84转BD-09（WGS-84转百度坐标系）"""
    return SpatialUtils.wgs84_to_bd09(lat, lon)
