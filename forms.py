from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import User


class LoginForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[
        DataRequired(message='Ce champ est obligatoire.'),
        Length(min=3, max=80)
    ])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message='Ce champ est obligatoire.')
    ])
    remember_me = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')


class CreateUserForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[
        DataRequired(),
        Length(min=3, max=80)
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Email invalide.')
    ])
    full_name = StringField('Nom complet', validators=[
        DataRequired(),
        Length(max=100)
    ])
    role = SelectField('Rôle', choices=[
        ('controller', 'Contrôleur'),
        ('admin', 'Administrateur')
    ], validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(),
        Length(min=6, message='Minimum 6 caractères.')
    ])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(),
        EqualTo('password', message='Les mots de passe ne correspondent pas.')
    ])
    submit = SubmitField('Créer l\'utilisateur')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ce nom d\'utilisateur existe déjà.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Cet email est déjà utilisé.')