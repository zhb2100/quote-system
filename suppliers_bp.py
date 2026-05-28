"""Suppliers Blueprint — 供应商管理 API"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from extensions import db
from models import Supplier, Quote
from auth import require_auth, require_admin
from helpers import get_pagination_args

suppliers_bp = Blueprint('suppliers', __name__)


@suppliers_bp.route('/api/suppliers', methods=['GET'])
@require_auth
def list_suppliers():
    page, per_page = get_pagination_args()
    search = request.args.get('search', '').strip()
    query = Supplier.query
    if search:
        query = query.filter(Supplier.name.ilike(f'%{search}%'))
    query = query.order_by(Supplier.id.desc())
    total = query.count()
    suppliers = query.offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        'suppliers': [s.to_dict() for s in suppliers],
        'total': total,
        'page': page,
        'per_page': per_page,
    })


@suppliers_bp.route('/api/suppliers', methods=['POST'])
@require_admin
def create_supplier():
    data = request.get_json(silent=True) or {}
    if not data.get('name', '').strip():
        return jsonify({'error': '供应商名称不能为空'}), 400
    supplier = Supplier(
        name=data['name'].strip(),
        contact_person=(data.get('contact_person') or '').strip(),
        phone=(data.get('phone') or '').strip(),
        email=(data.get('email') or '').strip(),
        address=(data.get('address') or '').strip(),
        notes=(data.get('notes') or '').strip(),
        created_by=g.current_user.id,
    )
    db.session.add(supplier)
    db.session.commit()
    return jsonify({'supplier': supplier.to_dict()}), 201


@suppliers_bp.route('/api/suppliers/<int:supplier_id>', methods=['GET'])
@require_auth
def get_supplier(supplier_id):
    supplier = db.session.get(Supplier, supplier_id)
    if not supplier:
        return jsonify({'error': '供应商不存在'}), 404
    return jsonify({'supplier': supplier.to_dict()})


@suppliers_bp.route('/api/suppliers/<int:supplier_id>', methods=['PUT'])
@require_admin
def update_supplier(supplier_id):
    supplier = db.session.get(Supplier, supplier_id)
    if not supplier:
        return jsonify({'error': '供应商不存在'}), 404
    data = request.get_json(silent=True) or {}
    if data.get('name') is not None:
        name = data['name'].strip()
        if not name:
            return jsonify({'error': '供应商名称不能为空'}), 400
        supplier.name = name
    if data.get('contact_person') is not None:
        supplier.contact_person = data['contact_person'].strip()
    if data.get('phone') is not None:
        supplier.phone = data['phone'].strip()
    if data.get('email') is not None:
        supplier.email = data['email'].strip()
    if data.get('address') is not None:
        supplier.address = data['address'].strip()
    if data.get('notes') is not None:
        supplier.notes = data['notes'].strip()
    supplier.updated_at = datetime.now()
    db.session.commit()
    return jsonify({'supplier': supplier.to_dict()})


@suppliers_bp.route('/api/suppliers/<int:supplier_id>', methods=['DELETE'])
@require_admin
def delete_supplier(supplier_id):
    supplier = db.session.get(Supplier, supplier_id)
    if not supplier:
        return jsonify({'error': '供应商不存在'}), 404
    # 引用检查：有报价单关联时拒绝删除（同 salespersons_bp 的保护逻辑）
    ref_count = db.session.query(Quote).filter(Quote.supplier_id == supplier_id).count()
    if ref_count > 0:
        return jsonify({'error': f'该供应商被 {ref_count} 条报价单引用，无法删除'}), 400
    db.session.delete(supplier)
    db.session.commit()
    return jsonify({'message': '已删除'})
