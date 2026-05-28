"""认证模块 — JWT + 登录/注册/会话（Flask Blueprint）"""
import threading
from datetime import datetime, timedelta
from functools import wraps

import bcrypt
import hashlib
import jwt
from flask import Blueprint, request, jsonify, g

from extensions import db
from models import User, SystemSetting, LoginLog

auth_bp = Blueprint('auth', __name__)


# ─── Helpers ─────────────────────────────────

def _get_client_ip():
    """获取客户端真实 IP，支持常见反代头"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    if request.headers.get('X-Real-IP'):
        return request.headers['X-Real-IP'].strip()
    return request.remote_addr or ''


def _is_private_ip(ip):
    """判断是否为私有/本地 IP，避免向 ipapi.co 发送无效请求"""
    if not ip:
        return True
    private_prefixes = (
        '127.', '::1', 'localhost',
        '10.',
        '192.168.',
        '169.254.',  # link-local
    )
    if ip.startswith(private_prefixes):
        return True
    # 172.16.0.0/12
    parts = ip.split('.')
    if len(parts) == 4 and parts[0] == '172':
        try:
            second = int(parts[1])
            if 16 <= second <= 31:
                return True
        except ValueError:
            pass
    return False


def _lookup_ip_region(ip):
    """查询 IP 归属地（ipapi.co，免费 1000次/天）"""
    if _is_private_ip(ip):
        return '内网'
    try:
        import urllib.request, json
        resp = urllib.request.urlopen(f'https://ipapi.co/{ip}/json/', timeout=3)
        data = json.loads(resp.read())
        if data.get('error'):
            return ''
        parts = [data.get(k, '') for k in ('country_name', 'region', 'city')]
        return ' '.join(p for p in parts if p) or ''
    except Exception:
        return ''


def _record_login(user):
    """异步记录用户登录日志（放后台线程，不阻塞登录响应）"""
    ip = _get_client_ip()
    ua = (request.headers.get('User-Agent') or '')[:300]

    def _bg():
        region = _lookup_ip_region(ip)
        try:
            from app import app as _app
            with _app.app_context():
                log = LoginLog(
                    user_id=user.id, username=user.username,
                    ip_address=ip, region=region, user_agent=ua,
                )
                db.session.add(log)
                db.session.commit()
        except Exception:
            pass

    threading.Thread(target=_bg, daemon=True).start()


def hash_password(password):
    """bcrypt 哈希密码（work factor=12）"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')


def verify_password(password, password_hash):
    """验证密码，兼容旧 SHA256 格式，登录成功后自动升级"""
    try:
        if password_hash.startswith('$2b$') or password_hash.startswith('$2a$'):
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        pass
    # 旧 SHA256 兼容：salt$hash
    try:
        if '$' in password_hash:
            salt, h = password_hash.split('$', 1)
            if hashlib.sha256((salt + password).encode()).hexdigest() == h:
                return True
    except Exception:
        pass
    return False


def is_legacy_hash(password_hash):
    """判断是否为旧 SHA256 哈希（需要升级）"""
    return bool(password_hash and '$' in password_hash and not password_hash.startswith('$2'))


def create_token(user, app):
    payload = {
        'user_id': user.id, 'username': user.username, 'role': user.role,
        'exp': datetime.utcnow() + timedelta(hours=app.config['JWT_EXPIRY_HOURS']),
    }
    return jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')


def get_current_user(app):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return None
    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
        user = db.session.get(User, data['user_id'])
        if user and user.is_active:
            return user
    except Exception:
        pass
    return None


def require_auth(fn):
    """验证当前用户已登录（直接读 g.current_user，避免重复解码 JWT）"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not getattr(g, 'current_user', None):
            return jsonify({'error': '请先登录'}), 401
        return fn(*args, **kwargs)
    return wrapper


def require_admin(fn):
    """验证当前用户为管理员（直接读 g.current_user，避免重复解码 JWT）"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': '请先登录'}), 401
        if user.role != 'admin':
            return jsonify({'error': '需要管理员权限'}), 403
        return fn(*args, **kwargs)
    return wrapper


def _is_registration_open():
    """检查注册是否开放（DB 优先，解决多 worker 不一致问题）"""
    s = SystemSetting.query.filter_by(key='registration_open').first()
    db_val = (s.value if s else '').strip().lower()
    if db_val in ('true', 'false'):
        return db_val == 'true'
    from flask import current_app
    return current_app.config.get('REGISTRATION_OPEN', True)


# ─── Routes ─────────────────────────────────

@auth_bp.route('/api/auth/registration-status', methods=['GET'])
def auth_registration_status():
    return jsonify({'registration_open': _is_registration_open()})


@auth_bp.route('/api/auth/register', methods=['POST'])
def auth_register():
    from flask import current_app
    if not _is_registration_open():
        return jsonify({'error': '暂不开放自主注册'}), 403
    data = request.get_json(silent=True) or {}
    if not data.get('username', '').strip() or not data.get('password', '').strip():
        return jsonify({'error': '用户名和密码不能为空'}), 400
    username = data['username'].strip()
    if len(username) < 2 or len(username) > 30:
        return jsonify({'error': '用户名需2-30位'}), 400
    import re
    if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fff]+$', username):
        return jsonify({'error': '用户名只能含字母、数字、下划线、中文'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已存在'}), 409
    user = User(
        username=username,
        password_hash=hash_password(data['password'].strip()),
        role='user', is_active=True,
        email=data.get('email', '').strip(),
    )
    db.session.add(user)
    db.session.commit()
    user.last_login = datetime.now()
    db.session.commit()
    _record_login(user)
    token = create_token(user, current_app)
    return jsonify({'token': token, 'user': user.to_dict()}), 201


@auth_bp.route('/api/auth/login', methods=['POST'])
def auth_login():
    from flask import current_app
    data = request.get_json(silent=True) or {}
    if not data.get('username', '').strip() or not data.get('password', '').strip():
        return jsonify({'error': '用户名和密码不能为空'}), 400
    user = User.query.filter_by(username=data['username'].strip()).first()
    if not user or not verify_password(data['password'].strip(), user.password_hash):
        return jsonify({'error': '用户名或密码错误'}), 401
    if not user.is_active:
        return jsonify({'error': '账号已被停用'}), 403
    # 自动升级旧 SHA256 哈希为 bcrypt
    if is_legacy_hash(user.password_hash):
        user.password_hash = hash_password(data['password'].strip())
    user.last_login = datetime.now()
    db.session.commit()
    _record_login(user)
    token = create_token(user, current_app)
    return jsonify({'token': token, 'user': user.to_dict()})


@auth_bp.route('/api/auth/profile', methods=['PUT'])
@require_auth
def update_profile():
    data = request.get_json(silent=True) or {}
    user = g.current_user
    changed = False

    if 'email' in data:
        user.email = (data['email'] or '').strip()
        changed = True

    new_pw = (data.get('new_password') or '').strip()
    if new_pw:
        current_pw = (data.get('current_password') or '').strip()
        if not verify_password(current_pw, user.password_hash):
            return jsonify({'error': '当前密码错误'}), 400
        if len(new_pw) < 8:
            return jsonify({'error': '新密码至少8位'}), 400
        user.password_hash = hash_password(new_pw)
        changed = True

    if changed:
        db.session.commit()
        return jsonify({'user': user.to_dict(), 'message': '个人信息已更新'})
    return jsonify({'error': '没有需要修改的内容'}), 400


@auth_bp.route('/api/session', methods=['GET'])
@require_auth
def session_info():
    from flask import current_app
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    new_token = None
    try:
        data = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])
        remaining = data['exp'] - int(datetime.utcnow().timestamp())
        if remaining < 86400:
            new_token = create_token(g.current_user, current_app)
    except Exception:
        pass
    resp = jsonify({
        'user': g.current_user.to_dict(),
        'registration_open': _is_registration_open(),
    })
    if new_token:
        resp.headers['X-New-Token'] = new_token
    return resp
