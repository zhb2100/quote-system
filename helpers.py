"""共享辅助函数 — 从 app.py 提取，消除循环依赖"""
from datetime import datetime
from flask import g, jsonify
from extensions import db
from models import Quote, FieldSetting, SystemSetting, User, Salesperson


def get_setting(key, default=''):
    """读取单个系统设置"""
    s = SystemSetting.query.filter_by(key=key).first()
    return s.value if s else default


def get_all_settings():
    """读取所有系统设置 (返回dict)"""
    return {s.key: s.value for s in SystemSetting.query.all()}


_field_cache = None
_field_cache_time = None


def get_field_visibility():
    global _field_cache, _field_cache_time
    now = datetime.now()
    if _field_cache and _field_cache_time and (now - _field_cache_time).seconds < 300:
        return _field_cache
    _field_cache = {f.field_name: f.user_visible for f in FieldSetting.query.all()}
    _field_cache_time = now
    return _field_cache


def check_quote_owner(quote_id):
    """管理员可看全部，业务员可看指派给自己的，其他人不能看。返回 (quote_or_error, status_code)."""
    quote = db.session.get(Quote, quote_id)
    if not quote:
        return None, jsonify({'error': '报价单不存在'}), 404
    if g.current_user.role == 'admin':
        return quote, None, None
    # 非管理员：能否看取决于是否被指派为业务员
    sp = Salesperson.query.filter_by(user_id=g.current_user.id).first()
    if sp and quote.salesperson_id == sp.id:
        return quote, None, None
    return None, jsonify({'error': '无权操作此报价单'}), 403
