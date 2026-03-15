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

# 配置 CORS（允许跨域请求，前端调试时很有用）
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
# 1. 定义 API 接口 (供前端 JS 中的 fetch 调用)
# ==========================================

@app.get("/api/dataset")
async def get_dataset(db: Session = Depends(get_db)):
    """
    前端 dataset.html 会调用这个接口获取数据。
    在这里调用你原有的 Python 逻辑。
    """
    try:
        # 从你的数据库中查询真实数据（限制50条避免前端过载，你可以根据需要调整）
        metrics = db.query(GlobalHealthMetric).limit(50).all()

        items = []
        for i, m in enumerate(metrics):
            # 将数据库字段映射为前端需要的格式
            # 使用 getattr 是为了防止你的模型字段名与我猜测的略有不同时报错
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

        # 兜底：如果数据库里暂时没数据，返回一条测试数据以确保前端渲染正常
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
    """
    接口 2：疾病负担预测 SDE 模拟接口
    供 frontend/infectious_diseases.html 调用
    """
    try:
        # 实例化你的分析器
        da = DiseaseRiskAnalyzer()

        # 调用你原有的 SDE 模型进行计算
        # 假设这里基于 2023 年预测未来 years 年 (比如 17 年即到 2040 年)
        # res = da.run_sde_model(years=years)

        # ---------------------------------------------------------
        # 注意：由于我没有看到你 run_sde_model 的具体返回格式，
        # 通常你需要在这里把 pandas DataFrame 转换成前端 Chart.js 需要的列表格式。
        # 这里我为你提供一个标准的数据装配模板，你可以根据实际 res 的格式解包：
        # ---------------------------------------------------------

        # 模拟组装后的真实返回数据（你可以替换为 res 中的真实推演结果）
        labels = ['2023', '2025', '2030', '2035', '2040']
        cardio_data = [45, 47, 52, 56, 60]  # res['心血管']
        cancer_data = [28, 30, 35, 39, 43]  # res['癌症']
        diabetes_data = [15, 17, 22, 26, 30]  # res['糖尿病']
        mental_data = [20, 22, 26, 29, 32]  # res['精神疾病']

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


# 你可以在这里继续添加更多的 API 接口
# @app.post("/api/predict")
# async def predict_disease_burden(data: dict):
#     result = modules.analysis.advanced_algorithms.run_prediction(data)
#     return {"result": result}


# ==========================================
# 2. 挂载前端静态页面 (HTML/CSS/JS)
# ==========================================

# 将 frontend 文件夹挂载到根路径，这样可以直接访问 /index.html 等
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


# 设置默认主页
@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

if __name__ == "__main__":
    # 启动命令
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)