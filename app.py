#!/usr/bin/env python3
"""
报价管理系统 - Quote Management System
Flask + SQLite + REST API + Web UI
"""

import os
import secrets
import time as _req_time
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, request, jsonify, send_file, send_from_directory, g
from flask_cors import CORS
from sqlalchemy import text, inspect as sa_inspect
import jwt

from extensions import db
from models import Quote, User, SystemSetting
from auth import (
    auth_bp, hash_password, verify_password, create_token,
    require_auth, require_admin, _is_registration_open,
)
from helpers import get_all_settings
from utils import _debug_log

# ─── 蓝图导入 ────────────────────────────────────────────────
from quotes_bp import quotes_bp
from admin_bp import admin_bp
from salespersons_bp import salespersons_bp
from suppliers_bp import suppliers_bp

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / 'uploads'
EXPORT_DIR = BASE_DIR / 'exports'

app = Flask(__name__)

# CORS
_cors_origins = os.environ.get('QUOTE_CORS_ORIGINS', '').strip()
cors_kwargs = {}
if _cors_origins:
    cors_kwargs['origins'] = [o.strip() for o in _cors_origins.split(',') if o.strip()]
else:
    cors_kwargs['origins'] = [
        'https://bwh.ddns.mobi',
        'http://localhost:5173',
    ]
CORS(app, **cors_kwargs)

# ─── 蓝图注册 ────────────────────────────────────────────────
for _bp in (auth_bp, quotes_bp, admin_bp, salespersons_bp, suppliers_bp):
    app.register_blueprint(_bp)

UPLOAD_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{BASE_DIR}/quote.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['JWT_EXPIRY_HOURS'] = 72
app.config['REGISTRATION_OPEN'] = os.environ.get('QUOTE_REGISTRATION', 'true').lower() == 'true'

# JWT Secret（文件持久化，保证多 worker 共享）
app.config['JWT_SECRET'] = os.environ.get('QUOTE_JWT_SECRET', '')
if not app.config['JWT_SECRET']:
    _secret_file = BASE_DIR / '.jwt_secret'
    if _secret_file.exists():
        app.config['JWT_SECRET'] = _secret_file.read_text().strip()
    if not app.config['JWT_SECRET']:
        app.config['JWT_SECRET'] = secrets.token_hex(32)
        _secret_file.write_text(app.config['JWT_SECRET'])
        _secret_file.chmod(0o600)

app.config['DEFAULT_ADMIN_PASSWORD'] = os.environ.get('QUOTE_ADMIN_PASSWORD', '')

db.init_app(app)

# ─── 公开路由（不需要认证） ────────────────────────────────────
PUBLIC_ROUTES = {
    'auth.auth_login', 'auth.auth_register', 'auth.auth_registration_status',
    'get_version', 'health_check', 'index',
}

# ─── 全局错误处理 ─────────────────────────────────────────────
@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(409)
@app.errorhandler(413)
@app.errorhandler(422)
@app.errorhandler(500)
def _handle_error(e):
    return jsonify({'error': e.description if hasattr(e, 'description') else str(e)}), \
           e.code if hasattr(e, 'code') else 500


# ─── 请求时间 & 日志中间件 ────────────────────────────────────
@app.before_request
def _mark_req_start():
    g._req_start = _req_time.time()


@app.after_request
def _log_request(response):
    if request.path.startswith('/api/') and not request.path.startswith('/api/assets'):
        elapsed = int((_req_time.time() - g.get('_req_start', _req_time.time())) * 1000)
        user = getattr(g, 'current_user', None)
        username = user.username if user else '-'
        if response.status_code >= 400 or elapsed > 3000:
            _debug_log(f'{request.method} {request.path} {response.status_code} {elapsed}ms user={username}')
    return response


# ─── 全局认证中间件 ───────────────────────────────────────────
@app.before_request
def check_auth():
    if request.method == 'OPTIONS':
        return None
    if not request.path.startswith('/api/') and not request.path.startswith('/uploads/'):
        return None
    endpoint = request.endpoint
    if endpoint in PUBLIC_ROUTES or (endpoint and endpoint.startswith('static')):
        return None
    token = request.headers.get('Authorization', '').replace('Bearer ', '') \
            or request.args.get('token', '')
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


# ─── 系统 API ─────────────────────────────────────────────────
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
    """健康检查 — 验证 DB 连通性"""
    try:
        db.session.execute(text('SELECT 1'))
        db_ok = True
    except Exception:
        db_ok = False
    status = 200 if db_ok else 503
    return jsonify({'status': 'ok' if db_ok else 'db_error', 'db': db_ok}), status


# ─── 静态文件 ─────────────────────────────────────────────────
_dist_dir = os.path.join(os.path.dirname(__file__), 'frontend', 'dist')
_has_vue_build = os.path.isdir(_dist_dir)


@app.route('/')
def index():
    if _has_vue_build:
        return send_file(os.path.join(_dist_dir, 'index.html'))
    return 'Frontend not built', 404


@app.route('/assets/<path:filename>')
@app.route('/quote/assets/<path:filename>')
def vue_assets(filename):
    if _has_vue_build:
        return send_from_directory(os.path.join(_dist_dir, 'assets'), filename)
    return 'Not Found', 404


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route('/<path:path>')
def spa_catch_all(path):
    # 未知 /api/ 路径返回 404 JSON，不走 SPA
    if path.startswith('api/'):
        return jsonify({'error': 'Not Found'}), 404
    if _has_vue_build:
        return send_file(os.path.join(_dist_dir, 'index.html'))
    return 'Frontend not built', 404


# ─── 数据库初始化 ─────────────────────────────────────────────

def _configure_sqlite():
    """启用 WAL 模式，提高并发读写性能"""
    try:
        db.session.execute(text('PRAGMA journal_mode=WAL'))
        db.session.execute(text('PRAGMA busy_timeout=5000'))
        db.session.commit()
    except Exception:
        pass


def _run_schema_migrations():
    """自动迁移：检测缺失列并 ALTER TABLE（SQLAlchemy 方式）"""
    columns_to_add = [
        ('quotes', 'remark', 'TEXT'),
    ]
    inspector = sa_inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    for tbl, col, col_type in columns_to_add:
        if tbl in existing_tables:
            existing_cols = {c['name'] for c in inspector.get_columns(tbl)}
            if col not in existing_cols:
                try:
                    db.session.execute(text(f'ALTER TABLE {tbl} ADD COLUMN {col} {col_type}'))
                    db.session.commit()
                    print(f'[Migrate] 已添加 {tbl}.{col}')
                except Exception as e:
                    print(f'[Migrate] 添加 {tbl}.{col} 失败: {e}')


def _run_data_migrations():
    """迁移历史数据（旧英文状态 → 新中文状态，孤儿报价单归属）"""
    valid_statuses = {'项目报价中', '项目已报价未付款', '项目生产中', '项目完结', '项目返工', '项目终止'}
    try:
        old_statuses = [
            r[0] for r in db.session.query(Quote.status).distinct().all()
            if r[0] and r[0] not in valid_statuses
        ]
        for old in old_statuses:
            db.session.query(Quote).filter(Quote.status == old).update(
                {'status': '项目报价中'}, synchronize_session=False)
            print(f'[Migrate] 报价单状态 "{old}" → "项目报价中"')
        if old_statuses:
            db.session.commit()
    except Exception as e:
        print(f'[Migrate] 状态迁移跳过: {e}')

    # 孤儿报价单（created_by 为空）归属给 admin
    try:
        orphans = Quote.query.filter(Quote.created_by.is_(None)).all()
        if orphans:
            admin_user = User.query.filter_by(username='admin').first()
            if admin_user:
                for q in orphans:
                    q.created_by = admin_user.id
                db.session.commit()
                print(f'[Init] 已为 {len(orphans)} 条孤儿报价单分配创建者: admin')
    except Exception:
        pass


def _seed_defaults():
    """预置管理员账号和默认系统设置"""
    # 管理员账号
    if not User.query.filter_by(username='admin').first():
        _admin_pwd = app.config['DEFAULT_ADMIN_PASSWORD']
        if not _admin_pwd:
            # 生成真正的随机密码
            _admin_pwd = secrets.token_urlsafe(16)
            _pwd_file = BASE_DIR / '.admin_password'
            _pwd_file.write_text(_admin_pwd)
            _pwd_file.chmod(0o600)
            print(f'[Init] 随机管理员密码已写入 {_pwd_file}（请妥善保管）')
        admin = User(
            username='admin',
            password_hash=hash_password(_admin_pwd),
            role='admin', is_active=True,
        )
        db.session.add(admin)
        db.session.commit()
        print('[Init] 已创建管理员: admin')

    # 默认系统设置
    defaults = {'company_name': '', 'footer_text': ''}
    for k, v in defaults.items():
        if not SystemSetting.query.filter_by(key=k).first():
            db.session.add(SystemSetting(key=k, value=v))
    db.session.commit()


# ─── 启动时执行 ───────────────────────────────────────────────
with app.app_context():
    db.create_all()
    _configure_sqlite()
    _run_schema_migrations()
    _run_data_migrations()
    _seed_defaults()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
