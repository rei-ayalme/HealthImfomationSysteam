# modules/deepseek_adapter.py
import pandas as pd
from db.connection import SessionLocal
from db.models import GlobalHealthMetric


def owid_2_deepseek_input(
        indicator_ids: list,
        countries: list,
        start_year: int,
        end_year: int,
        output_format: str = "dict",
        df_owid=None) -> dict:
    """
    将OWID数据库数据转换为DeepSeek_Analyzer可接受的输入格式
    :param indicator_ids: OWID指标ID列表
    :param countries: 国家列表
    :param start_year/end_year: 时间范围
    :return: DeepSeek输入字典（符合模型要求的格式）
    """
    db = SessionLocal()
    try:
        # 查询OWID数据
        query = db.query(GlobalHealthMetric).filter(
            GlobalHealthMetric.indicator.in_(indicator_ids),
            GlobalHealthMetric.region.in_(countries),
            GlobalHealthMetric.year.between(start_year, end_year)
        )
        raw_data = query.all()
        if not raw_data:
            return {"status": "error", "msg": "无可用OWID数据"}

        # 统一使用变量名 df
        df = pd.DataFrame([{
            "country": item.region,  # 确保与 filter 中的字段一致
            "year": item.year,
            "indicator": item.indicator,
            "value": item.value
        } for item in raw_data])

        # 修复 df_owid 未定义的 NameError
        df = df.dropna(subset=["value"])
        df = df.drop_duplicates(subset=["country", "year", "indicator"])
        if df.empty:
            return {"status": "error", "msg": "无可用OWID数据"}

        # 转换为要求的格式（假设模型要求：{国家: {年份: {指标: 值}}}）
        deepseek_input = {}
        for country in countries:
            country_data = df[df["country"] == country]
            year_data = {}
            for year in range(start_year, end_year + 1):
                year_df = country_data[country_data["year"] == year]
                indicator_data = year_df.set_index("indicator")["value"].to_dict()
                year_data[year] = indicator_data
            deepseek_input[country] = year_data

        return {
            "status": "success",
            "data": deepseek_input,
            "metadata": {
                "indicator_ids": indicator_ids,
                "countries": countries,
                "time_range": [start_year, end_year]
            }
        }
    except Exception as e:
        return {"status": "error", "msg": f"数据适配失败：{str(e)}"}
    finally:
        db.close()