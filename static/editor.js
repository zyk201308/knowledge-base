let articleId = null;

// 初始化编辑器
document.addEventListener('DOMContentLoaded', () => {
    // 检查是否是编辑模式
    const urlParams = new URLSearchParams(window.location.search);
    articleId = urlParams.get('id');

    if (articleId) {
        loadArticle(articleId);
    }

    // 实时预览
    document.getElementById('contentInput').addEventListener('input', updatePreview);
});

// 加载文章
async function loadArticle(id) {
    try {
        const response = await fetch(`/api/articles/${id}`);
        const article = await response.json();

        document.getElementById('titleInput').value = article.title;
        document.getElementById('contentInput').value = article.content;
        document.getElementById('categoryInput').value = article.category || '';
        document.getElementById('tagsInput').value = article.tags || '';

        updatePreview();
    } catch (error) {
        console.error('加载文章失败:', error);
        alert('加载文章失败');
    }
}

// 更新预览
function updatePreview() {
    const content = document.getElementById('contentInput').value;
    const html = marked.parse(content);
    document.getElementById('previewContent').innerHTML = html;
}

// 保存文章
async function saveArticle() {
    const title = document.getElementById('titleInput').value.trim();
    const content = document.getElementById('contentInput').value.trim();
    const category = document.getElementById('categoryInput').value.trim();
    const tags = document.getElementById('tagsInput').value.trim();

    if (!title || !content) {
        alert('标题和内容不能为空');
        return;
    }

    const data = {
        title,
        content,
        category,
        tags
    };

    try {
        let url = '/api/articles';
        let method = 'POST';

        if (articleId) {
            url = `/api/articles/${articleId}`;
            method = 'PUT';
        }

        const response = await fetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            alert(articleId ? '文章更新成功' : '文章创建成功');
            window.location.href = '/';
        } else {
            alert('保存失败: ' + result.error);
        }
    } catch (error) {
        console.error('保存失败:', error);
        alert('保存失败');
    }
}

// 插入文本到编辑器
function insertText(before, after) {
    const textarea = document.getElementById('contentInput');
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const selectedText = text.substring(start, end);

    const newText = text.substring(0, start) + before + selectedText + after + text.substring(end);

    textarea.value = newText;
    textarea.focus();
    textarea.setSelectionRange(start + before.length, start + before.length + selectedText.length);

    updatePreview();
}