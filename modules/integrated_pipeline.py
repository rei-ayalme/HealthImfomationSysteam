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
from db.models import Base, HealthResource, AdvancedDiseaseTransition, AdvancedRiskCloud, AdvancedResourceEfficiency
from utils.logger import logger
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
        """阶段一：本地卫生资源配置缺口与优化 (处理真实的年鉴数据)"""
        logger.info("\n" + "=" * 50)
        logger.info("▶ 阶段一: 本地卫生资源配置缺口分析 (基于真实卫生年鉴)")
        logger.info("=" * 50)

        # 变更为处理真实年鉴数据的目录
        input_file = SETTINGS.YEARBOOK_DATA_PATH
        output_file = SETTINGS.CLEANED_DATA_FILE

        if not os.path.exists(input_file):
            logger.warning(f"跳过本地分析: 未找到真实的卫生年鉴目录 '{input_file}'")
            return

        try:
            # 1. 数据预处理
            logger.info(f"1. 扫描并提取目录 {input_file} 下的真实年鉴数据...")
            preprocessor = HealthDataPreprocessor()
            # 指定提取省级或市级的数据，这里默认提取"合计"层级
            preprocessor.clean_health_data(input_file, output_file, hierarchy_level="合计")

            # 2. 核心分析
            logger.info("2. 执行核心指标分析...")
            raw_df = pd.read_excel(output_file)
            
            # 由于真实的年鉴数据量极大且可能存在空缺，我们在进入分析器前进行最后一次清洗
            raw_df = raw_df.dropna(subset=['region_name', 'year'])
            if raw_df.empty:
                logger.warning("提取出的数据为空，请检查年鉴格式或映射配置")
                return
                
            analyzer = UnifiedHealthAnalyzer(raw_df)

            latest_year = analyzer.data['year'].max() if 'year' in analyzer.data.columns else 2020
            logger.info(f"-> 分析基准年份: {latest_year}")

            gap_data = analyzer.compute_resource_gap(latest_year)
            logger.info(f"-> 缺口计算完成，共覆盖 {len(gap_data)} 个地区")

            # 2.5 同步入库（分阶段：先落清洗基础数据，再落缺口分析结果）
            logger.info("-> 同步清洗后的本地数据到数据库...")
            from db.crud import save_processed_data_to_db
            self.db.query(HealthResource).delete()
            self.db.commit()

            save_processed_data_to_db(self.db, raw_df)

            gap_df = pd.DataFrame(gap_data).T.reset_index()
            if not gap_df.empty:
                gap_df = gap_df.rename(columns={'index': 'region_name'})
                if 'year' not in gap_df.columns:
                    gap_df['year'] = latest_year
                latest_snapshot = raw_df[raw_df['year'] == latest_year].copy()
                snapshot_cols = ['region_name', 'year', 'physicians_per_1000', 'nurses_per_1000', 'hospital_beds_per_1000', 'population']
                available_cols = [col for col in snapshot_cols if col in latest_snapshot.columns]
                latest_snapshot = latest_snapshot[available_cols].drop_duplicates('region_name')
                merged_gap_df = gap_df.merge(latest_snapshot, on=['region_name', 'year'], how='left')
                save_processed_data_to_db(self.db, merged_gap_df)
                logger.info("✅ 成功入库本地卫生资源数据与缺口分析结果！")

            # 3. 运筹学优化
            logger.info("3. 执行运筹学资源再分配优化...")
            result = analyzer.optimize_resource_allocation(latest_year, 'maximize_health')
            if result and result.get('success'):
                logger.info(f"✅ 优化方案已生成: {result.get('message', '最优解已找到')}")

        except Exception as e:
            logger.exception("阶段一执行失败")

    def run_global_burden_analysis(self):
        """阶段二：GBD 疾病负担、风险归因与硬核DEA评价 (原 run_gbd_analysis.py 升级版)"""
        logger.info("\n" + "=" * 50)
        logger.info("▶ 阶段二: GBD 全球健康洞察与高级算法(DEA & 云模型)")
        logger.info("=" * 50)

        # ---------------------------------------------------------
        # 1. 构造多源测试数据 (实际项目中可替换为 pd.read_csv 读取真实文件)
        # ---------------------------------------------------------
        logger.info("1. 加载 GBD/WDI 等真实多源数据集...")
        
        # 读取真实数据
        try:
            raw_gbd_data = pd.read_csv("data/raw/GBD.csv")
        except FileNotFoundError:
            from utils.logger import log_missing_data
            log_missing_data("GBD_Pipeline", "All Metrics", 2019, "Global", "未找到 GBD.csv 真实文件")
            raw_gbd_data = pd.DataFrame()

        try:
            raw_wdi_data = pd.read_csv("data/raw/WDI.csv")
        except FileNotFoundError:
            from utils.logger import log_missing_data
            log_missing_data("WDI_Pipeline", "All Metrics", 2019, "Global", "未找到 WDI.csv 真实文件")
            raw_wdi_data = pd.DataFrame()

        if not raw_gbd_data.empty:
            # 简单的真实数据抽取 (提取需要的字段给模型测试用)
            # 根据 GBD 数据实际列名调整，尝试匹配各种可能的列名
            measure_col = None
            for col in ['测量', 'measure', 'Measure']:
                if col in raw_gbd_data.columns:
                    measure_col = col
                    break
                    
            if measure_col:
                # 只过滤出与疾病和风险相关的子集，排除如"死亡排名"等无关测量
                valid_measures = ['死亡', 'Deaths', 'PAF', 'Attributable']
                mask = raw_gbd_data[measure_col].astype(str).apply(lambda x: any(m in x for m in valid_measures))
                raw_gbd_filtered = raw_gbd_data[mask]
                
                # 分离风险和谱系数据
                is_risk = raw_gbd_filtered[measure_col].astype(str).str.contains('风险|PAF|Attributable', na=False, case=False)
                raw_risk_data = raw_gbd_filtered[is_risk]
                raw_spectrum_data = raw_gbd_filtered[~is_risk]
            else:
                # 兼容旧版本数据或没有 measure 列的情况
                raw_risk_data = raw_gbd_data.copy()
                raw_spectrum_data = raw_gbd_data.copy()
            
            # 标准化列名映射
            col_mapping = {
                '地理位置': 'Location',
                'location': 'Location',
                'Location Name': 'Location',
                '年份': 'Year',
                'year': 'Year',
                '死亡或受伤原因': 'Cause Name',
                'cause': 'Cause Name',
                'cause_name': 'Cause Name',
                '数值': 'Value',
                'val': 'Value'
            }
            
            # 如果从 GBD 中抽不到，使用模拟回退
            if raw_risk_data.empty:
                from utils.logger import log_missing_data
                log_missing_data("GBD_Pipeline", "Risk/PAF", 2019, "Global", "从 GBD 中未能提取出有效的风险数据字段")
                raw_risk_data = pd.DataFrame(columns=['Location', 'Year', 'Risk Name', 'PAF', 'exposure_category'])
            else:
                raw_risk_data = raw_risk_data.rename(columns=col_mapping)
                # 尝试找到风险名称列
                for col in ['Cause Name', 'cause_name', 'risk', 'Risk Name', '死亡或受伤原因']:
                    if col in raw_risk_data.columns:
                        raw_risk_data = raw_risk_data.rename(columns={col: 'Risk Name'})
                        break
                
                # 尝试找到数值列
                for col in ['Value', 'val', '数值', 'mean']:
                    if col in raw_risk_data.columns:
                        raw_risk_data = raw_risk_data.rename(columns={col: 'PAF'})
                        break
                        
                raw_risk_data['exposure_category'] = '中' # 临时填充
                
            if raw_spectrum_data.empty:
                from utils.logger import log_missing_data
                log_missing_data("GBD_Pipeline", "Disease Spectrum", 2019, "Global", "从 GBD 中未能提取出有效的疾病谱系字段")
                raw_spectrum_data = pd.DataFrame(columns=['Location', 'Year', 'cause', 'Cause Name', 'Value'])
            else:
                raw_spectrum_data = raw_spectrum_data.rename(columns=col_mapping)
                raw_spectrum_data['cause'] = 600 # 临时填充
        else:
            raw_risk_data = pd.DataFrame(columns=['Location', 'Year', 'Risk Name', 'PAF', 'exposure_category'])
            raw_spectrum_data = pd.DataFrame(columns=['Location', 'Year', 'cause', 'Cause Name', 'Value'])

        # 构造资源数据
        if not raw_wdi_data.empty and 'Country Name' in raw_wdi_data.columns and 'Indicator Name' in raw_wdi_data.columns:
            # 从 WDI 数据中提取医生、床位等数据
            physicians = raw_wdi_data[raw_wdi_data['Indicator Name'].str.contains('Physicians', na=False, case=False)]
            beds = raw_wdi_data[raw_wdi_data['Indicator Name'].str.contains('Hospital beds', na=False, case=False)]
            expenditure = raw_wdi_data[raw_wdi_data['Indicator Name'].str.contains('Health expenditure', na=False, case=False)]
            
            wdi_list = []
            countries = raw_wdi_data['Country Name'].unique()[:50] # 取前50个国家
            for country in countries:
                p_val = physicians[physicians['Country Name'] == country]['2019'].values if '2019' in physicians.columns else [2.0]
                b_val = beds[beds['Country Name'] == country]['2019'].values if '2019' in beds.columns else [3.0]
                e_val = expenditure[expenditure['Country Name'] == country]['2019'].values if '2019' in expenditure.columns else [500.0]
                
                wdi_list.append({
                    'Location': country,
                    'Year': 2019,
                    'physicians': p_val[0] if len(p_val) > 0 and not pd.isna(p_val[0]) else 2.0,
                    'beds': b_val[0] if len(b_val) > 0 and not pd.isna(b_val[0]) else 3.0,
                    'health expenditure per capita': e_val[0] if len(e_val) > 0 and not pd.isna(e_val[0]) else 500.0,
                    'hale': 65.0 # WDI可能没有HALE，使用默认值
                })
            raw_resources_data = pd.DataFrame(wdi_list)
        else:
            from utils.logger import log_missing_data
            log_missing_data("WDI_Pipeline", "Resource Capacity", 2019, "Global", "WDI 资源数据不足")
            raw_resources_data = pd.DataFrame(columns=['Location', 'Year', 'physicians', 'beds', 'health expenditure per capita', 'hale'])

        raw_data_dict = {
            'gbd_disease': raw_spectrum_data,
            'gbd_risk': raw_risk_data,
            'who_resources': raw_resources_data
        }

        # ---------------------------------------------------------
        # 2. 调用高级清洗器 (提取 ETI、生成云参数、建立鲁棒边界)
        # ---------------------------------------------------------
        logger.info("2. 启动高级特征工程 (云模型转化、ETI指数计算)...")
        cleaner = AdvancedGlobalHealthCleaner()
        cleaned_dict = cleaner.run_full_pipeline(raw_data_dict)

        disease_df = cleaned_dict.get('disease_spectrum', pd.DataFrame())
        risk_df = cleaned_dict.get('risk_attribution', pd.DataFrame())
        resource_df = cleaned_dict.get('health_resources', pd.DataFrame())

        # ---------------------------------------------------------
        # 3. 硬核算法环节：线性规划求 DEA 效率前沿面
        # ---------------------------------------------------------
        logger.info("3. 执行线性规划算法求 DEA 综合技术效率...")
        
        # 为了测试真实 DEA 模型，我们构造或者从本地清洗好的省份数据中提取 X 和 Y 矩阵
        # 此处我们模拟从 cleaned_health_data.xlsx 中读取省级数据
        from config.settings import SETTINGS
        local_db_path = SETTINGS.CLEANED_DATA_FILE
        if os.path.exists(local_db_path):
            try:
                local_df = pd.read_excel(local_db_path)
                # 假设提取 2020 年的省级数据进行 DEA 计算
                df_dea = local_df[local_df['year'] == 2020].copy()
                if not df_dea.empty:
                    # 确保投入产出不能为 0
                    X_dea = df_dea[['physicians_per_1000', 'hospital_beds_per_1000', 'nurses_per_1000']].fillna(0.1).replace(0, 0.1).values
                    # 这里假设以 population (或其他可用指标) 作为简单的产出替代，实际应使用真实的诊疗/出院人数
                    Y_dea = df_dea[['population']].fillna(0.1).replace(0, 0.1).values
                    
                    efficiencies = HealthMathModels.calculate_dea_efficiency(X_dea, Y_dea)
                    df_dea['dea_efficiency'] = efficiencies
                    logger.info(f"-> 本地省份级 DEA 计算完成，共处理 {len(df_dea)} 个省/市，发现 {sum(efficiencies >= 0.99)} 个效率标杆。")
            except Exception as e:
                logger.warning(f"-> 读取本地数据计算 DEA 失败: {e}")
        
        if not resource_df.empty:
            # 投入变量 (医生、床位、卫生支出)
            X = resource_df[['physicians_per_1000', 'hospital_beds_per_1000', 'health_expenditure_per_capita']].fillna(0.1).replace(0, 0.1).values
            # 产出变量 (健康期望寿命 HALE)
            Y = resource_df[['hale']].fillna(0.1).replace(0, 0.1).values

            # 真实计算
            efficiencies = HealthMathModels.calculate_dea_efficiency(X, Y)
            resource_df['dea_efficiency'] = efficiencies
            logger.info(f"-> 国际对比 DEA 计算完成，发现 {sum(efficiencies >= 0.99)} 个效率标杆地区。")

        # ---------------------------------------------------------
        # 4. E2SFCA 空间可及性分析测试
        # ---------------------------------------------------------
        logger.info("\n4. 执行 E2SFCA 微观空间可及性计算...")
        try:
            from modules.spatial.poi_fetcher import fetch_hospital_pois, fetch_community_demand
            logger.info("-> 正在通过高德 API 获取成都市医院及社区人口数据...")
            
            df_3a = fetch_hospital_pois(city="成都市", keyword="三甲医院")
            if not df_3a.empty:
                df_3a['type'] = '三甲医院'
                df_3a['search_radius'] = 30.0  # 60分钟圈
                
            df_comm = fetch_hospital_pois(city="成都市", keyword="社区卫生服务中心")
            if not df_comm.empty:
                df_comm['type'] = '社区医院'
                df_comm['search_radius'] = 7.5  # 15分钟圈
                
            supply_df = pd.concat([df_3a, df_comm], ignore_index=True) if not df_3a.empty or not df_comm.empty else pd.DataFrame()
            demand_df = fetch_community_demand(city="成都市")
            
            if not supply_df.empty and not demand_df.empty:
                logger.info(f"-> 成功获取 {len(supply_df)} 家医疗机构，{len(demand_df)} 个社区节点，开始计算 E2SFCA 指数...")
                
                # 注意：不再使用 random 随机模拟人口等，如果缺失，抛出日志并放弃或使用真实均值填补
                if 'population' not in demand_df.columns:
                    from utils.logger import log_missing_data
                    log_missing_data("HealthMathModels", "E2SFCA", 2024, "Chengdu", "缺失网格人口数据")
                    # 记录完缺失后我们仍然给一个默认常量以保证流程能跑通，但不使用随机数造假
                    demand_df['population'] = 5000
                    
                # 传入 use_network_distance=True 使用真实高德路网计算可及性
                access_scores = HealthMathModels.calculate_e2sfca(
                    supply_df, demand_df, 
                    radius_col='search_radius',
                    default_radius_km=10.0, 
                    decay_type='piecewise_power',
                    use_network_distance=True
                )
                demand_df['2sfca_access_score'] = access_scores
                logger.info("-> E2SFCA 计算完成，部分社区可及性指数：\n" + str(demand_df[['name', '2sfca_access_score']].head()))
            else:
                logger.warning("-> 获取微观地理数据失败，跳过 E2SFCA 计算。")
        except Exception as e:
            logger.exception("-> E2SFCA 计算异常")

        # ---------------------------------------------------------
        # 5. 疾病风险归因分析测试
        # ---------------------------------------------------------
        analyzer = DiseaseRiskAnalyzer(spectrum_data=disease_df, risk_data=risk_df)
        logger.info("\n-> 分析洞察结果节选：")
        logger.info(analyzer.get_attribution(year=2019, region='China'))

        # ---------------------------------------------------------
        # 6. 结果落库 (持久化存储)
        # ---------------------------------------------------------
        logger.info("\n6. 将高级特征持久化至数据库 (MySQL/SQLite)...")
        self._save_to_database(disease_df, risk_df, resource_df)
        
        # 将清洗好的数据持久化为文件以供分析使用
        try:
            from config.settings import SETTINGS
            if not disease_df.empty:
                disease_df.to_csv(os.path.join(SETTINGS.PROCESSED_DATA_PATH, "cleaned_gbd_disease.csv"), index=False)
            if not risk_df.empty:
                risk_df.to_csv(os.path.join(SETTINGS.PROCESSED_DATA_PATH, "cleaned_gbd_risk.csv"), index=False)
            if not resource_df.empty:
                resource_df.to_csv(os.path.join(SETTINGS.PROCESSED_DATA_PATH, "cleaned_wdi_resources.csv"), index=False)
            logger.info("✅ 已将清洗后的国际数据保存至 data/processed/")
        except Exception as e:
            logger.warning(f"保存清洗后的国际数据失败: {e}")

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
                        transition_stage=row.get('transition_stage'),
                        latitude=0.0,
                        longitude=0.0,
                        urban_zone_type='未知',
                        elderly_ratio=0.0
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
            logger.info("✅ 数据库入库成功！(表: adv_disease_transition, adv_risk_cloud, adv_resource_efficiency)")
        except Exception as e:
            self.db.rollback()
            logger.exception("❌ 数据库写入失败")
        finally:
            self.db.close()


def main():
    logger.info("★★★ 健康信息系统综合分析管线启动 ★★★")
    pipeline = HealthDataPipeline()

    # 执行阶段一：本地宏观配置
    pipeline.run_local_resource_analysis()

    # 执行阶段二：GBD高级算法
    pipeline.run_global_burden_analysis()

    logger.info("\n★★★ 全管线执行完毕！可以打开前端查看数据图表了 ★★★")


if __name__ == "__main__":
    main()
