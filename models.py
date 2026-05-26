"""报价系统数据模型 — Quote / QuoteItem / User / 辅助表"""
from datetime import datetime
from extensions import db


class QuoteEvent(db.Model):
    __tablename__ = 'quote_events'
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    direction = db.Column(db.String(20), nullable=True, default='')
    quote_status = db.Column(db.String(20), nullable=True, default='')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        creator = db.session.get(User, self.created_by) if self.created_by else None
        return {
            'id': self.id,
            'quote_id': self.quote_id,
            'content': self.content,
            'direction': self.direction or '',
            'quote_status': self.quote_status or '',
            'creator_name': creator.username if creator else '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
        }


class StatusLog(db.Model):
    __tablename__ = 'status_logs'
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, nullable=False, index=True)
    from_status = db.Column(db.String(20), nullable=True)
    to_status = db.Column(db.String(20), nullable=False)
    operator_name = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'quote_id': self.quote_id,
            'from_status': self.from_status or '',
            'to_status': self.to_status,
            'operator_name': self.operator_name or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
        }


class Salesperson(db.Model):
    __tablename__ = 'salespersons'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'user_id': self.user_id}



# ─── 供应商 ───────────────────────────────────────────────────
class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    contact_person = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    address = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact_person': self.contact_person or '',
            'phone': self.phone or '',
            'email': self.email or '',
            'address': self.address or '',
            'notes': self.notes or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else '',
        }


# ─── 沟通记录（供应商↔客服）─────────────────────────────────
class CommunicationRecord(db.Model):
    __tablename__ = 'communication_records'
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    communication_date = db.Column(db.DateTime, default=datetime.now)
    created_at = db.Column(db.DateTime, default=datetime.now)
    supplier = db.relationship('Supplier', backref=db.backref('communication_records', lazy='dynamic', cascade='all, delete-orphan'))

    def to_dict(self):
        creator_name = ''
        if self.user_id:
            user = db.session.get(User, self.user_id)
            creator_name = user.username if user else ''
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'user_id': self.user_id,
            'creator_name': creator_name,
            'content': self.content,
            'communication_date': self.communication_date.strftime('%Y-%m-%d %H:%M') if self.communication_date else '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
        }


class Quote(db.Model):
    __tablename__ = 'quotes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='项目报价中', index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    project_category = db.Column(db.String(100), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    salesperson_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    order_start = db.Column(db.String(20), nullable=True)
    order_end = db.Column(db.String(20), nullable=True)
    remark = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self, users_map=None, suppliers_map=None, salespersons_map=None):
        creator_name = None
        if self.created_by:
            if users_map is not None:
                creator_name = users_map.get(self.created_by)
            else:
                creator = db.session.get(User, self.created_by)
                creator_name = creator.username if creator else None
        supplier_name = ''
        if self.supplier_id:
            if suppliers_map is not None:
                supplier_name = suppliers_map.get(self.supplier_id, '')
            else:
                s = db.session.get(Supplier, self.supplier_id)
                supplier_name = s.name if s else ''
        salesperson_name = ''
        if self.salesperson_id:
            if salespersons_map is not None:
                salesperson_name = salespersons_map.get(self.salesperson_id, '')
            else:
                sp = db.session.get(Salesperson, self.salesperson_id)
                salesperson_name = sp.name if sp else ''
        return {
            'id': self.id,
            'title': self.title or '',
            'status': self.status,
            'created_by': self.created_by,
            'created_by_name': creator_name,
            'project_category': self.project_category or '',
            'supplier_id': self.supplier_id,
            'supplier_name': supplier_name,
            'salesperson_id': self.salesperson_id,
            'salesperson_name': salesperson_name,
            'order_start': self.order_start or '',
            'order_end': self.order_end or '',
            'remark': self.remark or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else '',
        }


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(10), default='user')
    is_active = db.Column(db.Boolean, default=True)
    email = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id, 'username': self.username,
            'role': self.role, 'is_active': self.is_active,
            'email': self.email or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M') if self.last_login else '',
        }


class FieldSetting(db.Model):
    __tablename__ = 'field_settings'
    id = db.Column(db.Integer, primary_key=True)
    field_name = db.Column(db.String(50), unique=True, nullable=False)
    label = db.Column(db.String(100), nullable=False)
    user_visible = db.Column(db.Boolean, default=True)


class SystemSetting(db.Model):
    """系统设置 key-value 存储 (v1.3.8)"""
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True, default='')


class LoginLog(db.Model):
    """用户登录记录 — 记录登录时间、IP、区域"""
    __tablename__ = 'login_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    username = db.Column(db.String(50), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    region = db.Column(db.String(100), nullable=True)
    user_agent = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    user = db.relationship('User', backref=db.backref('login_logs', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'ip_address': self.ip_address or '',
            'region': self.region or '',
            'user_agent': self.user_agent or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
        }
