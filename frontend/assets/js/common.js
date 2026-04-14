/*
 * [参赛作品说明]
 * 本模块为学生参赛作品的前端交互/样式支持。
 * 重点展示了数据可视化、动态交互以及响应式布局的技术实现。
 */
/**
 * 全局公共脚本
 */

// ==========================================
// 导航栏组件动态加载模块
// ==========================================

const NavigationLoader = {
    loaded: false,
    loading: false,

    async loadHeader(type = 'frontend') {
        if (this.loaded) {
            return Promise.resolve();
        }

        if (this.loading) {
            return new Promise((resolve) => {
                const checkLoaded = setInterval(() => {
                    if (this.loaded) {
                        clearInterval(checkLoaded);
                        resolve();
                    }
                }, 50);
            });
        }

        this.loading = true;

        const container = document.getElementById('site-header-container');
        if (!container) {
            console.warn('未找到导航容器 #site-header-container');
            this.loading = false;
            return Promise.resolve();
        }

        const headerFile = type === 'admin'
            ? '/components/header-admin.html'
            : '/components/header-frontend.html';

        try {
            const response = await fetch(headerFile);
            if (!response.ok) {
                throw new Error(`加载导航组件失败: ${response.status}`);
            }
            const html = await response.text();
            container.innerHTML = html;
            this.loaded = true;
            this.loading = false;

            if (typeof GlobalTopBar !== 'undefined') {
                GlobalTopBar.init();
            }
        } catch (error) {
            console.error('导航栏加载失败:', error);
            this.loading = false;
            this.showFallbackHeader(container, type);
        }
    },

    showFallbackHeader(container, type) {
        const isFrontend = type !== 'admin';
        const fallbackHtml = isFrontend
            ? `<header class="global-top-bar">
                <div class="brand">
                    <div class="brand-logo">🏥</div>
                    <span class="brand-name">HealthImfomationSysteam</span>
                </div>
                <nav class="nav-center">
                    <ul class="nav-menu">
                        <li class="nav-menu-item"><a href="/use/index.html" class="nav-menu-link"><span>🏠</span><span>首页</span></a></li>
                        <li class="nav-menu-item"><a href="/use/datasets.html" class="nav-menu-link"><span>📁</span><span>数据集</span></a></li>
                    </ul>
                </nav>
                <div class="nav-right">
                    <a href="/use/login.html" class="btn-login">登录</a>
                </div>
            </header>`
            : `<header class="global-top-bar">
                <div class="brand">
                    <div class="brand-logo">🏥</div>
                    <span class="brand-name">HealthImfomationSysteam</span>
                </div>
                <nav class="nav-center">
                    <ul class="nav-menu">
                        <li class="nav-menu-item"><a href="/admin/dashboard.html" class="nav-menu-link"><span>📊</span><span>数据概览</span></a></li>
                    </ul>
                </nav>
                <div class="nav-right">
                    <a href="/use/index.html" class="back-to-frontend"><span>🏠</span><span>返回前台</span></a>
                </div>
            </header>`;

        container.innerHTML = fallbackHtml;
        if (typeof showToast === 'function') {
            showToast('导航栏加载失败，已显示简化版本', 'warning');
        }
    }
};

function loadNavigationHeader(type = 'frontend') {
    return NavigationLoader.loadHeader(type);
}

// ==========================================
// 全局顶部导航栏 (Global Top Bar) 功能模块
// ==========================================

const GlobalTopBar = {
    // 初始化导航栏
    init() {
        this.initActiveState();
        this.initMobileMenu();
        this.initUserMenu();
        this.initSearch();
        this.initNotifications();
        this.updateAuthState();
    },

    // 根据当前页面路径设置导航高亮
    initActiveState() {
        const currentPath = window.location.pathname;
        const currentPage = currentPath.split('/').pop() || 'index.html';

        // 处理主导航链接
        document.querySelectorAll('.global-top-bar .nav-menu-link[data-nav], .global-top-bar .dropdown-item[data-nav]').forEach(link => {
            const navPage = link.getAttribute('data-nav');
            if (navPage === currentPage || currentPath.includes(navPage)) {
                link.classList.add('active');
                // 如果是下拉菜单项，同时高亮父级
                const parentDropdown = link.closest('.nav-dropdown');
                if (parentDropdown) {
                    const toggle = parentDropdown.querySelector('.nav-dropdown-toggle');
                    if (toggle) toggle.classList.add('active');
                }
            } else {
                link.classList.remove('active');
            }
        });

        // 处理移动端导航
        document.querySelectorAll('.mobile-nav-panel .mobile-nav-link[data-nav]').forEach(link => {
            const navPage = link.getAttribute('data-nav');
            if (navPage === currentPage || currentPath.includes(navPage)) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    },

    // 初始化移动端菜单
    initMobileMenu() {
        const menuBtn = document.querySelector('.global-top-bar .mobile-menu-btn');
        const mobilePanel = document.querySelector('.mobile-nav-panel');

        if (menuBtn && mobilePanel) {
            menuBtn.addEventListener('click', () => {
                mobilePanel.classList.toggle('show');
                const isOpen = mobilePanel.classList.contains('show');
                menuBtn.setAttribute('aria-expanded', isOpen);
            });

            // 点击外部关闭菜单
            document.addEventListener('click', (e) => {
                if (!menuBtn.contains(e.target) && !mobilePanel.contains(e.target)) {
                    mobilePanel.classList.remove('show');
                    menuBtn.setAttribute('aria-expanded', 'false');
                }
            });
        }
    },

    // 初始化用户菜单交互
    initUserMenu() {
        const userMenu = document.querySelector('.global-top-bar .user-menu');
        if (userMenu) {
            // 点击用户头像切换下拉菜单
            const avatar = userMenu.querySelector('.user-avatar');
            const dropdown = userMenu.querySelector('.user-dropdown');

            if (avatar && dropdown) {
                avatar.addEventListener('click', (e) => {
                    e.stopPropagation();
                    dropdown.classList.toggle('show');
                });

                // 点击外部关闭下拉菜单
                document.addEventListener('click', (e) => {
                    if (!userMenu.contains(e.target)) {
                        dropdown.classList.remove('show');
                    }
                });
            }
        }
    },

    // 初始化搜索功能
    initSearch() {
        const searchInput = document.querySelector('.global-top-bar .global-search input');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const query = searchInput.value.trim();
                    if (query) {
                        // 触发全局搜索事件
                        window.dispatchEvent(new CustomEvent('globalSearch', {
                            detail: { query }
                        }));
                        showToast(`搜索: ${query}`, 'info');
                    }
                }
            });
        }
    },

    // 初始化通知功能
    initNotifications() {
        const notifBtn = document.querySelector('.global-top-bar .notification-btn');
        if (notifBtn) {
            notifBtn.addEventListener('click', () => {
                showToast('通知功能开发中...', 'info');
            });
        }
    },

    // 更新认证状态（显示/隐藏登录/用户相关元素）
    updateAuthState() {
        const userStr = localStorage.getItem('user') || localStorage.getItem('currentUser');
        const isLoggedIn = !!userStr;
        let user = null;

        if (isLoggedIn) {
            try {
                user = JSON.parse(userStr);
            } catch (e) {
                console.warn('解析用户信息失败', e);
            }
        }

        // 更新用户头像显示
        const avatar = document.querySelector('.global-top-bar .user-avatar');
        if (avatar && user) {
            const initials = user.name
                ? user.name.substring(0, 2).toUpperCase()
                : user.username
                    ? user.username.substring(0, 2).toUpperCase()
                    : '用户';
            avatar.textContent = initials;
        }

        // 显示/隐藏登录/用户相关元素
        document.querySelectorAll('.global-top-bar .guest-only').forEach(el => {
            el.style.display = isLoggedIn ? 'none' : 'flex';
        });

        document.querySelectorAll('.global-top-bar .user-only').forEach(el => {
            el.style.display = isLoggedIn ? 'flex' : 'none';
        });

        // 管理员专属元素
        if (user && user.role === 'admin') {
            document.querySelectorAll('.global-top-bar .admin-only').forEach(el => {
                el.style.display = 'flex';
            });
        } else {
            document.querySelectorAll('.global-top-bar .admin-only').forEach(el => {
                el.style.display = 'none';
            });
        }
    },

    // 退出登录
    logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.removeItem('currentUser');
        showToast('已成功退出登录', 'success');
        setTimeout(() => {
            window.location.href = '/use/login.html';
        }, 1000);
    }
};

// 页面加载完成后初始化导航栏（仅当导航栏已存在于页面中时）
// 如果使用组件化加载，则由 loadNavigationHeader 函数负责初始化
document.addEventListener('DOMContentLoaded', () => {
    const existingHeader = document.querySelector('.global-top-bar');
    if (existingHeader && !NavigationLoader.loaded) {
        GlobalTopBar.init();
    }
});

// ==========================================
// 工具函数
// ==========================================

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
        toast.style.borderLeft = '4px solid #fff';
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

    // 设置骨架屏状态（仅对存在的元素）
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

                // 更新 DALYs 卡片（元素存在性检查）
                const dalysCard = document.getElementById('card-dalys');
                if (dalysCard) {
                    dalysCard.classList.remove('skeleton', 'disabled');
                    const metricDalys = document.getElementById('metric-dalys');
                    if (metricDalys) metricDalys.innerText = data.dalys.value.toLocaleString();
                    const trendEl = document.getElementById('metric-dalys-trend');
                    if (trendEl) {
                        trendEl.innerText = `${Math.abs(data.dalys.trend)}%`;
                        trendEl.parentElement.className = data.dalys.trend > 0 ? 'trend up' : 'trend down';
                        if (trendEl.previousElementSibling) {
                            trendEl.previousElementSibling.innerHTML = data.dalys.trend > 0 ? '↑' : '↓';
                        }
                    }
                    if (window.echarts && data.dalys.sparkline) {
                        renderSparkline('sparkline-dalys', data.dalys.sparkline, data.dalys.trend > 0 ? '#f5222d' : '#52c41a');
                    }
                }

                // 更新高发疾病卡片（元素存在性检查）
                const diseaseCard = document.getElementById('card-top-disease');
                if (diseaseCard) {
                    diseaseCard.classList.remove('skeleton', 'disabled');
                    const metricDiseaseName = document.getElementById('metric-disease-name');
                    if (metricDiseaseName) metricDiseaseName.innerText = data.top_disease.name;
                    const ratioEl = document.getElementById('metric-disease-ratio');
                    if (ratioEl) ratioEl.innerText = `${data.top_disease.ratio}%`;
                }

                // 更新 DEA 效率卡片（元素存在性检查）
                const deaCard = document.getElementById('card-dea');
                if (deaCard) {
                    deaCard.classList.remove('skeleton', 'disabled');
                    const metricDea = document.getElementById('metric-dea');
                    if (metricDea) metricDea.innerText = data.dea.value.toFixed(3);
                    const trendEl = document.getElementById('metric-dea-trend');
                    if (trendEl) {
                        trendEl.innerText = `${Math.abs(data.dea.trend)}%`;
                        // 效率上升是好事 (绿色)，下降是坏事 (红色)
                        trendEl.parentElement.className = data.dea.trend > 0 ? 'trend down' : 'trend up';
                        if (trendEl.previousElementSibling) {
                            trendEl.previousElementSibling.innerHTML = data.dea.trend > 0 ? '↑' : '↓';
                        }
                    }
                    if (window.echarts && data.dea.sparkline) {
                        renderSparkline('sparkline-dea', data.dea.sparkline, data.dea.trend > 0 ? '#52c41a' : '#f5222d');
                    }
                }

                // 更新预测卡片（元素存在性检查）
                const predCard = document.getElementById('card-prediction');
                if (predCard) {
                    predCard.classList.remove('skeleton', 'disabled');
                    const metricPredRate = document.getElementById('metric-pred-rate');
                    if (metricPredRate) metricPredRate.innerText = `${data.prediction.growth_rate}%`;
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

// 退出登录（兼容旧版函数）
function logout() {
    if (typeof GlobalTopBar !== 'undefined' && GlobalTopBar.logout) {
        GlobalTopBar.logout();
    } else {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/use/login.html';
    }
}
