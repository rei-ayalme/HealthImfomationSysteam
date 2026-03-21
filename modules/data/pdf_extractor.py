import pdfplumber
import pandas as pd
import re
import os

class AppendixToCSVConverter:
    def __init__(self, target_year: int):
        self.target_year = target_year
        # 附录全球数据核心指标映射字典
        self.column_mapping_rules = {
            r'(国家|国别)': 'country',
            r'(预期寿命|期望寿命)': 'life_expectancy',
            r'(婴儿死亡率)': 'infant_mortality_rate',
            r'(孕产妇死亡率)': 'maternal_mortality_rate',
            r'(卫生.*支出.*GDP|卫生总费用.*GDP)': 'health_expenditure_pct_gdp',
            r'(每万人口.*医师|每千人口.*医师)': 'physicians_per_1k',
            r'(每万人口.*护士|每千人口.*护士)': 'nurses_per_1k',
            r'(每万人口.*床位|每千人口.*床位)': 'hospital_beds_per_1k'
        }

    def _clean_country_name(self, name: str) -> str:
        """清洗国家名称，去除脚注、空格和换行"""
        if pd.isna(name):
            return ""
        name = str(name).replace('\n', '').replace(' ', '')
        # 去除常见的年鉴脚注符号，如 [1], ①, a 等
        name = re.sub(r'[\*①②③④\d\(\)（）\[\]a-zA-Z]', '', name)
        return name

    def _extract_numeric(self, val) -> float:
        """提取纯数字（处理千分位和特殊缺失符号如 '-' 或 '…'）"""
        if pd.isna(val) or val == '':
            return None # 国际数据缺失较多，用 None 而不是 0 更好
        val_str = str(val).replace(',', '').replace(' ', '').replace('\n', '')
        match = re.search(r'-?\d+\.?\d*', val_str)
        return float(match.group()) if match else None

    def process_appendix(self, pdf_path: str, scan_last_n_pages: int = 50) -> pd.DataFrame:
        print(f"[{self.target_year}] 开始解析年鉴附录: {pdf_path}")
        all_tables_data = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                # 附录通常在最后，只扫描最后 N 页可以极大节省时间
                start_page = max(0, total_pages - scan_last_n_pages)
                
                for page_num in range(start_page, total_pages):
                    page = pdf.pages[page_num]
                    # 提取表格
                    tables = page.extract_tables({
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines"
                    })

                    for table in tables:
                        if not table or len(table) < 3:
                            continue
                        
                        df = pd.DataFrame(table).dropna(how='all').dropna(axis=1, how='all')
                        
                        # 假设第一行是表头，处理可能的重名列
                        header_1 = df.iloc[0].fillna('').astype(str)
                        header_2 = df.iloc[1].fillna('').astype(str) if len(df) > 1 else pd.Series(['']*len(df.columns))
                        raw_columns = (header_1 + "_" + header_2).str.replace('\n', '')
                        
                        # 避免列名重复引发 Reindexing error
                        new_cols = []
                        col_counts = {}
                        for col in raw_columns:
                            if col in col_counts:
                                col_counts[col] += 1
                                new_cols.append(f"{col}_{col_counts[col]}")
                            else:
                                col_counts[col] = 0
                                new_cols.append(col)
                        
                        df.columns = new_cols
                        df = df.iloc[2:].reset_index(drop=True)

                        # 核心判断：表头里有没有“国家”或“国别”
                        country_col = [c for c in df.columns if '国家' in c or '国别' in c]
                        if not country_col:
                            continue
                        
                        all_tables_data.append(df)

            if not all_tables_data:
                print(f"[{self.target_year}] 未能提取到有效的全球/国家统计附录表格。")
                return pd.DataFrame()

            # 合并提取到的附录表
            raw_df = pd.concat(all_tables_data, ignore_index=True)

            # ====== 字段重命名映射 ======
            standard_df = pd.DataFrame()
            standard_df['year'] = [self.target_year] * len(raw_df)
            
            for rule, std_col in self.column_mapping_rules.items():
                matched_cols = [c for c in raw_df.columns if re.search(rule, c)]
                if matched_cols:
                    standard_df[std_col] = raw_df[matched_cols[0]]

            # ====== 数据清洗 ======
            if 'country' in standard_df.columns:
                standard_df['country'] = standard_df['country'].apply(self._clean_country_name)
                
                # 剔除表头残留或空白行
                standard_df = standard_df[standard_df['country'] != '']
                standard_df = standard_df[~standard_df['country'].str.contains('国家|国别')]
                
                # 转换数值列
                numeric_cols = [c for c in standard_df.columns if c not in ['year', 'country']]
                for col in numeric_cols:
                    standard_df[col] = standard_df[col].apply(self._extract_numeric)

                # 按国家聚合，去重
                final_df = standard_df.groupby('country', as_index=False).max()
                
                print(f"[{self.target_year}] 附录全球数据提取成功！提取了 {len(final_df)} 个国家的数据。")
                return final_df
            else:
                print(f"[{self.target_year}] 未能成功映射出 country 字段。")
                return pd.DataFrame()

        except Exception as e:
            print(f"[{self.target_year}] 解析 PDF 文件 {pdf_path} 失败: {e}")
            return pd.DataFrame()

def extract_tables_from_pdf(pdf_path: str) -> pd.DataFrame:
    """
    为了兼容之前的调用方式，封装一个快捷入口，默认扫描最后50页并自动推断年份
    """
    year = 2020  # 默认年份
    year_match = re.search(r'20\d{2}', os.path.basename(pdf_path))
    if year_match:
        year = int(year_match.group())
        
    converter = AppendixToCSVConverter(target_year=year)
    return converter.process_appendix(pdf_path, scan_last_n_pages=50)

if __name__ == "__main__":
    # 测试提取
    test_pdf = r"d:\python_HIS\pythonProject\Health_Imformation_Systeam\data\raw\卫生年鉴表\2003.pdf"
    if os.path.exists(test_pdf):
        print(f"正在测试提取: {test_pdf}")
        df = extract_tables_from_pdf(test_pdf)
        print(f"提取结果形状: {df.shape}")
        if not df.empty:
            print(df.head())
    else:
        print("未找到测试 PDF 文件")
