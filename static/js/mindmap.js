// ============================================
// mindmap.js — 思维导图交互逻辑
// 作用:
//   1. 从API加载层级数据并构建思维导图节点树
//   2. 使用SVG渲染可交互的思维导图
//   3. 支持缩放、拖拽、节点展开/折叠
//   4. 点击节点在右侧面板显示详情
// ============================================

class MedicalMindMap {
    constructor(containerId, panelId) {
        this.container = document.getElementById(containerId);
        this.panel = document.getElementById(panelId);
        this.svgNS = 'http://www.w3.org/2000/svg';

        // 视图状态
        this.scale = 1;
        this.translateX = 0;
        this.translateY = 0;
        this.nodeData = null;
        this.selectedNodeId = null;

        // 节点布局参数
        this.nodeWidth = 200;
        this.nodeHeight = 50;
        this.horizontalGap = 220;
        this.verticalGap = 35;
        this.cornerRadius = 8;

        this.colors = {
            root: { bg: '#667eea', text: '#fff', stroke: '#4c51bf' },
            system: { bg: '#e3f2fd', text: '#1565c0', stroke: '#90caf9' },
            disease: { bg: '#e8f5e9', text: '#2e7d32', stroke: '#a5d6a7' },
            default: { bg: '#f5f5f5', text: '#424242', stroke: '#bdbdbd' },
        };

        this.init();
    }

    init() {
        this.createSVG();
        this.bindEvents();
        this.showLoading();
    }

    createSVG() {
        this.svg = document.createElementNS(this.svgNS, 'svg');
        this.svg.setAttribute('width', '100%');
        this.svg.setAttribute('height', '100%');
        this.svg.style.position = 'absolute';
        this.svg.style.top = '0';
        this.svg.style.left = '0';

        const defs = document.createElementNS(this.svgNS, 'defs');
        defs.innerHTML = `
            <filter id="mindmap-shadow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="1" dy="2" stdDeviation="3" flood-opacity="0.15"/>
            </filter>
        `;
        this.svg.appendChild(defs);

        this.linksGroup = document.createElementNS(this.svgNS, 'g');
        this.svg.appendChild(this.linksGroup);

        this.nodesGroup = document.createElementNS(this.svgNS, 'g');
        this.svg.appendChild(this.nodesGroup);

        this.container.appendChild(this.svg);
    }

    async loadData(systemId, level) {
        this.showLoading();
        try {
            let url = '/api/mindmap-data?';
            if (systemId) url += `root=${systemId}`;
            else url += 'root=all';
            if (level && level !== 'all') url += `&level=${level}`;

            const response = await fetch(url);
            const data = await response.json();
            this.nodeData = data.nodeData;
            this.render();
        } catch (err) {
            this.showError('数据加载失败: ' + err.message);
        }
    }

    render() {
        this.clearCanvas();
        if (!this.nodeData || !this.nodeData.children) return;

        this.positions = {};
        this._layoutNode(this.nodeData, 50, 100, 0);
        this._renderLinks(this.nodeData);
        this._renderNode(this.nodeData);
        this._fitCanvas();
    }

    _layoutNode(node, x, y, depth) {
        this.positions[node.id] = { x, y, depth };
        const children = node.children || [];
        if (children.length === 0) return;

        const totalHeight = this._calcSubtreeHeight(node) * (this.nodeHeight + this.verticalGap);
        let startY = y - totalHeight / 2 + this.nodeHeight / 2;

        for (const child of children) {
            const childHeight = this._calcSubtreeHeight(child) * (this.nodeHeight + this.verticalGap);
            const childY = startY + childHeight / 2;
            this._layoutNode(child, x + this.horizontalGap, childY, depth + 1);
            startY += childHeight;
        }
    }

    _calcSubtreeHeight(node) {
        const children = node.children || [];
        if (children.length === 0) return 1;
        let total = 0;
        for (const child of children) {
            total += this._calcSubtreeHeight(child);
        }
        return Math.max(total, 1);
    }

    _renderNode(node) {
        if (!this.positions[node.id]) return;

        const { x, y, depth } = this.positions[node.id];
        const w = this.nodeWidth;
        const h = this.nodeHeight;
        const r = this.cornerRadius;

        let theme;
        if (depth === 0) theme = this.colors.root;
        else if (depth === 1) theme = this.colors.system;
        else if (depth === 2) theme = this.colors.disease;
        else theme = this.colors.default;

        const group = document.createElementNS(this.svgNS, 'g');
        group.setAttribute('transform', `translate(${x - w/2}, ${y - h/2})`);
        group.style.cursor = 'pointer';

        const rect = document.createElementNS(this.svgNS, 'rect');
        rect.setAttribute('width', w);
        rect.setAttribute('height', h);
        rect.setAttribute('rx', r);
        rect.setAttribute('ry', r);
        rect.setAttribute('fill', theme.bg);
        rect.setAttribute('stroke', theme.stroke);
        rect.setAttribute('stroke-width', depth <= 1 ? '2.5' : '1.5');
        rect.setAttribute('filter', 'url(#mindmap-shadow)');
        group.appendChild(rect);

        const text = document.createElementNS(this.svgNS, 'text');
        text.setAttribute('fill', theme.text);
        text.setAttribute('font-size', depth <= 1 ? '13' : '11');
        text.setAttribute('font-weight', depth <= 1 ? '600' : '400');
        text.setAttribute('font-family', 'Microsoft YaHei, sans-serif');

        const topic = (node.topic || '').replace(/\n/g, ' ');
        const maxChars = Math.floor(w / 7) - 2;
        const displayText = topic.length > maxChars ? topic.slice(0, maxChars) + '..' : topic;

        text.setAttribute('x', '10');
        text.setAttribute('y', h / 2 + 4);
        text.textContent = displayText;
        group.appendChild(text);

        if (node.children && node.children.length > 0) {
            const dot = document.createElementNS(this.svgNS, 'circle');
            dot.setAttribute('cx', w - 12);
            dot.setAttribute('cy', h / 2);
            dot.setAttribute('r', '5');
            dot.setAttribute('fill', theme.stroke);
            dot.setAttribute('opacity', '0.7');
            group.appendChild(dot);
        }

        group.addEventListener('click', (e) => { e.stopPropagation(); this.onNodeClick(node); });
        group.addEventListener('mouseenter', () => rect.setAttribute('opacity', '0.85'));
        group.addEventListener('mouseleave', () => rect.setAttribute('opacity', '1'));

        this.nodesGroup.appendChild(group);

        if (node.children && node.expanded !== false) {
            for (const child of node.children) this._renderNode(child);
        }
    }

    _renderLinks(node) {
        if (!this.positions[node.id]) return;
        const children = node.children || [];
        if (node.expanded === false) return;

        for (const child of children) {
            if (!this.positions[child.id]) continue;
            const p1 = this.positions[node.id];
            const p2 = this.positions[child.id];

            const path = document.createElementNS(this.svgNS, 'path');
            const sx = p1.x + this.nodeWidth / 2;
            const sy = p1.y;
            const ex = p2.x - this.nodeWidth / 2;
            const ey = p2.y;
            const cx = (sx + ex) / 2;

            path.setAttribute('d', `M ${sx} ${sy} C ${cx} ${sy}, ${cx} ${ey}, ${ex} ${ey}`);
            path.setAttribute('fill', 'none');
            path.setAttribute('stroke', '#b0bec5');
            path.setAttribute('stroke-width', '1.5');
            path.setAttribute('opacity', '0.5');
            this.linksGroup.appendChild(path);

            this._renderLinks(child);
        }
    }

    onNodeClick(node) {
        this.selectedNodeId = node.id;
        if (node.id.startsWith('dis_')) {
            const diseaseId = node.id.replace('dis_', '');
            this.showDiseasePanel(diseaseId);
        } else if (node.href) {
            window.location.href = node.href;
        }
    }

    async showDiseasePanel(diseaseId) {
        try {
            const resp = await fetch(`/api/diseases/${diseaseId}`);
            const data = await resp.json();

            let symptomsHtml = '';
            if (data.symptoms && data.symptoms.length > 0) {
                symptomsHtml = data.symptoms.map(s => {
                    const cls = s.relevance === 'main' ? 'symptom-main' : `symptom-${s.relevance}`;
                    return `<span class="badge symptom-tag ${cls}">${s.name}</span>`;
                }).join('');
            }

            const defInfo = data.infos?.definition?.[0]?.content || data.overview || '';

            this.panel.innerHTML = `
                <div class="panel-disease-name">${data.name}</div>
                <div class="panel-system-badge">${data.system?.name || ''}</div>
                ${symptomsHtml ? '<div class="panel-symptoms">' + symptomsHtml + '</div>' : ''}
                <div class="panel-info-section">
                    <h6>定义</h6>
                    <p>${truncateText(defInfo, 150)}</p>
                </div>
                ${data.infos?.differential_diagnosis?.[0] ? `
                <div class="panel-info-section">
                    <h6>鉴别诊断</h6>
                    <p>${truncateText(data.infos.differential_diagnosis[0].content, 120)}</p>
                </div>` : ''}
                <div class="mt-3">
                    <a href="/disease/${diseaseId}" class="btn btn-sm btn-outline-primary w-100 mb-2">查看完整信息</a>
                    <a href="/differential/${diseaseId}" class="btn btn-sm btn-outline-warning w-100">鉴别诊断对比</a>
                </div>
            `;
        } catch (err) {
            this.panel.innerHTML = '<div class="panel-empty"><p>加载失败</p></div>';
        }
    }

    clearPanel() {
        this.panel.innerHTML = '<div class="panel-empty"><div class="panel-icon">👆</div><p>点击思维导图节点<br>查看详细信息</p></div>';
    }

    _fitCanvas() {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const [id, pos] of Object.entries(this.positions)) {
            minX = Math.min(minX, pos.x - this.nodeWidth / 2);
            minY = Math.min(minY, pos.y - this.nodeHeight / 2);
            maxX = Math.max(maxX, pos.x + this.nodeWidth / 2);
            maxY = Math.max(maxY, pos.y + this.nodeHeight / 2);
        }
        const w = maxX - minX + 100;
        const h = maxY - minY + 100;
        this.svg.setAttribute('viewBox', `${minX - 50} ${minY - 50} ${w} ${h}`);
    }

    _expandAll() {
        if (!this.nodeData) return;
        this._setExpandAll(this.nodeData);
        this.render();
    }

    _setExpandAll(node) {
        if (node.children && node.children.length > 0) {
            node.expanded = true;
            for (const child of node.children) this._setExpandAll(child);
        }
    }

    clearCanvas() {
        while (this.linksGroup.firstChild) this.linksGroup.removeChild(this.linksGroup.firstChild);
        while (this.nodesGroup.firstChild) this.nodesGroup.removeChild(this.nodesGroup.firstChild);
    }

    showLoading() {
        this.clearCanvas();
        const text = document.createElementNS(this.svgNS, 'text');
        text.setAttribute('x', '200');
        text.setAttribute('y', '100');
        text.setAttribute('fill', '#adb5bd');
        text.setAttribute('font-size', '16');
        text.setAttribute('font-family', 'Microsoft YaHei, sans-serif');
        text.textContent = '加载思维导图...';
        this.nodesGroup.appendChild(text);
        this.clearPanel();
    }

    showError(msg) {
        this.clearCanvas();
        const text = document.createElementNS(this.svgNS, 'text');
        text.setAttribute('x', '200');
        text.setAttribute('y', '100');
        text.setAttribute('fill', '#dc3545');
        text.setAttribute('font-size', '14');
        text.setAttribute('font-family', 'Microsoft YaHei, sans-serif');
        text.textContent = msg;
        this.nodesGroup.appendChild(text);
    }

    bindEvents() {
        this.container.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            this.scale = Math.max(0.3, Math.min(3, this.scale * delta));
            const tx = `scale(${this.scale}) translate(${this.translateX}, ${this.translateY})`;
            this.nodesGroup.setAttribute('transform', tx);
            this.linksGroup.setAttribute('transform', tx);
        });
    }
}

function truncateText(text, maxLen) {
    if (!text) return '';
    return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
}

document.addEventListener('DOMContentLoaded', function () {
    window.mindmap = new MedicalMindMap('mindmapCanvas', 'mindmapPanel');

    const systemSelect = document.getElementById('mindmapSystemSelect');
    const levelSelect = document.getElementById('mindmapLevelSelect');

    function reloadMindmap() {
        const systemId = systemSelect ? systemSelect.value : '';
        const level = levelSelect ? levelSelect.value : 'all';
        window.mindmap.loadData(systemId || null, level);
    }

    if (systemSelect) systemSelect.addEventListener('change', reloadMindmap);
    if (levelSelect) levelSelect.addEventListener('change', reloadMindmap);

    document.getElementById('btnExpandAll')?.addEventListener('click', () => window.mindmap._expandAll());
    document.getElementById('btnResetView')?.addEventListener('click', () => {
        window.mindmap.scale = 1;
        window.mindmap.render();
    });

    reloadMindmap();
});
