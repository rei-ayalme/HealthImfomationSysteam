# modules/owid_data_fetcher.py
import requests
import pandas as pd
import json
import os
from datetime import datetime
from db.connection import SessionLocal
from db.models import GlobalHealthMetric, WHOGlobalHealth, OWIDFetchLog
from config.settings import OWID_INDICATORS, SETTINGS  # 后续在settings里配置需要的OWID指标

# -----------------------------------------------------------------------------
# 外部数据获取与爬虫逻辑保存声明
# 本模块包含了通过 Our World in Data (OWID) API 获取全球健康指标数据的核心爬取逻辑。
# 根据系统规范，此爬虫代码与项目一同保存并上传，以确保后续环境可直接复现抓取过程。
# 数据不仅会入库，还会将原始抓取数据备份为 CSV 文件，保存在 data/raw 目录下。
# -----------------------------------------------------------------------------

def create_owid_unique_index():
    """创建唯一索引，防止重复入库（country_code+year+indicator_name）"""
    db = SessionLocal()
    try:
        # 执行SQL创建唯一索引（适配MySQL/PostgreSQL）
        db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_who_owid_unique 
            ON who_global_health (country_code, year, indicator_name);
        """)
        db.commit()
        print("✅ OWID唯一索引创建成功")
    except Exception as e:
        print(f"⚠️ 索引创建失败（可能已存在）：{e}")
    finally:
        db.close()

# 初始化索引（项目启动时执行）
create_owid_unique_index()


def get_owid_single_indicator(indicator_id: str, target_countries: list = None, last_fetch_time=None) -> pd.DataFrame:
    """复用OWID API代码，获取单个指标数据"""
    api_url = f"https://ourworldindata.org/grapher/data/v1/indicators/{indicator_id}.json"
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        # 解析国家/年份/数值
        entity_map = {e["id"]: {"name": e["name"], "code": e.get("code")} for e in data["entities"]}
        all_data = []
        for entity_id, time_series in data["data"].items():
            ent = entity_map.get(int(entity_id))
            if not ent:
                continue
            # 过滤目标国家
            if target_countries and ent["name"] not in target_countries:
                continue

            # 增量过滤：只处理年份>上次爬取年份（简化版，OWID无更新时间则按年份过滤）
            for year, value in time_series.items():
                if value is None:
                    continue
                year_int = int(year)
                # 增量逻辑：若有上次爬取时间，只取近2年数据（OWID数据更新频率低）
                # 这里现在可以合法使用 last_fetch_time 了，因为我们在函数参数里定义了它
                if last_fetch_time and year_int < datetime.now().year - 2:
                    continue
                all_data.append({
                    "country_name": ent["name"],
                    "country_code": ent["code"],
                    "year": year_int,
                    "indicator_id": indicator_id,
                    "value": float(value),
                    "fetch_time": datetime.now()  # 本次爬取时间
                })

        df = pd.DataFrame(all_data)
        # 去重：按country_code+year+indicator_id去重
        df = df.drop_duplicates(subset=["country_code", "year", "indicator_id"])
        
        # 将原始数据备份为 CSV，保存在 data/raw 目录下
        if not df.empty:
            os.makedirs(SETTINGS.RAW_DATA_PATH, exist_ok=True)
            backup_file = os.path.join(SETTINGS.RAW_DATA_PATH, f"owid_indicator_{indicator_id}_backup.csv")
            try:
                # 若文件存在则追加，否则新建
                if os.path.exists(backup_file):
                    df.to_csv(backup_file, mode='a', header=False, index=False, encoding='utf-8')
                else:
                    df.to_csv(backup_file, index=False, encoding='utf-8')
                print(f"✅ OWID指标 {indicator_id} 的原始爬取数据已备份至 {backup_file}")
            except Exception as e:
                print(f"⚠️ 备份 CSV 失败: {e}")

        return df
    except Exception as e:
        print(f"拉取OWID指标{indicator_id}失败：{e}")
        return pd.DataFrame()

def owid_data_2_db(indicator_ids: list, target_countries: list = None, is_who_table: bool = True):
    """将OWID数据存入现有数据库（WHOGlobalHealth/GlobalHealthMetric）"""
    db = SessionLocal()
    fetch_log = {}
    try:
        for ind in indicator_ids:
            # 获取该指标上次爬取日志（用于增量）
            last_log = db.query(OWIDFetchLog).filter(
                OWIDFetchLog.indicator_id == ind,
                OWIDFetchLog.status == True
            ).order_by(OWIDFetchLog.fetch_time.desc()).first()

            # 增量爬取：传入上次爬取时间
            last_fetch_time = last_log.fetch_time if last_log else None
            df = get_owid_single_indicator(ind, target_countries, last_fetch_time)

            if df.empty:
                fetch_log[ind] = {"status": False, "data_count": 0, "error_msg": "无可用数据"}
                continue

            # 入库（利用唯一索引自动去重，无需手动判断）
            new_data_count = 0
            if is_who_table:
                for _, row in df.iterrows():
                    try:
                        db.add(WHOGlobalHealth(
                            country_code=row["country_code"],
                            country_name=row["country_name"],
                            year=row["year"],
                            indicator_name=row["indicator_id"],
                            value=row["value"]
                        ))
                        new_data_count += 1
                    except Exception as e:
                        # 唯一索引冲突：跳过重复数据
                        if "duplicate key" in str(e).lower():
                            continue
                        raise e
            else:
                for _, row in df.iterrows():
                    try:
                        db.add(GlobalHealthMetric(
                            region=row["country_name"],
                            year=row["year"],
                            indicator=row["indicator_id"],
                            value=row["value"]
                        ))
                        new_data_count += 1
                    except Exception as e:
                        if "duplicate key" in str(e).lower():
                            continue
                        raise e

            db.commit()
            fetch_log[ind] = {"status": True, "data_count": new_data_count, "error_msg": None}
            print(f"✅ OWID指标{ind}入库完成，新增{new_data_count}条数据")

        # 记录爬取日志到数据库
        for ind, log in fetch_log.items():
            log_entry = OWIDFetchLog(
                indicator_id=ind,
                target_countries=json.dumps(target_countries) if target_countries else "",
                status=log["status"],
                data_count=log["data_count"],
                error_msg=log["error_msg"]
            )
            db.add(log_entry)
        db.commit()
        return fetch_log
    except Exception as e:
        db.rollback()
        print(f"❌ OWID数据入库失败：{e}")
        # 记录失败日志
        for ind in indicator_ids:
            log_entry = OWIDFetchLog(
                indicator_id=ind,
                target_countries=json.dumps(target_countries) if target_countries else "",
                status=False,
                data_count=0,
                error_msg=str(e)[:500]  # 截断过长错误信息
            )
            db.add(log_entry)
        db.commit()
        raise e
    finally:
        db.close()

# 批量拉取封装
def batch_fetch_owid(target_countries: list = ["China", "United States", "India", "Germany"]):
    """批量拉取项目需要的OWID指标（疾病/风险/卫生资源）"""
    # 从配置文件读取需要的OWID指标ID
    from config.settings import OWID_HEALTH_INDICATORS
    owid_data_2_db(OWID_HEALTH_INDICATORS, target_countries)