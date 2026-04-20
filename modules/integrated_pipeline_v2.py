# modules/integrated_pipeline_v2.py
"""
统一数据调用管道 - 优化版本

优化要点 (2026-04-17):
1. 实现基于 column_mapping.json 的动态列名映射
2. 消除数据源调用冗余，实现"一次读取，多次分析"
3. 添加数据缓存机制和性能监控
4. 增强代码健壮性和日志记录
5. 统一数据格式验证

解决报告问题:
- 问题1: 数据源调用冗余
- 问题2: 数据格式不匹配
- 问题3: DEA效率计算逻辑错误 (已修正投入产出指标)
"""

import json
import time
import hashlib
import warnings
import os
import sys
import traceback
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from functools import wraps
from datetime import datetime

# ==========================================
# 1. 动态路径加载
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

# 导入双引擎架构
from modules.data.loader import DataLoader
from modules.data.processor import DataProcessor

# 导入所有分析器与算法库
from modules.core.analyzer import ComprehensiveAnalyzer
from modules.core.evaluator import HealthMathModels, EfficiencyEvaluator, DEAInputOutputConfig


@dataclass
class DataLoadMetrics:
    """数据加载性能指标"""
    load_start_time: float = field(default_factory=time.time)
    load_end_time: float = 0.0
    cache_hit: bool = False
    rows_loaded: int = 0
    columns_loaded: int = 0
    file_size_mb: float = 0.0
    data_source: str = ""
    
    @property
    def load_duration_ms(self) -> float:
        """获取加载耗时（毫秒）"""
        end = self.load_end_time if self.load_end_time > 0 else time.time()
        return (end - self.load_start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'load_duration_ms': round(self.load_duration_ms, 2),
            'cache_hit': self.cache_hit,
            'rows_loaded': self.rows_loaded,
            'columns_loaded': self.columns_loaded,
            'file_size_mb': round(self.file_size_mb, 2),
            'data_source': self.data_source
        }


class DataCache:
    """
    数据缓存管理器
    
    实现内存缓存和文件缓存两级机制，避免重复数据加载
    """
    
    def __init__(self, max_memory_items: int = 10, cache_dir: str = "data/cache"):
        self._memory_cache: Dict[str, Any] = {}
        self._cache_metadata: Dict[str, Dict] = {}
        self.max_memory_items = max_memory_items
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        
    def _generate_cache_key(self, data_source: str, params: Dict) -> str:
        """生成缓存键"""
        key_str = f"{data_source}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        # 使用 CSV 格式作为默认缓存格式（兼容性更好）
        return self.cache_dir / f"{cache_key}.csv"
    
    def get(self, data_source: str, params: Dict) -> Tuple[Optional[pd.DataFrame], bool]:
        """
        从缓存获取数据
        
        Returns:
            (data, cache_hit): 数据和是否命中缓存
        """
        cache_key = self._generate_cache_key(data_source, params)
        
        # 1. 检查内存缓存
        if cache_key in self._memory_cache:
            self.logger.debug(f"内存缓存命中: {data_source}")
            return self._memory_cache[cache_key], True
        
        # 2. 检查文件缓存
        cache_file = self._get_cache_file_path(cache_key)
        if cache_file.exists():
            try:
                data = pd.read_csv(cache_file)
                # 加载到内存缓存
                self._add_to_memory_cache(cache_key, data)
                self.logger.debug(f"文件缓存命中: {data_source}")
                return data, True
            except Exception as e:
                self.logger.warning(f"读取缓存文件失败: {e}")
        
        return None, False
    
    def set(self, data_source: str, params: Dict, data: pd.DataFrame, 
            metadata: Optional[Dict] = None) -> None:
        """设置缓存"""
        cache_key = self._generate_cache_key(data_source, params)
        
        # 添加到内存缓存
        self._add_to_memory_cache(cache_key, data)
        
        # 保存到文件缓存
        try:
            cache_file = self._get_cache_file_path(cache_key)
            data.to_csv(cache_file, index=False)

            # 保存元数据
            self._cache_metadata[cache_key] = {
                'data_source': data_source,
                'params': params,
                'timestamp': datetime.now().isoformat(),
                'rows': len(data),
                'columns': len(data.columns),
                **(metadata or {})
            }
        except Exception as e:
            self.logger.warning(f"保存缓存文件失败: {e}")
    
    def _add_to_memory_cache(self, cache_key: str, data: pd.DataFrame) -> None:
        """添加到内存缓存，LRU策略"""
        if len(self._memory_cache) >= self.max_memory_items:
            # 移除最旧的项
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]
        
        self._memory_cache[cache_key] = data
    
    def clear(self) -> None:
        """清空缓存"""
        self._memory_cache.clear()
        self._cache_metadata.clear()
        # 清空文件缓存
        for f in self.cache_dir.glob("*.csv"):
            f.unlink()
        self.logger.info("缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'memory_cache_items': len(self._memory_cache),
            'file_cache_items': len(list(self.cache_dir.glob("*.csv"))),
            'metadata_entries': len(self._cache_metadata)
        }


class ColumnMappingManager:
    """
    列名映射管理器
    
    基于 column_mapping.json 实现动态列名映射
    支持多数据源类型和省份代码的差异化处理
    """
    
    def __init__(self, mapping_file: str = 'config/column_mapping.json'):
        self.mapping_file = Path(mapping_file)
        self.column_map: Dict[str, Any] = {}
        self.logger = logger
        self._load_mapping()
        
    def _load_mapping(self) -> None:
        """加载列名映射配置"""
        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                self.column_map = json.load(f)
            self.logger.info(f"列名映射配置加载成功，版本: {self.column_map.get('_meta', {}).get('version', 'unknown')}")
        except Exception as e:
            self.logger.error(f"加载列名映射配置失败: {e}")
            self.column_map = {}
    
    def get_standard_name(self, column_name: str) -> Optional[str]:
        """
        根据列名获取标准名称
        
        Args:
            column_name: 原始列名
            
        Returns:
            标准列名，如果未找到则返回 None
        """
        column_name_lower = column_name.lower().strip()
        
        for standard_name, config in self.column_map.items():
            if standard_name.startswith('_'):
                continue
                
            aliases = config.get('aliases', [])
            if column_name_lower in [a.lower().strip() for a in aliases]:
                return standard_name
            
            # 精确匹配标准名称
            if column_name_lower == standard_name.lower():
                return standard_name
        
        return None
    
    def create_mapping_dict(self, df_columns: List[str]) -> Dict[str, str]:
        """
        为数据框创建列名映射字典
        
        Args:
            df_columns: 数据框的列名列表
            
        Returns:
            原始列名到标准列名的映射字典
        """
        mapping = {}
        unmatched = []
        
        for col in df_columns:
            standard_name = self.get_standard_name(col)
            if standard_name:
                mapping[col] = standard_name
            else:
                unmatched.append(col)
        
        if unmatched:
            self.logger.warning(f"以下列名未能映射到标准名称: {unmatched}")
        
        return mapping
    
    def apply_mapping(self, df: pd.DataFrame, data_source_type: str = 'yearbook') -> pd.DataFrame:
        """
        应用列名映射到数据框
        
        Args:
            df: 原始数据框
            data_source_type: 数据源类型 (yearbook, gbd, wdi等)
            
        Returns:
            列名标准化后的数据框
        """
        if df.empty:
            return df
        
        mapping = self.create_mapping_dict(df.columns.tolist())
        
        if not mapping:
            self.logger.warning(f"未能创建任何列名映射，保留原始列名")
            return df
        
        # 应用映射
        df_mapped = df.rename(columns=mapping)
        
        self.logger.info(f"列名映射完成: {len(mapping)} 列已标准化")
        return df_mapped
    
    def validate_columns(self, df: pd.DataFrame, required_columns: List[str]) -> Tuple[bool, List[str]]:
        """
        验证数据框是否包含必需的列
        
        Args:
            df: 数据框
            required_columns: 必需的列名列表
            
        Returns:
            (is_valid, missing_columns): 验证结果和缺失列列表
        """
        df_columns_lower = [c.lower() for c in df.columns]
        missing = []
        
        for req_col in required_columns:
            # 检查标准名称
            if req_col in df.columns:
                continue
            # 检查别名
            found = False
            for standard_name, config in self.column_map.items():
                if standard_name == req_col:
                    aliases = [a.lower() for a in config.get('aliases', [])]
                    if any(alias in df_columns_lower for alias in aliases):
                        found = True
                        break
            if not found:
                missing.append(req_col)
        
        return len(missing) == 0, missing


class DataValidator:
    """数据格式验证器"""
    
    def __init__(self, column_manager: ColumnMappingManager):
        self.column_manager = column_manager
        self.logger = logger
    
    def validate_dataframe(self, df: pd.DataFrame, 
                          required_columns: Optional[List[str]] = None,
                          numeric_columns: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
        """
        验证数据框格式
        
        Args:
            df: 数据框
            required_columns: 必需的列名列表
            numeric_columns: 应为数值类型的列名列表
            
        Returns:
            (is_valid, errors): 验证结果和错误信息列表
        """
        errors = []
        
        # 1. 检查数据框非空
        if df.empty:
            errors.append("数据框为空")
            return False, errors
        
        # 2. 检查必需列
        if required_columns:
            is_valid, missing = self.column_manager.validate_columns(df, required_columns)
            if not is_valid:
                errors.append(f"缺少必需列: {missing}")
        
        # 3. 检查数值列类型
        if numeric_columns:
            for col in numeric_columns:
                if col in df.columns:
                    if not pd.api.types.is_numeric_dtype(df[col]):
                        errors.append(f"列 '{col}' 应为数值类型，实际为 {df[col].dtype}")
        
        # 4. 检查异常值
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                inf_count = np.isinf(df[col]).sum()
                if inf_count > 0:
                    errors.append(f"列 '{col}' 包含 {inf_count} 个无穷大值")
        
        return len(errors) == 0, errors
    
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗数据框
        
        Args:
            df: 原始数据框
            
        Returns:
            清洗后的数据框
        """
        df_clean = df.copy()
        
        # 1. 去除完全空行
        df_clean = df_clean.dropna(how='all')
        
        # 2. 处理无穷大值
        for col in df_clean.columns:
            if pd.api.types.is_numeric_dtype(df_clean[col]):
                df_clean[col] = df_clean[col].replace([np.inf, -np.inf], np.nan)
        
        # 3. 去除重复行
        df_clean = df_clean.drop_duplicates()
        
        self.logger.info(f"数据清洗完成: 原始 {len(df)} 行 -> 清洗后 {len(df_clean)} 行")
        
        return df_clean


class IntegratedPipeline:
    """
    统一数据调用管道
    
    整合数据加载、列名映射、缓存管理、格式验证和效率评估
    实现"一次读取，多次分析"的核心逻辑
    """
    
    def __init__(self, config_path: str = 'config/column_mapping.json'):
        """
        初始化管道
        
        Args:
            config_path: 列名映射配置文件路径
        """
        # 初始化数据库连接
        self.db = SessionLocal()
        Base.metadata.create_all(bind=self.db.get_bind())
        
        # 初始化列名映射管理器
        self.column_manager = ColumnMappingManager(config_path)
        
        # 初始化数据缓存
        self.cache = DataCache()
        
        # 初始化数据验证器
        self.validator = DataValidator(self.column_manager)
        
        # 初始化数据加载器和处理器
        self.loader = DataLoader()
        self.processor = DataProcessor()
        
        # 初始化分析器
        self.analyzer = ComprehensiveAnalyzer(self.processor, self.loader)
        
        # 初始化效率评估器
        dea_config = DEAInputOutputConfig(
            input_columns=['hospital_beds', 'physicians', 'population'],
            output_columns=['total_outpatient_visits', 'discharged_patients']
        )
        self.efficiency_evaluator = EfficiencyEvaluator(config=dea_config)
        
        # 性能指标记录
        self.metrics: List[DataLoadMetrics] = []
        
        self.logger = logger
        self.logger.info("=" * 60)
        self.logger.info("统一数据调用管道初始化完成")
        self.logger.info("=" * 60)
    
    def _load_data_with_cache(self, data_source: str, 
                              load_func: Callable, 
                              params: Dict,
                              use_cache: bool = True) -> Tuple[pd.DataFrame, DataLoadMetrics]:
        """
        带缓存的数据加载
        
        Args:
            data_source: 数据源标识
            load_func: 实际加载数据的函数
            params: 加载参数
            use_cache: 是否使用缓存
            
        Returns:
            (data, metrics): 数据和性能指标
        """
        metrics = DataLoadMetrics(data_source=data_source)
        
        # 尝试从缓存获取
        if use_cache:
            cached_data, cache_hit = self.cache.get(data_source, params)
            if cache_hit:
                metrics.cache_hit = True
                metrics.rows_loaded = len(cached_data)
                metrics.columns_loaded = len(cached_data.columns)
                metrics.load_end_time = time.time()
                self.metrics.append(metrics)
                self.logger.info(f"缓存命中 [{data_source}]: {len(cached_data)} 行, "
                               f"耗时 {metrics.load_duration_ms:.2f}ms")
                return cached_data, metrics
        
        # 执行实际加载
        try:
            data = load_func(**params)
            metrics.rows_loaded = len(data)
            metrics.columns_loaded = len(data.columns)
            
            # 保存到缓存
            if use_cache and not data.empty:
                self.cache.set(data_source, params, data)
            
            metrics.load_end_time = time.time()
            self.metrics.append(metrics)
            
            self.logger.info(f"数据加载完成 [{data_source}]: {len(data)} 行 x {len(data.columns)} 列, "
                           f"耗时 {metrics.load_duration_ms:.2f}ms")
            
            return data, metrics
            
        except Exception as e:
            metrics.load_end_time = time.time()
            self.metrics.append(metrics)
            self.logger.error(f"数据加载失败 [{data_source}]: {e}")
            raise
    
    def load_province_data(self, province_code: str, year: int,
                          data_source_type: str = 'yearbook') -> pd.DataFrame:
        """
        加载省份数据（统一入口）
        
        Args:
            province_code: 省份代码
            year: 年份
            data_source_type: 数据源类型
            
        Returns:
            标准化后的数据框
        """
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"开始加载省份数据: {province_code}, 年份: {year}")
        self.logger.info(f"{'='*50}")
        
        # 1. 加载原始数据（带缓存）
        def _load_raw_data(province_code: str, year: int):
            # 根据数据源类型选择加载方式
            if data_source_type == 'yearbook':
                input_file = SETTINGS.YEARBOOK_DATA_PATH
                if not os.path.exists(input_file):
                    raise FileNotFoundError(f"年鉴数据目录不存在: {input_file}")
                
                # 使用 DataLoader 加载本地文件
                raw_df = self.loader.load_local_files(input_file)
                # 过滤指定年份
                if 'year' in raw_df.columns:
                    raw_df = raw_df[raw_df['year'] == year]
                return raw_df
            else:
                raise ValueError(f"不支持的数据源类型: {data_source_type}")
        
        raw_data, metrics = self._load_data_with_cache(
            data_source=f"{data_source_type}_{province_code}_{year}",
            load_func=_load_raw_data,
            params={'province_code': province_code, 'year': year}
        )
        
        if raw_data.empty:
            self.logger.warning(f"未找到数据: {province_code}, 年份 {year}")
            return raw_data
        
        # 2. 应用列名映射
        self.logger.info("应用列名标准化映射...")
        mapped_data = self.column_manager.apply_mapping(raw_data, data_source_type)
        
        # 3. 数据验证和清洗
        self.logger.info("执行数据验证和清洗...")
        required_cols = ['region_name', 'year']
        is_valid, errors = self.validator.validate_dataframe(
            mapped_data, 
            required_columns=required_cols
        )
        
        if not is_valid:
            self.logger.warning(f"数据验证警告: {errors}")
        
        cleaned_data = self.validator.clean_dataframe(mapped_data)
        
        # 4. 数据处理
        self.logger.info("执行数据标准化处理...")
        processed_data = self.processor.process_yearbook_resource(cleaned_data)
        
        self.logger.info(f"数据加载完成: {len(processed_data)} 行")
        return processed_data
    
    def run_meso_analysis(self, province_code: str, year: int) -> Dict[str, Any]:
        """
        运行中观分析（统一的数据清洗与分析管道）
        
        Args:
            province_code: 省份代码
            year: 年份
            
        Returns:
            分析结果字典
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"▶ 中观分析: {province_code}, 年份 {year}")
        self.logger.info(f"{'='*60}")
        
        results = {
            'province_code': province_code,
            'year': year,
            'success': False,
            'metrics': {},
            'data': {},
            'errors': []
        }
        
        try:
            # 1. 加载数据（一次读取）
            data = self.load_province_data(province_code, year)
            
            if data.empty:
                results['errors'].append("数据为空")
                return results
            
            results['data']['raw'] = data
            
            # 2. 资源缺口分析（多次分析之一）
            self.logger.info("\n执行资源缺口分析...")
            gap_data = self.analyzer.compute_resource_gap(data, year)
            results['data']['gap_analysis'] = gap_data
            
            # 3. DEA效率评估（多次分析之二）- 使用修正后的投入产出指标
            self.logger.info("\n执行DEA效率评估...")
            
            # 检查是否有产出指标
            has_output_cols = any(col in data.columns for col in 
                                 ['total_outpatient_visits', 'discharged_patients'])
            
            if has_output_cols:
                efficiency_result = self.efficiency_evaluator.calculate_dea_efficiency_from_df(
                    data,
                    dmu_col='region_name' if 'region_name' in data.columns else 'region',
                    return_details=True
                )
                results['data']['efficiency'] = efficiency_result
                
                # 获取效率标杆
                benchmarks = self.efficiency_evaluator.get_efficiency_benchmarks(
                    efficiency_result, 
                    'region_name' if 'region_name' in efficiency_result.columns else 'region'
                )
                results['data']['efficiency_benchmarks'] = benchmarks
                
                self.logger.info(f"DEA效率评估完成: 平均效率 {benchmarks['average_efficiency']:.3f}, "
                               f"有效DMU {benchmarks['efficient_dmus']}/{benchmarks['total_dmus']}")
            else:
                self.logger.warning("缺少产出指标列，跳过DEA效率评估")
                results['errors'].append("缺少产出指标列(total_outpatient_visits, discharged_patients)")
            
            # 4. 资源优化建议（多次分析之三）
            self.logger.info("\n执行资源优化分析...")
            optimization_result = self.analyzer.optimize_resource_allocation(year, 'maximize_health')
            results['data']['optimization'] = optimization_result
            
            # 5. 收集性能指标
            results['metrics'] = {
                'data_load_times': [m.to_dict() for m in self.metrics],
                'cache_stats': self.cache.get_stats(),
                'total_rows': len(data),
                'total_regions': data['region_name'].nunique() if 'region_name' in data.columns else 0
            }
            
            results['success'] = True
            
            # 6. 保存结果到数据库
            self._save_analysis_results(results)
            
        except Exception as e:
            error_msg = f"分析过程出错: {str(e)}"
            self.logger.error(error_msg)
            self.logger.exception(traceback.format_exc())
            results['errors'].append(error_msg)
        
        return results
    
    def run_batch_analysis(self, province_codes: List[str], year: int) -> Dict[str, Any]:
        """
        批量分析多个省份
        
        Args:
            province_codes: 省份代码列表
            year: 年份
            
        Returns:
            批量分析结果
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"▶ 批量分析: {len(province_codes)} 个省份, 年份 {year}")
        self.logger.info(f"{'='*60}")
        
        batch_results = {
            'year': year,
            'provinces_analyzed': [],
            'provinces_failed': [],
            'aggregated_metrics': {},
            'results': {}
        }
        
        for province_code in province_codes:
            result = self.run_meso_analysis(province_code, year)
            
            if result['success']:
                batch_results['provinces_analyzed'].append(province_code)
                batch_results['results'][province_code] = result
            else:
                batch_results['provinces_failed'].append({
                    'province': province_code,
                    'errors': result['errors']
                })
        
        # 聚合指标
        if batch_results['provinces_analyzed']:
            all_efficiencies = []
            for province, result in batch_results['results'].items():
                if 'efficiency_benchmarks' in result['data']:
                    all_efficiencies.append(result['data']['efficiency_benchmarks']['average_efficiency'])
            
            if all_efficiencies:
                batch_results['aggregated_metrics'] = {
                    'avg_efficiency_across_provinces': np.mean(all_efficiencies),
                    'min_efficiency': np.min(all_efficiencies),
                    'max_efficiency': np.max(all_efficiencies),
                    'total_provinces': len(batch_results['provinces_analyzed'])
                }
        
        return batch_results
    
    def _save_analysis_results(self, results: Dict[str, Any]) -> None:
        """保存分析结果到数据库"""
        try:
            # 保存效率评估结果
            if 'efficiency' in results['data']:
                efficiency_df = results['data']['efficiency']
                
                for _, row in efficiency_df.iterrows():
                    record = AdvancedResourceEfficiency(
                        location_name=row.get('region_name', row.get('region')),
                        year=results['year'],
                        dea_efficiency=row.get('dea_efficiency'),
                        resource_quadrant=row.get('resource_quadrant', '未知'),
                        robust_data={
                            'efficiency_rank': row.get('dea_rank'),
                            'is_efficient': row.get('is_efficient', False)
                        }
                    )
                    self.db.add(record)
                
                self.db.commit()
                self.logger.info(f"分析结果已保存到数据库: {len(efficiency_df)} 条记录")
                
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"保存分析结果失败: {e}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        if not self.metrics:
            return {"message": "暂无性能数据"}
        
        total_load_time = sum(m.load_duration_ms for m in self.metrics)
        cache_hits = sum(1 for m in self.metrics if m.cache_hit)
        
        return {
            'total_data_loads': len(self.metrics),
            'cache_hits': cache_hits,
            'cache_hit_rate': cache_hits / len(self.metrics) if self.metrics else 0,
            'total_load_time_ms': round(total_load_time, 2),
            'avg_load_time_ms': round(total_load_time / len(self.metrics), 2) if self.metrics else 0,
            'cache_stats': self.cache.get_stats(),
            'load_details': [m.to_dict() for m in self.metrics[-10:]]  # 最近10次加载
        }
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.logger.info("管道缓存已清空")
    
    def close(self) -> None:
        """关闭管道，释放资源"""
        self.db.close()
        self.logger.info("管道已关闭")


def main():
    """主函数 - 演示统一管道的使用"""
    logger.info("★★★ 统一数据调用管道演示 ★★★")
    
    # 创建管道实例
    pipeline = IntegratedPipeline()
    
    try:
        # 示例：运行单个省份分析
        result = pipeline.run_meso_analysis(
            province_code="SICHUAN",
            year=2020
        )
        
        if result['success']:
            logger.info("\n分析成功！")
            logger.info(f"性能指标: {result['metrics']}")
            
            if 'efficiency_benchmarks' in result['data']:
                benchmarks = result['data']['efficiency_benchmarks']
                logger.info(f"\n效率标杆:")
                logger.info(f"  - 平均效率: {benchmarks['average_efficiency']:.3f}")
                logger.info(f"  - 有效DMU: {benchmarks['efficient_dmus']}/{benchmarks['total_dmus']}")
        else:
            logger.error(f"分析失败: {result['errors']}")
        
        # 打印性能报告
        perf_report = pipeline.get_performance_report()
        logger.info(f"\n性能报告:\n{json.dumps(perf_report, indent=2, ensure_ascii=False)}")
        
    finally:
        pipeline.close()
    
    logger.info("\n★★★ 演示完成 ★★★")


if __name__ == "__main__":
    main()
