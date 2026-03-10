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
    """医疗资源配置系统配置类"""
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    DATA_DIR = os.path.join(BASE_DIR, "data")
    RAW_DATA_PATH = os.path.join(DATA_DIR, "raw")
    PROCESSED_DATA_PATH = os.path.join(DATA_DIR, "processed")

    for path in [RAW_DATA_PATH, PROCESSED_DATA_PATH]:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

    # 疾病分析配置
    DISEASE_CODES = {
        'Malaria': '08',
        'Tuberculosis': '09',
        'Measles': '10'
    }

    # 干预措施列表 - 可通过配置进行动态管理（算法可替换）
    INTERVENTION_MEASURES = {
        'default': [
            {"name": "公共卫生教育", "type": "Primary Prevention", "priority": "High", "status": "Recommended"},
            {"name": "预防疫苗接种", "type": "Primary Prevention", "priority": "High", "status": "Essential"},
            {"name": "早期筛查", "type": "Secondary Prevention", "priority": "Medium", "status": "Recommended"},
            {"name": "治疗方案优化", "type": "Tertiary Prevention", "priority": "High", "status": "Priority"}
        ]
    }

    # SDE模型参数配置
    SDE_MODEL_PARAMS = {
        'dt': 5,  # 时间步长
        't_max': 30,  # 最大时间
        'num_samples': 10,
        'diffusion_coefficient': 0.1
    }

    # --- 路径配置 (使用相对路径指向 data 文件夹) ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RAW_DATA_FILE = os.path.join(RAW_DATA_PATH, "中国卫生健康统计年鉴面板数据（2001-2020年）.xlsx")
    CLEANED_DATA_FILE = os.path.join(PROCESSED_DATA_PATH, "cleaned_health_data.xlsx")
    GBD_DATA_FILE = os.path.join(BASE_DIR, "data", "raw", "IHME-GBD_2023_DATA-7dc96f7f-1.csv")

    # 列名标准映射
    STANDARD_COLUMN_MAPPING = {
        'physicians_per_1000': ['医师人数', 'doctors', 'physicians', '医师数量', '注册医师', '执业（助理）医师（人）'],
        'nurses_per_1000': ['护士人数', 'nurses', '护理人员', '注册护士', '注册护士（人）'],
        'hospital_beds_per_1000': ['床位数', 'hospital_beds', '病床数', '医院床位', '医疗卫生机构床位数（张）'],
        'population': ['总人口', 'population', '人口数量', '人口总数', '年末总人口（万人）'],
        'area_code': ['地区编码', '地域代码', '代码'],
        'region_name': ['地区名称', '地区', '城市', '省份', 'province', 'city'],
        'year': ['年份', 'year', '年度', 'time', 'date'],
        # WHO外部健康因素列名映射
        'hypertension_awareness': ['高血压认知', '高血压知晓率', 'hypertension awareness'],
        'hypertension_prevalence': ['高血压患病', '高血压患病率', 'hypertension prevalence'],
        'pm25_level': ['PM2.5', 'pm2.5浓度', '细颗粒物'],
        'obesity_rate': ['肥胖率', 'BMI≥30', '超重率'],
        'smoking_rate': ['吸烟率', '吸烟者', 'smoking'],
        'life_expectancy': ['预期寿命', '人均寿命', 'life expectancy']
    }

    # WHO GHO 指标代码映射
    WHO_INDICATOR_CODES = {
        'hypertension_awareness': 'NCD_HYPERTENSION_AWARENESS',
        'hypertension_prevalence': 'NCD_HYPERTENSION_PREVALENCE',
        'pm25_level': 'AIR_POLLUTION_PMC',
        'obesity_rate': 'NCD_BMI_30',
        'smoking_rate': 'NCD_SMOKING_PREVALENCE',
        'life_expectancy': 'LIFE_EXPECTANCY'
    }

    # WHO GHO 返回结果预处理列名映射
    WHO_RESULT_COLUMN_MAPPINGS = {
        'NCD_HYPERTENSION_AWARENESS': 'external_hypertension_awareness',
        'NCD_HYPERTENSION_PREVALENCE': 'external_hypertension_prevalence',
        'AIR_POLLUTION_PMC': 'external_pm25',
        'NCD_BMI_30': 'external_obesity',
        'NCD_SMOKING_PREVALENCE': 'external_smoking',
        'LIFE_EXPECTANCY': 'external_life_exp'
    }

    # 基础医疗资源密度配置（每千人）
    BASE_MEDICAL_RESOURCE_DENSITIES = {
        'physicians_per_1000': 2.5,  # 每千人医生数
        'nurses_per_1000': 3.2,     # 每千人护士数
        'hospital_beds_per_1000': 6.0  # 每千人床位数
    }

    # 外部健康因素基准值（WHO标准）
    BASE_HEALTH_FACTORS_WHO = {
        'hypertension_awareness': 28.0,   # 高血压认知率百分比 (WHO标准)
        'hypertension_prevalence': 25.2,  # 高血压患病率百分比
        'pm25_level': 42.0,              # PM2.5浓度 μg/m³
        'obesity_rate': 16.4,            # 肥胖率百分比
        'smoking_rate': 26.6,            # 吸烟率百分比
        'life_expectancy': 77.0          # 预期寿命
    }

    BASE_HEALTH_FACTORS = BASE_HEALTH_FACTORS_WHO

    # 资源权重配置
    RESOURCE_WEIGHTS = {
        'physicians_per_1000': 0.4,
        'nurses_per_1000': 0.35,
        'hospital_beds_per_1000': 0.25
    }

    # 外部因素敏感性系数
    EXTERNAL_FACTOR_SENSITIVITY = {
        'hypertension_awareness_sensitivity': 0.1,
        'hypertension_prevalence_sensitivity': 0.4,
        'pm25_sensitivity': 0.05,
        'obesity_sensitivity': 0.3,
        'smoking_sensitivity': 0.25,
        'threshold_ratio': 0.8
    }

    # 健康影响因子
    HEALTH_IMPACT_FACTORS = {
        'hypertension_prevalence_impact': 0.3,
        'pm25_impact': 0.04,
        'obesity_impact': 0.25,
        'smoking_impact': 0.2,
        'life_expectancy_adjustment': -0.02
    }
    #智能体设置
    LANGUAGES = {
        'zh': {
            'average_gap_rate': '平均相对缺口率',
            'supply_index': '资源供给指数',
            'demand_index': '理论需求数值',
            'gap_ratio': '相对缺口率'
        },
        'en': {
            'average_gap_rate': 'Average Gap Rate',
            'supply_index': 'Resource Supply Index',
            'demand_index': 'Theoretical Demand Value',
            'gap_ratio': 'Relative Gap Ratio'
        }
    }

    # 标签映射配置
    COLUMN_LABELS = {
        'chinese': {
            'supply_index_col': '资源供给指数',
            'demand_value_col': '理论需求数值',
            'relative_gap_col': '相对缺口率'
        },
        'english': {
            'supply_index_col': 'Supply_Index',
            'demand_value_col': 'Demand_Value',
            'relative_gap_col': 'Relative_Gap_Rate'
        }
    }

    # API配置
    API_CONFIG = {
        'world_bank_base_url': 'https://api.worldbank.org/v2/',
        'who_gho_base_url': 'https://ghoapi.azureedge.net/api/',
        'world_bank_api_timeout': 30,
        'who_gho_timeout': 60,
        'request_delay': 0.5,
        'max_retry_attempts': 3,
        'fallback_timeout_minutes': 5
    }

    # 分析参数
    ANALYSIS_PARAMS = {
        'min_gap_threshold': -0.1,
        'max_gap_threshold': 0.1,
        'gap_severity_labels': {
            'excess': '过度配置',
            'balanced': '配置合理',
            'shortage': '短缺严重',
            'critical_shortage': '极度短缺'
        },
        'severity_classification_logic': 'gap_ratio'
    }

    # 容错容差设置
    TOLERANCE_LEVELS = {
        'missing_data_tolerance': 0.3,
        'computation_error_threshold': 0.001,
        'nan_substitution_default': 0.0,
        'zero_division_fallback': 1e-8
    }

    # 数据库字段配置
    DB_FIELD_MAPPINGS = {
        'id_field': 'id',
        'primary_keys': ['region_name', 'year'],
        'numeric_fields': [
            'physicians_per_1000', 'nurses_per_1000', 'hospital_beds_per_1000',
            'population', 'supply_index', 'theoretical_need', 'resource_gap_ratio',
            'external_hypertension_awareness', 'external_hypertension_prevalence',
            'external_pm25', 'external_obesity', 'external_smoking',
            'external_life_exp'
        ],
        'textual_fields': ['region_name', 'gap_severity', 'year']
    }

    # 输出配置
    OUTPUT_SETTINGS = {
        'output_format': 'excel',
        'decimal_places': 4,
        'output_nan_placeholder': 'N/A',
        'default_date_format': '%Y-%m-%d'
    }

    # OWID配置
    OWID_HEALTH_INDICATORS = [
        "physicians-per-1000-people",  # 医生密度
        "share-of-deaths-from-non-communicable-diseases",  # 非传疾病死亡占比
        "share-of-deaths-from-communicable-diseases",  # 传疾病死亡占比
        "pm2-5-air-pollution-exposure",  # PM2.5暴露
        "share-of-adults-who-smoke",  # 成人吸烟率
        "health-expenditure-share-of-gdp",  # 卫生支出占GDP
        "life-expectancy"  # 人均预期寿命
    ]


SETTINGS = Settings()

# 配置别名 - 维持向后兼容性
PAGE_TITLE = "全国卫生资源配置优化平台"
RAW_DATA_FILE = SETTINGS.RAW_DATA_FILE
CLEANED_DATA_FILE = SETTINGS.CLEANED_DATA_FILE
GBD_DATA_FILE = SETTINGS.GBD_DATA_FILE
STANDARD_COLUMN_MAPPING = SETTINGS.STANDARD_COLUMN_MAPPING
BASE_MEDICAL_RESOURCE_DENSITIES = SETTINGS.BASE_MEDICAL_RESOURCE_DENSITIES
BASE_HEALTH_FACTORS = SETTINGS.BASE_HEALTH_FACTORS
BASE_HEALTH_FACTORS_WHO = SETTINGS.BASE_HEALTH_FACTORS_WHO
RESOURCE_WEIGHTS = SETTINGS.RESOURCE_WEIGHTS
EXTERNAL_FACTOR_SENSITIVITY = SETTINGS.EXTERNAL_FACTOR_SENSITIVITY
HEALTH_IMPACT_FACTORS = SETTINGS.HEALTH_IMPACT_FACTORS
WHO_INDICATOR_CODES = SETTINGS.WHO_INDICATOR_CODES
WHO_RESULT_COLUMN_MAPPINGS = SETTINGS.WHO_RESULT_COLUMN_MAPPINGS
API_CONFIG = SETTINGS.API_CONFIG
ANALYSIS_PARAMS = SETTINGS.ANALYSIS_PARAMS
TOLERANCE_LEVELS = SETTINGS.TOLERANCE_LEVELS
DB_FIELD_MAPPINGS = SETTINGS.DB_FIELD_MAPPINGS
OUTPUT_SETTINGS = SETTINGS.OUTPUT_SETTINGS
DISEASE_CODES = SETTINGS.DISEASE_CODES
SDE_MODEL_PARAMS = SETTINGS.SDE_MODEL_PARAMS
INTERVENTION_MEASURES = SETTINGS.INTERVENTION_MEASURES

if __name__ == "__main__":
    # 测试配置
    print(f"配置文件加载成功!")
    print(f"医疗资源基础密度: {Settings.BASE_MEDICAL_RESOURCE_DENSITIES}")
    print(f"WHO标准健康因素: {Settings.BASE_HEALTH_FACTORS_WHO}")
    print(f"WHO GHO指标代码: {Settings.WHO_INDICATOR_CODES}")
    print(f"敏感度系数: {Settings.EXTERNAL_FACTOR_SENSITIVITY}")
