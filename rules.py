import json
from typing import List, Dict, Any
from datetime import datetime, timezone
from models import Rule, Customer, Transaction, Alert, db


class RuleEngine:
    def __init__(self):
        self.db = db.session

    def evaluate_transaction(self, transaction: Transaction) -> Dict[str, Any]:
        customer = db.session.get(Customer, transaction.customer_id)
        if not customer:
            transaction.status = 'RED'
            transaction.required_action = 'CONTROLLER_REVIEW'
            db.session.commit()
            return {'status': 'RED', 'triggered_rules': ['ERR-001'], 'required_action': 'CONTROLLER_REVIEW',
                    'alerts_count': 0}

        transaction.customer_residency_at_txn = customer.residency

        rules = Rule.query.filter(
            Rule.event_type == transaction.event_type,
            Rule.is_active.is_(True),
            Rule.residency_filter.in_([customer.residency, 'ANY'])
        ).order_by(Rule.priority.asc()).all()

        triggered = []
        for rule in rules:
            if self._matches(rule.conditions, transaction, customer):
                triggered.append(rule)

        status, action = self._determine_status(triggered)
        transaction.status = status
        transaction.rules_triggered = [r.rule_id for r in triggered]
        transaction.required_action = action
        transaction.evaluated_at = datetime.now(timezone.utc)

        alerts_count = 0
        if status in ('RED', 'YELLOW'):
            for rule in triggered:
                if rule.action in ('BLOCK', 'REQUIRE_AUTHORIZATION', 'REQUIRE_DOCUMENT'):
                    alert = Alert(
                        transaction_id=transaction.transaction_id,
                        customer_id=customer.customer_id,
                        customer_name=customer.name,
                        rule_id=rule.rule_id,
                        article_ref=rule.article_ref,
                        alert_color='RED' if rule.action == 'BLOCK' else 'YELLOW',
                        violation_description=rule.description,
                        required_authority=rule.authority
                    )
                    self.db.add(alert)
                    alerts_count += 1

        self.db.commit()
        return {'status': status, 'triggered_rules': [r.rule_id for r in triggered], 'required_action': action,
                'alerts_count': alerts_count, 'residency': customer.residency}

    def _matches(self, conditions, transaction, customer):
        if isinstance(conditions, str):
            conditions = json.loads(conditions)
        for key, expected in conditions.items():
            actual = getattr(transaction, key, None) or getattr(customer, key, None)
            if actual is None:
                return False
            actual_str = str(actual).upper()
            expected_str = str(expected).upper()
            if expected_str.startswith('!='):
                if actual_str == expected_str[2:]: return False
            elif expected_str.startswith('>='):
                if float(actual) < float(expected_str[2:]): return False
            elif expected_str.startswith('<='):
                if float(actual) > float(expected_str[2:]): return False
            elif expected_str.startswith('>'):
                if float(actual) <= float(expected_str[1:]): return False
            elif expected_str.startswith('<'):
                if float(actual) >= float(expected_str[1:]): return False
            elif actual_str != expected_str:
                return False
        return True

    def _determine_status(self, triggered):
        if not triggered:
            return 'GREEN', 'NONE'
        actions = [r.action for r in triggered]
        if 'BLOCK' in actions:
            return 'RED', 'CONTROLLER_REVIEW'
        if 'REQUIRE_DOCUMENT' in actions:
            return 'YELLOW', 'AWAITING_DOCS'
        if 'REQUIRE_AUTHORIZATION' in actions:
            return 'YELLOW', 'AWAITING_AUTH'
        if 'MANDATE' in actions:
            return 'GREEN', 'MANDATE_FOLLOW_UP'
        return 'GREEN', 'NONE'

    def evaluate_batch(self, transactions: List[Transaction]) -> Dict[str, int]:
        results = {'GREEN': 0, 'YELLOW': 0, 'RED': 0, 'ERROR': 0}
        for txn in transactions:
            try:
                res = self.evaluate_transaction(txn)
                results[res['status']] += 1
            except Exception as e:
                results['ERROR'] += 1
                txn.status = 'RED'
                txn.required_action = 'CONTROLLER_REVIEW'
                db.session.commit()
        return results