#!/usr/bin/env python3
"""测试中文新闻API"""
import requests
import json

r = requests.get('http://127.0.0.1:8081/api/news')
d = r.json()

print('=== 中文资讯测试结果 ===')
print(f'状态: {d["status"]}')
print(f'新闻数量: {len(d.get("news", []))}')

print('\n所有新闻标题:')
for i, news in enumerate(d.get('news', []), 1):
    print(f"{i}. {news['title']}")

print('\n第一条新闻详情:')
if d.get('news'):
    print(json.dumps(d['news'][0], indent=2, ensure_ascii=False))
