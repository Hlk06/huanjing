// ============================================
// search.js — 症状搜索页面交互逻辑
// 作用:
//   1. 搜索输入自动补全建议
//   2. 多症状空格/逗号分隔输入
//   3. 级别筛选按钮切换
//   4. AJAX搜索结果动态加载（可选：即时搜索模式）
// 依赖: common.js（工具函数）
// ============================================

document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const searchForm = document.getElementById('searchForm');
    const suggestionsDiv = document.getElementById('searchSuggestions');

    // 如果没有搜索输入框（未加载此页面），跳过
    if (!searchInput) return;

    // ============================================
    // 功能1: 搜索输入自动补全
    // 作用: 用户输入时异步查询匹配的症状名，显示下拉建议
    // ============================================
    let debounceTimer = null;
    searchInput.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        const query = this.value.trim();

        if (query.length < 1) {
            suggestionsDiv.style.display = 'none';
            return;
        }

        // 防抖: 200ms后才发送请求，避免频繁API调用
        debounceTimer = setTimeout(() => {
            fetch(`/api/symptoms/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(symptoms => {
                    if (symptoms.length === 0) {
                        suggestionsDiv.style.display = 'none';
                        return;
                    }
                    // 渲染建议列表
                    suggestionsDiv.innerHTML = symptoms.map(s => `
                        <a class="dropdown-item d-flex justify-content-between align-items-center"
                           href="#" data-name="${s.name}">
                            <span>${highlightMatch(s.name, query)}</span>
                            <small class="text-muted">${s.category || '症状'}</small>
                        </a>
                    `).join('');
                    suggestionsDiv.style.display = 'block';

                    // 绑定点击事件: 点击建议项后填入输入框并搜索
                    suggestionsDiv.querySelectorAll('.dropdown-item').forEach(item => {
                        item.addEventListener('click', function (e) {
                            e.preventDefault();
                            // 如果已有输入，追加到后面（多症状搜索）
                            const current = searchInput.value.trim();
                            const symptomName = this.dataset.name;
                            if (current && !current.includes(symptomName)) {
                                searchInput.value = current + ' ' + symptomName;
                            } else if (!current) {
                                searchInput.value = symptomName;
                            }
                            suggestionsDiv.style.display = 'none';
                            searchInput.focus();
                        });
                    });
                })
                .catch(err => console.error('搜索建议获取失败:', err));
        }, 200);
    });

    // ============================================
    // 功能2: 键盘快捷键
    // 作用: Enter提交搜索, Escape关闭建议
    // ============================================
    searchInput.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            suggestionsDiv.style.display = 'none';
        }
        // Enter键在建议框可见时选择第一项
        if (e.key === 'Enter' && suggestionsDiv.style.display === 'block') {
            const firstItem = suggestionsDiv.querySelector('.dropdown-item');
            if (firstItem && document.activeElement === searchInput) {
                // 允许默认提交行为
                suggestionsDiv.style.display = 'none';
            }
        }
    });

    // ============================================
    // 功能3: 点击外部区域关闭建议
    // ============================================
    document.addEventListener('click', function (e) {
        if (!searchInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
            suggestionsDiv.style.display = 'none';
        }
    });

    // ============================================
    // 功能4: 级别筛选按钮 — 切换时自动提交表单
    // ============================================
    const levelRadios = document.querySelectorAll('input[name="level"]');
    levelRadios.forEach(radio => {
        radio.addEventListener('change', function () {
            // 如果搜索框有内容，自动提交
            if (searchInput.value.trim()) {
                searchForm.submit();
            }
        });
    });

    // ============================================
    // 功能5: 搜索结果高亮匹配文本
    // 作用: 在搜索结果中高亮显示匹配的症状词
    // ============================================
    highlightSearchResults();

    // ============================================
    // 辅助函数
    // ============================================

    /**
     * 高亮匹配的文本片段
     * 作用: 在建议列表中用<strong>标签高亮用户输入匹配的部分
     */
    function highlightMatch(text, query) {
        if (!query) return escapeHtml(text);
        const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        return escapeHtml(text).replace(
            new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
            '<strong class="text-primary">$1</strong>'
        );
    }

    /**
     * 高亮搜索结果中的匹配症状
     * 作用: 在结果卡片中加粗显示匹配的症状名称
     */
    function highlightSearchResults() {
        const queryText = searchInput.value.trim();
        if (!queryText) return;

        // 拆分搜索词
        const keywords = queryText.split(/[,，、\s]+/).filter(Boolean);

        // 遍历所有匹配症状标签
        document.querySelectorAll('.text-success strong').forEach(el => {
            const text = el.textContent;
            keywords.forEach(kw => {
                if (text.includes(kw)) {
                    el.style.backgroundColor = '#fff3cd';
                    el.style.padding = '0 4px';
                    el.style.borderRadius = '3px';
                }
            });
        });
    }
});
