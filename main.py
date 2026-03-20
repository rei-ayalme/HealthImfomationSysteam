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
        metrics = db.query(GlobalHealthMetric).limit(50).all()
        items = []
        for i, m in enumerate(metrics):
            items.append({
                "id": getattr(m, 'id', i + 1),
                "name": getattr(m, 'indicator_name', '健康指标'),
                "type": "data",
                "typeName": "数据表格",
                "topic": "health-indicators",
                "topicName": "健康指标分析",
                "country": getattr(m, 'country', getattr(m, 'region', '全球')),
                "year": getattr(m, 'year', 2023),
                "value": getattr(m, 'value', 0),
                "unit": getattr(m, 'unit', ''),
                "status": "success"
            })

        if not items:
            items = [
                {
                    "id": 1, "name": "预期寿命趋势 (示例)", "type": "data", "typeName": "数据表格",
                    "topic": "health-indicators", "topicName": "健康指标分析",
                    "country": "全球", "year": 2023, "value": 73.2, "unit": "岁", "status": "info"
                }
            ]
        return {"items": items}
    except Exception as e:
        print(f"数据库查询异常: {e}")
        return {"items": []}

@app.get("/api/disease_simulation")
async def get_disease_simulation(years: int = 17):
    try:
        da = DiseaseRiskAnalyzer()
        # 实际开发时解开下面这行的注释并处理返回数据
        # res = da.run_sde_model(years=years)

        labels = ['2023', '2025', '2030', '2035', '2040']
        cardio_data = [45, 47, 52, 56, 60]
        cancer_data = [28, 30, 35, 39, 43]
        diabetes_data = [15, 17, 22, 26, 30]
        mental_data = [20, 22, 26, 29, 32]

        return {
            "status": "success",
            "chart_data": {
                "labels": labels,
                "datasets": [
                    {"label": "心血管疾病 (动态)", "data": cardio_data, "borderColor": "#2b6cb0", "borderWidth": 3},
                    {"label": "癌症 (动态)", "data": cancer_data, "borderColor": "#c53030", "borderWidth": 3},
                    {"label": "糖尿病 (动态)", "data": diabetes_data, "borderColor": "#d69e2e", "borderWidth": 3},
                    {"label": "精神疾病 (动态)", "data": mental_data, "borderColor": "#319795", "borderWidth": 3}
                ]
            }
        }
    except Exception as e:
        print(f"预测模拟失败: {e}")
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
    import json
    import os
    file_path = "data/geojson/ne_10m_admin_0_countries.geojson"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/json")
    return {"status": "error", "msg": "GeoJSON file not found"}

@app.get("/api/geojson/continents")
async def get_continents_geojson():
    import json
    import os
    file_path = "data/raw/五大洲/custom.geo.json"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/json")
    return {"status": "error", "msg": "GeoJSON file not found"}

@app.get("/api/geojson/china")
async def get_china_geojson():
    import json
    import os
    file_path = "data/geojson/中华人民共和国.geojson"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/json")
    return {"status": "error", "msg": "GeoJSON file not found"}

# ==========================================
# 2. 核心页面路由 (必须优先于泛匹配挂载)
# ==========================================

@app.get("/")
async def root():
    # 修复：指向真实的 frontend/use 目录
    return FileResponse("frontend/use/index.html")

# ==========================================
# 3. 挂载前端静态目录 (按范围从小到大挂载)
# ==========================================

app.mount("/admin", StaticFiles(directory="frontend/admin", html=True), name="admin")
# 修复：将 user 挂载路径更正为您的实际目录 use
app.mount("/use", StaticFiles(directory="frontend/use", html=True), name="use")
app.mount("/assets", StaticFiles(directory="frontend/assets"), name="assets")

# 泛拦截挂载必须放在文件的最后，作为兜底（提供根目录的其他可能静态文件）
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)