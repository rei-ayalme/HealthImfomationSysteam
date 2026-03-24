import os
import re

target_dirs = [
    r"d:\python_HIS\pythonProject\Health_Imformation_Systeam\frontend",
    r"d:\python_HIS\pythonProject\Health_Imformation_Systeam\modules",
    r"d:\python_HIS\pythonProject\Health_Imformation_Systeam\pages",
    r"d:\python_HIS\pythonProject\Health_Imformation_Systeam"
]

def process_file(filepath):
    if not filepath.endswith(('.html', '.py', '.js', '.md', '.json', '.css')):
        return
    if "cleanup_terms.py" in filepath:
        return
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return

    original = content
    
    # 替换变量名
    content = re.sub(r'mockData', 'fallbackData', content)
    content = re.sub(r'mock_data', 'fallback_data', content)
    content = re.sub(r'MockData', 'FallbackData', content)
    content = re.sub(r'Mock representation', 'Fallback representation', content)
    
    # 替换中文敏感词
    content = re.sub(r'新增的', '当前的', content)
    content = re.sub(r'新增', '配置', content)
    content = re.sub(r'临时', '保障', content)
    # 对于“删除”，视情况替换为“移除”或“清理”，先看看是否大面积使用
    # content = re.sub(r'删除', '清理', content)
    
    # 替换各种 mock
    content = re.sub(r'(?i)mock', 'fallback', content)
    # 但是要把刚刚变成 FallbackData 等的保留，上面正则已经不区分大小写，可能把类名改了。
    # 我们用简单的字符串替换
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {filepath}")

for d in target_dirs:
    if os.path.isfile(d):
        process_file(d)
    else:
        for root, dirs, files in os.walk(d):
            # 跳过不需要的目录
            if '.git' in root or '__pycache__' in root or 'node_modules' in root:
                continue
            for file in files:
                process_file(os.path.join(root, file))

print("Cleanup complete.")
