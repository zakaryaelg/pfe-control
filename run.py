import csv
import io
from typing import List
from models import Transaction, Customer, db


class CSVService:
    REQUIRED = ['customer_id', 'event_type', 'amount', 'currency', 'direction', 'counterparty_country']

    def parse_csv(self, file_stream, filename: str) -> List[Transaction]:
        stream = io.StringIO(file_stream.read().decode('utf-8'))
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        missing = set(self.REQUIRED) - set(headers)
        if missing:
            raise ValueError(f"Colonnes manquantes: {missing}")

        transactions = []
        for row in reader:
            try:
                cid = row.get('customer_id', '').strip()
                if not cid: continue

                customer = db.session.get(Customer, cid)
                if not customer:
                    customer = Customer(
                        customer_id=cid, name=f"Client {cid}", customer_type='PHYSICAL',
                        primary_economic_center='CI', residency='RESIDENT'
                    )
                    db.session.add(customer)
                    db.session.commit()

                txn = Transaction(
                    customer_id=cid,
                    customer_residency_at_txn=customer.residency,
                    event_type=row.get('event_type', 'TRANSFER').strip().upper(),
                    operation_category=row.get('operation_category', 'CURRENT').strip().upper(),
                    direction=row.get('direction', 'OUTBOUND').strip().upper(),
                    amount=float(row.get('amount', 0) or 0),
                    currency=row.get('currency', 'XOF').strip().upper(),
                    counterparty_country=row.get('counterparty_country', 'FR').strip().upper(),
                    account_type=row.get('account_type', '').strip().upper() or None,
                    weight_grams=float(row.get('weight_grams', 0) or 0) if row.get('weight_grams') else None,
                    actor_type=row.get('actor_type', 'REGULAR').strip().upper(),
                    source_file=filename,
                    raw_data=dict(row),
                    status='PENDING'
                )
                transactions.append(txn)
                db.session.add(txn)
            except Exception as e:
                print(f"Erreur ligne: {e}")
                continue

        db.session.commit()
        return transactions