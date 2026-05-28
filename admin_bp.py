"""
Admin Blueprint — 管理后台 API 路由
"""
from flask import Blueprint, request, jsonify, g, current_app

from extensions import db
from models import User, SystemSetting, LoginLog
from auth import require_admin, hash_password, _is_registration_open
from helpers import get_all_settings, upsert_setting, get_pagination_args

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# 允许通过 API 写入的设置键白名单
ALLOWED_SETTING_KEYS = {'company_name', 'footer_text', 'registration_open'}

# ─── Registration ────────────────────────────────────────────

@admin_bp.route('/registration', methods=['GET'])
@require_admin
def get_registration():
    return jsonify({'registration_open': _is_registration_open()})


@admin_bp.route('/registration', methods=['PUT'])
@require_admin
def set_registration():
    data = request.get_json(silent=True) or {}
    if 'registration_open' in data:
        open_val = str(data['registration_open']).lower() == 'true'
        upsert_setting('registration_open', str(open_val).lower())
        db.session.commit()
        current_app.config['REGISTRATION_OPEN'] = open_val
    return jsonify({'registration_open': _is_registration_open()})


@admin_bp.route('/settings', methods=['GET'])
@require_admin
def get_settings():
    return jsonify({'settings': get_all_settings()})


@admin_bp.route('/settings', methods=['PUT'])
@require_admin
def update_settings():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({'error': '数据为空'}), 400
    for key, value in data.items():
        if key not in ALLOWED_SETTING_KEYS:
            continue
        if isinstance(value, bool):
            value = str(value).lower()
        else:
            value = str(value) if value is not None else ''
        upsert_setting(key, value)
    db.session.commit()
    return jsonify({'settings': get_all_settings()})


# ─── 用户管理 ────────────────────────────────────────────────

@admin_bp.route('/users', methods=['GET'])
@require_admin
def list_users():
    page, per_page = get_pagination_args()
    search = request.args.get('search', '').strip()
    query = User.query
    if search:
        query = query.filter(
            db.or_(User.username.contains(search), User.email.contains(search))
        )
    query = query.order_by(User.created_at.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'users': [u.to_dict() for u in paginated.items],
        'total': paginated.total,
        'page': page,
        'pages': paginated.pages,
    })


@admin_bp.route('/users/options', methods=['GET'])
@require_admin
def list_users_options():
    """管理员用：获取所有用户列表用于下拉选择（从 quotes_bp 移入）"""
    users = User.query.order_by(User.username).all()
    return jsonify({'users': [{'id': u.id, 'username': u.username} for u in users]})


@admin_bp.route('/users', methods=['POST'])
@require_admin
def create_user():
    data = request.get_json(silent=True) or {}
    if not data.get('username', '').strip() or not data.get('password', '').strip():
        return jsonify({'error': '用户名和密码不能为空'}), 400
    username = data['username'].strip()
    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已存在'}), 409
    user = User(
        username=username,
        password_hash=hash_password(data['password'].strip()),
        role=data.get('role', 'user'),
        is_active=True,
        email=data.get('email', '').strip(),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'user': user.to_dict()}), 201


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_admin
def update_user(user_id):
    if user_id == g.current_user.id:
        return jsonify({'error': '不能修改自己的状态'}), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    data = request.get_json(silent=True) or {}
    if user_id == 1 and 'role' in data and data['role'] != 'admin':
        return jsonify({'error': '主管理员不能被降级'}), 403
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
    if 'role' in data and data['role'] in ('admin', 'user'):
        user.role = data['role']
    db.session.commit()
    return jsonify({'user': user.to_dict()})


@admin_bp.route('/users/<int:user_id>/password', methods=['PUT'])
@require_admin
def reset_user_password(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    data = request.get_json(silent=True) or {}
    new_pw = (data.get('password') or '').strip()
    if len(new_pw) < 8:
        return jsonify({'error': '密码至少8位'}), 400
    user.password_hash = hash_password(new_pw)
    db.session.commit()
    return jsonify({'success': True, 'username': user.username})


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    if user_id == g.current_user.id:
        return jsonify({'error': '不能删除自己'}), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    if user.role == 'admin':
        return jsonify({'error': '不能删除管理员'}), 403
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': f'用户 {user.username} 已删除'})


# ─── 登录记录 ───────────────────────────────────────────────

@admin_bp.route('/login-logs', methods=['GET'])
@require_admin
def login_logs():
    page, per_page = get_pagination_args()
    user_id = request.args.get('user_id', type=int)
    query = LoginLog.query.order_by(LoginLog.created_at.desc())
    if user_id:
        query = query.filter(LoginLog.user_id == user_id)
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'logs': [log.to_dict() for log in paginated.items],
        'total': paginated.total,
        'page': page,
        'pages': paginated.pages,
    })
