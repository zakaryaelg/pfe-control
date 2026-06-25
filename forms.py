from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, FileField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, ValidationError
from flask_wtf.file import FileAllowed, FileRequired
from models import User


class LoginForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember_me = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')


class CreateUserForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Nom complet', validators=[DataRequired(), Length(max=100)])
    role = SelectField('Rôle', choices=[('controller', 'Contrôleur'), ('admin', 'Administrateur')],
                       validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmer', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Créer')

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError('Ce nom existe déjà.')

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError('Cet email existe déjà.')


class UploadTransactionsForm(FlaskForm):
    csv_file = FileField('Fichier CSV', validators=[FileRequired(), FileAllowed(['csv'], 'CSV uniquement')])
    submit = SubmitField('Uploader et Évaluer')


class AlertDecisionForm(FlaskForm):
    decision = SelectField('Décision', choices=[
        ('APPROVED', 'Approuver — Transaction conforme'),
        ('REJECTED', 'Rejeter — Blocage confirmé'),
        ('PENDING', 'Mettre en attente — En cours d\'instruction'),
    ], validators=[DataRequired()])
    notes = TextAreaField('Notes du contrôleur', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Enregistrer la décision')


class EditUserForm(FlaskForm):
    full_name = StringField('Nom complet', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Rôle', choices=[('controller', 'Contrôleur'), ('admin', 'Administrateur')],
                       validators=[DataRequired()])
    is_active = BooleanField('Compte actif')
    submit = SubmitField('Enregistrer les modifications')

    def __init__(self, original_email=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        if email.data != self.original_email:
            if User.query.filter_by(email=email.data).first():
                raise ValidationError('Cet email est déjà utilisé.')