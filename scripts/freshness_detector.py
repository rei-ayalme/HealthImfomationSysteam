import json
import time

def check_freshness(data_source_meta):
    """
    检查数据新鲜度是否超过 730 天 (17520 小时)
    """
    freshness_hour = data_source_meta.get("freshness_hour", 0)
    if freshness_hour > 17520:
        return False, f"Data is too old: {freshness_hour} hours > 17520 hours"
    return True, "Data is fresh"

if __name__ == "__main__":
    # 模拟检查全球预期寿命数据新鲜度
    test_meta = {"freshness_hour": 18000}
    is_valid, msg = check_freshness(test_meta)
    print(f"验证结果: {is_valid} - {msg}")
    if not is_valid:
        print("操作: 触发回退策略，使用 UN 2019 历史趋势外推法...")
