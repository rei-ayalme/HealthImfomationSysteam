# settings.py
import os
from typing import Dict, List, Any
from enum import Enum

class WeightingMethod(Enum):
    EQUAL = "equal"
    EXPERT = "expert"
    INVERSE_VARIANCE = "inverse_variance"
    CUSTOM = "custom"
    BENCHMARK_RELATIVE = "benchmark_relative"

class Settings:
    """医疗资源配置系统核心配置类"""
    # 路径管理
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    RAW_DATA_PATH = os.path.join(DATA_DIR, "raw")
    PROCESSED_DATA_PATH = os.path.join(DATA_DIR, "processed")

    # 数据库配置
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'db', 'health_system.db')}")

    # 自动创建必要目录
    for path in [RAW_DATA_PATH, PROCESSED_DATA_PATH]:
        os.makedirs(path, exist_ok=True)

    # Redis 配置
    # 默认使用本地 Redis 服务 (127.0.0.1:6379)
    # 如需修改，请设置环境变量 REDIS_HOST 和 REDIS_PORT
    REDIS_CONFIG = {
        "host": os.getenv("REDIS_HOST", "127.0.0.1"),  # 默认本地地址
        "port": int(os.getenv("REDIS_PORT", 6379)),     # Redis 默认端口
        "password": os.getenv("REDIS_PASSWORD", None),
        "db": int(os.getenv("REDIS_DB", 0))
    }

    # DPIO 硬件驱动配置
    DPIO_CONFIG = {
        "driver_path": "/sys/class/dpio",  # 驱动在 sysfs 中的路径
        "buffer_pool": "/dev/dpio_buffer0",  # 硬件缓冲区设备节点
        "driver_module_name": "dpio_drv",  # 内核模块名称
        "test_frame_data": b"\xAA\x55\xDE\xAD\xBE\xEF",  # 测试帧数据
        "timeout": 5  # 操作超时时间（秒）
    }

    DATA_CONFIG = {
        "supported_formats": [".csv", ".xlsx", ".xls"],  # 支持的文件格式
        "default_encoding": ["utf-8", "gbk", "gb2312"],  # 自动尝试的编码
        "default_sep": [",", "\t", ";"],  # 自动尝试的分隔符
        "null_values": ["无数据", "NaN", "NA", "-", 0, -999],  # 识别为空值的标记
        "numeric_cols": ["value", "数值", "数量", "占比", "密度"],  # 需转为数值的列名关键词
        "date_cols": ["year", "年份", "日期", "时间"],  # 需转为日期的列名关键词
        "standard_output_cols": ["country", "year", "indicator", "value", "region"]  # 标准化输出列名
         }

    # 文件名配置
    RAW_DATA_FILE = RAW_DATA_PATH # 修改为扫描整个文件夹
    CLEANED_DATA_FILE = os.path.join(PROCESSED_DATA_PATH, "cleaned_health_data.xlsx")
    GBD_DATA_FILE = os.path.join(RAW_DATA_PATH, "global_burden_of_disease_data.xlsx")

    # 原始卫生年鉴数据目录
    YEARBOOK_DATA_PATH = os.path.join(RAW_DATA_PATH, "卫生年鉴表")

    STANDARD_COLUMN_MAPPING = {
        # 针对年鉴数据的映射关系
        "physicians": ["执业(助理)医师", "执业医师", "医师", "physicians", "doctor"],
        "nurses": ["注册护士", "护士", "nurses", "nurse"],
        "hospital_beds": ["床位数", "医疗卫生机构床位数", "医院床位数", "beds", "hospital_beds"],
        "population": ["人口数", "年末人口数", "总人口", "population", "pop"],
        "region_name": ["地区", "省份", "省市", "region", "location", "area"]
    }
    BASE_HEALTH_FACTORS = ["infant_mortality", "life_expectancy"]
    BASE_HEALTH_FACTORS_WHO = ["gho_infant_mortality", "gho_life_expectancy"]
    EXTERNAL_FACTOR_SENSITIVITY = 0.1
    HEALTH_IMPACT_FACTORS = {"gdp_per_capita": 0.2, "urbanization": 0.15}
    WHO_INDICATOR_CODES = {"infant_mortality": "WHOSIS_000001"}
    WHO_RESULT_COLUMN_MAPPINGS = {"Value": "value", "Year": "year"}
    ANALYSIS_PARAMS = {"confidence_level": 0.95, "window_size": 5}
    TOLERANCE_LEVELS = {"low": 0.05, "medium": 0.1, "high": 0.2}
    DB_FIELD_MAPPINGS = {"country_name": "region", "indicator_value": "value"}
    OUTPUT_SETTINGS = {"format": "excel", "encoding": "utf-8"}
    DISEASE_CODES = {"diabetes": "ICD10_E11", "hypertension": "ICD10_I10"}
    SDE_MODEL_PARAMS = {"drift": 0.02, "volatility": 0.1}
    INTERVENTION_MEASURES = {"primary_care": 0.3, "public_health": 0.25}

    # 资源权重配置 (P0: 统一计算口径)
    RESOURCE_WEIGHTS = {
        'physicians_per_1000': 0.4,
        'nurses_per_1000': 0.35,
        'hospital_beds_per_1000': 0.25
    }

    # 基础医疗资源密度基准 (每千人)
    BASE_MEDICAL_RESOURCE_DENSITIES = {
        'physicians_per_1000': 2.5,
        'nurses_per_1000': 3.2,
        'hospital_beds_per_1000': 6.0
    }

    # OWID 指标 ID 配置
    OWID_HEALTH_INDICATORS = [
        "445883",  # 预期寿命
        "445888",  # 5岁以下儿童死亡率
        "540660",  # 医师密度 (每万人)
    ]
    OWID_INDICATORS = OWID_HEALTH_INDICATORS

    # 配置：GeoJSON 地图文件路径配置
    GEOJSON_PATH_WORLD = os.getenv("GEOJSON_PATH_WORLD", "data/geojson/ne_10m_admin_0_countries.geojson")
    GEOJSON_PATH_CONTINENTS = os.getenv("GEOJSON_PATH_CONTINENTS", "data/geojson/continents.geojson")
    GEOJSON_PATH_CHINA = os.getenv("GEOJSON_PATH_CHINA", "data/geojson/china.geojson")
    GEOJSON_PATH_CHENGDU = os.getenv("GEOJSON_PATH_CHENGDU", "data/geojson/chengdu_boundary.geojson")
    GEOJSON_PATH_CHENGDU_HOSPITALS = os.getenv("GEOJSON_PATH_CHENGDU_HOSPITALS", "data/geojson/chengdu_hospitals.geojson")
    GEOJSON_PATH_CHENGDU_STREET = os.getenv("GEOJSON_PATH_CHENGDU_STREET", "data/geojson/chengdu_street.geojson")

    # 配置：资源缺口等级阈值
    GAP_THRESHOLD_ADEQUATE = float(os.getenv("GAP_THRESHOLD_ADEQUATE", 0.0))
    GAP_THRESHOLD_REASONABLE = float(os.getenv("GAP_THRESHOLD_REASONABLE", 0.1))
    GAP_THRESHOLD_MILD = float(os.getenv("GAP_THRESHOLD_MILD", 0.3))

    # 配置：预测增长率情景配置
    SCENARIO_MULTIPLIERS = {
        "基准": float(os.getenv("SCENARIO_BASELINE", 1.02)),
        "高增长": float(os.getenv("SCENARIO_HIGH", 1.05)),
        "平稳": float(os.getenv("SCENARIO_STABLE", 1.00))
    }

    # GBD与高级数据分析配置 (融合学术文献方法)
    GBD_ANALYSIS_CONFIG = {
        'min_year': 1990,
        'max_year': 2025,
        'sdi_reference_group': 0.8,  # 高SDI参照组阈值
        'uncertainty_budget': 0.1,  # 鲁棒DEA Γ参数 (邵龙龙等, 2025) - 容忍10%的数据波动
        'cloud_params': {  # 云模型参数 (张翔等, 2026) - 用于暴露等级量化
            'zeta_min': 0.8,
            'zeta_max': 1.2,
            'beta': 9
        }
    }

    DEEPSEEK_CONFIG = {
        "api_url": "https://api.deepseek.com/v1",  # 或你的本地地址
        "api_key": os.getenv("DEEPSEEK_API_KEY", "sk-xxx"),
        "call_type": "api",  # 'local' 或 'api'
        "timeout": 60,
        "retry_times": 3,
        "model_params": {
            "max_tokens": 2048,
            "temperature": 0.7
        }
    }

    OPENAI_CONFIG = {
        "api_key": os.getenv("OPENAI_API_KEY", "your_openai_fallback_key"),  # 修改了环境变量名
        "api_base": "https://api.openai.com/v1",  # 修复为OpenAI官方接口地址
        "chat_model": "gpt-4o",  # 修复为标准的OpenAI模型名
        "reasoner_model": "o1-preview"
    }

    # API 相关配置
    API_CONFIG = {
        'world_bank_base_url': 'https://api.worldbank.org/v2/',
        'who_gho_base_url': 'https://ghoapi.azureedge.net/api/',
        'timeout': 30,
        'max_retry': 3
    }

    # 高德地图 API 配置
    AMAP_CONFIG = {
        "key_name": "HLS_POL_Chengdu",
        "api_key": os.getenv("AMAP_API_KEY", "893aa291ba8fd5ceea01973a6162f182"),
        "poi_url": "https://restapi.amap.com/v3/place/text",
        "geocode_url": "https://restapi.amap.com/v3/geocode/geo"
    }

    # 搜索引擎API配置
    SEARCH_ENGINE_CONFIG = {
        "type": "serpapi",  # 可选 "serpapi" 或 "bing"
        "serpapi": {
            "api_key": os.getenv("SERPAPI_API_KEY", ""),
            "api_url": "https://serpapi.com/search",
            "result_num": 5,
            "retry_times": 3,
            "timeout": 10
        },
        "bing": {
            "api_key": os.getenv("BING_API_KEY", ""),
            "api_url": "https://api.bing.microsoft.com/v7.0/search",
            "result_num": 5,
            "timeout": 10
        },
        "news_api": {
            "api_key": os.getenv("NEWS_API_KEY", "CD3422DBBC0710A106D3C7178080DF4A"),  # Mediastack API Key
            "api_url": "http://api.mediastack.com/v1/news"
        }
    }

    # 公共卫生意识 (HLI) 模块数据映射
    PUBLIC_HEALTH_LITERACY_MAPPING = {
        "functional": ["basic_literacy", "reading_comprehension", "health_info_access"],
        "interactive": ["communication_skills", "social_support_seeking", "decision_making"],
        "critical": ["information_appraisal", "risk_perception", "system_navigation"]
    }


SETTINGS = Settings()



# 配置别名 - 维持向后兼容性
AMAP_CONFIG = SETTINGS.AMAP_CONFIG
ANALYSIS_PARAMS = SETTINGS.ANALYSIS_PARAMS
API_CONFIG = SETTINGS.API_CONFIG
BASE_HEALTH_FACTORS = SETTINGS.BASE_HEALTH_FACTORS
BASE_HEALTH_FACTORS_WHO = SETTINGS.BASE_HEALTH_FACTORS_WHO
BASE_MEDICAL_RESOURCE_DENSITIES = SETTINGS.BASE_MEDICAL_RESOURCE_DENSITIES
CLEANED_DATA_FILE = SETTINGS.CLEANED_DATA_FILE
DATA_CONFIG = SETTINGS.DATA_CONFIG
DATABASE_URL = SETTINGS.DATABASE_URL
DB_FIELD_MAPPINGS = SETTINGS.DB_FIELD_MAPPINGS
DEEPSEEK_CONFIG = SETTINGS.DEEPSEEK_CONFIG
DISEASE_CODES = SETTINGS.DISEASE_CODES
DPIO_CONFIG = SETTINGS.DPIO_CONFIG
EXTERNAL_FACTOR_SENSITIVITY = SETTINGS.EXTERNAL_FACTOR_SENSITIVITY
GAP_THRESHOLD_ADEQUATE = SETTINGS.GAP_THRESHOLD_ADEQUATE
GAP_THRESHOLD_REASONABLE = SETTINGS.GAP_THRESHOLD_REASONABLE
GAP_THRESHOLD_MILD = SETTINGS.GAP_THRESHOLD_MILD
GBD_ANALYSIS_CONFIG = SETTINGS.GBD_ANALYSIS_CONFIG
GBD_DATA_FILE = SETTINGS.GBD_DATA_FILE
GEOJSON_PATH_WORLD = SETTINGS.GEOJSON_PATH_WORLD
GEOJSON_PATH_CONTINENTS = SETTINGS.GEOJSON_PATH_CONTINENTS
GEOJSON_PATH_CHINA = SETTINGS.GEOJSON_PATH_CHINA
GEOJSON_PATH_CHENGDU = SETTINGS.GEOJSON_PATH_CHENGDU
GEOJSON_PATH_CHENGDU_HOSPITALS = SETTINGS.GEOJSON_PATH_CHENGDU_HOSPITALS
GEOJSON_PATH_CHENGDU_STREET = SETTINGS.GEOJSON_PATH_CHENGDU_STREET
HEALTH_IMPACT_FACTORS = SETTINGS.HEALTH_IMPACT_FACTORS
INTERVENTION_MEASURES = SETTINGS.INTERVENTION_MEASURES
OPENAI_CONFIG = SETTINGS.OPENAI_CONFIG
OUTPUT_SETTINGS = SETTINGS.OUTPUT_SETTINGS
OWID_INDICATORS = SETTINGS.OWID_INDICATORS
OWID_HEALTH_INDICATORS = SETTINGS.OWID_HEALTH_INDICATORS
PAGE_TITLE = "全国卫生资源配置优化平台"
RAW_DATA_FILE = SETTINGS.RAW_DATA_FILE
REDIS_CONFIG = SETTINGS.REDIS_CONFIG
RESOURCE_WEIGHTS = SETTINGS.RESOURCE_WEIGHTS
SCENARIO_MULTIPLIERS = SETTINGS.SCENARIO_MULTIPLIERS
SDE_MODEL_PARAMS = SETTINGS.SDE_MODEL_PARAMS
SEARCH_ENGINE_CONFIG = SETTINGS.SEARCH_ENGINE_CONFIG
STANDARD_COLUMN_MAPPING = SETTINGS.STANDARD_COLUMN_MAPPING
TOLERANCE_LEVELS = SETTINGS.TOLERANCE_LEVELS
WHO_INDICATOR_CODES = SETTINGS.WHO_INDICATOR_CODES
WHO_RESULT_COLUMN_MAPPINGS = SETTINGS.WHO_RESULT_COLUMN_MAPPINGS

if __name__ == "__main__":
    # 测试配置
    print(f"配置文件加载成功!")
    print(f"医疗资源基础密度: {Settings.BASE_MEDICAL_RESOURCE_DENSITIES}")
    print(f"WHO标准健康因素: {Settings.BASE_HEALTH_FACTORS_WHO}")
    print(f"WHO GHO指标代码: {Settings.WHO_INDICATOR_CODES}")
    print(f"敏感度系数: {Settings.EXTERNAL_FACTOR_SENSITIVITY}")
