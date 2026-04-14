/**
 * 中台调度中心 - Axios拦截器封装
 * 
 * 功能说明：
 * 1. 统一处理中台API请求和响应
 * 2. 标准化错误处理和用户提示
 * 3. 封装常用API接口供页面调用
 * 
 * @version 1.0.0
 * @author Health Information System
 */

// 确保Axios和SweetAlert2已加载
if (typeof axios === 'undefined') {
    console.error('[MiddlePlatform] Axios库未加载，请先引入axios');
}
if (typeof Swal === 'undefined') {
    console.error('[MiddlePlatform] SweetAlert2库未加载，请先引入sweetalert2');
}

/**
 * 创建中台专属通信实例
 * 配置基础参数：基础URL、超时时间、默认请求头
 */
const middlePlatform = axios.create({
    baseURL: 'http://127.0.0.1:8000/api',  // 中台API基础路径
    timeout: 15000,                       // 15秒超时设置，适应计算密集型操作
    headers: {                            // 添加默认请求头
        'Content-Type': 'application/json'
    }
});

/**
 * 请求拦截器
 * 可用于统一添加认证令牌、请求日志等
 */
middlePlatform.interceptors.request.use(
    function (config) {
        // TODO: 后续可在此处添加认证令牌
        // config.headers.Authorization = `Bearer ${token}`;
        
        // 请求日志记录（调试用）
        console.log(`[MiddlePlatform] 请求: ${config.method?.toUpperCase()} ${config.url}`);
        
        return config;
    },
    function (error) {
        console.error('[MiddlePlatform] 请求拦截器错误:', error);
        return Promise.reject(error);
    }
);

/**
 * 响应拦截器
 * 统一处理中台返回的标准格式响应
 */
middlePlatform.interceptors.response.use(
    // 成功响应处理（HTTP状态码2xx）
    function (response) {
        const res = response.data;
        
        // 验证响应数据结构完整性
        if (typeof res !== 'object' || res === null) {
            Swal.fire({
                title: '数据格式错误',
                text: '中台返回数据格式不符合预期',
                icon: 'error',
                confirmButtonText: '确定'
            });
            return Promise.reject(new Error('Invalid response format'));
        }
        
        // 业务逻辑成功处理 (code === 200)
        if (res.code === 200) {
            // 验证data字段存在性
            if (res.data === undefined) {
                Swal.fire({
                    title: '数据异常',
                    text: '响应中未包含data字段',
                    icon: 'warning',
                    confirmButtonText: '确定'
                });
                return Promise.reject(new Error('Response missing data field'));
            }
            // 直接返回核心数据给调用方，简化页面处理逻辑
            return res.data;
        }
        // 业务逻辑错误处理 (code !== 200)
        else {
            // 确保错误信息存在
            const errorMessage = res.message || '未知业务错误';
            Swal.fire({
                title: '操作提示',
                text: errorMessage,
                icon: 'warning',
                confirmButtonText: '确定'
            });
            return Promise.reject(new Error(errorMessage));
        }
    },
    // 错误响应处理（HTTP状态码非2xx或网络错误）
    function (error) {
        // 判断错误类型
        let title = '系统错误';
        let errorMsg = '无法连接到数据中台';
        let icon = 'error';
        
        if (error.response) {
            // 服务器返回了错误状态码
            const status = error.response.status;
            errorMsg = error.response.data?.message || '服务器处理请求时发生错误';
            
            // 根据状态码提供更具体的错误信息
            switch (status) {
                case 400:
                    title = '请求参数错误';
                    icon = 'warning';
                    break;
                case 401:
                    title = '身份验证失败';
                    break;
                case 403:
                    title = '权限不足';
                    break;
                case 404:
                    title = '接口不存在';
                    icon = 'warning';
                    break;
                case 408:
                    title = '请求超时';
                    errorMsg = '服务器响应超时，请稍后重试';
                    break;
                case 500:
                    title = '服务器内部错误';
                    break;
                case 502:
                    title = '网关错误';
                    errorMsg = '中台服务暂时不可用，请稍后重试';
                    break;
                case 503:
                    title = '服务不可用';
                    errorMsg = '中台算力引擎正在维护，请稍后重试';
                    break;
                default:
                    title = `请求失败 (${status})`;
            }
        } else if (error.request) {
            // 请求已发出但未收到响应（网络错误）
            title = '网络连接失败';
            errorMsg = '无法连接到数据中台，请检查网络连接';
        } else {
            // 请求配置出错
            title = '请求配置错误';
            errorMsg = error.message || '请求发送失败';
        }
        
        // 显示错误提示
        Swal.fire({
            title: title,
            text: errorMsg,
            icon: icon,
            confirmButtonText: '确定'
        });
        
        return Promise.reject(error);
    }
);

/**
 * API接口封装
 * 暴露供页面调用的标准化API方法
 */
window.API = {
    /**
     * 获取疾病预测数据
     * @param {string} region - 地区名称
     * @param {number} [years=15] - 预测年数，默认15年
     * @returns {Promise<Object>} - 包含预测数据的Promise对象
     * @throws {Error} - 参数验证失败时抛出错误
     */
    getDiseasePrediction: (region, years = 15) => {
        // 参数验证
        if (!region || typeof region !== 'string') {
            return Promise.reject(new Error('地区参数必须为非空字符串'));
        }
        if (typeof years !== 'number' || years <= 0 || !Number.isInteger(years)) {
            return Promise.reject(new Error('预测年数必须为正整数'));
        }
        
        // 构建请求URL（对参数进行编码防止注入）
        const params = new URLSearchParams({
            region: region.trim(),
            years: years.toString()
        });
        
        return middlePlatform.get(`/disease_simulation?${params.toString()}`);
    },

    /**
     * 获取空间分析数据
     * @param {string} region - 地区名称
     * @param {number} radius - 分析半径(公里)
     * @param {string} [level='district'] - 分析级别，默认'district'
     * @returns {Promise<Object>} - 包含空间分析数据的Promise对象
     * @throws {Error} - 参数验证失败时抛出错误
     */
    getSpatialAnalysis: (region, radius, level = 'district') => {
        // 参数验证
        if (!region || typeof region !== 'string') {
            return Promise.reject(new Error('地区参数必须为非空字符串'));
        }
        if (typeof radius !== 'number' || radius <= 0) {
            return Promise.reject(new Error('半径参数必须为正数字'));
        }
        if (!['district', 'community'].includes(level)) {
            return Promise.reject(new Error('分析级别必须是 district 或 community'));
        }
        
        // 构建请求URL
        const params = new URLSearchParams({
            region: region.trim(),
            threshold_km: radius.toString(),
            level: level
        });
        
        return middlePlatform.get(`/spatial_analysis?${params.toString()}`);
    },

    /**
     * 获取健康指标数据
     * @param {string} metric - 指标名称
     * @param {string} [region='Global'] - 地区名称，默认'Global'
     * @returns {Promise<Object>} - 包含指标数据的Promise对象
     */
    getHealthMetric: (metric, region = 'Global') => {
        if (!metric || typeof metric !== 'string') {
            return Promise.reject(new Error('指标参数必须为非空字符串'));
        }
        
        const params = new URLSearchParams({
            metric: metric.trim(),
            region: region.trim()
        });
        
        return middlePlatform.get(`/health_metrics?${params.toString()}`);
    },

    /**
     * 获取全球健康数据
     * @param {string} [region] - 可选的地区筛选
     * @returns {Promise<Object>} - 包含全球健康数据的Promise对象
     */
    getGlobalHealthData: (region) => {
        const params = new URLSearchParams();
        if (region) {
            params.append('region', region.trim());
        }
        
        const queryString = params.toString();
        return middlePlatform.get(`/global_health${queryString ? '?' + queryString : ''}`);
    },

    /**
     * 通用GET请求方法
     * @param {string} endpoint - API端点路径
     * @param {Object} [params] - 查询参数对象
     * @returns {Promise<Object>} - 响应数据
     */
    get: (endpoint, params) => {
        if (!endpoint || typeof endpoint !== 'string') {
            return Promise.reject(new Error('端点路径必须为非空字符串'));
        }
        
        // 确保端点以/开头
        const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
        
        // 构建查询字符串
        let queryString = '';
        if (params && typeof params === 'object') {
            const searchParams = new URLSearchParams();
            Object.entries(params).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    searchParams.append(key, String(value));
                }
            });
            queryString = searchParams.toString();
        }
        
        return middlePlatform.get(`${path}${queryString ? '?' + queryString : ''}`);
    },

    /**
     * 通用POST请求方法
     * @param {string} endpoint - API端点路径
     * @param {Object} data - 请求体数据
     * @returns {Promise<Object>} - 响应数据
     */
    post: (endpoint, data) => {
        if (!endpoint || typeof endpoint !== 'string') {
            return Promise.reject(new Error('端点路径必须为非空字符串'));
        }
        
        const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
        return middlePlatform.post(path, data);
    }
};

// 模块加载完成日志
console.log('[MiddlePlatform] API模块已加载，可用方法:', Object.keys(window.API).join(', '));
