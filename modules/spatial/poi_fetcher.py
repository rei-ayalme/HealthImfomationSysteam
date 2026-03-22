import requests
import pandas as pd
import json
import time
import os
import math
from coord_convert.transform import gcj2wgs
from config.settings import SETTINGS

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
    
    # 将获取的成都三甲医院 POI 数据转换为 geojson 保存到本地
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
        geojson_path = os.path.join(SETTINGS.BASE_DIR, "data", "geojson", "chengdu_hospitals.geojson")
        try:
            with open(geojson_path, "w", encoding="utf-8") as f:
                json.dump(geojson_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 成功将成都三甲医院数据保存至 GeoJSON: {geojson_path}")
        except Exception as e:
            print(f"保存 GeoJSON 失败: {e}")

    return df

def fetch_community_demand(city="成都市"):
    """模拟获取成都市街道/社区中心的经纬度及预估人口数据
       实际中应从人口普查网格或高德行政区划查询接口获取，此处以部分主要区县模拟
    """
    # 模拟成都市几个主要区域的中心点及人口数据
    communities = [
        {'name': '锦江区', 'lon': 104.083472, 'lat': 30.656545, 'population': 900000, 'elderly_ratio': 0.18},
        {'name': '青羊区', 'lon': 104.062086, 'lat': 30.673896, 'population': 950000, 'elderly_ratio': 0.20},
        {'name': '金牛区', 'lon': 104.051833, 'lat': 30.690859, 'population': 1200000, 'elderly_ratio': 0.22},
        {'name': '武侯区', 'lon': 104.04313, 'lat': 30.64223, 'population': 1100000, 'elderly_ratio': 0.15},
        {'name': '成华区', 'lon': 104.044558, 'lat': 30.64267, 'population': 1300000, 'elderly_ratio': 0.16},
        {'name': '高新区', 'lon': 104.043598, 'lat': 30.581561, 'population': 1500000, 'elderly_ratio': 0.12},
    ]
    return pd.DataFrame(communities)

if __name__ == "__main__":
    supply_df = fetch_hospital_pois()
    print("获取到的医院数据 (Supply):")
    print(supply_df.head())
    
    demand_df = fetch_community_demand()
    print("\n获取到的需求数据 (Demand):")
    print(demand_df.head())
