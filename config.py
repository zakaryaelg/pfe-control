import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uemoa-rfe-pfe-2024-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///rfe_control.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-WTF CSRF protection
    WTF_CSRF_ENABLED = True