// 文件路径: frontend/assets/js/config.js
// 全局应用配置文件 - 集中管理所有环境相关变量和应用配置

const AppConfig = {
    // 当前环境标识：'development' 表示开发环境，'production' 表示生产环境
    env: 'development',

    // API 基础配置
    api: {
        // 开发环境API基础URL - 使用/api前缀以匹配main.py中的路由配置
        // 使用相对路径或当前窗口协议/主机，避免硬编码端口
        development: '/api',
        // 生产环境API基础URL (部署时使用的真实后端域名)
        production: 'https://api.yourdomain.com/api',
    },

    // 第三方服务密钥配置
    thirdParty: {
        // 高德地图API密钥
        amapKey: '893aa291ba8fd5ceea01973a6162f182',
    },

    // 获取当前环境的API基础URL
    // 功能：根据当前env配置返回对应的API基础URL，若配置不存在则默认使用开发环境URL
    getBaseUrl: function() {
        return this.api[this.env] || this.api.development;
    }
};

// 模块化环境适配：若在模块化环境中则导出配置对象，否则挂载到全局window对象
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AppConfig;
} else {
    // 浏览器环境：挂载到全局window对象
    window.AppConfig = AppConfig;
}
