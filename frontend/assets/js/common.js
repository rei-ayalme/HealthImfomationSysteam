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
