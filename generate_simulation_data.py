import os
import json
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import sys
from coord_convert.transform import gcj2wgs

# 把当前项目根目录加入 sys.path 以便导入 config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config.settings import SETTINGS

class PopulationSimulator:
    def __init__(self, num_agents=5000):
        self.num_agents = num_agents
        
        # 1. 加载真实的成都市 GeoJSON 边界
        # 考虑到可能从不同目录执行脚本，确保路径绝对
        base_dir = os.path.dirname(os.path.abspath(__file__))
        geojson_path = os.path.join(base_dir, "data", "geojson", "chengdu_boundary.geojson")
        
        if not os.path.exists(geojson_path):
            print(f"警告：未找到 {geojson_path}，退回使用矩形生成。")
            self.lon = np.random.uniform(103.5, 104.9, num_agents)
            self.lat = np.random.uniform(30.1, 31.4, num_agents)
            self.use_polygon = False
        else:
            gdf = gpd.read_file(geojson_path)
            # 修复几何无效导致的 TopologyException
            gdf.geometry = gdf.geometry.make_valid()
            # 将所有区县的几何图形合并为一个大成都市多边形
            self.city_polygon = gdf.geometry.union_all()
            
            # 2. 获取多边形的经纬度外包框 (Bounding Box)
            self.minx, self.miny, self.maxx, self.maxy = self.city_polygon.bounds
            
            # 3. 严格在多边形内部生成随机初始点
            print("正在使用多边形拒绝采样法生成初始坐标...")
            self.lon, self.lat = self._generate_points_in_polygon(num_agents)
            self.use_polygon = True
        
        # 2. 初始状态：90%健康(0)，10%慢病(1)
        self.states = np.random.choice([0, 1], p=[0.9, 0.1], size=num_agents)
        
        # 3. 基础马尔可夫转移矩阵 (行：当前状态，列：下一状态 0,1,2,3)
        self.transition_matrix = np.array([
            [0.95, 0.04, 0.01, 0.00], # 健康 -> 维持, 慢病, 重症, 死亡
            [0.05, 0.85, 0.08, 0.02], # 慢病 -> 康复, 维持, 重症, 死亡
            [0.00, 0.10, 0.70, 0.20], # 重症 -> 康复, 慢病, 维持, 死亡
            [0.00, 0.00, 0.00, 1.00]  # 死亡 -> 吸收态
        ])
        
        # 4. 加载真实三甲医院坐标 (从 geojson 文件中读取，作为重症患者的聚集点)
        hospitals_geojson_path = os.path.join(base_dir, "data", "geojson", "chengdu_hospitals.geojson")
        self.pois = []
        if os.path.exists(hospitals_geojson_path):
            with open(hospitals_geojson_path, 'r', encoding='utf-8') as f:
                hospital_data = json.load(f)
                for feature in hospital_data.get('features', []):
                    coords = feature.get('geometry', {}).get('coordinates')
                    if coords and len(coords) >= 2:
                        self.pois.append((coords[0], coords[1]))
        
        # 如果读取失败或者文件为空，作为保底使用两个医院坐标
        if not self.pois:
            hx_lon, hx_lat = gcj2wgs(104.063228, 30.64098)
            sy_lon, sy_lat = gcj2wgs(104.041648, 30.665792)
            self.pois = [(hx_lon, hx_lat), (sy_lon, sy_lat)]
            
    def _generate_points_in_polygon(self, num_points):
        """核心算法：拒绝采样法生成多边形内部随机点"""
        lons, lats = [], []
        while len(lons) < num_points:
            # 批量在外包框生成点
            x_rand = np.random.uniform(self.minx, self.maxx, 2000)
            y_rand = np.random.uniform(self.miny, self.maxy, 2000)
            
            for x, y in zip(x_rand, y_rand):
                if len(lons) >= num_points:
                    break
                # 校验点是否在成都市边界内部
                if self.city_polygon.contains(Point(x, y)):
                    lons.append(x)
                    lats.append(y)
                    
        return np.array(lons), np.array(lats)

    def step(self):
        """执行一年的时间步推演"""
        new_states = np.zeros(self.num_agents, dtype=int)
        for i in range(self.num_agents):
            curr_state = self.states[i]
            # 根据转移矩阵概率，计算下一年的状态
            new_states[i] = np.random.choice([0, 1, 2, 3], p=self.transition_matrix[curr_state])
            
            # 如果变成重症(2)，则坐标向最近的医院 POI 移动 (产生聚集效果)
            if new_states[i] == 2:
                # 寻找最近医院 (简化的贪心移动逻辑)
                closest_poi = self.pois[i % len(self.pois)] # 简写，实际可用KDTree
                self.lon[i] = self.lon[i] + (closest_poi[0] - self.lon[i]) * 0.5
                self.lat[i] = self.lat[i] + (closest_poi[1] - self.lat[i]) * 0.5
            
            # 死去的粒子复活成健康状态并在随机位置重生，维持人口总量
            if new_states[i] == 3:
                new_states[i] = 0
                if self.use_polygon:
                    # 为了性能，死亡重生可以稍微简化，或者重新调用采样函数取1个点
                    new_lon, new_lat = self._generate_points_in_polygon(1)
                    self.lon[i] = new_lon[0]
                    self.lat[i] = new_lat[0]
                else:
                    self.lon[i] = np.random.uniform(103.5, 104.9)
                    self.lat[i] = np.random.uniform(30.1, 31.4)

        self.states = new_states
        return self.get_frame_data()

    def get_frame_data(self):
        """打包一帧的数据供前端渲染"""
        # 为了前端 linesGL 尾迹效果，额外打包一下位置信息
        return np.column_stack((self.lon, self.lat, self.states)).tolist()

if __name__ == "__main__":
    # 生成智能体以兼顾性能和效果
    simulator = PopulationSimulator(num_agents=5000)
    frames = {}
    
    print("Generating simulation data...")
    for year in range(2024, 2045):
        frames[str(year)] = simulator.step()
        print(f"Processed year {year}")
        
    output_dir = os.path.join(os.path.dirname(__file__), "frontend", "assets", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "simulation_data.json")
    
    with open(output_file, "w") as f:
        json.dump(frames, f)
        
    print(f"Successfully generated {output_file}")
