# RFE Control  — Digitalisation du Référentiel UEMOA

## Contexte
Règlement n°06/2024/CM/UEMOA relatif aux Relations Financières Extérieures des États membres de l'UEMOA.

## Objectif
Transformer un document réglementaire de 17 pages en un **système de conformité exécutable**.

## Architecture
- **Backend** : Flask + SQLAlchemy + WTForms
- **Base de données** : SQLite (PostgreSQL-ready)
- **Règles** : Moteur JSON/DB avec 36 articles digitalisés
- **Frontend** : Jinja2 + CSS vanilla

## Fonctionnalités
1. Automatisation : Évaluation automatique des transactions contre le référentiel
2. Exceptions : Dashboard contrôleur avec alertes colorées (RED/YELLOW)
3. Outils complémentaires : Arbre de décision HTML + Excel
4.Audit : Traçabilité complète des décisions

## Démarrage
bash
pip install -r requirements.txt
python init_db.py
python app.py
