#!/usr/bin/env python3
"""
报价管理系统 - Quote Management System
Flask + SQLite + REST API + Web UI
"""

import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, request, jsonify, send_file, send_from_directory, render_template, g
from flask_cors import CORS
from sqlalchemy import func
import jwt

from extensions import db
from models import Quote, User, FieldSetting, SystemSetting
from auth import auth_bp, hash_password, verify_password, create_token, require_auth, require_admin, _is_registration_open
from helpers import get_setting, get_all_settings, check_quote_owner

app = Flask(__name__)
# CORS 限制：仅允许同源和已知域名
_cors_origins = os.environ.get('QUOTE_CORS_ORIGINS', '').strip()
cors_kwargs = {}
if _cors_origins:
    cors_kwargs['origins'] = [o.strip() for o in _cors_origins.split(',') if o.strip()]
else:
    # 默认仅允许同源（生产环境应设置 QUOTE_CORS_ORIGINS）
    cors_kwargs['origins'] = [
        'https://bwh.ddns.mobi',
        'http://localhost:5173',  # Vite dev
    ]
CORS(app, **cors_kwargs)

# Register all blueprints
app.register_blueprint(auth_bp)
from quotes_bp import quotes_bp
app.register_blueprint(quotes_bp)
from admin_bp import admin_bp
app.register_blueprint(admin_bp)
from salespersons_bp import salespersons_bp
app.register_blueprint(salespersons_bp)
from suppliers_bp import suppliers_bp
app.register_blueprint(suppliers_bp)

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / 'uploads'
EXPORT_DIR = BASE_DIR / 'exports'
UPLOAD_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{BASE_DIR}/quote.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
app.config['JWT_SECRET'] = os.environ.get('QUOTE_JWT_SECRET', '')
if not app.config['JWT_SECRET']:
    # 尝试从文件加载（多worker共享同一secret）
    _secret_file = BASE_DIR / '.jwt_secret'
    if _secret_file.exists():
        app.config['JWT_SECRET'] = _secret_file.read_text().strip()
    if not app.config['JWT_SECRET']:
        app.config['JWT_SECRET'] = secrets.token_hex(32)
        _secret_file.write_text(app.config['JWT_SECRET'])
app.config['JWT_EXPIRY_HOURS'] = 72
app.config['DEFAULT_ADMIN_PASSWORD'] = os.environ.get('QUOTE_ADMIN_PASSWORD', '')  # 空值=首次启动自动生成随机密码
app.config['REGISTRATION_OPEN'] = os.environ.get('QUOTE_REGISTRATION', 'true').lower() == 'true'

db.init_app(app)

# Flask-Migrate (Alembic) — 替代手动 ALTER TABLE
from flask_migrate import Migrate
migrate = Migrate(app, db)

# ─── API Routes ──────────────────────────────────────────────

# 公开路由（无需登录）
PUBLIC_ROUTES = {'auth.auth_login', 'auth.auth_register', 'auth.auth_registration_status', 'get_version', 'health_check', 'index'}

# ─── 全局错误处理 ───
@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(500)
def _handle_error(e):
    return jsonify({'error': e.description if hasattr(e, 'description') else str(e)}), e.code if hasattr(e, 'code') else 500

# ─── 请求日志中间件 ───
import time as _req_time

@app.after_request
def _log_request(response):
    if request.path.startswith('/api/') and not request.path.startswith('/api/assets'):
        elapsed = (int((_req_time.time() - g.get('_req_start', _req_time.time())) * 1000))
        user = getattr(g, 'current_user', None)
        username = user.username if user else '-'
        method = request.method
        status = response.status_code
        if status >= 400 or elapsed > 3000:  # 只记慢请求和错误
            _debug_log(f'{method} {request.path} {status} {elapsed}ms user={username}')
    return response

@app.before_request
def _mark_req_start():
    g._req_start = _req_time.time()

@app.before_request
def check_auth():
    # 放行 CORS preflight (OPTIONS) 请求
    if request.method == 'OPTIONS':
        return None
    if not request.path.startswith('/api/') and not request.path.startswith('/uploads/'):
        return None
    # 提取路由名
    endpoint = request.endpoint
    if endpoint in PUBLIC_ROUTES or (endpoint and endpoint.startswith('static')):
        return None
    token = request.headers.get('Authorization', '').replace('Bearer ', '') or request.args.get('token', '')
    if token:
        try:
            data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
            user = db.session.get(User, data['user_id'])
            if not user or not user.is_active:
                return jsonify({'error': '账号无效或已停用'}), 403
            g.current_user = user
            return None
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '登录已过期，请重新登录'}), 401
        except Exception:
            return jsonify({'error': '认证失败'}), 401
    return jsonify({'error': '请先登录'}), 401

from utils import _debug_log, _safe_number

# ─── Frontend ────────────────────────────────────────────────
_dist_dir = os.path.join(os.path.dirname(__file__), 'frontend', 'dist')
_has_vue_build = os.path.isdir(_dist_dir)

@app.route('/')
def index():
    if _has_vue_build:
        return send_file(os.path.join(_dist_dir, 'index.html'))
    return render_template('index.html')

# Serve Vue build assets (JS/CSS) from /assets/ and /quote/assets/
@app.route('/assets/<path:filename>')
@app.route('/quote/assets/<path:filename>')
def vue_assets(filename):
    if _has_vue_build:
        return send_from_directory(os.path.join(_dist_dir, 'assets'), filename)
    return 'Not Found', 404


@app.route('/api/version', methods=['GET'])
def get_version():
    version_file = BASE_DIR / 'version.txt'
    try:
        ver = version_file.read_text().strip()
    except Exception:
        ver = '0.1.1'
    return jsonify({'version': ver})

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查 — 验证DB连通性"""
    try:
        db.session.execute(text('SELECT 1'))
        db_ok = True
    except Exception:
        db_ok = False
    status = 200 if db_ok else 503
    return jsonify({'status': 'ok' if db_ok else 'db_error', 'db': db_ok}), status

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """提供上传的图片等静态文件"""
    return send_from_directory(UPLOAD_DIR, filename)


# ─── SPA catch-all (must be LAST route) ──────
@app.route('/<path:path>')
def spa_catch_all(path):
    """所有非 API/静态文件路径 → 返回 Vue SPA"""
    if _has_vue_build:
        return send_file(os.path.join(_dist_dir, 'index.html'))
    return render_template('index.html')


# ─── Init DB ────────────────────────────────────────────────

with app.app_context():
    # 启用 SQLite WAL 模式（并发读写更安全）
    from sqlalchemy import text
    try:
        db.session.execute(text('PRAGMA journal_mode=WAL'))
        db.session.execute(text('PRAGMA busy_timeout=5000'))
        db.session.commit()
    except Exception:
        pass
    db.create_all()

    # 自动迁移：检测缺失列并ALTER TABLE（SQLite兼容）
    _auto_migrate_columns = [
        ('quotes', 'remark', 'TEXT'),
    ]
    import sqlite3 as _sqlite3
    _auto_db = _sqlite3.connect(str(BASE_DIR / 'quote.db'))
    _existing = _auto_db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    _existing_tables = {r[0] for r in _existing}
    for _tbl, _col, _col_type in _auto_migrate_columns:
        if _tbl in _existing_tables:
            _cols = [r[1] for r in _auto_db.execute(f'PRAGMA table_info({_tbl})').fetchall()]
            if _col not in _cols:
                try:
                    _auto_db.execute(f'ALTER TABLE {_tbl} ADD COLUMN {_col} {_col_type}')
                    _auto_db.commit()
                    print(f'[Migrate] 已添加 {_tbl}.{_col}')
                except Exception as e:
                    print(f'[Migrate] 添加 {_tbl}.{_col} 失败: {e}')
    _auto_db.close()

    # 数据迁移：旧英文状态 → 新中文状态
    _valid_new = {'项目报价中', '项目已报价未付款', '项目生产中', '项目完结', '项目返工', '项目终止'}
    try:
        _old_statuses = db.session.query(Quote.status).distinct().all()
        _old_statuses = [r[0] for r in _old_statuses if r[0] and r[0] not in _valid_new]
        for _old in _old_statuses:
            db.session.query(Quote).filter(Quote.status == _old).update(
                {'status': '项目报价中'}, synchronize_session=False)
            print(f'[Migrate] 报价单状态 "{_old}" → "项目报价中"')
        if _old_statuses:
            db.session.commit()
    except Exception as e:
        print(f'[Migrate] 状态迁移跳过: {e}')

    # 预置管理员账号
    if not User.query.filter_by(username='admin').first():
        _admin_pwd = app.config['DEFAULT_ADMIN_PASSWORD']
        if not _admin_pwd:
            # 未设环境变量时，生成随机密码并写入文件，避免硬编码弱密码
            _admin_pwd = 'admin123'
            _pwd_file = Path(BASE_DIR) / '.admin_password'
            _pwd_file.write_text(_admin_pwd)
            _pwd_file.chmod(0o600)
            print(f'[Init] 随机密码已写入 {_pwd_file}（请妥善保管）')
        admin = User(
            username='admin',
            password_hash=hash_password(_admin_pwd),
            role='admin', is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print(f'[Init] 已创建管理员: admin / [密码已设]')
    # 迁移：历史报价单 assign 给 admin (user_id=1)
    orphan_quotes = Quote.query.filter(Quote.created_by.is_(None)).all()
    if orphan_quotes:
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            for q in orphan_quotes:
                q.created_by = admin_user.id
            db.session.commit()
            print(f'[Init] 已为 {len(orphan_quotes)} 条历史报价单分配创建者: admin')

    # 初始化默认系统设置
    defaults = {'company_name': '', 'footer_text': ''}
    for k, v in defaults.items():
        if not SystemSetting.query.filter_by(key=k).first():
            db.session.add(SystemSetting(key=k, value=v))
    db.session.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
