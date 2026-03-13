let articles = [];
let categories = [];
let tags = [];
let currentFilter = 'all';

// 登出
async function logout() {
    try {
        await fetch('/api/logout', { method: 'POST' });
        window.location.href = '/login';
    } catch (error) {
        console.error('登出失败:', error);
        window.location.href = '/login';
    }
}

// 加载文章列表
async function loadArticles() {
    try {
        const response = await fetch('/api/articles');
        articles = await response.json();
        renderArticles();
        loadFilters();
    } catch (error) {
        console.error('加载文章失败:', error);
    }
}

// 加载分类和标签
async function loadFilters() {
    try {
        const [catRes, tagRes] = await Promise.all([
            fetch('/api/categories'),
            fetch('/api/tags')
        ]);

        categories = await catRes.json();
        tags = await tagRes.json();

        renderFilters();
    } catch (error) {
        console.error('加载筛选条件失败:', error);
    }
}

// 渲染文章列表
function renderArticles() {
    const grid = document.getElementById('articleGrid');
    let filteredArticles = articles;

    // 应用筛选
    if (currentFilter === 'uncategorized') {
        filteredArticles = articles.filter(a => !a.category || a.category === '');
    } else if (currentFilter !== 'all') {
        filteredArticles = articles.filter(a => a.category === currentFilter);
    }

    if (filteredArticles.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <p>暂无文章</p>
                <a href="/editor" class="btn" style="margin-top: 20px;">创建第一篇文章</a>
            </div>
        `;
        return;
    }

    grid.innerHTML = filteredArticles.map(article => `
        <div class="article-card" onclick="viewArticle(${article.id})">
            <h3>${escapeHtml(article.title)}</h3>
            <div class="article-meta">
                ${article.category ? `<span>${escapeHtml(article.category)}</span> • ` : ''}
                ${formatDate(article.updated_at)}
            </div>
            <div class="article-tags">
                ${article.tags ? article.tags.split(',').slice(0, 3).map(tag =>
                    `<span class="tag">${escapeHtml(tag.trim())}</span>`
                ).join('') : ''}
            </div>
        </div>
    `).join('');
}

// 渲染筛选按钮
function renderFilters() {
    const filtersDiv = document.getElementById('filters');
    let html = `
        <button class="filter-btn ${currentFilter === 'all' ? 'active' : ''}" data-filter="all" onclick="setFilter('all')">全部</button>
        <button class="filter-btn ${currentFilter === 'uncategorized' ? 'active' : ''}" data-filter="uncategorized" onclick="setFilter('uncategorized')">未分类</button>
    `;

    categories.forEach(cat => {
        html += `
            <button class="filter-btn ${currentFilter === cat ? 'active' : ''}" data-filter="${escapeHtml(cat)}" onclick="setFilter('${escapeHtml(cat)}')">${escapeHtml(cat)}</button>
        `;
    });

    filtersDiv.innerHTML = html;
}

// 设置筛选
function setFilter(filter) {
    currentFilter = filter;
    renderFilters();
    renderArticles();
}

// 查看文章
async function viewArticle(id) {
    try {
        const response = await fetch(`/api/articles/${id}`);
        const article = await response.json();

        // 使用 marked.js 解析 Markdown
        const content = marked.parse(article.content);

        document.getElementById('modalTitle').textContent = article.title;
        document.getElementById('modalContent').innerHTML = `
            <div style="margin-bottom: 20px; color: #6b7280; font-size: 14px;">
                ${article.category ? `<strong>分类:</strong> ${escapeHtml(article.category)} | ` : ''}
                ${article.tags ? `<strong>标签:</strong> ${escapeHtml(article.tags)}` : ''}
            </div>
            ${content}
        `;
        document.getElementById('editBtn').href = `/editor?id=${id}`;

        document.getElementById('articleModal').classList.add('active');
    } catch (error) {
        console.error('加载文章失败:', error);
    }
}

// 关闭模态框
function closeModal() {
    document.getElementById('articleModal').classList.remove('active');
}

// 搜索功能
let searchTimeout;
document.getElementById('searchInput').addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        const query = e.target.value.trim();
        if (!query) {
            loadArticles();
            return;
        }

        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            articles = await response.json();
            renderArticles();
        } catch (error) {
            console.error('搜索失败:', error);
        }
    }, 300);
});

// 格式化日期
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`;

    return date.toLocaleDateString('zh-CN');
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 点击模态框外部关闭
document.getElementById('articleModal').addEventListener('click', (e) => {
    if (e.target.id === 'articleModal') {
        closeModal();
    }
});

// ESC键关闭模态框
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal();
    }
});

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    loadArticles();
});