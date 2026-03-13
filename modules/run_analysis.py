# run_analysis.py
import warnings
import os
import sys
import traceback
import pandas as pd
from pathlib import Path
# 1. 将所有导入统一放在文件顶部（全局作用域）
from modules.data.preprocessor import HealthDataPreprocessor
from modules.analysis.health import UnifiedHealthAnalyzer
from config.settings import SETTINGS


warnings.filterwarnings('ignore')

root = str(Path(__file__).parent.parent)
if root not in sys.path:
    sys.path.insert(0, root)


def main():
    """主运行函数"""
    print("开始卫生资源配置分析...")

    # 使用 SETTINGS 中配置的统一路径
    input_file = SETTINGS.RAW_DATA_FILE
    output_file = SETTINGS.CLEANED_DATA_FILE

    # 1. 数据预处理
    print("1. 数据预处理...")

    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 输入文件 '{input_file}' 不存在!")
        print("请确保原始数据文件已放置在 data/raw 目录下")
        return

    try:
        # 只实例化并执行一次
        preprocessor = HealthDataPreprocessor()
        preprocessor.clean_health_data(input_file, output_file)
        print("数据清洗完成！")
    except Exception as e:
        print(f"数据预处理失败: {e}")
        return

    # 2. 核心分析
    print("2. 核心分析...")
    try:
        raw_df = pd.read_excel(output_file)
        analyzer = UnifiedHealthAnalyzer(raw_df)  # 使用统一分析器

        # 注意：新的统一分析器可能没有 .years 属性，我们从数据源中推断
        data = analyzer.data
        years = data['year'].unique() if 'year' in data.columns else [2020]
        latest_year = max(years)  # 获取最高年份

        print(f"分析年份: {latest_year}")

        # 计算缺口
        gap_data = analyzer.compute_resource_gap(latest_year)
        print(f"缺口分析完成，共{len(gap_data)}个地区")

        # 检查数据质量
        # 注意：这里改成了英文列名，你需要确保与 health.py 输出的一致
        # 假设之前的中文 '实际供给' 对应的是 'actual_supply_index'
        if 'actual_supply_index' in gap_data.columns:
            actual_supply_nonzero = gap_data[gap_data['actual_supply_index'] > 0]
            if len(actual_supply_nonzero) == 0:
                print("⚠️  警告：所有地区的实际供给都为0，可能存在列名不匹配问题")
                print("请检查实际数据列名并调整 key_indicators 映射")

        # 3. 优化分析
        print("3. 优化分析...")
        result1 = analyzer.optimize_resource_allocation(latest_year, 'maximize_health')

        # 注意：你的 health.py 里的接口目前只支持了一个预算参数，如果没有区分不同objective的实现，这里可能会报错
        # 建议先运行一个基础的优化测试
        if result1.get('success'):
            print(f"资源优化方案: 预计改善 {result1.get('improvement_estimate')}")

        # 保存结果
        output_filename = f"resource_gap_{latest_year}.xlsx"
        gap_data.to_excel(output_filename)
        print(f"结果已保存到 {output_filename}")

        print("分析完成！")

    except Exception as e:
        print(f"分析过程出现错误: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()