# run_analysis.py
import warnings
import os
from pathlib import Path
import sys
warnings.filterwarnings('ignore')

root = str(Path(__file__).parent.parent)
if root not in sys.path:
    sys.path.insert(0, root)

def main():
    """主运行函数"""
    print("开始卫生资源配置分析...")
    
    # 1. 数据预处理
    print("1. 数据预处理...")
    from modules.integrated_data_preprocessing_optimized import HealthDataPreprocessor

    input_file = "中国卫生健康统计年鉴面板数据（2001-2020年）.xlsx"
    output_file = "cleaned_health_data.xlsx"
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 输入文件 '{input_file}' 不存在!")
        print("请确保数据文件在当前目录下")
        return
    
    try:
        preprocessor = HealthDataPreprocessor()
        preprocessor.clean_health_data(input_file, output_file)
    except Exception as e:
        print(f"数据预处理失败: {e}")
        return
    
    # 2. 核心分析
    print("2. 核心分析...")
    from modules.unified_interface import get_unified_analyzer
    
    try:
        analyzer = get_unified_analyzer(output_file)  # 使用统一分析器
        # 注意：新的统一分析器可能没有 .years 属性，我们从数据源中推断
        data = analyzer.data_source['main']
        years = data['year'].unique() if 'year' in data.columns else [2020]
        latest_year = max(years)  # 获取最高年份

        print(f"分析年份: {latest_year}")
        
        # 计算缺口
        gap_data = analyzer.compute_resource_gap(latest_year)
        print(f"缺口分析完成，共{len(gap_data)}个地区")
        
        # 检查数据质量
        actual_supply_nonzero = gap_data[gap_data['实际供给'] > 0]
        if len(actual_supply_nonzero) == 0:
            print("⚠️  警告：所有地区的实际供给都为0，可能存在列名不匹配问题")
            print("请检查实际数据列名并调整 key_indicators 映射")
        
        # 优化分析
        print("3. 优化分析...")
        result1 = analyzer.optimize_resource_allocation(latest_year, 'maximize_health')
        result2 = analyzer.optimize_resource_allocation(latest_year, 'minimize_inequality')

        if result1['success']:
            print(f"最大化健康产出方案: {result1['message']}")
        if result2['success']:
            print(f"最小化不平等方案: {result2['message']}")
        
        # 保存结果
        output_filename = f"resource_gap_{latest_year}.xlsx"
        gap_data.to_excel(output_filename)
        print(f"结果已保存到 {output_filename}")
        
        print("分析完成！")
        
    except Exception as e:
        print(f"分析过程出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
