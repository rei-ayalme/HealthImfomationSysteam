# main.py
import uvicorn
from fastapi import FastAPI, Depends
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

@app.get("/api/dataset")
async def get_dataset(db: Session = Depends(get_db)):
    try:
        from db.models import AdvancedDiseaseTransition, AdvancedRiskCloud, AdvancedResourceEfficiency
        
        # 为了给前端提供丰富的数据，从多张真实的高级分析表中提取数据
        items = []
        
        # 1. 获取疾病负担数据
        disease_data = db.query(AdvancedDiseaseTransition).limit(20).all()
        for i, d in enumerate(disease_data):
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
        
        for idx, cause in enumerate(target_causes):
            # 获取该疾病的当前负担基线
            current_burden = 100.0
            if not spectrum_df.empty:
                cause_df = spectrum_df[spectrum_df['cause_name'].str.contains(cause.split()[0], na=False, case=False)]
                if not cause_df.empty:
                    current_burden = float(cause_df.sort_values(by='year').iloc[-1]['val'])
            
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
    file_path = SETTINGS.GEOJSON_PATH_WORLD
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/json")
    return {"status": "error", "msg": "GeoJSON file not found"}

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
    file_path = SETTINGS.GEOJSON_PATH_CHINA
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/json")
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