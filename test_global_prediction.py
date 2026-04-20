#!/usr/bin/env python3
"""测试 global 预测接口"""
import requests
import json

API_URL = 'http://127.0.0.1:8084/api/disease_simulation'

print('=== Global 预测接口测试 ===')
print(f'请求: {API_URL}?region=global&years=15')
print()

try:
    r = requests.get(API_URL, params={'region': 'global', 'years': 15}, timeout=10)
    d = r.json()
    
    print(f'状态码: {r.status_code}')
    print(f"code: {d.get('code')}")
    print(f"message: {d.get('message')}")
    print()
    
    if d.get('code') == 200 and d.get('data'):
        data = d['data']
        print('[OK] 接口调用成功！')
        print(f"labels: {data.get('labels', [])}")
        print(f"datasets 数量: {len(data.get('datasets', []))}")
        
        for ds in data.get('datasets', []):
            print(f"  - {ds.get('label')}: {ds.get('data', [])}")
    else:
        print('[ERROR] 接口返回错误:')
        print(json.dumps(d, indent=2, ensure_ascii=False))
    
except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()
