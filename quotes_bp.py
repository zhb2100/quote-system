"""
Quotes Blueprint — 报价单相关 API 路由
"""
import re
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, g
from sqlalchemy import func

from extensions import db
from models import Quote, User, Supplier, Salesperson, StatusLog, QuoteEvent
from auth import require_auth, require_admin
from helpers import check_quote_owner, apply_salesperson_scope, get_pagination_args

quotes_bp = Blueprint('quotes', __name__)


# ─── 状态机 ──────────────────────────────────────────────

STATUS_MACHINE = {
    '项目报价中':        ['项目已报价未付款'],
    '项目已报价未付款':  ['项目生产中'],
    '项目生产中':        ['项目完结'],
    '项目完结':          ['项目返工'],
    '项目返工':          ['项目完结'],
    '项目终止':          ['项目报价中'],
}


# ─── Quotes List ──────────────────────────────────────────

@quotes_bp.route('/api/quotes', methods=['GET'])
@require_auth
def list_quotes():
    page, per_page = get_pagination_args()
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()
    month_filter = request.args.get('month', '').strip()
    salesperson_id = request.args.get('salesperson_id', type=int)
    supplier_id = request.args.get('supplier_id', type=int)
    event_direction = request.args.get('event_direction', '').strip()
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'desc')

    sort_cols = {
        'id': Quote.id, 'title': Quote.title, 'status': Quote.status,
        'order_start': Quote.order_start, 'order_end': Quote.order_end,
        'created_at': Quote.created_at,
    }
    order_col = sort_cols.get(sort_by, Quote.id)
    order_fn = order_col.asc if sort_order == 'asc' else order_col.desc

    query = Quote.query
    query, early = apply_salesperson_scope(
        query,
        empty_json=jsonify({'quotes': [], 'total': 0, 'page': page, 'per_page': per_page}),
    )
    if early:
        return early

    if status_filter:
        query = query.filter(Quote.status == status_filter)
    if month_filter:
        query = query.filter(func.strftime('%Y-%m', Quote.created_at) == month_filter)
    if salesperson_id:
        query = query.filter(Quote.salesperson_id == salesperson_id)
    if supplier_id:
        query = query.filter(Quote.supplier_id == supplier_id)
    if event_direction:
        latest_event_id = (
            db.session.query(func.max(QuoteEvent.id))
            .filter(QuoteEvent.quote_id == Quote.id)
            .correlate(Quote)
            .as_scalar()
        )
        query = query.filter(
            db.session.query(QuoteEvent)
            .filter(QuoteEvent.id == latest_event_id, QuoteEvent.direction == event_direction)
            .exists()
        )

    # 拼音搜索（Python 端过滤，仅在非中文关键词时启用）
    is_pinyin = search and not re.search(r'[\u4e00-\u9fff]', search)
    if is_pinyin:
        from pypinyin import pinyin, Style
        q_lower = search.lower().strip()
        all_quotes = query.order_by(order_fn()).all()

        def pinyin_match(q):
            text = q.title or ''
            if not text:
                return False
            py_list = pinyin(text, style=Style.NORMAL, heteronym=False)
            full_py = ''.join(p[0] for p in py_list).lower()
            if q_lower in full_py:
                return True
            initials = ''.join(p[0][0] for p in py_list).lower()
            return q_lower in initials

        filtered = [q for q in all_quotes if pinyin_match(q)]
        total = len(filtered)
        quotes = filtered[(page - 1) * per_page: page * per_page]
    else:
        query = query.order_by(order_fn())
        if search:
            query = query.filter(Quote.title.ilike(f'%{search}%'))
        total = query.count()
        quotes = query.offset((page - 1) * per_page).limit(per_page).all()

    # 批量加载关联名称，避免 N+1
    creator_ids = list({q.created_by for q in quotes if q.created_by})
    users_map = {}
    if creator_ids:
        users_map = {u.id: u.username for u in User.query.filter(User.id.in_(creator_ids)).all()}

    supplier_ids = list({q.supplier_id for q in quotes if q.supplier_id})
    suppliers_map = {}
    if supplier_ids:
        suppliers_map = {s.id: s.name for s in Supplier.query.filter(Supplier.id.in_(supplier_ids)).all()}

    sp_ids = list({q.salesperson_id for q in quotes if q.salesperson_id})
    salespersons_map = {}
    if sp_ids:
        salespersons_map = {sp.id: sp.name for sp in Salesperson.query.filter(Salesperson.id.in_(sp_ids)).all()}

    return jsonify({
        'quotes': [q.to_dict(users_map=users_map, suppliers_map=suppliers_map, salespersons_map=salespersons_map) for q in quotes],
        'total': total,
        'page': page,
        'per_page': per_page,
    })


@quotes_bp.route('/api/quotes/stats', methods=['GET'])
@require_auth
def quote_stats():
    user_id = request.args.get('user_id', type=int)
    month = request.args.get('month', '').strip()
    year = request.args.get('year', '').strip()
    status = request.args.get('status', '').strip()

    base = Quote.query
    base, early = apply_salesperson_scope(
        base,
        empty_json=jsonify({'filter_users': [], 'total': 0, 'status_counts': {}}),
    )
    if early:
        return early

    if g.current_user.role == 'admin' and user_id:
        base = base.filter(Quote.created_by == user_id)

    if month:
        base = base.filter(func.strftime('%Y-%m', Quote.created_at) == month)
    elif year:
        base = base.filter(func.strftime('%Y', Quote.created_at) == year)

    # status_counts 基于完整过滤（不含 status 过滤），total 则包含 status 过滤
    status_counts_raw = base.with_entities(
        Quote.status, func.count(Quote.id).label('cnt')
    ).group_by(Quote.status).all()
    status_counts = {row.status: row.cnt for row in status_counts_raw}

    if status:
        base = base.filter(Quote.status == status)
    total = base.count()

    filter_users = []
    if g.current_user.role == 'admin':
        filter_users = (
            db.session.query(User.id, User.username)
            .distinct()
            .join(Quote, Quote.created_by == User.id)
            .order_by(User.username)
            .all()
        )

    return jsonify({
        'filter_users': [{'id': u, 'username': n} for u, n in filter_users],
        'total': total,
        'status_counts': status_counts,
    })


@quotes_bp.route('/api/quotes/trends', methods=['GET'])
@require_auth
def quote_trends():
    """月度新建趋势——单次 GROUP BY 聚合替代循环 N 次 COUNT"""
    months = request.args.get('months', 6, type=int)
    now = datetime.now()

    # 计算目标月份列表
    target_months = []
    for i in range(months - 1, -1, -1):
        d = now - timedelta(days=30 * i)
        target_months.append(d.strftime('%Y-%m'))

    # 单次聚合查询
    rows = (
        db.session.query(
            func.strftime('%Y-%m', Quote.created_at).label('ym'),
            func.count(Quote.id).label('cnt'),
        )
        .filter(func.strftime('%Y-%m', Quote.created_at).in_(target_months))
        .group_by('ym')
        .all()
    )
    counts = {r.ym: r.cnt for r in rows}
    results = [{'month': ym, 'created': counts.get(ym, 0)} for ym in target_months]
    return jsonify({'trends': results})


# ─── Quote CRUD ──────────────────────────────────────────

@quotes_bp.route('/api/quotes', methods=['POST'])
@require_admin
def create_quote():
    data = request.get_json(silent=True) or {}
    quote = Quote(
        title=data.get('title', ''),
        created_by=g.current_user.id,
        supplier_id=data.get('supplier_id'),
        salesperson_id=data.get('salesperson_id'),
        order_start=data.get('order_start', ''),
        order_end=data.get('order_end', ''),
        project_category=data.get('project_category', ''),
        remark=data.get('remark', ''),
    )
    db.session.add(quote)
    db.session.commit()
    return jsonify({'quote': quote.to_dict()}), 201


@quotes_bp.route('/api/quotes/<int:quote_id>', methods=['GET'])
@require_auth
def get_quote(quote_id):
    quote, err, status = check_quote_owner(quote_id)
    if not quote:
        return err, status

    # 构建正确的 map（suppliers_map + salespersons_map，非 users_map）
    suppliers_map = {}
    if quote.supplier_id:
        s = db.session.get(Supplier, quote.supplier_id)
        if s:
            suppliers_map = {s.id: s.name}

    salespersons_map = {}
    if quote.salesperson_id:
        sp = db.session.get(Salesperson, quote.salesperson_id)
        if sp:
            salespersons_map = {sp.id: sp.name}

    next_statuses = list(STATUS_MACHINE.get(quote.status, []))
    if quote.status != '项目终止':
        next_statuses.append('项目终止')

    result = quote.to_dict(suppliers_map=suppliers_map, salespersons_map=salespersons_map)
    result['next_statuses'] = next_statuses
    return jsonify({'quote': result})


@quotes_bp.route('/api/quotes/<int:quote_id>', methods=['PUT'])
@require_admin
def update_quote(quote_id):
    quote, err, status = check_quote_owner(quote_id)
    if not quote:
        return err, status
    data = request.get_json(silent=True) or {}
    if data.get('title') is not None:
        quote.title = data['title']
    if data.get('supplier_id') is not None:
        quote.supplier_id = data['supplier_id']
    if data.get('salesperson_id') is not None:
        quote.salesperson_id = data['salesperson_id']
    if data.get('order_start') is not None:
        quote.order_start = data['order_start']
    if data.get('order_end') is not None:
        quote.order_end = data['order_end']
    if data.get('project_category') is not None:
        quote.project_category = data['project_category']
    if 'remark' in data:
        quote.remark = data['remark']
    # 注意：status 字段不允许通过此接口修改，状态变更必须走 /status PATCH 接口
    quote.updated_at = datetime.now()
    db.session.commit()
    return jsonify({'quote': quote.to_dict()})


@quotes_bp.route('/api/quotes/<int:quote_id>', methods=['DELETE'])
@require_admin
def delete_quote(quote_id):
    quote, err, status = check_quote_owner(quote_id)
    if not quote:
        return err, status
    db.session.delete(quote)
    db.session.commit()
    return jsonify({'message': '已删除'})


@quotes_bp.route('/api/quotes/batch', methods=['DELETE'])
@require_admin
def batch_delete_quotes():
    data = request.get_json(silent=True) or {}
    ids = data.get('ids', [])
    if not isinstance(ids, list) or not ids:
        return jsonify({'error': '请提供要删除的报价单 ID 列表'}), 400
    if len(ids) > 100:
        return jsonify({'error': '单次最多删除 100 条'}), 400
    quotes = Quote.query.filter(Quote.id.in_(ids)).all()
    for q in quotes:
        db.session.delete(q)
    db.session.commit()
    return jsonify({'deleted': len(quotes), 'total': len(ids)})


# ─── 状态流转 ─────────────────────────────────────────────

@quotes_bp.route('/api/quotes/<int:quote_id>/status', methods=['PATCH'])
@require_auth
def update_quote_status(quote_id):
    quote, err, status = check_quote_owner(quote_id)
    if not quote:
        return err, status
    data = request.get_json(silent=True) or {}
    new_status = data.get('status', '')
    valid_statuses = list(STATUS_MACHINE.keys()) + ['项目终止']
    if new_status not in valid_statuses:
        return jsonify({'error': f'无效状态，可选: {valid_statuses}'}), 400
    old_status = quote.status
    if new_status == old_status:
        return jsonify({'error': '状态未变化'}), 400

    operator = g.current_user.username

    # 终止项目：允许从任意状态进入
    if new_status == '项目终止':
        quote.status = new_status
        quote.updated_at = datetime.now()
        db.session.add(StatusLog(
            quote_id=quote.id, from_status=old_status,
            to_status=new_status, operator_name=operator,
        ))
        db.session.commit()
        return jsonify({'quote': quote.to_dict()})

    # 其他状态：必须符合状态机
    allowed = STATUS_MACHINE.get(old_status, [])
    if new_status not in allowed:
        return jsonify({
            'error': f'状态 "{old_status}" 不允许直接跳转到 "{new_status}"，'
                     f'允许的下一步: {allowed or "无"}'
        }), 400
    quote.status = new_status
    quote.updated_at = datetime.now()
    db.session.add(StatusLog(
        quote_id=quote.id, from_status=old_status,
        to_status=new_status, operator_name=operator,
    ))
    db.session.commit()
    return jsonify({'quote': quote.to_dict()})


# ─── 状态日志 ──────────────────────────────────────────────

@quotes_bp.route('/api/quotes/<int:quote_id>/logs', methods=['GET'])
@require_auth
def quote_logs(quote_id):
    quote, err, status = check_quote_owner(quote_id)
    if not quote:
        return err, status
    logs = StatusLog.query.filter_by(quote_id=quote_id).order_by(StatusLog.created_at.desc()).all()
    return jsonify({'logs': [log.to_dict() for log in logs]})


# ─── 交流记录 ─────────────────────────────────────────────

@quotes_bp.route('/api/quotes/<int:quote_id>/events', methods=['GET'])
@require_auth
def list_quote_events(quote_id):
    quote, err, status = check_quote_owner(quote_id)
    if not quote:
        return err, status
    events = QuoteEvent.query.filter_by(quote_id=quote_id).order_by(QuoteEvent.created_at.desc()).all()
    # 批量加载创建人，避免 N+1
    creator_ids = list({e.created_by for e in events if e.created_by})
    users_map = {}
    if creator_ids:
        users_map = {u.id: u.username for u in User.query.filter(User.id.in_(creator_ids)).all()}
    return jsonify({'events': [e.to_dict(users_map=users_map) for e in events]})


@quotes_bp.route('/api/quotes/<int:quote_id>/events', methods=['POST'])
@require_auth
def create_quote_event(quote_id):
    quote, err, status = check_quote_owner(quote_id)
    if not quote:
        return err, status
    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'error': '内容不能为空'}), 400
    event = QuoteEvent(
        quote_id=quote_id,
        content=content,
        direction=data.get('direction', ''),
        quote_status=quote.status,
        created_by=g.current_user.id,
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({'event': event.to_dict()}), 201
