from flask_wtf import Form
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import (DataRequired, ValidationError, Email, Length, EqualTo)

from models import User

def username_exists(form, field):
	if User.select().where(User.username == field.data).exists():
		raise ValidationError('Username already exists!')

def email_exists(form, field):
	if User.select().where(User.email == field.data).exists():
		raise ValidationError('Email already exists!')

class RegisterForm(Form):
	username = StringField(
		'Username',
		validators = [
			DataRequired(),
			username_exists
		]
	)
	email = StringField(
		'Email',
		validators = [
			DataRequired(),
			Email(),
			email_exists
		]
	)
	password = PasswordField(
		'Password',
		validators = [
			DataRequired(),
			Length(min=2),
			EqualTo('password2', message='Passwords must match')
		]
	)
	password2 = PasswordField(
		'Confirm password',
		validators = [
			DataRequired(),
		]
	)
class LoginForm(Form):
	email= StringField(
		'Email',
		validators = [
			DataRequired(),
			Email()
		]
	)
	password= PasswordField(
		'Password',
		validators = [
			DataRequired()
		]
	)

class SearchUser(Form):
	username = StringField(
		'username',
		validators = [
			DataRequired()
		]
	)
class SearchGroup(Form):
	name = StringField(
		'name',
		validators = [
			DataRequired()
		]
	)
class CreateGroupForm(Form):
	name = StringField(
		'Group name',
		validators = [
			DataRequired(),
		]
	)
	private_group = BooleanField(
		'Private group',
	)
