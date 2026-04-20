import functools
import logging
import os
import time
import re
import pdfplumber
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd
import requests
import requests.exceptions
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TypedDict
from config.settings import SETTINGS

# 尝试导入 Redis，如果不可用则使用内存缓存
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

# 定义数据交换协议
class ExchangeMeta(TypedDict, total=False):
    source_path: str
    source_type: str
    row_count: int
    columns: list[str]
    notes: str

@dataclass(frozen=True)
class StandardizedDataContract:
    """模块间标准数据协议：只承载标准化后的 DataFrame 与元数据。"""
    data: pd.DataFrame
    meta: ExchangeMeta = field(default_factory=dict)


class DataLoader:
    """
    数据装载机 —— 纯 I/O
    唯一职责：把外界的字节/文件，变成 Python 内存里的"原生态" pd.DataFrame
    它不管数据有多脏，表头有多乱，只负责**"搬运"**
    """

    def __init__(self,
                 logger_name: Optional[str] = None,
                 max_retries: int = 3,
                 backoff_factor: float = 2.0,
                 enable_fallback: bool = True,
                 fallback_expire: int = 86400):
        """
        初始化数据装载机

        Args:
            logger_name: 日志记录器名称
            max_retries: 最大重试次数
            backoff_factor: 退避因子
            enable_fallback: 是否启用降级缓存
            fallback_expire: 缓存过期时间（秒），默认1天
        """
        self.logger = logging.getLogger(logger_name or "health_system.loader")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.api_config = SETTINGS.API_CONFIG
        self.enable_fallback = enable_fallback
        self.fallback_expire = fallback_expire

        # 初始化缓存（Redis 或内存）
        self._fallback_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._redis_client = None

        # 尝试连接真正的Redis服务，并添加2秒超时限制作为安全防护
        if REDIS_AVAILABLE and enable_fallback:
            try:
                redis_config = SETTINGS.REDIS_CONFIG
                self._redis_client = redis.Redis(
                    host=redis_config.get("host", "127.0.0.1"),  # 默认使用本地Redis
                    port=redis_config.get("port", 6379),         # Redis默认端口
                    password=redis_config.get("password"),
                    db=redis_config.get("db", 0),
                    decode_responses=True,
                    socket_connect_timeout=2.0,  # 关键安全设置：2秒内无法建立连接则放弃
                    socket_timeout=2.0,         # 关键安全设置：2秒内无响应则超时
                    retry_on_timeout=False
                )
                self._redis_client.ping()  # 执行心跳检测以验证连接有效性
                self.use_redis = True
                self.logger.info("✅ Redis 高速缓存连接成功！")
            except Exception as e:
                self.logger.warning(f"⚠️ 降级缓存：Redis 连接失败，使用内存缓存: {e}")
                self._redis_client = None
                self.use_redis = False
                self._memory_cache = {}

    def _get_cache_key(self, source: str, indicator: str, **kwargs) -> str:
        """生成缓存键"""
        target_countries = kwargs.get('target_countries', [])
        country_str = ','.join(sorted(target_countries)) if target_countries else 'all'
        return f"loader:fallback:{source}:{indicator}:{country_str}"

    def _get_fallback_data(self, cache_key: str) -> Optional[pd.DataFrame]:
        """获取降级缓存数据"""
        if not self.enable_fallback:
            return None

        try:
            # 尝试从 Redis 获取
            if self._redis_client:
                data_json = self._redis_client.get(cache_key)
                if data_json:
                    data = json.loads(data_json)
                    df = pd.DataFrame(data['records'])
                    self.logger.info(f"降级缓存命中（Redis）: {cache_key}")
                    return df

            # 从内存缓存获取
            if cache_key in self._fallback_cache:
                timestamp = self._cache_timestamps.get(cache_key, 0)
                if time.time() - timestamp < self.fallback_expire:
                    self.logger.info(f"降级缓存命中（内存）: {cache_key}")
                    return self._fallback_cache[cache_key]
                else:
                    # 过期清理
                    del self._fallback_cache[cache_key]
                    del self._cache_timestamps[cache_key]

        except Exception as e:
            self.logger.warning(f"获取降级缓存失败: {e}")

        return None

    def _set_fallback_data(self, cache_key: str, df: pd.DataFrame) -> bool:
        """设置降级缓存数据"""
        if not self.enable_fallback or df.empty:
            return False

        try:
            # 转换为可序列化格式
            cache_data = {
                'records': df.to_dict('records'),
                'columns': df.columns.tolist(),
                'timestamp': time.time()
            }

            # 尝试保存到 Redis
            if self._redis_client:
                self._redis_client.setex(
                    cache_key,
                    timedelta(seconds=self.fallback_expire),
                    json.dumps(cache_data)
                )
                self.logger.info(f"降级缓存已更新（Redis）: {cache_key}")
                return True

            # 保存到内存缓存
            self._fallback_cache[cache_key] = df
            self._cache_timestamps[cache_key] = time.time()
            self.logger.info(f"降级缓存已更新（内存）: {cache_key}")
            return True

        except Exception as e:
            self.logger.warning(f"设置降级缓存失败: {e}")
            return False

    def api_fallback_decorator(self, source: str, indicator_param: str = 'indicator'):
        """
        API 降级装饰器
        当 API 调用失败时，返回缓存数据或空 DataFrame

        Args:
            source: 数据源名称（如 'owid', 'who', 'world_bank'）
            indicator_param: 指标参数名
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # 获取指标值
                indicator = kwargs.get(indicator_param)
                if not indicator and len(args) >= 1:
                    indicator = args[0]

                # 生成缓存键
                cache_key = self._get_cache_key(source, indicator or 'unknown', **kwargs)

                try:
                    # 尝试执行原函数
                    result = func(*args, **kwargs)

                    # 如果成功且结果有效，更新缓存
                    if isinstance(result, pd.DataFrame) and not result.empty:
                        self._set_fallback_data(cache_key, result)
                        self.logger.info(f"API 调用成功 [{source}]: {indicator}")

                    return result

                except Exception as e:
                    # API 调用失败，尝试获取降级数据
                    self.logger.warning(f"API 调用失败 [{source}]: {indicator}, 错误: {e}")

                    fallback_df = self._get_fallback_data(cache_key)
                    if fallback_df is not None:
                        self.logger.info(f"返回降级缓存数据 [{source}]: {indicator}, 记录数: {len(fallback_df)}")
                        return fallback_df

                    # 无缓存，返回空 DataFrame
                    self.logger.error(f"无降级缓存可用 [{source}]: {indicator}")
                    return pd.DataFrame()

            return wrapper
        return decorator

    def load_local_files(self, directory_path: str, 
                        supported_formats: Optional[List[str]] = None,
                        skip_empty: bool = True) -> pd.DataFrame:
        """
        接管原 preprocessor.py 中的 os.walk 遍历 Excel/CSV 逻辑
        
        Args:
            directory_path: 文件夹路径
            supported_formats: 支持的格式列表（默认['.xlsx', '.xls', '.csv']）
            skip_empty: 是否跳过空数据文件
        
        Returns:
            合并后的原始 DataFrame
        """
        df_list: List[pd.DataFrame] = []
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"未找到路径: {directory_path}")

        # 支持的格式
        if supported_formats is None:
            supported_formats = ['.xlsx', '.xls', '.csv']
        
        file_count = 0
        success_count = 0
        error_files = []

        for root, _, files in os.walk(directory_path):
            for file in files:
                if any(file.endswith(fmt) for fmt in supported_formats) and not file.startswith("~"):
                    file_path = os.path.join(root, file)
                    try:
                        if file.endswith(".csv"):
                            df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
                        elif file.endswith(".xls"):
                            df = pd.read_excel(file_path)
                        else:
                            # Excel 文件，尝试多种读取方式
                            try:
                                df = pd.read_excel(file_path)
                            except Exception as e:
                                # 兼容某些 .xls 实为 HTML 的文件
                                try:
                                    html_dfs = pd.read_html(file_path)
                                    df = html_dfs[0] if html_dfs else pd.DataFrame()
                                except Exception as e2:
                                    self.logger.warning(f"Excel/HTML 读取失败 {file_path}: {e2}")
                                    df = pd.DataFrame()

                        # 数据验证
                        if not df.empty:
                            # 统一列名类型
                            df.columns = df.columns.astype(str)
                            
                            # 移除重复列
                            df = df.loc[:, ~df.columns.duplicated()]
                            
                            # 跳过空数据
                            if skip_empty and df.empty:
                                self.logger.info(f"跳过空数据文件: {file}")
                                continue
                            
                            df_list.append(df)
                            file_count += 1
                            success_count += 1
                        else:
                            self.logger.info(f"跳过空数据文件: {file}")
                            
                    except Exception as e:
                        error_files.append(file_path)
                        self.logger.warning(f"读取文件失败 {file_path}: {e}")

        if df_list:
            result = pd.concat(df_list, ignore_index=True)
            self.logger.info(f"成功加载 {file_count} 个文件，读取 {success_count} 个有效文件")
            return result
        else:
            self.logger.warning("未加载到任何数据")
            return pd.DataFrame()

    def load_gbd_data(self, file_path: str, validate: bool = True) -> pd.DataFrame:
        """
        专门加载 GBD 原始数据
        
        Args:
            file_path: GBD 数据文件路径
            validate: 是否进行数据验证
        
        Returns:
            GBD 数据 DataFrame
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"未找到 GBD 数据：{file_path}")

        # 确定文件类型并读取
        if file_path.endswith(".csv"):
            return pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
        return pd.read_excel(file_path)

    def fetch_api_data(self, source: str, indicator: str, 
                       target_countries: Optional[List[str]] = None,
                       timeout: int = 30) -> pd.DataFrame:
        """
        接管原 owid_fetcher.py 和 sync.py 逻辑，从 API 获取数据
        
        Args:
            source: 数据源（'owid', 'who', 'world_bank'）
            indicator: 指标代码或名称
            target_countries: 目标国家列表
            timeout: 请求超时时间（秒）
        
        Returns:
            原始 API 数据 DataFrame
        """
        if source == 'owid':
            return self._fetch_owid_data(indicator, target_countries, timeout)
        elif source == 'who':
            return self._fetch_who_data(indicator, timeout)
        elif source == 'world_bank':
            return self._fetch_world_bank_data(indicator, target_countries, timeout)
        else:
            raise ValueError(f"不支持的数据源: {source}")

    def _fetch_owid_data(self, indicator_code: str,
                        target_countries: Optional[List[str]] = None,
                        timeout: int = 30) -> pd.DataFrame:
        """
        从 Our World in Data 在线拉取指标数据
        已应用降级装饰器，API 失败时返回缓存数据
        """
        # 使用内部函数包装实际逻辑，以便应用装饰器
        @self.api_fallback_decorator(source='owid', indicator_param='indicator_code')
        def _fetch_logic(indicator_code, target_countries=None, timeout=30):
            return self._fetch_owid_data_impl(indicator_code, target_countries, timeout)

        return _fetch_logic(indicator_code, target_countries, timeout)

    def _fetch_owid_data_impl(self, indicator_code: str,
                              target_countries: Optional[List[str]] = None,
                              timeout: int = 30) -> pd.DataFrame:
        """OWID 数据获取实际实现"""
        api_url = f"https://ourworldindata.org/grapher/data/v1/indicators/{indicator_code}.json"
        
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.get(api_url, timeout=timeout)
                response.raise_for_status()
                data = response.json()

                entity_map = {e["id"]: {"name": e["name"], "code": e.get("code")} for e in data["entities"]}
                all_data = []
                for entity_id, time_series in data["data"].items():
                    ent = entity_map.get(int(entity_id))
                    if not ent:
                        continue
                    
                    # 过滤目标国家
                    if target_countries and ent["name"] not in target_countries:
                        continue

                    for year, value in time_series.items():
                        if value is None:
                            continue
                        all_data.append({
                            "country_name": ent["name"],
                            "country_code": ent["code"],
                            "year": int(year),
                            "indicator_id": indicator_code,
                            "value": float(value),
                            "fetch_time": datetime.now(),
                        })

                df = pd.DataFrame(all_data)
                if not df.empty:
                    df = df.drop_duplicates(subset=["country_code", "year", "indicator_id"])
                return df
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    wait_time = self.backoff_factor ** attempt
                    self.logger.warning(f"请求失败 (尝试 {attempt+1}/{self.max_retries+1}): {e}. 等待 {wait_time} 秒重试...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"拉取 OWID 指标 {indicator_code} 失败：{e}")
                    return pd.DataFrame()
            
            except Exception as e:
                self.logger.warning(f"处理数据失败 {indicator_code}: {e}")
                return pd.DataFrame()
        
        return pd.DataFrame()

    def _fetch_who_data(self, indicator_code: str, timeout: int = 30) -> pd.DataFrame:
        """
        从 WHO GHO API 获取数据
        已应用降级装饰器，API 失败时返回缓存数据
        """
        @self.api_fallback_decorator(source='who', indicator_param='indicator_code')
        def _fetch_logic(indicator_code, timeout=30):
            return self._fetch_who_data_impl(indicator_code, timeout)

        return _fetch_logic(indicator_code, timeout)

    def _fetch_who_data_impl(self, indicator_code: str, timeout: int = 30) -> pd.DataFrame:
        """WHO 数据获取实际实现"""
        url = f"{self.api_config['who_gho_base_url']}{indicator_code}"
        
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            raw_data = response.json()

            records = raw_data.get('value', [])
            if not records:
                return pd.DataFrame()

            df = pd.DataFrame(records)
            # 统一列名
            df_clean = pd.DataFrame({
                'region': df['SpatialDim'],
                'year': df['TimeDim'].astype(int),
                'value': df['NumericValue'].astype(float),
                'indicator': indicator_code,
                'source': 'WHO',
                'unit': df.get('Id', '')
            })

            return df_clean

        except Exception as e:
            self.logger.error(f"WHO 同步失败: {e}")
            return pd.DataFrame()

    def _fetch_world_bank_data(self, indicator: str,
                              target_countries: Optional[List[str]] = None,
                              timeout: int = 30) -> pd.DataFrame:
        """
        从世界银行获取数据
        已应用降级装饰器，API 失败时返回缓存数据
        """
        @self.api_fallback_decorator(source='world_bank', indicator_param='indicator')
        def _fetch_logic(indicator, target_countries=None, timeout=30):
            return self._fetch_world_bank_data_impl(indicator, target_countries, timeout)

        return _fetch_logic(indicator, target_countries, timeout)

    def _fetch_world_bank_data_impl(self, indicator: str,
                                    target_countries: Optional[List[str]] = None,
                                    timeout: int = 30) -> pd.DataFrame:
        """World Bank 数据获取实际实现"""
        country = target_countries[0] if target_countries else "CHN"
        url = f"{self.api_config['world_bank_base_url']}country/{country}/indicator/{indicator}"
        params = {"format": "json", "per_page": 100}

        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            raw_json = response.json()

            if len(raw_json) < 2:
                return pd.DataFrame()

            data_list = raw_json[1]
            df_clean = pd.DataFrame([
                {
                    'region': country,
                    'year': int(item['date']),
                    'value': float(item['value']) if item['value'] else 0,
                    'indicator': indicator,
                    'source': 'WorldBank',
                    'unit': 'per 1,000 people'
                } for item in data_list if item['value'] is not None
            ])

            return df_clean

        except Exception as e:
            self.logger.error(f"World Bank 同步失败: {e}")
            return pd.DataFrame()

    # ==================== POI 数据获取（整合自 spatial/poi_fetcher.py） ====================

    def fetch_poi_data(
        self,
        city: str,
        keyword: str,
        provider: str = "amap",
        poi_type: Optional[str] = None,
        max_results: int = 1000
    ) -> pd.DataFrame:
        """
        获取兴趣点(POI)数据

        支持高德地图(amap)和百度地图(baidu)API获取POI数据。
        整合自原 poi_fetcher.py 模块。

        Args:
            city: 城市名称，如"成都市"
            keyword: 搜索关键词，如"三甲医院"
            provider: 地图服务提供商，"amap"或"baidu"
            poi_type: POI类型分类，如"医疗保健服务"
            max_results: 最大返回结果数

        Returns:
            POI数据DataFrame，包含列：name, lon, lat, address, capacity

        示例:
            >>> loader = DataLoader()
            >>> df = loader.fetch_poi_data("成都市", "三甲医院", provider="amap")
        """
        if provider == "amap":
            return self._fetch_amap_poi(city, keyword, poi_type, max_results)
        elif provider == "baidu":
            return self._fetch_baidu_poi(city, keyword, poi_type, max_results)
        else:
            raise ValueError(f"不支持的地图服务提供商: {provider}")

    def _fetch_amap_poi(
        self,
        city: str,
        keyword: str,
        poi_type: Optional[str] = None,
        max_results: int = 1000
    ) -> pd.DataFrame:
        """
        高德地图POI获取实现
        已应用降级机制，API失败时返回缓存数据
        """
        @self.api_fallback_decorator(source='amap_poi', indicator_param='keyword')
        def _fetch_logic(city, keyword, poi_type, max_results):
            return self._fetch_amap_poi_impl(city, keyword, poi_type, max_results)

        return _fetch_logic(city, keyword, poi_type, max_results)

    def _fetch_amap_poi_impl(
        self,
        city: str,
        keyword: str,
        poi_type: Optional[str] = None,
        max_results: int = 1000
    ) -> pd.DataFrame:
        """高德地图POI获取实际实现"""
        try:
            api_key = self.api_config.get('amap', {}).get('api_key', '')
            url = self.api_config.get('amap', {}).get('poi_url', 'https://restapi.amap.com/v3/place/text')
        except:
            api_key = ''
            url = 'https://restapi.amap.com/v3/place/text'

        if not api_key:
            self.logger.warning("高德地图API密钥未配置")
            return pd.DataFrame()

        pois = []
        page = 1
        page_size = 20

        while len(pois) < max_results:
            params = {
                'key': api_key,
                'keywords': keyword,
                'city': city,
                'citylimit': 'true',
                'offset': page_size,
                'page': page,
                'extensions': 'all'
            }
            if poi_type:
                params['types'] = poi_type

            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if data.get('status') == '1' and int(data.get('count', 0)) > 0:
                    poi_list = data.get('pois', [])

                    for poi in poi_list:
                        location = poi.get('location', '').split(',')
                        if len(location) == 2:
                            try:
                                lon = float(location[0])
                                lat = float(location[1])

                                # 高德坐标(GCJ-02)转WGS-84
                                from utils.spatial_utils import gcj02_to_wgs84
                                wgs_lat, wgs_lon = gcj02_to_wgs84(lat, lon)

                                pois.append({
                                    'name': poi.get('name', ''),
                                    'lon': wgs_lon,
                                    'lat': wgs_lat,
                                    'address': poi.get('address', ''),
                                    'type': poi.get('type', ''),
                                    'capacity': 1000  # 默认容量
                                })
                            except (ValueError, TypeError):
                                continue

                    if len(poi_list) < page_size:
                        break
                    page += 1
                    time.sleep(0.5)  # 避免触发频率限制
                else:
                    break

            except requests.exceptions.RequestException as e:
                self.logger.error(f"高德API请求失败: {e}")
                raise  # 抛出异常以便降级装饰器捕获
            except Exception as e:
                self.logger.error(f"处理高德POI数据失败: {e}")
                raise

        df = pd.DataFrame(pois)

        # 保存为GeoJSON
        if not df.empty:
            self._save_poi_to_geojson(df, city, keyword)

        return df

    def _fetch_baidu_poi(
        self,
        city: str,
        keyword: str,
        poi_type: Optional[str] = None,
        max_results: int = 1000
    ) -> pd.DataFrame:
        """
        百度地图POI获取实现
        已应用降级机制，API失败时返回缓存数据
        """
        @self.api_fallback_decorator(source='baidu_poi', indicator_param='keyword')
        def _fetch_logic(city, keyword, poi_type, max_results):
            return self._fetch_baidu_poi_impl(city, keyword, poi_type, max_results)

        return _fetch_logic(city, keyword, poi_type, max_results)

    def _fetch_baidu_poi_impl(
        self,
        city: str,
        keyword: str,
        poi_type: Optional[str] = None,
        max_results: int = 1000
    ) -> pd.DataFrame:
        """百度地图POI获取实际实现"""
        try:
            api_key = self.api_config.get('baidu', {}).get('api_key', '')
            url = self.api_config.get('baidu', {}).get('poi_url', 'https://api.map.baidu.com/place/v2/search')
        except:
            api_key = ''
            url = 'https://api.map.baidu.com/place/v2/search'

        if not api_key:
            self.logger.warning("百度地图API密钥未配置")
            return pd.DataFrame()

        pois = []
        page = 0
        page_size = 20

        while len(pois) < max_results:
            params = {
                'ak': api_key,
                'query': keyword,
                'region': city,
                'output': 'json',
                'page_size': page_size,
                'page_num': page
            }
            if poi_type:
                params['tag'] = poi_type

            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if data.get('status') == 0 and data.get('results'):
                    poi_list = data['results']

                    for poi in poi_list:
                        location = poi.get('location', {})
                        if location:
                            try:
                                lat = float(location.get('lat', 0))
                                lon = float(location.get('lng', 0))

                                pois.append({
                                    'name': poi.get('name', ''),
                                    'lon': lon,
                                    'lat': lat,
                                    'address': poi.get('address', ''),
                                    'type': poi.get('detail_info', {}).get('tag', ''),
                                    'capacity': 1000
                                })
                            except (ValueError, TypeError):
                                continue

                    if len(poi_list) < page_size:
                        break
                    page += 1
                    time.sleep(0.5)
                else:
                    break

            except requests.exceptions.RequestException as e:
                self.logger.error(f"百度API请求失败: {e}")
                raise
            except Exception as e:
                self.logger.error(f"处理百度POI数据失败: {e}")
                raise

        df = pd.DataFrame(pois)

        if not df.empty:
            self._save_poi_to_geojson(df, city, keyword)

        return df

    def _save_poi_to_geojson(self, df: pd.DataFrame, city: str, keyword: str) -> None:
        """将POI数据保存为GeoJSON格式"""
        try:
            features = []
            for _, row in df.iterrows():
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [row['lon'], row['lat']]
                    },
                    "properties": {
                        "name": row['name'],
                        "address": row.get('address', ''),
                        "capacity": row.get('capacity', 1000)
                    }
                })

            geojson_data = {
                "type": "FeatureCollection",
                "features": features
            }

            # 确保目录存在
            geojson_dir = os.path.join(SETTINGS.BASE_DIR, "data", "geojson")
            os.makedirs(geojson_dir, exist_ok=True)

            # 生成文件名
            safe_city = city.replace('市', '').replace('省', '')
            safe_keyword = keyword.replace('/', '_').replace('\\', '_')
            filename = f"{safe_city}_{safe_keyword}_poi.geojson"
            geojson_path = os.path.join(geojson_dir, filename)

            with open(geojson_path, "w", encoding="utf-8") as f:
                json.dump(geojson_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"POI数据已保存至: {geojson_path}")

        except Exception as e:
            self.logger.warning(f"保存GeoJSON失败: {e}")

    def fetch_community_demand(self, city: str = "成都市") -> pd.DataFrame:
        """
        获取社区需求数据

        返回指定城市的行政区划中心坐标和人口数据。
        整合自原 poi_fetcher.py 模块。

        Args:
            city: 城市名称

        Returns:
            社区需求DataFrame，包含列：name, lon, lat, population, elderly_ratio

        示例:
            >>> loader = DataLoader()
            >>> df = loader.fetch_community_demand("成都市")
        """
        # 预定义的城市数据
        city_data = {
            "成都市": [
                {'name': '锦江区', 'lon': 104.083472, 'lat': 30.656545, 'population': 900000, 'elderly_ratio': 0.18},
                {'name': '青羊区', 'lon': 104.062086, 'lat': 30.673896, 'population': 950000, 'elderly_ratio': 0.20},
                {'name': '金牛区', 'lon': 104.051833, 'lat': 30.690859, 'population': 1200000, 'elderly_ratio': 0.22},
                {'name': '武侯区', 'lon': 104.04313, 'lat': 30.64223, 'population': 1200000, 'elderly_ratio': 0.15},
                {'name': '成华区', 'lon': 104.044558, 'lat': 30.64267, 'population': 1380000, 'elderly_ratio': 0.16},
                {'name': '高新区', 'lon': 104.043598, 'lat': 30.581561, 'population': 1500000, 'elderly_ratio': 0.12},
                {'name': '龙泉驿区', 'lon': 104.2689, 'lat': 30.5601, 'population': 1340000, 'elderly_ratio': 0.13},
                {'name': '青白江区', 'lon': 103.9248, 'lat': 30.8785, 'population': 600000, 'elderly_ratio': 0.16},
                {'name': '新都区', 'lon': 104.1587, 'lat': 30.8234, 'population': 900000, 'elderly_ratio': 0.15},
                {'name': '温江区', 'lon': 104.2052, 'lat': 30.6868, 'population': 960000, 'elderly_ratio': 0.14},
                {'name': '双流区', 'lon': 103.9234, 'lat': 30.5744, 'population': 1460000, 'elderly_ratio': 0.12},
                {'name': '郫都区', 'lon': 103.8872, 'lat': 30.8055, 'population': 1390000, 'elderly_ratio': 0.13},
                {'name': '新津区', 'lon': 103.8114, 'lat': 30.4141, 'population': 360000, 'elderly_ratio': 0.17},
                {'name': '金堂县', 'lon': 104.4119, 'lat': 30.8619, 'population': 800000, 'elderly_ratio': 0.19},
                {'name': '大邑县', 'lon': 103.5207, 'lat': 30.5873, 'population': 510000, 'elderly_ratio': 0.18},
                {'name': '蒲江县', 'lon': 103.5061, 'lat': 30.1966, 'population': 260000, 'elderly_ratio': 0.21},
                {'name': '都江堰市', 'lon': 103.6194, 'lat': 30.9982, 'population': 730000, 'elderly_ratio': 0.18},
                {'name': '彭州市', 'lon': 103.958, 'lat': 30.9804, 'population': 780000, 'elderly_ratio': 0.19},
                {'name': '邛崃市', 'lon': 103.4649, 'lat': 30.4102, 'population': 610000, 'elderly_ratio': 0.20},
                {'name': '崇州市', 'lon': 103.673, 'lat': 30.6301, 'population': 710000, 'elderly_ratio': 0.20},
                {'name': '简阳市', 'lon': 104.5486, 'lat': 30.3905, 'population': 1110000, 'elderly_ratio': 0.18},
                {'name': '天府新区', 'lon': 104.073, 'lat': 30.432, 'population': 800000, 'elderly_ratio': 0.11}
            ]
        }

        if city not in city_data:
            self.logger.warning(f"未找到城市 {city} 的预定义数据，返回空DataFrame")
            return pd.DataFrame()

        return pd.DataFrame(city_data[city])

    # ==================== 地理编码服务（整合自 coordTransform_utils.py） ====================

    def fetch_coordinates_by_address(
        self,
        address: str,
        city: str = "全国",
        timeout: int = 5,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        通过地址获取地理坐标（高德地图地理编码服务）

        利用高德地图 Geocoding API 将中文地址解析为经纬度坐标（GCJ-02火星坐标系）。
        整合自原 coordTransform_utils.py 中的 Geocoding 类。

        Args:
            address: 需要解析的中文地址，如"北京市朝阳区朝阳公园"
            city: 指定城市，默认为"全国"
            timeout: 请求超时时间（秒），默认5秒
            max_retries: 最大重试次数，默认3次

        Returns:
            成功时返回 "longitude,latitude" 格式的字符串
            失败时返回 None

        Raises:
            不抛出异常，所有错误通过日志记录并返回None

        示例:
            >>> loader = DataLoader()
            >>> coords = loader.fetch_coordinates_by_address("北京市朝阳区朝阳公园")
            >>> print(coords)  # "116.4890,39.9350"

        注意:
            - 需要配置有效的 AMAP_KEY
            - 返回的是 GCJ-02（火星坐标系）坐标
            - 如需 WGS-84 坐标，请使用 utils.spatial_utils.gcj02_to_wgs84 转换
        """
        # 获取API密钥
        api_key = self.api_config.get("amap", {}).get("api_key", "")
        if not api_key:
            api_key = self.api_config.get("AMAP_KEY", "")

        if not api_key:
            self.logger.error("高德地图API密钥未配置，请在配置中设置 AMAP_KEY 或 amap.api_key")
            return None

        # 构建请求参数
        url = "http://restapi.amap.com/v3/geocode/geo"
        params = {
            "key": api_key,
            "address": address,
            "city": city,
            "s": "rsv3"
        }

        # 重试逻辑
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    params=params,
                    timeout=timeout
                )
                response.raise_for_status()

                data = response.json()

                # 检查响应状态
                if data.get("status") == "1" and int(data.get("count", 0)) >= 1:
                    geocodes = data["geocodes"][0]
                    location = geocodes.get("location")

                    if location:
                        self.logger.info(f"地址解析成功: '{address}' -> {location}")
                        return location
                    else:
                        self.logger.warning(f"地址解析返回空坐标: '{address}'")
                        return None
                else:
                    info = data.get("info", "未知错误")
                    self.logger.warning(f"地址解析失败: '{address}', 原因: {info}")
                    return None

            except requests.exceptions.Timeout:
                self.logger.warning(f"地址解析请求超时 (尝试 {attempt + 1}/{max_retries}): '{address}'")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))  # 指数退避
                continue

            except requests.exceptions.RequestException as e:
                self.logger.error(f"地址解析请求异常: '{address}', 错误: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                continue

            except (KeyError, IndexError, ValueError) as e:
                self.logger.error(f"地址解析响应解析失败: '{address}', 错误: {e}")
                return None

        # 所有重试都失败
        self.logger.error(f"地址解析在 {max_retries} 次尝试后失败: '{address}'")
        return None

    def batch_geocode(
        self,
        addresses: List[str],
        city: str = "全国",
        delay: float = 0.1
    ) -> Dict[str, Optional[str]]:
        """
        批量地址解析

        对多个地址进行地理编码，自动添加延迟以避免触发API频率限制。

        Args:
            addresses: 地址列表
            city: 指定城市，默认为"全国"
            delay: 每次请求间隔（秒），默认0.1秒

        Returns:
            字典，键为地址，值为坐标字符串或None

        示例:
            >>> loader = DataLoader()
            >>> addresses = ["北京市朝阳区", "上海市浦东新区"]
            >>> results = loader.batch_geocode(addresses)
            >>> print(results)  # {"北京市朝阳区": "116.4,39.9", "上海市浦东新区": "121.5,31.2"}
        """
        results = {}
        total = len(addresses)

        self.logger.info(f"开始批量地理编码，共 {total} 个地址")

        for i, address in enumerate(addresses, 1):
            coords = self.fetch_coordinates_by_address(address, city)
            results[address] = coords

            if i < total:
                time.sleep(delay)

            if i % 10 == 0:
                self.logger.info(f"批量地理编码进度: {i}/{total}")

        success_count = sum(1 for v in results.values() if v is not None)
        self.logger.info(f"批量地理编码完成: {success_count}/{total} 成功")

        return results

    def extract_pdf_tables(self, pdf_path: str, scan_last_n_pages: int = 50) -> pd.DataFrame:
        """
        接管原 pdf_extractor.py 逻辑，从 PDF 文件中提取表格数据
        
        Args:
            pdf_path: PDF 文件路径
            scan_last_n_pages: 扫描最后 N 页（附录通常在最后）
        
        Returns:
            提取的原始表格数据
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"未找到 PDF 文件：{pdf_path}")
        
        print(f"正在解析 PDF: {pdf_path}")
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

                        # 核心判断：表头里有没有"国家"或"国别"
                        country_col = [c for c in df.columns if '国家' in c or '国别' in c]
                        if not country_col:
                            continue
                        
                        all_tables_data.append(df)

            if not all_tables_data:
                print(f"未能提取到有效的全球/国家统计附录表格。")
                return pd.DataFrame()

            # 合并提取到的附录表
            raw_df = pd.concat(all_tables_data, ignore_index=True)
            print(f"PDF 提取成功！提取了 {len(raw_df)} 行数据。")
            return raw_df

        except Exception as e:
            self.logger.error(f"从 PDF 提取数据失败 {pdf_path}: {e}")
            raise

    def validate_dataframe(self, df: pd.DataFrame, 
                          required_columns: Optional[List[str]] = None) -> bool:
        """
        验证 DataFrame 的有效性
        
        Args:
            df: 要验证的 DataFrame
            required_columns: 必需列名列表
        
        Returns:
            是否有效的布尔值
        """
        if df.empty:
            return False
        
        if required_columns:
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                self.logger.warning(f"缺少必需列：{missing_cols}")
                return False
        
        return True

    def get_stats(self, df: pd.DataFrame) -> dict:
        """
        获取数据框统计信息
        
        Args:
            df: 数据框
        
        Returns:
            统计信息字典
        """
        if df.empty:
            return {}
        
        stats = {
            "shape": df.shape,
            "columns": list(df.columns),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 ** 2),
            "missing_values": df.isna().sum().to_dict(),
            "column_types": {col: str(df[col].dtype) for col in df.columns},
            "numeric_columns": df.select_dtypes(include=['number']).columns.tolist(),
            "categorical_columns": df.select_dtypes(include=['object', 'category']).columns.tolist(),
        }
        
        return stats

    # ================= 标准化数据契约功能 (整合自 analysis/loader.py) =================

    def load_with_contract(self, file_path: str, sheet_name: int | str = 0) -> StandardizedDataContract:
        """
        加载文件并返回标准化数据契约
        整合自 analysis/loader.py 的 load 功能
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".csv":
            df = pd.read_csv(file_path)
            source_type = "csv"
        elif ext in {".xlsx", ".xls"}:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            source_type = "excel"
        elif ext == ".pdf":
            df = self.extract_pdf_tables(file_path)
            source_type = "pdf"
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

        standardized = self._standardize_dataframe(df)
        return StandardizedDataContract(
            data=standardized,
            meta={
                "source_path": file_path,
                "source_type": source_type,
                "row_count": int(len(standardized)),
                "columns": [str(c) for c in standardized.columns],
            },
        )

    def from_dataframe_with_contract(self, df: pd.DataFrame, notes: str = "") -> StandardizedDataContract:
        """
        从DataFrame创建标准化数据契约
        整合自 analysis/loader.py 的 from_dataframe 功能
        """
        standardized = self._standardize_dataframe(df)
        return StandardizedDataContract(
            data=standardized,
            meta={
                "source_type": "dataframe",
                "row_count": int(len(standardized)),
                "columns": [str(c) for c in standardized.columns],
                "notes": notes,
            },
        )

    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化DataFrame
        整合自 analysis/loader.py 的 _standardize 功能
        """
        out = df.copy()
        out.columns = [str(col).strip() for col in out.columns]

        # 应用列名映射（如果存在）
        if hasattr(self, 'col_map') and self.col_map:
            # 反向映射：从标准列名到实际列名
            reverse_map = {}
            for std_key, keywords in self.col_map.items():
                for col in out.columns:
                    col_str = str(col)
                    if any(kw in col_str for kw in keywords):
                        reverse_map[col] = std_key
                        break
            if reverse_map:
                out = out.rename(columns=reverse_map)

        # 清洗阶段只做"格式标准化"，不做业务计算
        for col in out.columns:
            if col.lower() == "year":
                out[col] = pd.to_numeric(out[col], errors="coerce")
        return out.reset_index(drop=True)

    # ==================== 健康资讯获取（带24小时缓存机制） ====================

    def _get_news_cache_key(self) -> str:
        """生成新闻缓存键（按天）"""
        today = datetime.now().strftime("%Y-%m-%d")
        return f"mediastack:news:{today}"

    def _get_api_usage_key(self) -> str:
        """生成API调用计数键（按月）"""
        month = datetime.now().strftime("%Y-%m")
        return f"mediastack:usage:{month}"

    def _get_cached_news(self) -> Optional[List[dict]]:
        """从缓存获取新闻数据"""
        try:
            cache_key = self._get_news_cache_key()

            # 尝试从 Redis 获取
            if self._redis_client:
                cached_data = self._redis_client.get(cache_key)
                if cached_data:
                    self.logger.info(f"[NewsCache] 缓存命中: {cache_key}")
                    return json.loads(cached_data)

            # 从内存缓存获取
            if cache_key in self._fallback_cache:
                timestamp = self._cache_timestamps.get(cache_key, 0)
                if time.time() - timestamp < 86400:  # 24小时过期
                    self.logger.info(f"[NewsCache] 内存缓存命中: {cache_key}")
                    return self._fallback_cache[cache_key]

        except Exception as e:
            self.logger.warning(f"[NewsCache] 获取缓存失败: {e}")

        return None

    def _set_cached_news(self, news_list: List[dict]) -> bool:
        """缓存新闻数据（24小时）"""
        try:
            cache_key = self._get_news_cache_key()

            # 尝试保存到 Redis（24小时过期）
            if self._redis_client:
                self._redis_client.setex(
                    cache_key,
                    timedelta(hours=24),
                    json.dumps(news_list, ensure_ascii=False)
                )
                self.logger.info(f"[NewsCache] 已更新Redis缓存: {cache_key}")
                return True

            # 保存到内存缓存
            self._fallback_cache[cache_key] = news_list
            self._cache_timestamps[cache_key] = time.time()
            self.logger.info(f"[NewsCache] 已更新内存缓存: {cache_key}")
            return True

        except Exception as e:
            self.logger.warning(f"[NewsCache] 设置缓存失败: {e}")
            return False

    def _increment_api_usage(self) -> int:
        """增加API调用计数，返回当前计数"""
        try:
            usage_key = self._get_api_usage_key()

            # 使用 Redis 计数器
            if self._redis_client:
                count = self._redis_client.incr(usage_key)
                # 设置过期时间为月底
                now = datetime.now()
                next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
                ttl = int((next_month - now).total_seconds())
                self._redis_client.expire(usage_key, ttl)
                return count

            # 内存计数器
            if not hasattr(self, '_api_usage_counter'):
                self._api_usage_counter = {}
            self._api_usage_counter[usage_key] = self._api_usage_counter.get(usage_key, 0) + 1
            return self._api_usage_counter[usage_key]

        except Exception as e:
            self.logger.warning(f"[APIUsage] 计数失败: {e}")
            return -1

    def get_api_usage_stats(self) -> Dict[str, Any]:
        """获取API调用统计信息"""
        try:
            usage_key = self._get_api_usage_key()
            current_month = datetime.now().strftime("%Y-%m")

            # 获取当前月份调用次数
            if self._redis_client:
                count = int(self._redis_client.get(usage_key) or 0)
                ttl = self._redis_client.ttl(usage_key)
            else:
                count = getattr(self, '_api_usage_counter', {}).get(usage_key, 0)
                ttl = -1

            return {
                "current_month": current_month,
                "api_calls_used": count,
                "api_calls_limit": 100,  # 每月限额
                "api_calls_remaining": max(0, 100 - count),
                "usage_percentage": round((count / 100) * 100, 2),
                "cache_ttl_seconds": ttl,
                "status": "normal" if count < 80 else "warning" if count < 95 else "critical"
            }

        except Exception as e:
            self.logger.error(f"[APIUsage] 获取统计失败: {e}")
            return {
                "current_month": datetime.now().strftime("%Y-%m"),
                "api_calls_used": -1,
                "error": str(e)
            }

    def fetch_health_news(self, limit: int = 5) -> List[dict]:
        """
        获取健康资讯（带24小时缓存机制）

        实现策略：
        1. 优先从缓存获取（24小时有效）
        2. 缓存未命中时才调用 Mediastack API
        3. 严格监控API调用次数（每月限额100次）
        4. API调用失败时返回缓存数据或兜底数据

        参数:
            limit: int - 请求的新闻数量，默认为5条

        返回:
            List[dict] - 包含新闻信息的字典列表
        """
        # 第一步：检查缓存
        cached_news = self._get_cached_news()
        if cached_news is not None:
            self.logger.info(f"[NewsCache] 返回缓存数据，共 {len(cached_news)} 条")
            return cached_news

        # 第二步：检查API调用额度
        usage_stats = self.get_api_usage_stats()
        if usage_stats["api_calls_remaining"] <= 0:
            self.logger.warning(f"[APIUsage] API调用额度已用完: {usage_stats['api_calls_used']}/100")
            return [{
                "title": "API调用额度已用完",
                "description": f"本月已使用 {usage_stats['api_calls_used']} 次API调用，额度已耗尽。请下月再试或联系管理员。",
                "source": "System",
                "publishedAt": datetime.now().isoformat(),
                "url": "#"
            }]

        # 第三步：调用 Mediastack API
        try:
            api_key = os.getenv("MEDIASTACK_API_KEY", "")

            # API Key 未配置
            if not api_key:
                self.logger.warning("[NewsAPI] API Key 未配置")
                return [{
                    "title": "系统提示：未配置新闻API Key",
                    "description": "请在环境变量中配置 MEDIASTACK_API_KEY 以获取真实健康资讯",
                    "source": "HIS System",
                    "publishedAt": datetime.now().isoformat(),
                    "url": "#"
                }]

            # 构建请求URL - 获取中国地区健康新闻
            url = f"http://api.mediastack.com/v1/news?access_key={api_key}&keywords=health&countries=cn&limit={limit}"
            
            self.logger.info(f"[NewsAPI] 发起API请求(中国地区): {url.split('?')[0]}")

            # 发送请求
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            # 处理响应数据
            articles = data.get("data", [])
            
            # 检查是否有中文内容（标题包含中文字符）
            def has_chinese(text):
                if not text:
                    return False
                return any('\u4e00' <= char <= '\u9fff' for char in text)
            
            chinese_articles = [a for a in articles if has_chinese(a.get("title", ""))]
            
            # 如果没有中文新闻，使用中文兜底数据
            if not chinese_articles:
                self.logger.info("[NewsAPI] 未获取到中文健康新闻，使用系统预置中文资讯")
                fallback_news = [
                    {
                        "title": "每日健康资讯 - 系统推荐",
                        "description": "今日暂无新的中文健康新闻，为您推荐系统预置健康资讯。保持良好的生活习惯是健康的基础。建议规律作息、均衡饮食、适量运动。",
                        "source": "健康资讯系统",
                        "publishedAt": datetime.now().isoformat(),
                        "url": "#"
                    },
                    {
                        "title": "健康生活方式指南",
                        "description": "保持规律作息、均衡饮食和适量运动是维护健康的基础。建议每周进行至少150分钟中等强度运动，多摄入蔬菜水果，减少高盐高脂食品。",
                        "source": "健康知识库",
                        "publishedAt": datetime.now().isoformat(),
                        "url": "#"
                    },
                    {
                        "title": "慢性病预防要点",
                        "description": "定期体检、控制体重、戒烟限酒可有效预防心脑血管疾病和糖尿病等慢性疾病。建议40岁以上人群每年进行一次全面体检。",
                        "source": "健康知识库",
                        "publishedAt": datetime.now().isoformat(),
                        "url": "#"
                    },
                    {
                        "title": "心理健康同样重要",
                        "description": "保持良好心态，学会压力管理，必要时寻求专业心理支持，是全面健康的重要组成部分。每天留出时间放松心情，与亲友交流。",
                        "source": "健康知识库",
                        "publishedAt": datetime.now().isoformat(),
                        "url": "#"
                    },
                    {
                        "title": "科学运动促进健康",
                        "description": "适度运动能增强免疫力、改善心血管功能、控制体重。建议选择适合自己的运动方式，循序渐进，持之以恒。",
                        "source": "健康知识库",
                        "publishedAt": datetime.now().isoformat(),
                        "url": "#"
                    }
                ]
                return fallback_news
            
            # 使用中文新闻
            articles = chinese_articles
            
            news_list = []
            for article in articles:
                news_list.append({
                    "title": article.get("title", "无标题"),
                    "description": article.get("description", "暂无描述")[:100] + "..." if article.get("description") else "暂无描述",
                    "source": article.get("source", "未知来源"),
                    "publishedAt": article.get("published_at", datetime.now().isoformat()),
                    "url": article.get("url", "#")
                })

            # 增加API调用计数
            new_count = self._increment_api_usage()
            self.logger.info(f"[APIUsage] 本次调用后计数: {new_count}/100")

            # 缓存数据
            self._set_cached_news(news_list)
            self.logger.info(f"[NewsAPI] 成功获取 {len(news_list)} 条新闻")

            return news_list

        except requests.exceptions.RequestException as e:
            self.logger.error(f"[NewsAPI] API请求失败: {str(e)}")

            # 返回中文兜底数据 - 丰富的健康资讯
            return [
                {
                    "title": "网络连接异常 - 显示备用资讯",
                    "description": "当前无法连接到新闻服务器，显示预置健康资讯。系统将在网络恢复后自动更新内容。",
                    "source": "系统提示",
                    "publishedAt": datetime.now().isoformat(),
                    "url": "#"
                },
                {
                    "title": "健康生活方式指南",
                    "description": "保持规律作息、均衡饮食和适量运动是维护健康的基础。建议每周进行至少150分钟中等强度运动。",
                    "source": "健康知识库",
                    "publishedAt": datetime.now().isoformat(),
                    "url": "#"
                },
                {
                    "title": "慢性病预防要点",
                    "description": "定期体检、控制体重、戒烟限酒可有效预防心脑血管疾病和糖尿病等慢性疾病。",
                    "source": "健康知识库",
                    "publishedAt": datetime.now().isoformat(),
                    "url": "#"
                },
                {
                    "title": "心理健康同样重要",
                    "description": "保持良好心态，学会压力管理，必要时寻求专业心理支持，是全面健康的重要组成部分。",
                    "source": "健康知识库",
                    "publishedAt": datetime.now().isoformat(),
                    "url": "#"
                }
            ]
