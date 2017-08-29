from flask import session, Flask, g, render_template, flash, redirect, url_for, request
from flask_login import (	LoginManager, 
													logout_user, 
													login_user, 
													current_user, 
													login_required,
													user_logged_out )
from flask_bcrypt import check_password_hash
from flask_socketio import SocketIO, emit, join_room, leave_room
from playhouse.shortcuts import model_to_dict, dict_to_model
import models
import forms
import json
import datetime

app = Flask(__name__)
app.secret_key = 'jkskfh4khfjshfs'
socketio = SocketIO(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
current_room = None
@login_manager.user_loader
def load_user(user_id):
	try:
		return models.User.get(models.User.id == user_id)
	except models.DoesNotExist:
		return None

@app.before_request
def before_request():
	models.DATABASE.get_conn()

@app.after_request
def after_request(response):
	models.DATABASE.close()
	return response

@app.route('/')
def index():
	return render_template('layout.html', user = current_user)

@app.route('/register',methods=['POST','GET'])
def register():
	form = forms.RegisterForm()
	if form.validate_on_submit():
		user = models.User.create_user(
						username= form.username.data,
						email = form.email.data,
						password = form.password.data
					 )
		login_user(user)
		return redirect(url_for('profile'))
	return render_template('register.html', form = form)

@app.route('/login', methods=['POST','GET'])
def login():
	form = forms.LoginForm()
	if form.validate_on_submit() :
		try:
			user = models.User.get(models.User.email == form.email.data)
		except:
			flash('Email or password is not correct', 'error')
		else:
			if check_password_hash(user.password, form.password.data) :
				login_user(user)
				print(current_user.username)
				data = { 'room' : current_user.username }
				
				return redirect(url_for('profile'))
			else:
				flash('Email or password is not correct', 'error')
	return render_template('login.html', form = form)

@app.route('/logout')
def logout():
	socketio.emit('user-logged-out')
	logout_user()
	return redirect(url_for('index'))

@app.route('/profile')
@app.route('/profile/<username>')
@login_required
def profile(username = None):
	if username:
		if current_user.username != username:
			user = models.User.get(models.User.username == username)
		else:
			user = current_user
	else:
		user = current_user
	return render_template('profile.html', user = user)

@app.route('/find-users', methods=['GET','POST'])
def find_users():
	form = forms.SearchUser()
	if form.validate_on_submit():
		users = models.User.select().where(models.User.username.contains(form.username.data))
		if not users:
			flash('No users found', 'error')
		return render_template('find-users.html', form=form, users = users)
	return render_template('find-users.html', form = form )

@app.route('/create-group', methods=['GET','POST'])
def create_group():
	form = forms.CreateGroupForm()
	print('form fields : ', form.name.data , form.private_group.data, form.validate_on_submit() )
	if form.validate_on_submit():
		print('create group validating')
		try:
			group = models.Group.create (
				name = form.name.data,
				creator = current_user._get_current_object(),
				private = form.private_group.data
			)
			models.GroupMember.create(
				group = group,
				user = current_user._get_current_object()
			)
		except models.IntegrityError:
			pass
		else:
			return redirect(url_for('profile'))
	return render_template('create-group.html', form = form)

@app.route('/find-group', methods=['POST','GET'])
def find_group():
	form = forms.SearchGroup()
	if form.validate_on_submit():
		groups = models.Group.select().where(models.Group.name.contains(form.name.data))
		if not groups:
			flash('No groups found', 'error')
		return render_template('find-groups.html', form = form, groups = groups)
	return render_template('find-groups.html', form = form)

@app.route('/join-group/<group_name>', methods=['POST','GET'])
def join_group(group_name):
	try:
		group = models.Group.get(models.Group.name == group_name)
	except models.DoesNotExist:
		pass
	else:
		models.GroupMember.create(
			group = group,
			user = current_user._get_current_object()
		)
	socketio.emit('user-join-group', data = current_user.username, room = group.name, namespace='/group')
	return redirect(url_for('profile'))

@app.route('/unjoin-group/<group_name>',methods=['POST','GET'])
def unjoin_group(group_name):
	try:
		group = models.Group.get(models.Group.name == group_name)
		groupMember = models.GroupMember.get(models.GroupMember.user == current_user._get_current_object(), models.GroupMember.group == group)
		groupMember.delete_instance()
	except models.DoesNotExist:
		pass
	else:
		socketio.emit('user-unjoin-group', data = current_user.username, room = group_name, namespace='/group')
	return redirect(url_for('profile'))
		
@app.route('/delete-group/<group_name>', methods=['POST','GET'])
def delete_group(group_name):
	try:
		group = models.Group.get(models.Group.name == group_name)
		message_query = models.Message.delete().where(models.Message.group == group)
		message_query.execute()
		group_member_query = models.GroupMember.delete().where(models.GroupMember.group == group)
		group_member_query.execute()
		group.delete_instance()
	except:
		pass
	socketio.emit('group-deleted', room = group_name, namespace='/group')
	return redirect(url_for('profile'))

@socketio.on('message-send', namespace='/group')
def message_send(data):
	group = models.Group.get(models.Group.name == data['room'])
	user = current_user._get_current_object()
	content = data['message']
	message = models.Message.create(
							group = group,
							user = user,
							content = content
						)
	message_data = {}
	message_data['id'] = message.id
	message_data['user'] = message.user.username
	message_data['content'] = message.content
	message_data['timestamp'] = message.timestamp.strftime('%I:%M:%S %p %m/%d/%Y')
	json_data = json.dumps(message_data)
	socketio.emit('response', json_data , room = data['room'], namespace='/group')

@socketio.on('user-typing', namespace='/group')
def user_typing(data):
	socketio.emit('user-typing-response', current_user.username, include_self=False, room=data['room'], namespace='/group')

@socketio.on('user-not-typing', namespace='/group')
def user_typing(data):
	socketio.emit('user-not-typing-response', current_user.username, include_self=False, room=data['room'], namespace='/group')


@app.route('/group/<id>')
def group(id):
	try:
		group = models.Group.get(models.Group.id == id)
	except:
		pass
	else:
		return render_template('group.html', group = group)

@socketio.on('load-more', namespace='/group')
def load_more(data):
	group = models.Group.select().where(models.Group.name == data['groupName'])
	messages = models.Message.select().order_by(-models.Message.id).where(models.Message.group == group, models.Message.id < int(data['lastMessageId'])).limit(20)
	json_messages = []
	for message in messages:
		message_data = {}
		message_data['id'] = message.id
		message_data['user'] = message.user.username
		message_data['content'] = message.content
		message_data['timestamp'] = message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
		json_messages.append(message_data)
	socketio.emit('load-more-response', data = json_messages, room = request.sid , namespace='/group')

@socketio.on('join', namespace='/group')
def join(data):
	try:
			group_model = models.Group.get(models.Group.name == data['room'])		
			group_member = models.GroupMember.get(models.GroupMember.user == current_user._get_current_object() , models.GroupMember.group == group_model)	
			group_member.active = True
			group_member.save()
			active_group = current_user._get_current_object().get_active_group()
	except:
		pass
	print(data)
	join_room(data['room'])
	socketio.emit( 'user-joined', data = current_user.username, room = data['room'], namespace='/group' )

	

@socketio.on('disconnect', namespace='/group')
def user_unjoined():
	active_group = current_user._get_current_object().get_active_group()
	print('Disactivating group..', current_user.username, active_group.name)
	group_member = models.GroupMember.get(models.GroupMember.user == current_user._get_current_object() , models.GroupMember.group == active_group)	
	group_member.active = False
	group_member.save()
	leave_room(active_group.name)
 	socketio.emit('user-unjoined', data = current_user.username, room=active_group.name, namespace='/group')

@app.route('/add/<username>', methods=['GET','POST'])
@login_required
def add(username = None):
	try:
		to_user = models.User.get(models.User.username == username)
	except models.DoesNotExist:
		pass
	else:
		try:
			models.Relationship.create(
				from_user = current_user._get_current_object(),
				to_user = to_user
			)
		except models.IntegrityError:
			pass
		else:
			return redirect(url_for('find_users'))
		return redirect(url_for('find_users'))


if __name__=='__main__':
	models.initialize()
	socketio.run(app,debug=True)