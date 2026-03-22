# utils/logger.py
import logging
import os
import json
from datetime import datetime

def setup_logger(name: str = "health_system"):
    """配置全局日志器"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # 文件处理器
    log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)

    # 控制台处理器
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger

def log_missing_data(module_name: str, metric: str, year: int, region: str = "Global", details: str = ""):
    """
    记录并报告缺失的数据 (不使用模拟数据兜底)
    将其保存为专用的 missing_data 日志，供后续补全或算法降级处理
    """
    missing_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "missing_data")
    os.makedirs(missing_dir, exist_ok=True)
    
    missing_file = os.path.join(missing_dir, f"missing_report_{datetime.now().strftime('%Y-%m')}.json")
    
    missing_record = {
        "timestamp": datetime.now().isoformat(),
        "module": module_name,
        "region": region,
        "year": year,
        "metric": metric,
        "details": details
    }
    
    # 写入 JSON
    try:
        existing_data = []
        if os.path.exists(missing_file):
            with open(missing_file, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    pass
        existing_data.append(missing_record)
        with open(missing_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)
            
        logger.warning(f"[MISSING DATA] {module_name} 模块缺少真实数据: 地区={region}, 年份={year}, 指标={metric}. {details}")
    except Exception as e:
        logger.error(f"写入 missing_data 失败: {e}")

logger = setup_logger()