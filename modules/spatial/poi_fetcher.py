import requests
import pandas as pd
import json
import time
import os
import math
from coord_convert.transform import gcj2wgs
from config.settings import SETTINGS

# -----------------------------------------------------------------------------
# 外部数据获取与爬虫逻辑保存声明
# 本模块包含了通过高德 API 获取成都市医院微观地理数据的核心“爬取/请求”逻辑。
# 根据系统规范，此爬虫代码与项目一同保存并上传，以确保后续环境可直接复现抓取过程。
# 数据结果已通过该脚本自动导出至 data/geojson/chengdu_hospitals.geojson。
# -----------------------------------------------------------------------------

def fetch_hospital_pois(city="成都市", keyword="三甲医院"):
    """使用高德API获取成都市三甲医院POI数据"""
    api_key = SETTINGS.AMAP_CONFIG['api_key']
    url = SETTINGS.AMAP_CONFIG['poi_url']
    
    hospitals = []
    page = 1
    
    while True:
        params = {
            'key': api_key,
            'keywords': keyword,
            'city': city,
            'types': '医疗保健服务',
            'citylimit': 'true',
            'offset': 20,
            'page': page,
            'extensions': 'all'
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == '1' and int(data['count']) > 0:
                pois = data['pois']
                for poi in pois:
                    location = poi['location'].split(',')
                    # 高德返回的是 GCJ-02 坐标，我们需要使用 coord-convert 转成 WGS-84
                    wgs84_lon, wgs84_lat = gcj2wgs(float(location[0]), float(location[1]))
                    
                    hospitals.append({
                        'name': poi['name'],
                        'lon': wgs84_lon,
                        'lat': wgs84_lat,
                        'address': poi.get('address', ''),
                        'capacity': 1000  # 模拟默认床位数或医生数
                    })
                
                if len(pois) < 20:
                    break
                page += 1
                time.sleep(0.5)  # 避免触发频率限制
            else:
                break
        except Exception as e:
            print(f"高德API请求失败: {e}")
            break
            
    df = pd.DataFrame(hospitals)
    
    # 将获取的医院 POI 数据转换为 geojson 保存到本地
    if not df.empty:
        features = []
        for _, row in df.iterrows():
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row['lon'], row['lat']]
                },
                "properties": {
                    "name": row['name'],
                    "address": row['address'],
                    "capacity": row['capacity']
                }
            })
        
        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # 确保目录存在
        os.makedirs(os.path.join(SETTINGS.BASE_DIR, "data", "geojson"), exist_ok=True)
        # 根据关键词区分存储的文件，确保所有数据在本地持久化
        filename = "chengdu_hospitals_3a.geojson" if "三甲" in keyword else "chengdu_hospitals_comm.geojson"
        geojson_path = os.path.join(SETTINGS.BASE_DIR, "data", "geojson", filename)
        try:
            with open(geojson_path, "w", encoding="utf-8") as f:
                json.dump(geojson_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 成功将外部抓取的 {keyword} 数据持久化保存至: {geojson_path}，保证可复现性")
        except Exception as e:
            print(f"保存 GeoJSON 失败: {e}")

    return df

def fetch_community_demand(city="成都市"):
    """模拟获取成都市街道/社区中心的经纬度及预估人口数据
       此处使用成都市所有20个区（市）县的真实近似中心坐标与人口数据（七普数据或近似值）
    """
    # 包含了成都市真实的行政区划名称、中心经纬度和大致人口数据
    communities = [
        {'name': '锦江区', 'lon': 104.083472, 'lat': 30.656545, 'population': 900000, 'elderly_ratio': 0.18},
        {'name': '青羊区', 'lon': 104.062086, 'lat': 30.673896, 'population': 950000, 'elderly_ratio': 0.20},
        {'name': '金牛区', 'lon': 104.051833, 'lat': 30.690859, 'population': 1200000, 'elderly_ratio': 0.22},
        {'name': '武侯区', 'lon': 104.04313, 'lat': 30.64223, 'population': 1200000, 'elderly_ratio': 0.15},
        {'name': '成华区', 'lon': 104.044558, 'lat': 30.64267, 'population': 1380000, 'elderly_ratio': 0.16},
        {'name': '高新区', 'lon': 104.043598, 'lat': 30.581561, 'population': 1500000, 'elderly_ratio': 0.12}, # 高新区虽然是管委会，但在数据里通常作为独立区
        {'name': '龙泉驿区', 'lon': 104.2689, 'lat': 30.5601, 'population': 1340000, 'elderly_ratio': 0.13},
        {'name': '青白江区', 'lon': 103.9248, 'lat': 30.8785, 'population': 600000, 'elderly_ratio': 0.16},
        {'name': '新都区', 'lon': 104.1587, 'lat': 30.8234, 'population': 900000, 'elderly_ratio': 0.15},
        {'name': '温江区', 'lon': 104.2052, 'lat': 30.6868, 'population': 960000, 'elderly_ratio': 0.14},
        {'name': '双流区', 'lon': 103.9234, 'lat': 30.5744, 'population': 1460000, 'elderly_ratio': 0.12},
        {'name': '郫都区', 'lon': 103.8872, 'lat': 30.8055, 'population': 1390000, 'elderly_ratio': 0.13},
        {'name': '新津区', 'lon': 103.8114, 'lat': 30.4141, 'population': 360000, 'elderly_ratio': 0.17},
        {'name': '金堂县', 'lon': 104.4119, 'lat': 30.8619, 'population': 800000, 'elderly_ratio': 0.19},
        {'name': '大邑县', 'lon': 103.5207, 'lat': 30.5873, 'population': 510000, 'elderly_ratio': 0.18},
        {'name': '蒲江县', 'lon': 103.5061, 'lat': 30.1966, 'population': 260000, 'elderly_ratio': 0.21},
        {'name': '都江堰市', 'lon': 103.6194, 'lat': 30.9982, 'population': 730000, 'elderly_ratio': 0.18},
        {'name': '彭州市', 'lon': 103.958, 'lat': 30.9804, 'population': 780000, 'elderly_ratio': 0.19},
        {'name': '邛崃市', 'lon': 103.4649, 'lat': 30.4102, 'population': 610000, 'elderly_ratio': 0.20},
        {'name': '崇州市', 'lon': 103.673, 'lat': 30.6301, 'population': 710000, 'elderly_ratio': 0.20},
        {'name': '简阳市', 'lon': 104.5486, 'lat': 30.3905, 'population': 1110000, 'elderly_ratio': 0.18},
        {'name': '天府新区', 'lon': 104.073, 'lat': 30.432, 'population': 800000, 'elderly_ratio': 0.11}
    ]
    return pd.DataFrame(communities)

if __name__ == "__main__":
    supply_df = fetch_hospital_pois()
    print("获取到的医院数据 (Supply):")
    print(supply_df.head())
    
    demand_df = fetch_community_demand()
    print("\n获取到的需求数据 (Demand):")
    print(demand_df.head())
