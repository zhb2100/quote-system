"""
Quotes Blueprint — 报价单相关 API 路由
"""
import re
from datetime import datetime, timedelta
from pathlib import Path

from flask import Blueprint, request, jsonify, g
from sqlalchemy import func

from extensions import db
from models import Quote, User, Supplier, Salesperson, StatusLog, QuoteEvent
from auth import require_auth, require_admin

quotes_bp = Blueprint('quotes', __name__)
BASE_DIR = Path(__file__).parent


def _check_quote_owner(quote_id):
    from helpers import check_quote_owner
    return check_quote_owner(quote_id)


# ─── 状态机 ──────────────────────────────────────────────

STATUS_MACHINE = {
    '项目报价中':        ['项目已报价未付款'],
    '项目已报价未付款':  ['项目生产中'],
    '项目生产中':        ['项目完结'],
    '项目完结':          ['项目返工'],
    '项目返工':          ['项目完结'],
    '项目终止':          ['项目报价中'],
}

NEXT_STATUS_DISPLAY = {
    '项目报价中':        '下一步 → 项目已报价未付款',
    '项目已报价未付款':  '下一步 → 项目生产中',
    '项目生产中':        '下一步 → 项目完结',
    '项目完结':          '下一步 → 项目返工',
    '项目返工':          '下一步 → 项目完结',
    '项目终止':          '重启项目 → 项目报价中',
}


# ─── Quotes API ──────────────────────────────────────

@quotes_bp.route('/api/quotes', methods=['GET'])
def list_quotes():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 200)
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()
    month_filter = request.args.get('month', '').strip()
    salesperson_id = request.args.get('salesperson_id', type=int)
    supplier_id = request.args.get('supplier_id', type=int)
    event_direction = request.args.get('event_direction', '').strip()
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'desc')

    sort_cols = {'id': Quote.id, 'title': Quote.title, 'status': Quote.status,
                 'order_start': Quote.order_start, 'order_end': Quote.order_end, 'created_at': Quote.created_at}
    order_col = sort_cols.get(sort_by, Quote.id)
    order_fn = order_col.asc if sort_order == 'asc' else order_col.desc

    query = Quote.query
    # 非管理员只看指派给自己的报价单
    if hasattr(g, 'current_user') and g.current_user and g.current_user.role != 'admin':
        sp = Salesperson.query.filter_by(user_id=g.current_user.id).first()
        if sp:
            query = query.filter(Quote.salesperson_id == sp.id)
        else:
            return jsonify({'quotes': [], 'total': 0, 'page': page, 'per_page': per_page})
    if status_filter:
        query = query.filter(Quote.status == status_filter)
    if month_filter:
        query = query.filter(func.strftime('%Y-%m', Quote.created_at) == month_filter)
    if salesperson_id:
        query = query.filter(Quote.salesperson_id == salesperson_id)
    if supplier_id:
        query = query.filter(Quote.supplier_id == supplier_id)
    if event_direction:
        latest_event_id = db.session.query(
            func.max(QuoteEvent.id)
        ).filter(
            QuoteEvent.quote_id == Quote.id
        ).correlate(Quote).as_scalar()
        query = query.filter(
            db.session.query(QuoteEvent).filter(
                QuoteEvent.id == latest_event_id,
                QuoteEvent.direction == event_direction
            ).exists()
        )

    is_pinyin = search and not re.search(r'[\u4e00-\u9fff]', search)
    if is_pinyin:
        from pypinyin import pinyin, Style
        q_lower = search.lower().strip()
        all_quotes = query.order_by(order_fn()).all()

        def pinyin_match(q):
            texts = [q.title or '']
            for text in texts:
                if not text:
                    continue
                py_list = pinyin(text, style=Style.NORMAL, heteronym=False)
                full_py = ''.join(p[0] for p in py_list).lower()
                if q_lower in full_py:
                    return True
                initials = ''.join(p[0][0] for p in py_list).lower()
                if q_lower in initials:
                    return True
            return False

        filtered = [q for q in all_quotes if pinyin_match(q)]
        total = len(filtered)
        quotes = filtered[(page - 1) * per_page: page * per_page]
    else:
        query = query.order_by(order_fn())
        if search:
            like = f'%{search}%'
            query = query.filter(Quote.title.ilike(like))
        total = query.count()
        quotes = query.offset((page - 1) * per_page).limit(per_page).all()

    creator_ids = list(set(q.created_by for q in quotes if q.created_by))
    users_map = {}
    if creator_ids:
        users = User.query.filter(User.id.in_(creator_ids)).all()
        users_map = {u.id: u.username for u in users}

    supplier_ids = list(set(q.supplier_id for q in quotes if q.supplier_id))
    suppliers_map = {}
    if supplier_ids:
        suppliers = Supplier.query.filter(Supplier.id.in_(supplier_ids)).all()
        suppliers_map = {s.id: s.name for s in suppliers}

    sp_ids = list(set(q.salesperson_id for q in quotes if q.salesperson_id))
    salespersons_map = {}
    if sp_ids:
        sps = Salesperson.query.filter(Salesperson.id.in_(sp_ids)).all()
        salespersons_map = {sp.id: sp.name for sp in sps}

    return jsonify({
        'quotes': [q.to_dict(users_map=users_map, suppliers_map=suppliers_map, salespersons_map=salespersons_map) for q in quotes],
        'total': total,
        'page': page,
        'per_page': per_page,
    })


@quotes_bp.route('/api/quotes/stats', methods=['GET'])
def quote_stats():
    user_id = request.args.get('user_id', type=int)
    month = request.args.get('month', '').strip()
    year = request.args.get('year', '').strip()
    status = request.args.get('status', '').strip()

    base = Quote.query
    if hasattr(g, 'current_user') and g.current_user and g.current_user.role != 'admin':
        sp = Salesperson.query.filter_by(user_id=g.current_user.id).first()
        if sp:
            base = base.filter(Quote.salesperson_id == sp.id)
        else:
            return jsonify({'filter_users': [], 'total': 0, 'status_counts': {}})
    elif user_id:
        base = base.filter(Quote.created_by == user_id)

    if month:
        base = base.filter(func.strftime('%Y-%m', Quote.created_at) == month)
    elif year:
        base = base.filter(func.strftime('%Y', Quote.created_at) == year)

    status_counts_raw = base.with_entities(
        Quote.status, func.count(Quote.id).label('cnt')
    ).group_by(Quote.status).all()
    status_counts = {row.status: row.cnt for row in status_counts_raw}

    if status:
        base = base.filter(Quote.status == status)

    total = base.count()

    users_q = db.session.query(User.id, User.username).distinct().join(
        Quote, Quote.created_by == User.id
    ).order_by(User.username)
    if hasattr(g, 'current_user') and g.current_user and g.current_user.role != 'admin':
        sp = Salesperson.query.filter_by(user_id=g.current_user.id).first()
        if sp:
            users_q = users_q.filter(Quote.salesperson_id == sp.id)
        else:
            users_q = users_q.filter(0 == 1)
    filter_users = users_q.all()

    return jsonify({
        'filter_users': [{'id': u, 'username': n} for u, n in filter_users],
        'total': total,
        'status_counts': status_counts,
    })


@quotes_bp.route('/api/quotes/trends', methods=['GET'])
def quote_trends():
    months = request.args.get('months', 6, type=int)
    now = datetime.now()
    results = []
    for i in range(months - 1, -1, -1):
        d = now - timedelta(days=30 * i)
        ym = d.strftime('%Y-%m')
        created = db.session.query(func.count(Quote.id)).filter(
            func.strftime('%Y-%m', Quote.created_at) == ym
        ).scalar() or 0
        results.append({'month': ym, 'created': created})
    return jsonify({'trends': results})


@quotes_bp.route('/api/users/options', methods=['GET'])
def list_users_options():
    users = User.query.order_by(User.username).all()
    return jsonify({
        'users': [{'id': u.id, 'username': u.username} for u in users]
    })


@quotes_bp.route('/api/quotes/<int:quote_id>/status', methods=['PATCH'])
def update_quote_status(quote_id):
    quote, err, status = _check_quote_owner(quote_id)
    if not quote:
        return err, status
    data = request.get_json()
    new_status = data.get('status', '')
    valid_statuses = list(STATUS_MACHINE.keys())
    if new_status not in valid_statuses:
        return jsonify({'error': f'无效状态，可选: {valid_statuses}'}), 400
    old_status = quote.status
    if new_status == old_status:
        return jsonify({'error': '状态未变化'}), 400
    operator = g.current_user.username if hasattr(g, 'current_user') and g.current_user else '系统'
    if new_status == '项目终止':
        quote.status = new_status
        db.session.add(StatusLog(quote_id=quote.id, from_status=old_status, to_status=new_status, operator_name=operator))
        db.session.commit()
        return jsonify({'quote': quote.to_dict()})
    allowed = STATUS_MACHINE.get(old_status, [])
    if new_status not in allowed:
        return jsonify({'error': f'状态 "{old_status}" 不允许直接跳转到 "{new_status}"，允许的下一步: {allowed or "无"}'}), 400
    quote.status = new_status
    db.session.add(StatusLog(quote_id=quote.id, from_status=old_status, to_status=new_status, operator_name=operator))
    db.session.commit()
    return jsonify({'quote': quote.to_dict()})


@quotes_bp.route('/api/quotes/<int:quote_id>/logs', methods=['GET'])
def quote_logs(quote_id):
    quote, err, status = _check_quote_owner(quote_id)
    if not quote:
        return err, status
    logs = StatusLog.query.filter_by(quote_id=quote_id).order_by(StatusLog.created_at.desc()).all()
    return jsonify({'logs': [log.to_dict() for log in logs]})


@quotes_bp.route('/api/quotes/<int:quote_id>/events', methods=['GET'])
def list_quote_events(quote_id):
    quote, err, status = _check_quote_owner(quote_id)
    if not quote:
        return err, status
    events = QuoteEvent.query.filter_by(quote_id=quote_id).order_by(QuoteEvent.created_at.desc()).all()
    return jsonify({'events': [e.to_dict() for e in events]})


@quotes_bp.route('/api/quotes/<int:quote_id>/events', methods=['POST'])
def create_quote_event(quote_id):
    quote, err, status = _check_quote_owner(quote_id)
    if not quote:
        return err, status
    data = request.get_json()
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'error': '内容不能为空'}), 400
    direction = data.get('direction', '')
    event = QuoteEvent(
        quote_id=quote_id, content=content, direction=direction,
        quote_status=quote.status,
        created_by=g.current_user.id if hasattr(g, 'current_user') and g.current_user else None,
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({'event': event.to_dict()}), 201


@quotes_bp.route('/api/quotes', methods=['POST'])
@require_admin
def create_quote():
    data = request.get_json()
    if not data:
        return jsonify({'error': '缺少数据'}), 400

    quote = Quote(
        title=data.get('title', ''),
        created_by=g.current_user.id if hasattr(g, 'current_user') and g.current_user else None,
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
def get_quote(quote_id):
    quote, err, status = _check_quote_owner(quote_id)
    if not quote:
        return err, status
    suppliers_map = {}
    if quote.supplier_id:
        s = db.session.get(Supplier, quote.supplier_id)
        if s:
            suppliers_map = {s.id: s.name}
    users_map = {}
    if quote.salesperson_id:
        u = db.session.get(User, quote.salesperson_id)
        if u:
            users_map = {u.id: u.username}
    next_statuses = list(STATUS_MACHINE.get(quote.status, []))
    if quote.status != '项目终止':
        next_statuses.append('项目终止')
    result = quote.to_dict(suppliers_map=suppliers_map, users_map=users_map)
    result['next_statuses'] = next_statuses
    return jsonify({'quote': result})


@quotes_bp.route('/api/quotes/<int:quote_id>', methods=['PUT'])
@require_admin
def update_quote(quote_id):
    quote, err, status = _check_quote_owner(quote_id)
    if not quote:
        return err, status
    data = request.get_json()
    if data.get('title') is not None: quote.title = data['title']
    if data.get('status') is not None: quote.status = data['status']
    if data.get('supplier_id') is not None: quote.supplier_id = data['supplier_id']
    if data.get('salesperson_id') is not None: quote.salesperson_id = data['salesperson_id']
    if data.get('order_start') is not None: quote.order_start = data['order_start']
    if data.get('order_end') is not None: quote.order_end = data['order_end']
    if data.get('project_category') is not None: quote.project_category = data['project_category']
    if 'remark' in data: quote.remark = data['remark']
    db.session.commit()
    return jsonify({'quote': quote.to_dict()})


@quotes_bp.route('/api/quotes/<int:quote_id>', methods=['DELETE'])
@require_admin
def delete_quote(quote_id):
    quote, err, status = _check_quote_owner(quote_id)
    if not quote:
        return err, status
    db.session.delete(quote)
    db.session.commit()
    return jsonify({'message': '已删除'})


@quotes_bp.route('/api/quotes/batch', methods=['DELETE'])
@require_auth
def batch_delete_quotes():
    data = request.get_json(silent=True) or {}
    ids = data.get('ids', [])
    if not isinstance(ids, list) or not ids:
        return jsonify({'error': '请提供要删除的报价单 ID 列表'}), 400
    if len(ids) > 100:
        return jsonify({'error': '单次最多删除 100 条'}), 400
    user = g.current_user
    is_admin = user.role == 'admin'
    quotes = Quote.query.filter(Quote.id.in_(ids)).all()
    deletable = []
    forbidden = []
    for q in quotes:
        if is_admin or q.created_by == user.id:
            deletable.append(q)
        else:
            forbidden.append(q.id)
    for q in deletable:
        db.session.delete(q)
    db.session.commit()
    return jsonify({
        'deleted': len(deletable),
        'total': len(ids),
        'forbidden': forbidden,
    })
