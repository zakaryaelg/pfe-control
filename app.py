from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
from sqlalchemy import func

from config import Config
from models import db, User, Customer, Rule, Transaction, Alert
from forms import LoginForm, CreateUserForm, UploadTransactionsForm, AlertDecisionForm, EditUserForm
from run import CSVService
from rules import RuleEngine

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ─── Decorators ───
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin(): abort(403)
        return f(*args, **kwargs)
    return decorated

def controller_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_controller(): abort(403)
        return f(*args, **kwargs)
    return decorated

# ─── Routes ───
@app.route('/')
def index():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember_me.data)
            user.update_last_login()
            flash(f'Bienvenue, {user.full_name or user.username} !', 'success')
            next_page = request.args.get('next')
            if next_page and not next_page.startswith('/'):
                next_page = None
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        flash('Identifiants incorrects.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnecté.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin(): return redirect(url_for('admin_dashboard'))
    return redirect(url_for('controller_dashboard'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    users = User.query.all()
    return render_template('admin_dashboard.html',
        users=users,
        users_count=User.query.count(),
        controllers_count=User.query.filter_by(role='controller').count(),
        admins_count=User.query.filter_by(role='admin').count(),
        rules_count=Rule.query.filter_by(is_active=True).count())

@app.route('/admin/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    form = CreateUserForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data,
                    full_name=form.full_name.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Utilisateur {user.username} créé.', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('create_user.html', form=form)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    form = EditUserForm(original_email=user.email, obj=user)
    if form.validate_on_submit():
        user.full_name = form.full_name.data
        user.email = form.email.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        db.session.commit()
        flash(f'Utilisateur {user.username} mis à jour.', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_user.html', form=form, user=user)

@app.route('/controller/dashboard')
@controller_required
def controller_dashboard():
    stats = {
        'total_alerts': Alert.query.count(),
        'new_red': Alert.query.filter_by(alert_color='RED', alert_status='NEW').count(),
        'new_yellow': Alert.query.filter_by(alert_color='YELLOW', alert_status='NEW').count(),
        'resolved': Alert.query.filter_by(alert_status='RESOLVED').count()
    }
    red_alerts = Alert.query.filter(Alert.alert_color=='RED', Alert.alert_status.in_(['NEW','PENDING'])).order_by(Alert.created_at.desc()).all()
    yellow_alerts = Alert.query.filter(Alert.alert_color=='YELLOW', Alert.alert_status.in_(['NEW','PENDING'])).order_by(Alert.created_at.desc()).all()
    recent_green = Transaction.query.filter_by(status='GREEN').order_by(Transaction.evaluated_at.desc()).limit(5).all()
    recent_red = Transaction.query.filter_by(status='RED').order_by(Transaction.evaluated_at.desc()).limit(5).all()
    return render_template('controller_dashboard.html', stats=stats, red_alerts=red_alerts, yellow_alerts=yellow_alerts, recent_green=recent_green, recent_red=recent_red)

# ─── Alert detail & decision ───
@app.route('/alert/<string:alert_id>', methods=['GET', 'POST'])
@controller_required
def alert_detail(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    transaction = db.session.get(Transaction, alert.transaction_id)
    rule = db.session.get(Rule, alert.rule_id)
    form = AlertDecisionForm()
    if form.validate_on_submit():
        from datetime import datetime, timezone
        alert.controller_decision = form.decision.data
        alert.controller_notes = form.notes.data
        alert.decided_by = current_user.username
        alert.decided_at = datetime.now(timezone.utc)
        if form.decision.data in ('APPROVED', 'REJECTED'):
            alert.alert_status = 'RESOLVED'
        else:
            alert.alert_status = 'PENDING'
        db.session.commit()
        flash('Décision enregistrée avec succès.', 'success')
        return redirect(url_for('controller_dashboard'))
    # Pre-fill form with existing decision if any
    if alert.controller_decision and not form.is_submitted():
        form.decision.data = alert.controller_decision
        form.notes.data = alert.controller_notes
    return render_template('alert_detail.html', alert=alert, transaction=transaction, rule=rule, form=form)

# ─── Transactions list ───
@app.route('/transactions')
@login_required
def transactions():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    event_filter = request.args.get('event_type', '')
    customer_filter = request.args.get('customer_id', '').strip()

    query = Transaction.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if event_filter:
        query = query.filter_by(event_type=event_filter)
    if customer_filter:
        query = query.filter(Transaction.customer_id.ilike(f'%{customer_filter}%'))

    pagination = query.order_by(Transaction.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    event_types = [r[0] for r in db.session.query(Transaction.event_type).distinct().all()]
    return render_template('transactions.html', pagination=pagination,
                           status_filter=status_filter, event_filter=event_filter,
                           customer_filter=customer_filter, event_types=event_types)

# ─── Transaction detail ───
@app.route('/transaction/<string:transaction_id>')
@login_required
def transaction_detail(transaction_id):
    txn = Transaction.query.get_or_404(transaction_id)
    customer = db.session.get(Customer, txn.customer_id)
    triggered_rules = []
    if txn.rules_triggered:
        triggered_rules = Rule.query.filter(Rule.rule_id.in_(txn.rules_triggered)).all()
    alerts = Alert.query.filter_by(transaction_id=transaction_id).all()
    return render_template('transaction_detail.html', txn=txn, customer=customer,
                           triggered_rules=triggered_rules, alerts=alerts)

# ─── Rules browser ───
@app.route('/rules')
@login_required
def rules_browser():
    rules = Rule.query.order_by(Rule.action, Rule.rule_id).all()
    rules_count = Rule.query.filter_by(is_active=True).count()
    return render_template('rules.html', rules=rules, rules_count=rules_count)

# ─── Reports ───
@app.route('/reports')
@login_required
def reports():
    # Transaction counts
    green_count = Transaction.query.filter_by(status='GREEN').count()
    yellow_count = Transaction.query.filter_by(status='YELLOW').count()
    red_count = Transaction.query.filter_by(status='RED').count()
    total_txn = green_count + yellow_count + red_count

    # Alert counts
    alerts_new = Alert.query.filter_by(alert_status='NEW').count()
    alerts_pending = Alert.query.filter_by(alert_status='PENDING').count()
    alerts_resolved = Alert.query.filter_by(alert_status='RESOLVED').count()

    # Top violated rules
    top_rules = db.session.query(
        Alert.rule_id, Alert.article_ref, func.count(Alert.alert_id).label('cnt')
    ).group_by(Alert.rule_id, Alert.article_ref).order_by(func.count(Alert.alert_id).desc()).limit(5).all()

    # Recent resolved alerts
    recent_resolved = Alert.query.filter_by(alert_status='RESOLVED').order_by(Alert.decided_at.desc()).limit(10).all()

    return render_template('reports.html',
        green_count=green_count, yellow_count=yellow_count, red_count=red_count, total_txn=total_txn,
        alerts_new=alerts_new, alerts_pending=alerts_pending, alerts_resolved=alerts_resolved,
        top_rules=top_rules, recent_resolved=recent_resolved)

# ─── Upload ───
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_transactions():
    form = UploadTransactionsForm()
    if form.validate_on_submit():
        file = form.csv_file.data
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        try:
            csv_service = CSVService()
            transactions = csv_service.parse_csv(file, filename)
            engine = RuleEngine()
            results = engine.evaluate_batch(transactions)
            flash(f'Évalué: {results["GREEN"]} vert, {results["YELLOW"]} jaune, {results["RED"]} rouge, {results["ERROR"]} erreurs.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'danger')
    return render_template('upload.html', form=form)

@app.errorhandler(403)
def forbidden(error):
    flash('Accès refusé.', 'danger')
    return redirect(url_for('dashboard'))

@app.errorhandler(404)
def not_found(error):
    flash('Ressource introuvable.', 'warning')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
