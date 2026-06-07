from app import create_app
from models import db, User

app = create_app()

with app.app_context():
    db.create_all()

    # Create admin if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@uemoa.rfe',
            full_name='Administrateur Système',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        print('✓ Admin created: admin / admin123')

    # Create controller if not exists
    if not User.query.filter_by(username='controller').first():
        ctrl = User(
            username='controller',
            email='controller@uemoa.rfe',
            full_name='Contrôleur RFE',
            role='controller'
        )
        ctrl.set_password('ctrl123')
        db.session.add(ctrl)
        print('✓ Controller created: controller / ctrl123')

    db.session.commit()
    print('Database initialized successfully.')