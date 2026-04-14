import time
import logging
import uuid
import json
import os
import functools
from datetime import datetime
from collections import deque
import threading

# 统一日志配置
logger = logging.getLogger("DataOrchestrator")
logger.setLevel(logging.INFO)
# 如果未配置 handler，则添加一个
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.lock = threading.Lock()

    def record_success(self):
        with self.lock:
            self.failures = 0
            self.state = "CLOSED"

    def record_failure(self):
        with self.lock:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"

    def is_allowed(self):
        with self.lock:
            if self.state == "CLOSED":
                return True
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    return True
                return False
            if self.state == "HALF_OPEN":
                return True
        return True

class DataQualityMonitor:
    def __init__(self):
        self.records = deque(maxlen=10000)
        self.lock = threading.Lock()

    def add_record(self, record):
        with self.lock:
            self.records.append(record)

    def get_daily_report(self):
        with self.lock:
            now = time.time()
            one_day_ago = now - 86400
            recent_records = [r for r in self.records if r['timestamp'] >= one_day_ago]

        if not recent_records:
            return {
                "real_data_coverage": 0.0,
                "avg_response_time": 0.0,
                "fallback_count": 0,
                "freshness_avg": 0.0,
                "total_requests": 0
            }

        real_count = sum(1 for r in recent_records if r['dataSource'] == 'real')
        fallback_count = len(recent_records) - real_count
        total_time = sum(r['responseTime'] for r in recent_records)
        freshness_sum = sum(r.get('freshnessHour', 0) for r in recent_records if r['dataSource'] == 'real')

        return {
            "real_data_coverage": round((real_count / len(recent_records)) * 100, 2),
            "avg_response_time": round(total_time / len(recent_records), 3),
            "fallback_count": fallback_count,
            "freshness_avg": round(freshness_sum / max(real_count, 1), 2),
            "total_requests": len(recent_records)
        }

monitor = DataQualityMonitor()
circuit_breakers = {}

def get_circuit_breaker(module_name):
    if module_name not in circuit_breakers:
        circuit_breakers[module_name] = CircuitBreaker()
    return circuit_breakers[module_name]

class FallbackDataCache:
    def __init__(self):
        self.cache = {}
        
    def load_json(self, module_name, filepath):
        if not os.path.exists(filepath):
            logger.warning(f"Fallback JSON file not found: {filepath}")
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.cache[module_name] = data
                return data
        except Exception as e:
            logger.error(f"Error loading fallback JSON for {module_name}: {str(e)}")
            return None

    def get(self, module_name):
        return self.cache.get(module_name)

fallback_cache = FallbackDataCache()

def orchestrate_data(module_name, fallback_func, timeout=5.0, max_retries=3):
    def decorator(func):
        import asyncio

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            trace_id = str(uuid.uuid4())
            cb = get_circuit_breaker(module_name)
            start_time = time.time()
            
            record = {
                "trace_id": trace_id,
                "module": module_name,
                "timestamp": start_time,
                "dataSource": "fallback",
                "responseTime": 0,
                "httpStatus": 503,
                "recordCount": 0,
                "freshnessHour": 0
            }

            async def execute_fallback(error_msg=""):
                fallback_start = time.time()
                if asyncio.iscoroutinefunction(fallback_func):
                    data = await fallback_func(*args, **kwargs)
                else:
                    data = fallback_func(*args, **kwargs)
                record["responseTime"] = round(time.time() - start_time, 3)
                record["dataSource"] = "fallback"
                record["httpStatus"] = 200
                record["recordCount"] = len(data) if isinstance(data, list) else len(data.get("features", [])) if isinstance(data, dict) else 1
                monitor.add_record(record)
                
                log_msg = json.dumps(record)
                logger.warning(f"[{module_name}] Fallback activated. Reason: {error_msg}. Log: {log_msg}")
                return data

            if not cb.is_allowed():
                return await execute_fallback("Circuit Breaker OPEN")

            last_exception = None
            for attempt in range(max_retries):
                try:
                    call_start = time.time()
                    
                    try:
                        result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                    except asyncio.TimeoutError:
                        raise TimeoutError(f"Execution exceeded {timeout}s limit")
                    
                    cb.record_success()
                    
                    record["responseTime"] = round(time.time() - start_time, 3)
                    record["dataSource"] = "real"
                    record["httpStatus"] = 200
                    
                    if isinstance(result, dict) and "data" in result:
                        record["recordCount"] = len(result["data"])
                    elif isinstance(result, list):
                        record["recordCount"] = len(result)
                    else:
                        record["recordCount"] = 1
                    
                    if isinstance(result, dict) and "meta" in result and "freshness_hour" in result["meta"]:
                        record["freshnessHour"] = result["meta"]["freshness_hour"]
                        
                    monitor.add_record(record)
                    logger.info(f"[{module_name}] Real data fetched successfully. Log: {json.dumps(record)}")
                    return result

                except Exception as e:
                    last_exception = e
                    cb.record_failure()
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5 * (2 ** attempt))
            
            return await execute_fallback(str(last_exception))

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            trace_id = str(uuid.uuid4())
            cb = get_circuit_breaker(module_name)
            start_time = time.time()
            
            record = {
                "trace_id": trace_id,
                "module": module_name,
                "timestamp": start_time,
                "dataSource": "fallback",
                "responseTime": 0,
                "httpStatus": 503,
                "recordCount": 0,
                "freshnessHour": 0
            }

            def execute_fallback(error_msg=""):
                fallback_start = time.time()
                data = fallback_func(*args, **kwargs)
                record["responseTime"] = round(time.time() - start_time, 3)
                record["dataSource"] = "fallback"
                record["httpStatus"] = 200
                record["recordCount"] = len(data) if isinstance(data, list) else len(data.get("features", [])) if isinstance(data, dict) else 1
                monitor.add_record(record)
                
                log_msg = json.dumps(record)
                logger.warning(f"[{module_name}] Fallback activated. Reason: {error_msg}. Log: {log_msg}")
                return data

            if not cb.is_allowed():
                return execute_fallback("Circuit Breaker OPEN")

            last_exception = None
            for attempt in range(max_retries):
                try:
                    call_start = time.time()
                    
                    result = func(*args, **kwargs)
                    
                    call_duration = time.time() - call_start
                    if call_duration > timeout:
                        raise TimeoutError(f"Execution took {call_duration}s, exceeding {timeout}s limit")
                    
                    cb.record_success()
                    
                    record["responseTime"] = round(time.time() - start_time, 3)
                    record["dataSource"] = "real"
                    record["httpStatus"] = 200
                    
                    if isinstance(result, dict) and "data" in result:
                        record["recordCount"] = len(result["data"])
                    elif isinstance(result, list):
                        record["recordCount"] = len(result)
                    else:
                        record["recordCount"] = 1
                    
                    if isinstance(result, dict) and "meta" in result and "freshness_hour" in result["meta"]:
                        record["freshnessHour"] = result["meta"]["freshness_hour"]
                        
                    monitor.add_record(record)
                    logger.info(f"[{module_name}] Real data fetched successfully. Log: {json.dumps(record)}")
                    return result

                except Exception as e:
                    last_exception = e
                    cb.record_failure()
                    if attempt < max_retries - 1:
                        time.sleep(0.5 * (2 ** attempt))
            
            return execute_fallback(str(last_exception))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

# 质量报告 API 处理器
def get_quality_report():
    return monitor.get_daily_report()
