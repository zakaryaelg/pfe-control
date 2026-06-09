from app import app
from models import db, User, Customer, Rule

with app.app_context():
    db.create_all()

    # Users
    if not User.query.filter_by(username='admin').first():
        a = User(username='admin', email='admin@uemoa.rfe', full_name='Administrateur', role='admin')
        a.set_password('admin123')
        db.session.add(a)

    if not User.query.filter_by(username='controller').first():
        c = User(username='controller', email='ctrl@uemoa.rfe', full_name='Contrôleur RFE', role='controller')
        c.set_password('ctrl123')
        db.session.add(c)

    # Customers
    customers = [
        Customer(customer_id='CLI001', name='SAHEL COTTON SA', customer_type='LEGAL', primary_economic_center='CI',
                 residency='RESIDENT'),
        Customer(customer_id='CLI002', name='ALI DIALLO', customer_type='PHYSICAL', primary_economic_center='SN',
                 residency='RESIDENT'),
        Customer(customer_id='CLI003', name='GOLD TRADE LLC', customer_type='LEGAL', primary_economic_center='ML',
                 residency='RESIDENT'),
        Customer(customer_id='CLI004', name='EMBASSADE FRANCE', customer_type='DIPLOMATIC',
                 primary_economic_center='FR', residency='NON_RESIDENT', diplomatic_status=True),
    ]
    for c in customers:
        if not db.session.get(Customer, c.customer_id): db.session.add(c)

    # Rules
    rules = [
        Rule(rule_id='FXS-001', article_ref='Art. 5', title='Rapatriement obligatoire', event_type='FX_RECEIPT',
             residency_filter='RESIDENT', conditions={'currency': '!=XOF'}, action='MANDATE',
             description='Le résident doit céder ses devises à un intermédiaire agréé'),
        Rule(rule_id='ACC-001', article_ref='Art. 6', title='Compte étranger non-résident', event_type='ACCOUNT_OPEN',
             residency_filter='NON_RESIDENT', conditions={'account_type': 'FOREIGN_CURRENCY'},
             action='REQUIRE_AUTHORIZATION', authority='BCEAO', description='Autorisation BCEAO requise'),
        Rule(rule_id='ACC-002', article_ref='Art. 7', title='Compte devises résident', event_type='ACCOUNT_OPEN',
             residency_filter='RESIDENT', conditions={'account_type': 'FOREIGN_CURRENCY'},
             action='REQUIRE_AUTHORIZATION', authority='MINISTER_FINANCE',
             description='Autorisation Ministre + avis BCEAO'),
        Rule(rule_id='CAP-001', article_ref='Art. 12', title='Investissement à l\'étranger', event_type='INVESTMENT',
             residency_filter='RESIDENT', conditions={'direction': 'OUTBOUND'}, action='BLOCK',
             authority='MINISTER_FINANCE', description='Autorisation préalable obligatoire. Financement étranger ≥75%'),
        Rule(rule_id='CAP-002', article_ref='Art. 13', title='Prêt à non-résident', event_type='LOAN',
             residency_filter='RESIDENT', conditions={'direction': 'OUTBOUND'}, action='BLOCK',
             authority='MINISTER_FINANCE', description='Autorisation + avis BCEAO. Financement étranger ≥75%'),
        Rule(rule_id='CAP-003', article_ref='Art. 15', title='Investissement étranger UEMOA', event_type='INVESTMENT',
             residency_filter='NON_RESIDENT', conditions={'direction': 'INBOUND'}, action='ALLOW',
             description='Libre, sous réserve formalités nationales'),
        Rule(rule_id='GLD-001', article_ref='Art. 20', title='Or >500g', event_type='GOLD_EXPORT',
             residency_filter='ANY', conditions={'weight_grams': '>500'}, action='BLOCK', authority='MINISTER_FINANCE',
             description='Autorisation Ministre des Finances'),
        Rule(rule_id='GLD-002', article_ref='Art. 20', title='Or voyageur ≤500g', event_type='GOLD_EXPORT',
             residency_filter='ANY', conditions={'actor_type': 'TRAVELER', 'weight_grams': '<=500'}, action='ALLOW',
             description='Exemption voyageur ≤500g', priority=2),
        Rule(rule_id='CUR-001', article_ref='Art. 9', title='Paiements courants libres', event_type='TRANSFER',
             residency_filter='ANY', conditions={'amount': '<=10000000', 'operation_category': 'CURRENT'},
             action='ALLOW', description='Libres sous seuil BCEAO'),
        Rule(rule_id='CUR-002', article_ref='Art. 9', title='Paiements courants documentés', event_type='TRANSFER',
             residency_filter='ANY', conditions={'amount': '>10000000', 'operation_category': 'CURRENT'},
             action='REQUIRE_DOCUMENT', description='Pièces justificatives requises'),
    ]
    for r in rules:
        if not db.session.get(Rule, r.rule_id): db.session.add(r)

    db.session.commit()
    print('✓ Database seeded')