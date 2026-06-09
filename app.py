from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps

from config import Config
from models import db, User, Customer, Rule, Transaction, Alert
from forms import LoginForm, CreateUserForm, UploadTransactionsForm
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)