from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import uuid

db = SQLAlchemy()


# ─── 1. USERS ───
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='controller')
    full_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_controller(self):
        return self.role == 'controller'

    def update_last_login(self):
        self.last_login = datetime.now(timezone.utc)
        db.session.commit()


# ─── 2. CUSTOMERS ───
class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    customer_type = db.Column(db.String(20), nullable=False)
    tax_domicile_country = db.Column(db.String(2))
    primary_economic_center = db.Column(db.String(2), nullable=False)
    nationality = db.Column(db.String(2))
    diplomatic_status = db.Column(db.Boolean, default=False)
    official_post_abroad = db.Column(db.Boolean, default=False)
    residency = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    transactions = db.relationship('Transaction', backref='customer', lazy=True)


# ─── 3. RULES ───
class Rule(db.Model):
    __tablename__ = 'rules'
    rule_id = db.Column(db.String(20), primary_key=True)
    article_ref = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    residency_filter = db.Column(db.String(20), nullable=False)
    conditions = db.Column(db.JSON, nullable=False)
    action = db.Column(db.String(20), nullable=False)
    authority = db.Column(db.String(50))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=1)


# ─── 4. TRANSACTIONS ───
class Transaction(db.Model):
    __tablename__ = 'transactions'
    transaction_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.String(50), db.ForeignKey('customers.customer_id'), nullable=False)
    customer_residency_at_txn = db.Column(db.String(20), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    operation_category = db.Column(db.String(50))
    direction = db.Column(db.String(10))
    amount = db.Column(db.Numeric(18, 2))
    currency = db.Column(db.String(3))
    counterparty_country = db.Column(db.String(2))
    account_type = db.Column(db.String(50))
    weight_grams = db.Column(db.Numeric(10, 2))
    actor_type = db.Column(db.String(50))
    status = db.Column(db.String(20), default='PENDING')
    rules_triggered = db.Column(db.JSON)
    required_action = db.Column(db.String(50))
    source_file = db.Column(db.String(200))
    raw_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    evaluated_at = db.Column(db.DateTime)
    alerts = db.relationship('Alert', backref='transaction', lazy=True, cascade='all, delete-orphan')


# ─── 5. ALERTS ───
class Alert(db.Model):
    __tablename__ = 'alerts'
    alert_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = db.Column(db.String(36), db.ForeignKey('transactions.transaction_id'), nullable=False)
    customer_id = db.Column(db.String(50), nullable=False)
    customer_name = db.Column(db.String(200))
    rule_id = db.Column(db.String(20), nullable=False)
    article_ref = db.Column(db.String(20))
    alert_color = db.Column(db.String(10), nullable=False)
    violation_description = db.Column(db.Text)
    required_authority = db.Column(db.String(50))
    alert_status = db.Column(db.String(20), default='NEW')
    controller_decision = db.Column(db.String(20))
    controller_notes = db.Column(db.Text)
    decided_by = db.Column(db.String(50))
    decided_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))