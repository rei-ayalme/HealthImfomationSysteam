# main.py
import uvicorn
from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from modules.analysis.disease import DiseaseRiskAnalyzer

# 导入你现有的数据库模块
from db.connection import SessionLocal
from db.models import GlobalHealthMetric

app = FastAPI(title="健康数据分析平台 API")

# 配置 CORS（允许跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 1. 定义 API 接口 (必须放在静态目录挂载前)
# ==========================================

from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    from db.models import User
    
    user = db.query(User).filter(User.username == req.username).first()
    
    if not user or user.password != req.password:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="账号或密码错误")
        
    return {
        "status": "success",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
    }

@app.get("/api/admin/logs")
async def get_system_logs(db: Session = Depends(get_db)):
    from db.models import OWIDFetchLog
    try:
        # 获取最新的100条爬虫与系统日志
        logs = db.query(OWIDFetchLog).order_by(OWIDFetchLog.fetch_time.desc()).limit(100).all()
        log_list = []
        for log in logs:
            log_list.append({
                "id": log.id,
                "timestamp": log.fetch_time.strftime("%Y-%m-%d %H:%M:%S") if log.fetch_time else "",
                "module": "OWID_API",
                "action": f"抓取指标 {log.indicator_id}",
                "status": "success" if log.status else "error",
                "message": f"新增数据 {log.data_count} 条" if log.status else (log.error_msg or "抓取失败")
            })
        return {"status": "success", "data": log_list}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dataset")
async def get_dataset(db: Session = Depends(get_db)):
    try:
        from db.models import AdvancedDiseaseTransition, AdvancedRiskCloud, AdvancedResourceEfficiency
        
        # 为了给前端提供丰富的数据，从多张真实的高级分析表中提取数据
        items = []
        
        # 1. 获取疾病负担数据
        disease_data = db.query(AdvancedDiseaseTransition).limit(20).all()
        # 预先计算 DALYs 归一化 (假定当前取出的最大值作为基准)
        max_dalys = max([d.val for d in disease_data]) if disease_data else 1.0
        if max_dalys == 0: max_dalys = 1.0
        
        for i, d in enumerate(disease_data):
            z_weight = round(0.1 + 0.9 * (d.val / max_dalys), 4)
            items.append({
                "id": f"disease_{d.id}",
                "name": f"{d.cause_name} 疾病负担",
                "type": "disease_burden",
                "typeName": "疾病谱系",
                "topic": "health-indicators",
                "topicName": "健康指标分析",
                "country": d.location_name,
                "year": d.year,
                "value": d.val,
                "unit": 'DALYs',
                "z_weight": z_weight, # 新增 3D 渲染权重
                "status": "success"
            })
            
        # 2. 获取风险归因数据
        risk_data = db.query(AdvancedRiskCloud).limit(20).all()
        for i, r in enumerate(risk_data):
            items.append({
                "id": f"risk_{r.id}",
                "name": f"{r.rei_name} 风险归因",
                "type": "risk_factor",
                "typeName": "风险因素",
                "topic": "health-indicators",
                "topicName": "健康指标分析",
                "country": r.location_name,
                "year": r.year,
                "value": r.paf,
                "unit": 'PAF',
                "status": "success"
            })
            
        # 3. 获取卫生资源效率数据
        resource_data = db.query(AdvancedResourceEfficiency).limit(20).all()
        for i, r in enumerate(resource_data):
            items.append({
                "id": f"resource_{r.id}",
                "name": "卫生资源 DEA 效率",
                "type": "resource_efficiency",
                "typeName": "资源效率",
                "topic": "health-indicators",
                "topicName": "健康指标分析",
                "country": r.location_name,
                "year": r.year,
                "value": r.dea_efficiency if r.dea_efficiency else 0,
                "unit": '指数',
                "status": "success"
            })

        return {"items": items}
    except Exception as e:
        from utils.logger import logger
        logger.exception("数据库查询异常")
        return {"items": []}

@app.get("/api/dataset/{dataset_id}/detail")
async def get_dataset_detail(dataset_id: str, limit: int = 50, db: Session = Depends(get_db)):
    try:
        from db.models import AdvancedDiseaseTransition, AdvancedRiskCloud, AdvancedResourceEfficiency
        
        preview_data = []
        d_meta = {
            "title": f"数据集：{dataset_id}",
            "category": "健康指标",
            "record_count": 0,
            "region_coverage": 0,
            "year_min": 2000,
            "year_max": 2024,
            "latest_updated": "2024-03-21",
            "fields": [
                {"name": "region", "type": "string", "description": "国家/地区"},
                {"name": "year", "type": "int", "description": "年份"},
                {"name": "metric", "type": "string", "description": "指标名称"},
                {"name": "value", "type": "float", "description": "数值"},
                {"name": "source", "type": "string", "description": "数据来源"}
            ]
        }

        if dataset_id.startswith("disease_"):
            records = db.query(AdvancedDiseaseTransition).limit(limit).all()
            d_meta["category"] = "疾病负担数据"
            d_meta["record_count"] = db.query(AdvancedDiseaseTransition).count()
            d_meta["region_coverage"] = len(set([r.location_name for r in records]))
            for r in records:
                preview_data.append({
                    "region": r.location_name,
                    "year": r.year,
                    "metric": r.cause_name,
                    "value": r.val,
                    "source": "GBD 2019"
                })
        elif dataset_id.startswith("risk_"):
            records = db.query(AdvancedRiskCloud).limit(limit).all()
            d_meta["category"] = "风险因素数据"
            d_meta["record_count"] = db.query(AdvancedRiskCloud).count()
            d_meta["region_coverage"] = len(set([r.location_name for r in records]))
            for r in records:
                preview_data.append({
                    "region": r.location_name,
                    "year": r.year,
                    "metric": r.rei_name,
                    "value": r.paf,
                    "source": "GBD 2019"
                })
        elif dataset_id.startswith("resource_"):
            records = db.query(AdvancedResourceEfficiency).limit(limit).all()
            d_meta["category"] = "卫生资源效率数据"
            d_meta["record_count"] = db.query(AdvancedResourceEfficiency).count()
            d_meta["region_coverage"] = len(set([r.location_name for r in records]))
            for r in records:
                preview_data.append({
                    "region": r.location_name,
                    "year": r.year,
                    "metric": "DEA 效率",
                    "value": r.dea_efficiency if r.dea_efficiency else 0,
                    "source": "WDI / Local"
                })
        else:
            return {"status": "error", "msg": "未知数据集 ID"}

        if preview_data:
            d_meta["year_min"] = min([r["year"] for r in preview_data])
            d_meta["year_max"] = max([r["year"] for r in preview_data])

        return {
            "status": "success",
            "dataset": d_meta,
            "preview": preview_data
        }
    except Exception as e:
        from utils.logger import logger
        logger.exception("获取数据集详情失败")
        return {"status": "error", "msg": str(e)}

@app.get("/api/disease_simulation")
async def get_disease_simulation(years: int = 17, region: str = "China"):
    try:
        # 获取实际存在的清洗后数据
        db = SessionLocal()
        from db.models import AdvancedDiseaseTransition
        # 查询最近几年的真实数据作为基线
        real_data = db.query(AdvancedDiseaseTransition).filter(
            AdvancedDiseaseTransition.location_name == region
        ).order_by(AdvancedDiseaseTransition.year).all()
        db.close()
        
        # 将真实数据转换为 dataframe 供模型使用
        import pandas as pd
        if real_data:
            spectrum_df = pd.DataFrame([{
                'year': item.year,
                'cause_name': item.cause_name,
                'val': item.val
            } for item in real_data])
        else:
            spectrum_df = pd.DataFrame()

        da = DiseaseRiskAnalyzer(spectrum_data=spectrum_df)
        
        # 提取当前基线年份
        start_year = 2023
        if not spectrum_df.empty:
            start_year = spectrum_df['year'].max()
            
        labels = [str(start_year + i) for i in range(0, years + 1, max(1, years//4))]
        
        # 真实调用预测模型 (目前 DiseaseRiskAnalyzer 中的 run_sde_model_simple 已具备基本预测能力)
        datasets = []
        colors = ["#2b6cb0", "#c53030", "#d69e2e", "#319795", "#805ad5"]
        
        # 定义要预测的疾病类别
        target_causes = ["Cardiovascular diseases", "Neoplasms", "Diabetes", "Mental disorders"]
        display_names = ["心血管疾病", "肿瘤", "糖尿病", "精神疾病"]
        
        # 为了防止数据为空时前端无数据渲染，如果 spectrum_df 是空的，抛出警告，不生成伪造的 baseline
        if spectrum_df.empty:
            from utils.logger import log_missing_data
            log_missing_data("DiseaseSimulationAPI", "Disease Burden Baseline", 2023, region, "缺少该地区的疾病谱系数据作为预测基线")
            return {"status": "error", "msg": f"未能找到 {region} 的疾病负担基线数据，无法进行 SDE 预测"}

        for idx, cause in enumerate(target_causes):
            # 获取该疾病的当前负担基线
            current_burden = 0.0
            cause_df = spectrum_df[spectrum_df['cause_name'].str.contains(cause.split()[0], na=False, case=False)]
            if not cause_df.empty:
                current_burden = float(cause_df.sort_values(by='year').iloc[-1]['val'])
            else:
                # 记录该特定疾病在当前地区的缺失情况，跳过该疾病的模拟
                from utils.logger import log_missing_data
                log_missing_data("DiseaseSimulationAPI", f"{cause} Baseline", 2023, region, f"缺少 {cause} 负担基线数据")
                continue
            
            # 调用 SDE 模型生成未来趋势
            pred_df = da.run_sde_model_simple(cause, current_burden, years_ahead=years)
            
            # 提取与 labels 对应年份的数据点
            data_points = []
            for label_year in labels:
                year_val = int(label_year)
                # 寻找最接近的预测年份数据
                closest_row = pred_df.iloc[(pred_df['year'] - year_val).abs().argsort()[:1]]
                if not closest_row.empty:
                    data_points.append(round(float(closest_row['burden_index'].values[0]), 2))
                else:
                    data_points.append(current_burden)
                    
            datasets.append({
                "label": f"{display_names[idx]} (SDE预测)",
                "data": data_points,
                "borderColor": colors[idx % len(colors)],
                "borderWidth": 3
            })

        return {
            "status": "success",
            "chart_data": {
                "labels": labels,
                "datasets": datasets
            }
        }
    except Exception as e:
        from utils.logger import logger
        logger.exception("预测模拟失败")
        return {"status": "error", "msg": str(e)}

def run_spatial_analysis_task(region: str, threshold_km: float, cache_file: str, level: str = "community"):
    """后台运行实际的空间分析并写入缓存"""
    try:
        from modules.spatial.poi_fetcher import fetch_hospital_pois, fetch_community_demand
        from modules.analysis.advanced_algorithms import HealthMathModels
        import pandas as pd
        import json
        import os
        import math
        
        # 1. 获取供给端和需求端数据
        # 分别获取三甲医院和社区医院，体现不同层级医疗资源的搜寻半径差异
        df_3a = fetch_hospital_pois(city=region, keyword="三甲医院")
        if not df_3a.empty:
            df_3a['type'] = '三甲医院'
            df_3a['search_radius'] = 30.0  # 约60分钟车程 (假设30km/h)
            
        df_comm = fetch_hospital_pois(city=region, keyword="社区卫生服务中心")
        if not df_comm.empty:
            df_comm['type'] = '社区医院'
            df_comm['search_radius'] = 7.5   # 约15分钟车程 (假设30km/h)
            
        supply_df = pd.concat([df_3a, df_comm], ignore_index=True) if not df_3a.empty or not df_comm.empty else pd.DataFrame()
        demand_df = fetch_community_demand(city=region)
        
        if supply_df.empty or demand_df.empty:
            result_data = {"status": "error", "msg": f"未能获取 {region} 的微观地理数据"}
        else:
            # 2. 调用 E2SFCA 算法 (支持分段功率衰减和自定义半径)
            access_scores = HealthMathModels.calculate_e2sfca(
                supply_df, demand_df, 
                radius_col='search_radius', 
                default_radius_km=threshold_km,
                decay_type='piecewise_power',
                use_network_distance=True
            )
            demand_df['accessibility_score'] = access_scores
            
            # 2.5 聚合渲染机制：如果 level 为 district，后端预先对数据按行政区做 groupby 平均值处理
            if level == "district":
                # 尝试从 name 中提取行政区（如 xxx区，xxx县），若无法提取则使用默认值
                def extract_district(name):
                    for suffix in ['区', '县', '市']:
                        if suffix in name:
                            return name[:name.index(suffix)+1]
                    return name
                
                demand_df['district_name'] = demand_df['name'].apply(extract_district)
                # 按行政区聚合：计算平均可及性指数，以及平均经纬度作为中心点
                demand_df = demand_df.groupby('district_name').agg({
                    'accessibility_score': 'mean',
                    'lon': 'mean',
                    'lat': 'mean'
                }).reset_index().rename(columns={'district_name': 'name'})
            
            # 3. 构造前端需要的图表数据（增加坐标点用于热力图/散点图展示）
            labels = demand_df['name'].tolist()
            scores = demand_df['accessibility_score'].round(4).tolist()
            
            # 为了支持 3D 可视化，将 2SFCA 评分归一化为 Z 轴权重 (0.1 ~ 1.0)
            max_score = max(scores) if scores and max(scores) > 0 else 1.0
            min_score = min(scores) if scores else 0.0
            range_score = max_score - min_score if max_score > min_score else 1.0
            
            geo_points = []
            for _, row in demand_df.iterrows():
                score = round(row['accessibility_score'], 4)
                # 改进 Z 轴权重与 3D 视觉遮挡：使用非线性函数（平方根）压缩极端高值，防止个别点遮挡后方
                normalized_score = (score - min_score) / range_score if range_score > 0 else 0
                z_weight = round(0.1 + 0.9 * math.sqrt(normalized_score), 4)
                
                geo_points.append({
                    "name": row['name'],
                    "value": [row['lon'], row['lat'], score],
                    "z_weight": z_weight
                })
            
            result_data = {
                "status": "success",
                "region": region,
                "level": level,
                "chart_data": {
                    "labels": labels,
                    "datasets": [{
                        "label": f"{region} 空间可及性指数 (E2SFCA)",
                        "data": scores,
                        "backgroundColor": "#1890ff"
                    }],
                    "geo_points": geo_points
                }
            }
        
        # 写入缓存文件供下次读取
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False)
            
    except Exception as e:
        from utils.logger import logger
        logger.exception("后台执行微观空间分析失败")
        # 写入失败结果缓存，避免前端无限轮询
        error_data = {"status": "error", "msg": str(e)}
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(error_data, f, ensure_ascii=False)

@app.get("/api/spatial_analysis")
async def get_spatial_analysis(background_tasks: BackgroundTasks, region: str = "成都市", threshold_km: float = 10.0, level: str = "district"):
    try:
        from config.settings import SETTINGS
        import os
        import json
        import time
        
        # 增加本地缓存机制，减少高德API调用，并根据层级区分缓存
        cache_file = os.path.join(SETTINGS.DATA_DIR, "processed", f"spatial_cache_{region}_{level}.json")
        try:
            if os.path.exists(cache_file):
                file_mtime = os.path.getmtime(cache_file)
                current_time = time.time()
                # 缓存有效期设为 30 天
                if current_time - file_mtime < 30 * 86400:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cached_data = json.load(f)
                        return cached_data
                else:
                    # 缓存过期，删除它
                    os.remove(cache_file)
        except Exception as e:
            from utils.logger import logger
            logger.warning(f"读取或清理空间分析缓存失败: {e}")

        # 如果没有缓存，则将繁重的计算任务放入 BackgroundTasks 后台执行
        background_tasks.add_task(run_spatial_analysis_task, region, threshold_km, cache_file, level)
        
        # 立即返回接收状态，前端可以展示“正在分析中，请稍后刷新...”
        return {
            "status": "processing",
            "msg": f"正在后台调度高德API及进行E2SFCA计算 ({level} 级聚合)，这可能需要几十秒时间，请稍后自动重试...",
            "region": region,
            "level": level
        }
        
    except Exception as e:
        from utils.logger import logger
        logger.exception("触发微观空间分析任务失败")
        return {"status": "error", "msg": str(e)}

@app.get("/api/news")
async def get_health_news():
    """获取最新健康资讯 (Mediastack API) 带缓存"""
    import os
    import json
    import time
    from config.settings import SETTINGS
    import requests
    
    cache_file = os.path.join(SETTINGS.DATA_DIR, "processed", "news_cache.json")
    
    # 检查缓存是否存在且是3天内的
    try:
        if os.path.exists(cache_file):
            file_mtime = os.path.getmtime(cache_file)
            current_time = time.time()
            # 如果缓存文件是3天(259200秒)内生成的，直接返回缓存
            if current_time - file_mtime < 259200:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    return {"status": "success", "news": cached_data, "source": "cache"}
            else:
                # 缓存过期，删除它
                os.remove(cache_file)
    except Exception as e:
        from utils.logger import logger
        logger.warning(f"读取或清理新闻缓存失败: {e}")

    try:
        news_config = SETTINGS.SEARCH_ENGINE_CONFIG.get("news_api", {})
        api_key = news_config.get("api_key")
        if not api_key:
            return {"status": "error", "msg": "未配置 NewsAPI Key"}
            
        # Mediastack 参数
        # keywords: health, disease, WHO
        # categories: health
        # languages: en, zh (可选)
        url = f"{news_config['api_url']}?access_key={api_key}&categories=health&limit=10"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get("data", [])
            news_list = []
            for article in articles:
                if article.get("title"):
                    news_list.append({
                        "title": article.get("title"),
                        "description": article.get("description") or "点击查看详情",
                        "url": article.get("url"),
                        "source": article.get("source", "Health News"),
                        "publishedAt": article.get("published_at", "")
                    })
            
            # 保存到缓存
            try:
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(news_list, f, ensure_ascii=False)
            except Exception as e:
                from utils.logger import logger
                logger.warning(f"保存新闻缓存失败: {e}")
                
            return {"status": "success", "news": news_list, "source": "api"}
        else:
            return {"status": "error", "msg": f"NewsAPI 返回状态码: {response.status_code}, {response.text}"}
    except Exception as e:
        from utils.logger import logger
        logger.exception("获取健康资讯失败")
        return {"status": "error", "msg": str(e)}

@app.get("/api/geojson/hospitals")
async def get_hospitals_geojson():
    import os
    from config.settings import SETTINGS
    # 直接指向医院 POI 文件
    file_path = os.path.join(SETTINGS.BASE_DIR, "data", "geojson", "chengdu_hospitals.geojson")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/json")
    return {"status": "error", "msg": "Hospitals GeoJSON file not found"}

@app.get("/api/geojson/chengdu")
async def get_chengdu_geojson():
    import os
    from config.settings import SETTINGS
    file_path = os.path.join(SETTINGS.BASE_DIR, SETTINGS.GEOJSON_PATH_CHENGDU)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/json")
    
    fallback_path = os.path.join(SETTINGS.DATA_DIR, "geojson", "chengdu_hospitals.geojson")
    if os.path.exists(fallback_path):
        return FileResponse(fallback_path, media_type="application/json")
        
    return {"status": "error", "msg": "Chengdu GeoJSON file not found"}

@app.get("/api/admin/settings")
async def get_sys_settings():
    from config.settings import SETTINGS
    return {
        "medical_density": SETTINGS.BASE_MEDICAL_RESOURCE_DENSITIES,
        "analysis_params": SETTINGS.ANALYSIS_PARAMS,
        "gbd_config": SETTINGS.GBD_ANALYSIS_CONFIG
    }

@app.get("/api/geojson/world")
async def get_world_geojson():
    import os
    from config.settings import SETTINGS
    file_path = os.path.join(SETTINGS.BASE_DIR, SETTINGS.GEOJSON_PATH_WORLD)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/json")
    
    # 兼容回退策略，如果配置的路径未找到，尝试直接到 data/geojson 目录寻找
    fallback_path = os.path.join(SETTINGS.DATA_DIR, "geojson", "ne_10m_admin_0_countries.geojson")
    if os.path.exists(fallback_path):
        return FileResponse(fallback_path, media_type="application/json")
        
    # 如果真的没有，返回一个非常基础的全球轮廓（这里仅为了防止前端图表直接抛出 JSON parse error）
    return {
        "type": "FeatureCollection",
        "features": []
    }

@app.get("/api/geojson/continents")
async def get_continents_geojson():
    import os
    from config.settings import SETTINGS
    file_path = SETTINGS.GEOJSON_PATH_CONTINENTS
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/json")
    return {"status": "error", "msg": "GeoJSON file not found"}

@app.get("/api/geojson/china")
async def get_china_geojson():
    import os
    from config.settings import SETTINGS
    file_path = os.path.join(SETTINGS.BASE_DIR, SETTINGS.GEOJSON_PATH_CHINA)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/json")
        
    fallback_path = os.path.join(SETTINGS.DATA_DIR, "geojson", "中华人民共和国.geojson")
    if os.path.exists(fallback_path):
        return FileResponse(fallback_path, media_type="application/json")
        
    return {"status": "error", "msg": "GeoJSON file not found"}

@app.get("/api/config/public-routes")
async def get_public_routes():
    # 返回无需鉴权即可访问的公共页面列表
    return {
        "publicPages": ['login.html', 'register.html', 'index.html', '/', 'help.html']
    }

import os
from pathlib import Path

# 获取当前文件所在目录的绝对路径
BASE_DIR = Path(__file__).resolve().parent

# ==========================================
# 2. 核心页面路由 (必须优先于泛匹配挂载)
# ==========================================

@app.get("/")
async def root():
    # 指向真实的 frontend/use 目录下的 index.html
    return FileResponse(str(BASE_DIR / "frontend/use/index.html"))

# ==========================================
# 3. 挂载前端静态目录 (按范围从小到大挂载)
# ==========================================

app.mount("/admin", StaticFiles(directory=str(BASE_DIR / "frontend/admin"), html=True), name="admin")
app.mount("/use", StaticFiles(directory=str(BASE_DIR / "frontend/use"), html=True), name="use")
app.mount("/assets", StaticFiles(directory=str(BASE_DIR / "frontend/assets")), name="assets")

# 泛拦截挂载必须放在文件的最后，作为兜底（提供根目录的其他可能静态文件）
app.mount("/", StaticFiles(directory=str(BASE_DIR / "frontend"), html=False), name="frontend")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)