/**
 * 全局公共脚本
 */

// 显示全局提示 (增加深色背景错误提示)
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast-message';
    
    // 如果是错误，添加 error 类以应用深色背景
    if (type === 'error') {
        toast.classList.add('error');
    }
    
    // 根据类型设置图标或颜色，使用CSS变量
    let icon = '';
    if (type === 'success') {
        icon = '✅ ';
        toast.style.borderLeft = '4px solid var(--success-color, #52c41a)';
    } else if (type === 'error') {
        icon = '❌ ';
        toast.style.borderLeft = '4px solid #fff'; // 错误时边框变白
    } else if (type === 'warning') {
        icon = '⚠️ ';
        toast.style.borderLeft = '4px solid var(--warning-color, #fa8c16)';
    } else {
        icon = 'ℹ️ ';
        toast.style.borderLeft = '4px solid var(--primary-color, #1890ff)';
    }
    
    toast.innerHTML = `${icon}<span>${message}</span>`;
    document.body.appendChild(toast);
    
    // 3秒后自动消失
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translate(-50%, -10px)';
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// 统一分析页面导航：支持 macro / micro / prediction 三类按钮
const ANALYSIS_NAV_ROUTE_MAP = Object.freeze({
    index: '/use/index.html',
    'index.html': '/use/index.html',
    datasets: '/use/datasets.html',
    'datasets.html': '/use/datasets.html',
    meso: '/use/meso-analysis.html',
    'meso-analysis': '/use/meso-analysis.html',
    'meso-analysis.html': '/use/meso-analysis.html',
    macro: '/use/macro-analysis.html',
    'macro-analysis': '/use/macro-analysis.html',
    'macro-analysis.html': '/use/macro-analysis.html',
    micro: '/use/micro-analysis.html',
    'micro-analysis': '/use/micro-analysis.html',
    'micro-analysis.html': '/use/micro-analysis.html',
    prediction: '/use/prediction.html',
    'prediction.html': '/use/prediction.html'
});

function resolveAnalysisRoute(target) {
    if (typeof target !== 'string') return null;
    const normalized = target.trim().toLowerCase();
    if (!normalized) return null;

    if (ANALYSIS_NAV_ROUTE_MAP[normalized]) {
        return ANALYSIS_NAV_ROUTE_MAP[normalized];
    }

    // 兼容传入完整路径的场景
    if (normalized.startsWith('/')) {
        return normalized;
    }

    // 兼容传入文件名的场景
    if (normalized.endsWith('.html')) {
        const fileName = normalized.split('/').pop();
        if (ANALYSIS_NAV_ROUTE_MAP[fileName]) {
            return ANALYSIS_NAV_ROUTE_MAP[fileName];
        }
        return `/use/${fileName}`;
    }

    return null;
}

function notifyNavFailure(message) {
    if (typeof showToast === 'function') {
        showToast(message, 'error');
        return;
    }
    alert(message);
}

// 供各页面内联 onclick 统一调用
window.aiNavigate = function aiNavigate(target) {
    const route = resolveAnalysisRoute(target);
    if (!route) {
        notifyNavFailure(`无法识别跳转目标：${target || '空值'}`);
        return false;
    }

    try {
        if (window.location.pathname === route) {
            showToast('当前已在目标页面', 'info');
            return false;
        }
        window.location.assign(route);
        return true;
    } catch (error) {
        console.error('页面跳转失败', error);
        notifyNavFailure(`页面跳转失败：${route}`);
        return false;
    }
};

// 模拟骨架屏加载数据 (包装原有 fetch)
async function fetchWithSkeleton(url, containerId, renderCallback) {
    const container = document.getElementById(containerId);
    if (container) {
        // 渲染骨架屏
        container.innerHTML = `
            <div style="padding: 20px;">
                <div class="skeleton-box" style="height: 24px; width: 60%; margin-bottom: 16px;"></div>
                <div class="skeleton-box" style="height: 120px; width: 100%; margin-bottom: 12px;"></div>
                <div class="skeleton-box" style="height: 120px; width: 100%;"></div>
            </div>
        `;
    }
    
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`API 请求失败: ${response.status}`);
        }
        const data = await response.json();
        if (renderCallback && container) {
            container.innerHTML = ''; // 清除骨架屏
            renderCallback(data, container);
        }
        return data;
    } catch (e) {
        showToast(e.message, 'error');
        if (container) {
            container.innerHTML = `<div style="padding: 20px; color: var(--error-color); text-align: center;">数据加载失败</div>`;
        }
        throw e;
    }
}

// 当右侧地图点击切换区域或参数改变时，触发更新左侧指标栏
function updateSidebarMetrics(regionName, year) {
    // 侧边栏卡片元素 ID 列表
    const cardIds = ['card-dalys', 'card-top-disease', 'card-dea', 'card-prediction'];
    
    // 设置骨架屏状态
    cardIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('skeleton');
    });

    // 请求后端指标
    fetch(`/api/analysis/metrics?region=${regionName}&year=${year}`)
        .then(response => {
            if (!response.ok) throw new Error('Metrics API Error');
            return response.json();
        })
        .then(res => {
            if (res.status === 'success') {
                const data = res.data;
                
                // 更新 DALYs 卡片
                const dalysCard = document.getElementById('card-dalys');
                if (dalysCard) {
                    dalysCard.classList.remove('skeleton', 'disabled');
                    document.getElementById('metric-dalys').innerText = data.dalys.value.toLocaleString();
                    const trendEl = document.getElementById('metric-dalys-trend');
                    if (trendEl) {
                        trendEl.innerText = `${Math.abs(data.dalys.trend)}%`;
                        trendEl.parentElement.className = data.dalys.trend > 0 ? 'trend up' : 'trend down';
                        trendEl.previousElementSibling.innerHTML = data.dalys.trend > 0 ? '↑' : '↓';
                    }
                    if (window.echarts && data.dalys.sparkline) {
                        renderSparkline('sparkline-dalys', data.dalys.sparkline, data.dalys.trend > 0 ? '#f5222d' : '#52c41a');
                    }
                }

                // 更新高发疾病卡片
                const diseaseCard = document.getElementById('card-top-disease');
                if (diseaseCard) {
                    diseaseCard.classList.remove('skeleton', 'disabled');
                    document.getElementById('metric-disease-name').innerText = data.top_disease.name;
                    const ratioEl = document.getElementById('metric-disease-ratio');
                    if (ratioEl) ratioEl.innerText = `${data.top_disease.ratio}%`;
                }

                // 更新 DEA 效率卡片
                const deaCard = document.getElementById('card-dea');
                if (deaCard) {
                    deaCard.classList.remove('skeleton', 'disabled');
                    document.getElementById('metric-dea').innerText = data.dea.value.toFixed(3);
                    const trendEl = document.getElementById('metric-dea-trend');
                    if (trendEl) {
                        trendEl.innerText = `${Math.abs(data.dea.trend)}%`;
                        // 效率上升是好事 (绿色)，下降是坏事 (红色)
                        trendEl.parentElement.className = data.dea.trend > 0 ? 'trend down' : 'trend up';
                        trendEl.previousElementSibling.innerHTML = data.dea.trend > 0 ? '↑' : '↓';
                    }
                    if (window.echarts && data.dea.sparkline) {
                        renderSparkline('sparkline-dea', data.dea.sparkline, data.dea.trend > 0 ? '#52c41a' : '#f5222d');
                    }
                }

                // 更新预测卡片
                const predCard = document.getElementById('card-prediction');
                if (predCard) {
                    predCard.classList.remove('skeleton', 'disabled');
                    document.getElementById('metric-pred-rate').innerText = `${data.prediction.growth_rate}%`;
                    const targetEl = document.getElementById('metric-pred-target');
                    if (targetEl) targetEl.innerText = data.prediction.target;
                }
            } else {
                handleMetricsError(cardIds);
            }
        })
        .catch(error => {
            console.error("指标加载失败", error);
            handleMetricsError(cardIds);
        });
}

function handleMetricsError(cardIds) {
    cardIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.classList.remove('skeleton');
            el.classList.add('disabled');
            const valEl = el.querySelector('.metric-value');
            if (valEl) valEl.innerText = '暂无数据';
        }
    });
}

function renderSparkline(elementId, dataArray, color) {
    const dom = document.getElementById(elementId);
    if (!dom || !window.echarts) return;
    const chart = echarts.getInstanceByDom(dom) || echarts.init(dom);
    chart.setOption({
        xAxis: { type: 'category', show: false, boundaryGap: false },
        yAxis: { type: 'value', show: false, min: 'dataMin', max: 'dataMax' },
        series: [{
            type: 'line',
            data: dataArray,
            showSymbol: false,
            smooth: true,
            lineStyle: { width: 2, color: color },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: color },
                    { offset: 1, color: 'rgba(255,255,255,0)' }
                ])
            }
        }],
        grid: { left: 0, right: 0, top: 0, bottom: 0 }
    });
}

// 检查是否登录（示例方法，根据实际情况调整）
async function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        const path = window.location.pathname;
        let publicPages = ['/login.html', '/register.html', '/index.html', '/'];
        
        // 尝试从后端获取动态配置的公共页面列表
        try {
            const response = await fetch('/api/config/public-routes');
            if (response.ok) {
                const data = await response.json();
                if (data.publicPages && Array.isArray(data.publicPages)) {
                    // 确保匹配格式
                    publicPages = data.publicPages.map(p => p.startsWith('/') ? p : '/' + p);
                }
            }
        } catch (e) {
            console.warn('获取公共路由配置失败，使用默认配置', e);
        }

        const isPublic = publicPages.some(p => path.endsWith(p));
        
        if (!isPublic) {
            window.location.href = '/use/login.html';
        }
        return false;
    }
    return true;
}

// 退出登录
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/use/login.html';
}
