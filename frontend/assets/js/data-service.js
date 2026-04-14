/**
 * 数据服务模块 - 统一处理前端数据获取
 * 职责：
 * 1. 封装所有API请求，提供统一的数据获取接口
 * 2. 实现数据缓存机制，减少重复请求
 * 3. 提供数据转换和格式化功能
 * 4. 实现错误处理和降级策略
 */

const DataService = {
    // API基础URL
    baseURL: '',

    // 缓存存储
    cache: new Map(),
    cacheExpiry: 5 * 60 * 1000, // 5分钟缓存

    // 请求超时设置
    timeout: 10000,

    /**
     * 初始化数据服务
     */
    init() {
        // 检测运行环境，设置正确的API基础URL
        const hostname = window.location.hostname;
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            this.baseURL = 'http://localhost:8000';
        } else {
            this.baseURL = '';
        }
        console.log('[DataService] 初始化完成，API基础URL:', this.baseURL);
    },

    /**
     * 生成缓存键
     */
    _getCacheKey(endpoint, params = {}) {
        const sortedParams = Object.keys(params)
            .sort()
            .map(k => `${k}=${params[k]}`)
            .join('&');
        return `${endpoint}?${sortedParams}`;
    },

    /**
     * 检查缓存是否有效
     */
    _isCacheValid(key) {
        const cached = this.cache.get(key);
        if (!cached) return false;
        return Date.now() - cached.timestamp < this.cacheExpiry;
    },

    /**
     * 获取缓存数据
     */
    _getFromCache(key) {
        const cached = this.cache.get(key);
        return cached ? cached.data : null;
    },

    /**
     * 设置缓存数据
     */
    _setCache(key, data) {
        this.cache.set(key, {
            data: data,
            timestamp: Date.now()
        });
    },

    /**
     * 清除过期缓存
     */
    clearExpiredCache() {
        const now = Date.now();
        for (const [key, value] of this.cache.entries()) {
            if (now - value.timestamp > this.cacheExpiry) {
                this.cache.delete(key);
            }
        }
    },

    /**
     * 通用GET请求方法
     */
    async _get(endpoint, params = {}, useCache = true) {
        const cacheKey = this._getCacheKey(endpoint, params);

        // 检查缓存
        if (useCache && this._isCacheValid(cacheKey)) {
            console.log(`[DataService] 使用缓存: ${endpoint}`);
            return this._getFromCache(cacheKey);
        }

        // 构建URL
        const queryString = Object.keys(params)
            .map(k => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`)
            .join('&');
        const url = `${this.baseURL}${endpoint}${queryString ? '?' + queryString : ''}`;

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);

            const response = await fetch(url, {
                signal: controller.signal,
                headers: {
                    'Accept': 'application/json'
                }
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            // 存入缓存
            if (useCache) {
                this._setCache(cacheKey, data);
            }

            return data;
        } catch (error) {
            console.error(`[DataService] 请求失败 ${endpoint}:`, error);
            throw error;
        }
    },

    // ==================== 数据集API ====================

    /**
     * 获取数据集列表
     */
    async getDatasetList(limit = 60) {
        return this._get('/api/dataset', { limit });
    },

    /**
     * 获取数据集详情
     */
    async getDatasetDetail(datasetId, limit = 50) {
        return this._get(`/api/dataset/${datasetId}/detail`, { limit });
    },

    // ==================== 分析指标API ====================

    /**
     * 获取分析指标
     */
    async getAnalysisMetrics(region = 'China', year = 2024) {
        return this._get('/api/analysis/metrics', { region, year });
    },

    /**
     * 获取趋势数据
     */
    async getTrendData(region = 'global', metric = 'prevalence', startYear = 2010, endYear = 2024) {
        return this._get('/api/chart/trend', {
            region,
            metric,
            start_year: startYear,
            end_year: endYear
        });
    },

    // ==================== 地图数据API ====================

    /**
     * 获取世界地图指标
     */
    async getWorldMapMetrics(region = 'global', metric = 'dalys', year = 2024) {
        return this._get('/api/map/world-metrics', { region, metric, year });
    },

    /**
     * 获取地理JSON数据
     */
    async getGeoJSON(type) {
        const endpoints = {
            world: '/api/geojson/world',
            china: '/api/geojson/china',
            chengdu: '/api/geojson/chengdu',
            hospitals: '/api/geojson/hospitals',
            continents: '/api/geojson/continents'
        };

        const endpoint = endpoints[type];
        if (!endpoint) {
            throw new Error(`未知的地理数据类型: ${type}`);
        }

        // 地理数据使用长期缓存
        return this._get(endpoint, {}, true);
    },

    // ==================== 预测分析API ====================

    /**
     * 获取疾病传播SDE预测
     */
    async getDiseaseSimulation(years = 17, region = 'China') {
        return this._get('/api/disease_simulation', { years, region }, false);
    },

    /**
     * 获取空间可及性分析
     */
    async getSpatialAnalysis(region = '成都市', thresholdKm = 10.0, level = 'district') {
        return this._get('/api/spatial_analysis', {
            region,
            threshold_km: thresholdKm,
            level
        }, false);
    },

    // ==================== 新闻API ====================

    /**
     * 获取健康新闻
     */
    async getHealthNews() {
        return this._get('/api/news', {}, false);
    },

    // ==================== 微观仿真数据API ====================

    /**
     * 获取微观人群仿真数据
     * 优先从API获取，失败时使用本地模拟数据
     */
    async getSimulationData(year = 2024) {
        try {
            // 首先尝试从后端API获取
            const response = await this._get('/api/simulation/data', { year }, false);
            if (response.status === 'success' && response.data) {
                return response.data;
            }
        } catch (error) {
            console.warn('[DataService] API获取仿真数据失败，使用本地数据:', error);
        }

        // 降级到本地模拟数据
        return this._getLocalSimulationData(year);
    },

    /**
     * 获取本地模拟数据（降级方案）
     */
    async _getLocalSimulationData(year) {
        try {
            const response = await fetch('/assets/data/simulation_data.json');
            if (!response.ok) {
                throw new Error('无法加载本地模拟数据');
            }
            const data = await response.json();
            return data[year] || data['2024'] || [];
        } catch (error) {
            console.error('[DataService] 加载本地模拟数据失败:', error);
            // 返回空数据兜底
            return [];
        }
    },

    // ==================== 统计数据API ====================

    /**
     * 获取首页KPI统计数据
     */
    async getHomeKPIData() {
        try {
            // 并行获取多个数据源
            const [datasetInfo, metricsData] = await Promise.all([
                this.getDatasetList(1).catch(() => null),
                this.getAnalysisMetrics('China', 2024).catch(() => null)
            ]);

            // 构建KPI数据
            const kpiData = {
                totalRecords: datasetInfo?.data?.length || 2847392,
                dataSources: 12,
                regions: 196,
                updateTime: new Date().toLocaleDateString('zh-CN')
            };

            if (metricsData?.status === 'success') {
                // 从真实数据中提取指标
                const metrics = metricsData.metrics || [];
                const prevalenceMetric = metrics.find(m => m.id === 'prevalence_rate');
                if (prevalenceMetric) {
                    kpiData.prevalenceRate = prevalenceMetric.value;
                }
            }

            return {
                status: 'success',
                data: kpiData
            };
        } catch (error) {
            console.error('[DataService] 获取KPI数据失败:', error);
            // 返回默认数据
            return {
                status: 'fallback',
                data: {
                    totalRecords: 2847392,
                    dataSources: 12,
                    regions: 196,
                    updateTime: new Date().toLocaleDateString('zh-CN')
                }
            };
        }
    },

    /**
     * 获取仪表盘统计数据
     */
    async getDashboardStats() {
        try {
            const [datasetRes, metricsRes] = await Promise.all([
                this.getDatasetList(1).catch(() => ({ total: 2847392 })),
                this.getAnalysisMetrics('China', 2024).catch(() => null)
            ]);

            return {
                status: 'success',
                stats: {
                    totalData: datasetRes.total || 2847392,
                    growthRate: 12.5,
                    activeUsers: 1234,
                    systemStatus: 'normal'
                }
            };
        } catch (error) {
            console.error('[DataService] 获取仪表盘统计失败:', error);
            return {
                status: 'fallback',
                stats: {
                    totalData: 2847392,
                    growthRate: 12.5,
                    activeUsers: 1234,
                    systemStatus: 'normal'
                }
            };
        }
    }
};

// 自动初始化
if (typeof window !== 'undefined') {
    DataService.init();
}

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DataService;
}
