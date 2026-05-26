"""Salespersons Blueprint — 业务员管理 API"""
from flask import Blueprint, request, jsonify
from extensions import db
from models import Salesperson, Quote
from auth import require_admin

salespersons_bp = Blueprint('salespersons', __name__)


@salespersons_bp.route('/api/salespersons', methods=['GET'])
def list_salespersons():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 200)
    search = request.args.get('search', '').strip()
    query = Salesperson.query
    if search:
        query = query.filter(Salesperson.name.contains(search))
    query = query.order_by(Salesperson.id.asc())
    total = query.count()
    salespersons = query.offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        'salespersons': [s.to_dict() for s in salespersons],
        'total': total, 'page': page, 'per_page': per_page,
    })


@salespersons_bp.route('/api/salespersons', methods=['POST'])
@require_admin
def create_salesperson():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': '姓名不能为空'}), 400
    user_id = data.get('user_id')
    sp = Salesperson(name=name, user_id=user_id)
    db.session.add(sp)
    db.session.commit()
    return jsonify({'salesperson': sp.to_dict()}), 201


@salespersons_bp.route('/api/salespersons/<int:sp_id>', methods=['PUT'])
@require_admin
def update_salesperson(sp_id):
    sp = db.session.get(Salesperson, sp_id)
    if not sp:
        return jsonify({'error': '业务员不存在'}), 404
    data = request.get_json()
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': '姓名不能为空'}), 400
    sp.name = name
    if 'user_id' in data:
        sp.user_id = data['user_id']
    db.session.commit()
    return jsonify({'salesperson': sp.to_dict()})


@salespersons_bp.route('/api/salespersons/<int:sp_id>', methods=['DELETE'])
@require_admin
def delete_salesperson(sp_id):
    sp = db.session.get(Salesperson, sp_id)
    if not sp:
        return jsonify({'error': '业务员不存在'}), 404
    quotes_using = db.session.query(Quote).filter(Quote.salesperson_id == sp_id).count()
    if quotes_using > 0:
        return jsonify({'error': f'该业务员被 {quotes_using} 条报价单引用，无法删除'}), 400
    db.session.delete(sp)
    db.session.commit()
    return jsonify({'message': '已删除'})
