import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
import markdown
import jieba
import hashlib
from functools import wraps
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)

# 配置
# 数据库配置
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///data/knowledge_base.db')
USE_POSTGRES = DATABASE_URL.startswith('postgres')

# Flask配置
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# 生产环境配置
IS_PRODUCTION = os.environ.get('FLASK_ENV') == 'production'
if IS_PRODUCTION:
    app.config['DEBUG'] = False
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


def get_db():
    """获取数据库连接（支持SQLite和PostgreSQL）"""
    if USE_POSTGRES:
        # PostgreSQL连接
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        # SQLite连接
        os.makedirs('data', exist_ok=True)
        conn = sqlite3.connect('data/knowledge_base.db')
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    """初始化数据库"""
    conn = get_db()
    cursor = conn.cursor()

    # 创建用户表
    if USE_POSTGRES:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    # 创建默认用户（如果不存在）
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        default_username = 'admin'
        default_password = 'admin123'
        password_hash = hashlib.sha256(default_password.encode()).hexdigest()
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (default_username, password_hash))
        print(f"默认用户已创建，用户名: {default_username}, 密码: {default_password}")

    # 创建文章表
    if USE_POSTGRES:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    # 创建标签表
    if USE_POSTGRES:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')

    # 创建分类表
    if USE_POSTGRES:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')

    # 创建全文搜索虚拟表（仅SQLite）
    if not USE_POSTGRES:
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                title, content, content=articles, content_rowid=rowid
            )
        ''')

        # 创建全文搜索触发器
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
                INSERT INTO articles_fts(rowid, title, content)
                VALUES (new.id, new.title, new.content);
            END
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, content)
                VALUES('delete', old.id, old.title, old.content);
            END
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, content)
                VALUES('delete', old.id, old.title, old.content);
                INSERT INTO articles_fts(rowid, title, content)
                VALUES (new.id, new.title, new.content);
            END
        ''')

    conn.commit()
    conn.close()


# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# 路由
@app.route('/login')
def login():
    """登录页面"""
    if 'logged_in' in session:
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/register')
def register():
    """注册页面"""
    if 'logged_in' in session:
        return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/api/login', methods=['POST'])
def api_login():
    """登录API"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': '请输入用户名和密码'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({'error': '用户名或密码错误'}), 401

    password_hash = hashlib.sha256(password.encode()).hexdigest()

    if password_hash == user['password_hash']:
        session['logged_in'] = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        session.permanent = True
        return jsonify({'success': True, 'message': '登录成功'})
    else:
        return jsonify({'error': '用户名或密码错误'}), 401


@app.route('/api/register', methods=['POST'])
def api_register():
    """注册API"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': '请输入用户名和密码'}), 400

    if len(password) < 6:
        return jsonify({'error': '密码长度至少为6位'}), 400

    conn = get_db()
    cursor = conn.cursor()

    try:
        # 检查用户名是否已存在
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': '用户名已存在'}), 400

        # 创建新用户
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '注册成功'})
    except Exception as e:
        conn.close()
        return jsonify({'error': '注册失败，请重试'}), 500


@app.route('/api/logout', methods=['POST'])
def api_logout():
    """登出API"""
    session.clear()
    return jsonify({'success': True, 'message': '登出成功'})


@app.route('/')
@login_required
def index():
    """首页"""
    return render_template('index.html')


@app.route('/editor')
@login_required
def editor():
    """编辑器页面"""
    return render_template('editor.html')


@app.route('/api/articles', methods=['GET'])
@login_required
def get_articles():
    """获取所有文章列表"""
    conn = get_db()
    cursor = conn.cursor()

    category = request.args.get('category')
    tag = request.args.get('tag')

    if category:
        cursor.execute('SELECT * FROM articles WHERE category = ? ORDER BY updated_at DESC', (category,))
    elif tag:
        cursor.execute('SELECT * FROM articles WHERE tags LIKE ? ORDER BY updated_at DESC', (f'%{tag}%',))
    else:
        cursor.execute('SELECT * FROM articles ORDER BY updated_at DESC')

    articles = cursor.fetchall()
    conn.close()

    return jsonify([dict(article) for article in articles])


@app.route('/api/articles/<int:article_id>', methods=['GET'])
@login_required
def get_article(article_id):
    """获取单篇文章"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM articles WHERE id = ?', (article_id,))
    article = cursor.fetchone()
    conn.close()

    if article:
        return jsonify(dict(article))
    return jsonify({'error': 'Article not found'}), 404


@app.route('/api/articles', methods=['POST'])
@login_required
def create_article():
    """创建新文章"""
    data = request.json
    title = data.get('title', '')
    content = data.get('content', '')
    tags = data.get('tags', '')
    category = data.get('category', '')

    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO articles (title, content, tags, category)
        VALUES (?, ?, ?, ?)
    ''', (title, content, tags, category))
    article_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'id': article_id, 'message': 'Article created successfully'}), 201


@app.route('/api/articles/<int:article_id>', methods=['PUT'])
@login_required
def update_article(article_id):
    """更新文章"""
    data = request.json
    title = data.get('title', '')
    content = data.get('content', '')
    tags = data.get('tags', '')
    category = data.get('category', '')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE articles
        SET title = ?, content = ?, tags = ?, category = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (title, content, tags, category, article_id))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Article updated successfully'})


@app.route('/api/articles/<int:article_id>', methods=['DELETE'])
@login_required
def delete_article(article_id):
    """删除文章"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM articles WHERE id = ?', (article_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Article deleted successfully'})


@app.route('/api/search', methods=['GET'])
@login_required
def search_articles():
    """搜索文章"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    conn = get_db()
    cursor = conn.cursor()

    if USE_POSTGRES:
        # PostgreSQL使用ILIKE进行模糊搜索
        cursor.execute('''
            SELECT * FROM articles
            WHERE title ILIKE %s OR content ILIKE %s
            ORDER BY updated_at DESC
        ''', (f'%{query}%', f'%{query}%'))
    else:
        # SQLite使用全文搜索
        cursor.execute('''
            SELECT articles.* FROM articles
            JOIN articles_fts ON articles.id = articles_fts.rowid
            WHERE articles_fts MATCH ?
            ORDER BY articles.updated_at DESC
        ''', (query,))

    articles = cursor.fetchall()
    conn.close()

    return jsonify([dict(article) for article in articles])


@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    """获取所有分类"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM articles WHERE category IS NOT NULL AND category != ""')
    categories = cursor.fetchall()
    conn.close()

    return jsonify([cat['category'] for cat in categories])


@app.route('/api/tags', methods=['GET'])
@login_required
def get_tags():
    """获取所有标签"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT tags FROM articles WHERE tags IS NOT NULL AND tags != ""')
    articles = cursor.fetchall()
    conn.close()

    all_tags = set()
    for article in articles:
        tags = article['tags'].split(',')
        all_tags.update([tag.strip() for tag in tags if tag.strip()])

    return jsonify(list(all_tags))


@app.route('/api/preview', methods=['POST'])
@login_required
def preview_markdown():
    """预览Markdown"""
    data = request.json
    content = data.get('content', '')
    html = markdown.markdown(content, extensions=['extra', 'codehilite', 'tables'])
    return jsonify({'html': html})


@app.route('/api/export/<int:article_id>', methods=['GET'])
@login_required
def export_article(article_id):
    """导出文章"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM articles WHERE id = ?', (article_id,))
    article = cursor.fetchone()
    conn.close()

    if not article:
        return jsonify({'error': 'Article not found'}), 404

    article = dict(article)
    html = markdown.markdown(article['content'], extensions=['extra', 'codehilite', 'tables'])

    full_html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{article['title']}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto; padding: 40px 20px; line-height: 1.6; }}
            h1 {{ border-bottom: 1px solid #eee; padding-bottom: 0.3em; }}
            code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }}
            pre {{ background: #f5f5f5; padding: 16px; border-radius: 6px; overflow-x: auto; }}
            blockquote {{ border-left: 4px solid #ddd; padding-left: 16px; margin: 0; color: #666; }}
        </style>
    </head>
    <body>
        <h1>{article['title']}</h1>
        <p><strong>分类:</strong> {article['category'] or '未分类'} | <strong>标签:</strong> {article['tags'] or '无'}</p>
        <hr>
        {html}
    </body>
    </html>
    '''

    return full_html, 200, {'Content-Type': 'text/html; charset=utf-8'}


if __name__ == '__main__':
    # 确保数据目录存在（仅SQLite）
    if not USE_POSTGRES:
        os.makedirs('data', exist_ok=True)

    # 初始化数据库
    init_db()

    # 获取环境变量配置
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = not IS_PRODUCTION

    # 运行应用
    print("=" * 50)
    print("个人知识库服务器")
    print("=" * 50)
    print(f"数据库: {'PostgreSQL' if USE_POSTGRES else 'SQLite'}")
    print(f"环境: {'生产环境' if IS_PRODUCTION else '开发环境'}")
    print(f"地址: http://{host}:{port}")
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)

    app.run(host=host, port=port, debug=debug)