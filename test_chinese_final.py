#!/usr/bin/env python3
"""测试中文新闻API"""
import requests
import json

API_URL = 'http://127.0.0.1:8082/api/news'

print('=== 中文资讯组件测试 ===')
print(f'请求: {API_URL}')
print()

try:
    r = requests.get(API_URL, timeout=10)
    d = r.json()
    
    print(f'状态: {d["status"]}')
    
    if d.get('cache_info'):
        print(f"缓存信息: {d['cache_info']}")
    
    print(f"\n新闻数量: {len(d.get('news', []))}")
    print("\n所有新闻标题:")
    print("-" * 50)
    
    for i, news in enumerate(d.get('news', []), 1):
        title = news.get('title', '无标题')
        source = news.get('source', '未知来源')
        print(f"{i}. {title}")
        print(f"   来源: {source}")
        print()
    
    print("-" * 50)
    print("\n第一条新闻详情:")
    if d.get('news'):
        first = d['news'][0]
        print(f"标题: {first.get('title')}")
        print(f"描述: {first.get('description')}")
        print(f"来源: {first.get('source')}")
        print(f"日期: {first.get('publishedAt')}")
        print(f"链接: {first.get('url')}")
    
    # 检查是否都是中文
    print("\n" + "=" * 50)
    print("中文内容检查:")
    all_chinese = True
    for news in d.get('news', []):
        title = news.get('title', '')
        # 简单检查是否包含中文字符
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in title)
        if not has_chinese:
            all_chinese = False
            print(f"  ⚠ 非中文标题: {title[:30]}...")
    
    if all_chinese:
        print("  ✓ 所有标题均为中文")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
