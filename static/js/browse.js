// ============================================
// browse.js — 按系统浏览页面交互逻辑
// 作用:
//   1. 左侧系统列表点击高亮
//   2. 疾病卡片的异步症状标签加载
//   3. 级别筛选按钮动态切换
//   4. 疾病卡片的键盘导航支持
// ============================================

document.addEventListener('DOMContentLoaded', function () {
    // ============================================
    // 功能1: 左侧系统列表 — 当前选中项高亮
    // 作用: 无需额外操作，服务端渲染已完成active状态
    // 此处预留给未来可能的AJAX动态加载
    // ============================================
    const systemList = document.getElementById('systemList');
    if (systemList) {
        // 确保当前选中项在可视区域内
        const activeItem = systemList.querySelector('.active');
        if (activeItem) {
            activeItem.scrollIntoView({ block: 'nearest' });
        }
    }

    // ============================================
    // 功能2: 疾病卡片症状标签异步加载
    // 作用: 页面加载后，通过API批量获取每个疾病的症状数据
    // 异步加载可以更快地渲染页面主体
    // ============================================
    const diseaseCards = document.querySelectorAll('.disease-card');
    diseaseCards.forEach(card => {
        // 从卡片链接中提取disease_id
        const link = card.querySelector('a[href*="/disease/"]');
        if (!link) return;
        const href = link.getAttribute('href');
        const match = href.match(/\/disease\/(\d+)/);
        if (!match) return;
        const diseaseId = match[1];

        const symptomContainer = document.getElementById(`symptoms-${diseaseId}`);
        if (!symptomContainer) return;

        // 异步加载症状数据
        fetch(`/api/diseases/${diseaseId}`)
            .then(response => {
                if (!response.ok) throw new Error('加载失败');
                return response.json();
            })
            .then(data => {
                if (data.symptoms && data.symptoms.length > 0) {
                    symptomContainer.innerHTML = data.symptoms.map(s => {
                        const relevanceLabel = s.relevance === 'main' ? '（主要）' : '';
                        return `<span class="badge symptom-tag symptom-${s.relevance} me-1 mb-1">
                            ${s.name}${relevanceLabel}
                        </span>`;
                    }).join('');
                } else {
                    symptomContainer.innerHTML = '<span class="text-muted small">暂无症状记录</span>';
                }
            })
            .catch(err => {
                console.error(`症状加载失败 (disease ${diseaseId}):`, err);
                symptomContainer.innerHTML = '<span class="text-muted small">加载失败</span>';
            });
    });

    // ============================================
    // 功能3: 级别筛选按钮 — URL参数处理
    // 作用: 筛选按钮绑定level参数，保持当前system_id
    // ============================================
    // 筛选按钮已通过href生成正确的URL，无需额外JS处理

    // ============================================
    // 功能4: 响应式侧边栏 — 移动端下系统列表折叠
    // 作用: 小屏幕上将系统列表改为可折叠的下拉选择
    // ============================================
    function handleResponsiveLayout() {
        if (window.innerWidth < 992) {
            // 移动端: 确保系统列表可见
            const sidebar = document.querySelector('.sticky-lg-top');
            if (sidebar) {
                sidebar.classList.remove('sticky-lg-top');
            }
        }
    }
    handleResponsiveLayout();
    window.addEventListener('resize', debounce(handleResponsiveLayout, 200));
});
