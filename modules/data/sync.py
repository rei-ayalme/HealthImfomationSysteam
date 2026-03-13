import os
import requests
import pandas as pd
import json
from datetime import datetime
from db.connection import SessionLocal
from db.models import GlobalHealthMetric
from modules.data.cleaner import HealthDataCleaner
from config.settings import SETTINGS


class HealthDataSyncManager:
    """
    卫生数据同步管理类
    负责：API请求、原始数据备份、标准化清洗、数据库入库
    """

    def __init__(self):
        self.raw_path = SETTINGS.RAW_DATA_PATH
        self.cleaner = HealthDataCleaner()
        self.api_config = SETTINGS.API_CONFIG

    def _save_raw_backup(self, data: dict, source_name: str):
        """将API返回的原始数据保存到 data/raw 供开发者溯源"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_name}_raw_{timestamp}.json"
        full_path = os.path.join(self.raw_path, filename)

        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"📦 原始数据已备份至: {filename}")

    def sync_who_data(self, indicator_code: str = "NCD_HYPERTENSION_PREVALENCE"):
        """同步 WHO GHO 数据"""
        url = f"{self.api_config['who_gho_base_url']}{indicator_code}"
        print(f"🌐 正在同步 WHO 指标: {indicator_code}...")

        try:
            response = requests.get(url, timeout=self.api_config['timeout'])
            response.raise_for_status()
            raw_data = response.json()

            # 步骤1：备份原始数据
            self._save_raw_backup(raw_data, "WHO")

            # 步骤2：解析并清洗
            records = raw_data.get('value', [])
            if not records:
                return

            df = pd.DataFrame(records)
            # 统一列名：国家代码、年份、数值
            df_clean = pd.DataFrame({
                'region': df['SpatialDim'],
                'year': df['TimeDim'].astype(int),
                'value': df['NumericValue'].astype(float),
                'indicator': indicator_code,
                'source': 'WHO',
                'unit': df.get('Id', '')  # 示例占位
            })

            # 步骤3：入库
            self._persist_to_db(df_clean)

        except Exception as e:
            print(f"❌ WHO 同步失败: {e}")

    def sync_world_bank_data(self, country: str = "CHN", indicator: str = "SH.MED.PHYS.ZS"):
        """同步世界银行数据 (如：医师密度)"""
        url = f"{self.api_config['world_bank_base_url']}country/{country}/indicator/{indicator}"
        params = {"format": "json", "per_page": 100}

        try:
            response = requests.get(url, params=params, timeout=self.api_config['timeout'])
            response.raise_for_status()
            raw_json = response.json()

            if len(raw_json) < 2: return

            # 备份原始数据
            self._save_raw_backup(raw_json, f"WorldBank_{country}")

            # 解析
            data_list = raw_json[1]
            df_clean = pd.DataFrame([
                {
                    'region': country,
                    'year': int(item['date']),
                    'value': float(item['value']) if item['value'] else 0,
                    'indicator': indicator,
                    'source': 'WorldBank',
                    'unit': 'per 1,000 people'
                } for item in data_list if item['value'] is not None
            ])

            self._persist_to_db(df_clean)

        except Exception as e:
            print(f"❌ World Bank 同步失败: {e}")

    def _persist_to_db(self, df: pd.DataFrame):
        """将清洗后的标准数据保存到 health_metrics 表"""
        db = SessionLocal()
        try:
            for _, row in df.iterrows():
                # 避免重复插入：基于来源、地区、指标、年份判断
                exists = db.query(GlobalHealthMetric).filter(
                    GlobalHealthMetric.source == row['source'],
                    GlobalHealthMetric.region == row['region'],
                    GlobalHealthMetric.indicator == row['indicator'],
                    GlobalHealthMetric.year == row['year']
                ).first()

                if not exists:
                    metric = GlobalHealthMetric(**row.to_dict())
                    db.add(metric)

            db.commit()
            print(f"✅ 成功入库 {len(df)} 条标准指标数据。")
        except Exception as e:
            db.rollback()
            print(f"❌ 数据库写入失败: {e}")
        finally:
            db.close()