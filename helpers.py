"""共享辅助函数 — 工具函数/查询封装/权限检查"""
from flask import g, jsonify, request
from extensions import db
from models import Quote, SystemSetting, User, Salesperson


# ─── 系统设置 ────────────────────────────────────────────────

def get_setting(key, default=''):
    """读取单个系统设置"""
    s = SystemSetting.query.filter_by(key=key).first()
    return s.value if s else default


def get_all_settings():
    """读取所有系统设置 (返回dict)"""
    return {s.key: s.value for s in SystemSetting.query.all()}


def upsert_setting(key, value):
    """插入或更新单个系统设置"""
    s = SystemSetting.query.filter_by(key=key).first()
    if s:
        s.value = value
    else:
        db.session.add(SystemSetting(key=key, value=value))


# ─── 请求参数 ────────────────────────────────────────────────

def get_pagination_args(default_per_page=20, max_per_page=200):
    """从请求参数中解析分页参数，返回 (page, per_page)"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', default_per_page, type=int), max_per_page)
    return page, per_page


# ─── 权限/作用域 ─────────────────────────────────────────────

def check_quote_owner(quote_id):
    """检查当前用户是否有权访问指定报价单。
    返回 3 元组：(quote, error_response_or_None, status_code_or_None)
      成功: (quote_obj, None, None)
      失败: (None, jsonify({error}), http_status_code)
    """
    quote = db.session.get(Quote, quote_id)
    if not quote:
        return None, jsonify({'error': '报价单不存在'}), 404
    if g.current_user.role == 'admin':
        return quote, None, None
    sp = Salesperson.query.filter_by(user_id=g.current_user.id).first()
    if sp and quote.salesperson_id == sp.id:
        return quote, None, None
    return None, jsonify({'error': '无权操作此报价单'}), 403


def apply_salesperson_scope(query, empty_json=None):
    """对 Quote 查询应用当前非管理员用户的业务员范围过滤。
    返回 (filtered_query, early_response_or_None)
      管理员: (query, None) — 不过滤
      业务员: (query.filter(...), None)
      无归属: (query, early_response) — 应立刻 return early_response
    """
    user = g.current_user
    if user.role == 'admin':
        return query, None
    sp = Salesperson.query.filter_by(user_id=user.id).first()
    if sp:
        return query.filter(Quote.salesperson_id == sp.id), None
    # 没有对应业务员，返回空结果
    if empty_json is None:
        empty_json = jsonify({'quotes': [], 'total': 0})
    return query, empty_json
