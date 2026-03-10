import pandas as pd
import io
import re

def parse_text_to_df(raw_text: str) -> pd.DataFrame:
    """
    将搜索到的文本内容转化为 DataFrame。
    这里提供两种实现思路：
    """
    # 思路 A: 如果文本中包含 Markdown 表格或 CSV 格式（Agent 常见输出）
    try:
        # 尝试寻找文本中的表格特征
        if "|" in raw_text and "-" in raw_text:
            # 提取 Markdown 表格部分的简易逻辑
            lines = [line.strip() for line in raw_text.split('\n') if '|' in line]
            if len(lines) > 2:
                # 过滤掉分割线行
                header = [c.strip() for c in lines[0].split('|') if c.strip()]
                data = []
                for l in lines[2:]:
                    row = [c.strip() for c in l.split('|') if c.strip()]
                    if len(row) == len(header):
                        data.append(row)
                return pd.DataFrame(data, columns=header)
    except Exception:
        pass

    # 思路 B: 兜底方案 - 创建一个空的含有标准列名的 DF
    # 在实际 Agent 运行中，通常会让 LLM 直接输出 JSON，然后用 pd.DataFrame.from_dict()
    return pd.DataFrame(columns=['country_code', 'year', 'indicator_name', 'value'])