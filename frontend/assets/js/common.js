/**
 * 全局公共脚本
 */

// 显示全局提示
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast-message';
    
    // 根据类型设置图标或颜色
    let icon = '';
    if (type === 'success') {
        icon = '✅ ';
        toast.style.borderLeft = '4px solid #52c41a';
    } else if (type === 'error') {
        icon = '❌ ';
        toast.style.borderLeft = '4px solid #f5222d';
    } else if (type === 'warning') {
        icon = '⚠️ ';
        toast.style.borderLeft = '4px solid #fa8c16';
    } else {
        icon = 'ℹ️ ';
        toast.style.borderLeft = '4px solid #1890ff';
    }
    
    toast.innerHTML = `${icon}<span>${message}</span>`;
    document.body.appendChild(toast);
    
    // 3秒后自动消失
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// 检查是否登录（示例方法，根据实际情况调整）
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        // 如果未登录，且不是登录页/注册页/首页，则跳转到登录页
        const path = window.location.pathname;
        const publicPages = ['/login.html', '/register.html', '/index.html', '/'];
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
