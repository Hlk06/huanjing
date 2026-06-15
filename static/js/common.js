// ============================================
// common.js — 公共工具函数
// 作用: 提供所有页面共用的工具函数
// 包含: API请求包装、URL参数解析、防抖函数、格式化工具等
// ============================================

/**
 * API基础请求封装
 * 作用: 统一处理fetch请求，自动处理错误状态码
 * @param {string} url - 请求地址
 * @param {object} options - fetch选项
 * @returns {Promise<any>} 解析后的JSON数据
 */
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`请求失败 (${response.status}): ${errorText}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`[API Error] ${url}:`, error);
        throw error;
    }
}

/**
 * URL参数解析
 * 作用: 获取当前页面URL中的查询参数
 * @param {string} name - 参数名
 * @returns {string|null} 参数值
 */
function getUrlParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
}

/**
 * 防抖函数
 * 作用: 限制高频事件的触发频率（如搜索输入），在最后一次调用后延迟执行
 * @param {Function} fn - 要执行的函数
 * @param {number} delay - 延迟毫秒数
 * @returns {Function} 防抖后的函数
 */
function debounce(fn, delay = 300) {
    let timer = null;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

/**
 * HTML转义
 * 作用: 防止XSS攻击，将用户输入中的特殊字符转为HTML实体
 * @param {string} str - 原始字符串
 * @returns {string} 转义后的字符串
 */
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * 截断文本
 * 作用: 将长文本截断到指定长度并添加省略号
 * @param {string} text - 原始文本
 * @param {number} maxLen - 最大长度
 * @returns {string} 截断后的文本
 */
function truncateText(text, maxLen = 100) {
    if (!text || text.length <= maxLen) return text;
    return text.substring(0, maxLen) + '...';
}

/**
 * 格式化日期时间
 * 作用: 将ISO日期字符串格式化为本地化的中文日期
 * @param {string} dateStr - ISO日期字符串
 * @returns {string} 格式化后的日期
 */
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return d.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
    });
}

/**
 * 显示Toast提示消息
 * 作用: 在页面右下角显示短暂的通知消息（自动消失）
 * @param {string} message - 消息内容
 * @param {string} type - 消息类型: 'success' | 'danger' | 'warning' | 'info'
 * @param {number} duration - 显示时长（毫秒）
 */
function showToast(message, type = 'info', duration = 3000) {
    // 创建Toast容器（如果不存在）
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }

    // 创建Toast元素
    const toastId = 'toast-' + Date.now();
    const bgClass = {
        success: 'bg-success text-white',
        danger: 'bg-danger text-white',
        warning: 'bg-warning',
        info: 'bg-info text-white',
    }[type] || 'bg-info text-white';

    const iconMap = {
        success: 'bi-check-circle',
        danger: 'bi-x-circle',
        warning: 'bi-exclamation-triangle',
        info: 'bi-info-circle',
    };

    const toastHtml = `
        <div id="${toastId}" class="toast ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi ${iconMap[type] || 'bi-info-circle'} me-2"></i>${escapeHtml(message)}
                </div>
                <button class="btn-close me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', toastHtml);
    const toastEl = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastEl, { delay: duration });
    toast.show();

    // 隐藏后自动移除DOM元素
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

/**
 * 确认对话框（返回Promise）
 * 作用: 用Bootstrap模态框替代原生confirm，UI更美观
 * 注: 当前使用原生confirm作为简化实现，可根据需要替换为模态框
 * @param {string} message - 确认消息
 * @returns {boolean} 用户是否确认
 */
function confirmDialog(message) {
    return confirm(message);
}

// ============================================
// 页面初始化通用逻辑
// ============================================
document.addEventListener('DOMContentLoaded', function () {
    // 激活当前路由对应的导航链接（Bootstrap自动处理）
    // 此处预留给未来的全局初始化逻辑
    console.log('[临床医学学习系统] 页面就绪');
});
