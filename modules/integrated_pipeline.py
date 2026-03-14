# modules/integrated_pipeline.py
import warnings
import os
import sys
import traceback
import pandas as pd
from pathlib import Path

# ==========================================
# 1. 动态路径加载 (因为脚本放在 modules/ 目录下)
# ==========================================
root = str(Path(__file__).parent.parent)
if root not in sys.path:
    sys.path.insert(0, root)

warnings.filterwarnings('ignore')

# 导入配置与数据库
from config.settings import SETTINGS
from db.connection import SessionLocal
from db.models import Base, AdvancedDiseaseTransition, AdvancedRiskCloud, AdvancedResourceEfficiency
# 导入所有清洗器
from modules.data.preprocessor import HealthDataPreprocessor
from modules.data.gbd_preprocessor import AdvancedGlobalHealthCleaner

# 导入所有分析器与算法库
from modules.analysis.health import UnifiedHealthAnalyzer
from modules.analysis.disease import DiseaseRiskAnalyzer
from modules.analysis.advanced_algorithms import HealthMathModels


class HealthDataPipeline:
    """
    健康数据统一指挥官管道
    整合了“本地卫生资源优化”与“全球疾病负担洞察(GBD)”两大核心业务
    """

    def __init__(self):
        self.db = SessionLocal()
        Base.metadata.create_all(bind=self.db.get_bind())

    def run_local_resource_analysis(self):
        """阶段一：本地卫生资源配置缺口与优化 (原 run_analysis.py 逻辑)"""
        print("\n" + "=" * 50)
        print("▶ 阶段一: 本地卫生资源配置缺口分析")
        print("=" * 50)

        input_file = SETTINGS.RAW_DATA_FILE
        output_file = SETTINGS.CLEANED_DATA_FILE

        if not os.path.exists(input_file):
            print(f"⚠️ 跳过本地分析: 未找到原始数据文件 '{input_file}'")
            return

        try:
            # 1. 数据预处理
            print("1. 执行基础预处理...")
            preprocessor = HealthDataPreprocessor()
            preprocessor.clean_health_data(input_file, output_file)

            # 2. 核心分析
            print("2. 执行核心指标分析...")
            raw_df = pd.read_excel(output_file)
            analyzer = UnifiedHealthAnalyzer(raw_df)

            latest_year = analyzer.data['year'].max() if 'year' in analyzer.data.columns else 2020
            print(f"-> 分析基准年份: {latest_year}")

            gap_data = analyzer.compute_resource_gap(latest_year)
            print(f"-> 缺口计算完成，共覆盖 {len(gap_data)} 个地区")

            # 3. 运筹学优化
            print("3. 执行运筹学资源再分配优化...")
            result = analyzer.optimize_resource_allocation(latest_year, 'maximize_health')
            if result and result.get('success'):
                print(f"✅ 优化方案已生成: {result.get('message', '最优解已找到')}")

        except Exception as e:
            print(f"❌ 阶段一执行失败: {e}")
            traceback.print_exc()

    def run_global_burden_analysis(self):
        """阶段二：GBD 疾病负担、风险归因与硬核DEA评价 (原 run_gbd_analysis.py 升级版)"""
        print("\n" + "=" * 50)
        print("▶ 阶段二: GBD 全球健康洞察与高级算法(DEA & 云模型)")
        print("=" * 50)

        # ---------------------------------------------------------
        # 1. 构造多源测试数据 (实际项目中可替换为 pd.read_csv 读取真实文件)
        # ---------------------------------------------------------
        print("1. 加载 GBD 多源数据集...")
        raw_risk_data = pd.DataFrame({
            'Location': ['China', 'China', 'USA'],
            'Year': [2019, 2019, 2019],
            'Risk Name': ['Smoking', 'Ambient particulate matter pollution', 'High BMI'],
            'PAF': [0.15, 0.08, 0.20],
            'exposure_category': ['高', '中', '极高']  # 用于触发云模型
        })

        raw_spectrum_data = pd.DataFrame({
            'Location': ['China', 'China', 'USA'],
            'Year': [2019, 2019, 2019],
            'cause': [400, 600, 600],  # 400级别传染病, 600级别非传染
            'Cause Name': ['Tuberculosis', 'Cardiovascular diseases', 'Cardiovascular diseases'],
            'Value': [1200.0, 5000.5, 4800.0]
        })

        raw_resources_data = pd.DataFrame({
            'Location': ['China', 'USA', 'India'],
            'Year': [2019, 2019, 2019],
            'physicians': [2.2, 2.6, 0.9],
            'beds': [4.3, 2.9, 0.5],
            'health expenditure per capita': [500, 10000, 60],
            'hale': [68.5, 66.1, 60.3]
        })

        raw_data_dict = {
            'gbd_disease': raw_spectrum_data,
            'gbd_risk': raw_risk_data,
            'who_resources': raw_resources_data
        }

        # ---------------------------------------------------------
        # 2. 调用高级清洗器 (提取 ETI、生成云参数、建立鲁棒边界)
        # ---------------------------------------------------------
        print("2. 启动高级特征工程 (云模型转化、ETI指数计算)...")
        cleaner = AdvancedGlobalHealthCleaner()
        cleaned_dict = cleaner.run_full_pipeline(raw_data_dict)

        disease_df = cleaned_dict.get('disease_spectrum', pd.DataFrame())
        risk_df = cleaned_dict.get('risk_attribution', pd.DataFrame())
        resource_df = cleaned_dict.get('health_resources', pd.DataFrame())

        # ---------------------------------------------------------
        # 3. 硬核算法环节：线性规划求 DEA 效率前沿面
        # ---------------------------------------------------------
        print("3. 执行线性规划算法求 DEA 综合技术效率...")
        if not resource_df.empty:
            # 投入变量 (医生、床位、卫生支出)
            X = resource_df[['physicians_per_1000', 'hospital_beds_per_1000', 'health_expenditure_per_capita']].fillna(
                0).values
            # 产出变量 (健康期望寿命 HALE)
            Y = resource_df[['hale']].fillna(0).values

            # 真实计算
            efficiencies = HealthMathModels.calculate_dea_efficiency(X, Y)
            resource_df['dea_efficiency'] = efficiencies
            print(f"-> DEA 计算完成，发现 {sum(efficiencies >= 0.99)} 个效率标杆地区。")

        # ---------------------------------------------------------
        # 4. 疾病风险归因分析测试
        # ---------------------------------------------------------
        analyzer = DiseaseRiskAnalyzer(spectrum_data=disease_df, risk_data=risk_df)
        print("\n-> 分析洞察结果节选：")
        print(analyzer.get_attribution(year=2019, region='China'))

        # ---------------------------------------------------------
        # 5. 结果落库 (持久化存储)
        # ---------------------------------------------------------
        print("\n4. 将高级特征持久化至数据库 (MySQL/SQLite)...")
        self._save_to_database(disease_df, risk_df, resource_df)

    def _save_to_database(self, disease_df: pd.DataFrame, risk_df: pd.DataFrame, resource_df: pd.DataFrame):
        """批量写入我们之前设计好的三张高级分析表"""
        try:
            # 清理旧测试数据 (如果你想保留历史，可注释掉这几行)
            self.db.query(AdvancedDiseaseTransition).delete()
            self.db.query(AdvancedRiskCloud).delete()
            self.db.query(AdvancedResourceEfficiency).delete()

            # 入库 1: 疾病转型 (ETI)
            if not disease_df.empty:
                for _, row in disease_df.iterrows():
                    record = AdvancedDiseaseTransition(
                        location_name=row.get('location_name'),
                        year=row.get('year'),
                        cause_name=row.get('cause_name'),
                        disease_category=row.get('disease_category'),
                        val=row.get('val'),
                        eti=row.get('eti'),
                        transition_stage=row.get('transition_stage')
                    )
                    self.db.add(record)

            # 入库 2: 云模型与风险
            if not risk_df.empty:
                for _, row in risk_df.iterrows():
                    record = AdvancedRiskCloud(
                        location_name=row.get('location_name'),
                        year=row.get('year'),
                        rei_name=row.get('rei_name'),
                        risk_category=row.get('risk_category'),
                        paf=row.get('paf'),
                        exposure_category=row.get('exposure_category'),
                        cloud_ex=row.get('exposure_category_Ex'),
                        cloud_en=row.get('exposure_category_En'),
                        cloud_he=row.get('exposure_category_He')
                    )
                    self.db.add(record)

            # 入库 3: DEA效率与鲁棒参数
            if not resource_df.empty:
                for _, row in resource_df.iterrows():
                    robust_dict = {
                        "physicians_bounds": [row.get('physicians_per_1000_robust_lower'),
                                              row.get('physicians_per_1000_robust_upper')],
                        "beds_bounds": [row.get('hospital_beds_per_1000_robust_lower'),
                                        row.get('hospital_beds_per_1000_robust_upper')]
                    }
                    record = AdvancedResourceEfficiency(
                        location_name=row.get('location_name'),
                        year=row.get('year'),
                        dea_efficiency=row.get('dea_efficiency'),
                        resource_quadrant=row.get('resource_quadrant'),
                        robust_data=robust_dict
                    )
                    self.db.add(record)

            self.db.commit()
            print("✅ 数据库入库成功！(表: adv_disease_transition, adv_risk_cloud, adv_resource_efficiency)")
        except Exception as e:
            self.db.rollback()
            print(f"❌ 数据库写入失败: {e}")
        finally:
            self.db.close()


def main():
    print("★★★ 健康信息系统综合分析管线启动 ★★★")
    pipeline = HealthDataPipeline()

    # 执行阶段一：本地宏观配置
    pipeline.run_local_resource_analysis()

    # 执行阶段二：GBD高级算法
    pipeline.run_global_burden_analysis()

    print("\n★★★ 全管线执行完毕！可以打开前端查看数据图表了 ★★★")


if __name__ == "__main__":
    main()