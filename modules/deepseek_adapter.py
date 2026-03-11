# modules/deepseek_adapter.py
import pandas as pd
from db.connection import SessionLocal
from db.models import WHOGlobalHealth


def owid_2_deepseek_input(
        indicator_ids: list,
        countries: list,
        start_year: int,
        end_year: int,
        output_format: str = "dict"  # deepseek接受的格式：dict/df/tensor
) -> dict:
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
        query = db.query(WHOGlobalHealth).filter(
            WHOGlobalHealth.indicator_name.in_(indicator_ids),
            WHOGlobalHealth.country_name.in_(countries),
            WHOGlobalHealth.year.between(start_year, end_year)
        )
        df = pd.DataFrame([{
            "country": item.country_name,
            "country_code": item.country_code,
            "year": item.year,
            "indicator": item.indicator_name,
            "value": item.value
        } for item in query.all()])
        db.close()

        df_owid = df_owid.dropna(subset=["value"])
        df_owid = df_owid.drop_duplicates(subset=["country", "year", "indicator"])
        if df.empty:
            return {"status": "error", "msg": "无可用OWID数据"}

        # 转换为DeepSeek要求的格式（假设模型要求：{国家: {年份: {指标: 值}}}）
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