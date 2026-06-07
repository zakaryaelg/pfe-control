from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps

from config import Config
from models import db, User
from forms import LoginForm, CreateUserForm


# ─── App Factory ───
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ─── Role Decorators ───
    def admin_required(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.is_admin():
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    def controller_required(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.is_controller():
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    # ─── Routes ───

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        form = LoginForm()

        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()

            if user and user.check_password(form.password.data) and user.is_active:
                login_user(user, remember=form.remember_me.data)
                user.update_last_login()
                flash(f'Bienvenue, {user.full_name or user.username} !', 'success')

                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')

        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Vous avez été déconnecté.', 'info')
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Route unique qui redirige vers le bon tableau de bord selon le rôle."""
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('controller_dashboard'))

    @app.route('/admin/dashboard')
    @admin_required
    def admin_dashboard():
        users = User.query.all()
        users_count = User.query.count()
        controllers_count = User.query.filter_by(role='controller').count()
        admins_count = User.query.filter_by(role='admin').count()

        return render_template('admin_dashboard.html',
                               users=users,
                               users_count=users_count,
                               controllers_count=controllers_count,
                               admins_count=admins_count)

    @app.route('/admin/users/create', methods=['GET', 'POST'])
    @admin_required
    def create_user():
        form = CreateUserForm()

        if form.validate_on_submit():
            user = User(
                username=form.username.data,
                email=form.email.data,
                full_name=form.full_name.data,
                role=form.role.data
            )
            user.set_password(form.password.data)

            db.session.add(user)
            db.session.commit()

            flash(f'Utilisateur {user.username} créé avec succès.', 'success')
            return redirect(url_for('admin_dashboard'))

        return render_template('create_user.html', form=form)

    @app.route('/controller/dashboard')
    @controller_required
    def controller_dashboard():
        # Placeholder: les alertes seront ajoutées plus tard
        alerts = []
        return render_template('controller_dashboard.html', alerts=alerts)

    # ─── Error Handlers ───
    @app.errorhandler(403)
    def forbidden(error):
        flash('Accès refusé. Vous n\'avez pas les permissions nécessaires.', 'danger')
        return redirect(url_for('dashboard'))

    return app


# ─── Run ───
if __name__ == '__main__':
    app = create_app()

    with app.app_context():
        db.create_all()

    app.run(debug=True, port=5000)