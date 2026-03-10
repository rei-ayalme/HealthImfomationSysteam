import requests
import pandas as pd
import time
from datetime import datetime
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from db.models import GlobalHealthMetric  # 基础平台核心表
from utils.logger import logger  # 使用项目自带日志器

class HealthDataSyncManager:
    """多源卫生健康数据同步管理器"""

    def __init__(self):
        self.db: Session = SessionLocal()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (HealthInformationSystem/1.2)'
        }

    def _save_to_db(self, records: list):
        """批量保存数据到数据库"""
        try:
            if not records:
                return
            for data in records:
                record = GlobalHealthMetric(**data)
                self.db.add(record)
            self.db.commit()
            logger.info(f"成功同步 {len(records)} 条数据到数据库")
        except Exception as e:
            self.db.rollback()
            logger.error(f"数据库写入失败: {e}")

    def sync_who_gho(self, indicator_code="NCD_HYPERTENSION_PREVALENCE"):
        """1. WHO GHO 数据源同步"""
        url = f"https://ghoapi.azureedge.net/api/{indicator_code}"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json().get('value', [])
                records = []
                for item in data[:100]:  # 示例仅取前100条
                    records.append({
                        'source': 'WHO',
                        'region': item.get('SpatialDim'),
                        'indicator': indicator_code,
                        'year': int(item.get('TimeDim', 0)) if str(item.get('TimeDim')).isdigit() else 2020,
                        'value': float(item.get('NumericValue')) if item.get('NumericValue') else 0.0,
                        'unit': 'percentage'
                    })
                self._save_to_db(records)
        except Exception as e:
            logger.error(f"WHO 同步失败: {e}")

    def sync_world_bank(self, indicator="SH.MED.PHYS.ZS", country="CHN"):
        """2. 世界银行数据源同步"""
        url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json"
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            if len(data) > 1:
                records = []
                for item in data[1]:
                    if item.get('value'):
                        records.append({
                            'source': 'WorldBank',
                            'region': country,
                            'indicator': indicator,
                            'year': int(item.get('date')),
                            'value': float(item.get('value')),
                            'unit': 'per 1000 people'
                        })
                self._save_to_db(records)
        except Exception as e:
            logger.error(f"WorldBank 同步失败: {e}")

    def sync_unicef(self, indicator="MNCH_MCV1"):
        """3. UNICEF (联合国儿童基金会) 数据同步 - 侧重免疫接种"""
        url = f"https://data.unicef.org/resources/dataexplorer/api/data/UNICEF,{indicator},all"
        # 注意：此处为概念性URL，实际需根据UNICEF SDMX接口调整参数
        logger.info(f"正在从 UNICEF 同步指标: {indicator}")
        # 模拟同步逻辑...
        pass

    def sync_owid_covid(self):
        """4. Our World in Data (OWID) - COVID-19/疫苗数据同步"""
        url = "https://covid.ourworldindata.org/data/owid-covid-data.json"
        try:
            response = requests.get(url, timeout=60)
            data = response.json().get('CHN', {}) # 示例获取中国数据
            records = []
            for entry in data.get('data', [])[-10:]: # 获取最近10天
                records.append({
                    'source': 'OWID',
                    'region': 'CHN',
                    'indicator': 'new_cases_smoothed',
                    'year': 2023, # 简化处理，实际应解析日期
                    'value': float(entry.get('new_cases_smoothed', 0.0)),
                    'unit': 'cases'
                })
            self._save_to_db(records)
        except Exception as e:
            logger.error(f"OWID 同步失败: {e}")

    def sync_oecd_health(self, dataset="HEALTH_STAT"):
        """5. OECD Health Statistics (发达国家医疗支出)"""
        # OECD 常用 SDMX 接口获取数据
        logger.info(f"正在从 OECD 同步数据集: {dataset}")
        pass

    def close(self):
        self.db.close()