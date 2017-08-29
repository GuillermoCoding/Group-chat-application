import datetime

from flask_bcrypt import generate_password_hash
from flask_login import UserMixin
from peewee import * 

DATABASE = PostgresqlDatabase('guillermo',user='guillermo',host='localhost',password='guillermo')

class User( UserMixin, Model ):
	username = CharField(unique=True)
	email = CharField(unique=True)
	password = CharField(max_length=100)
	joined_at = DateTimeField(default = datetime.datetime.now)

	class Meta:
		database = DATABASE
		ordering = ('-joined_at')

	def get_groups(self):
		return (
			Group.select().join( GroupMember, on = GroupMember.group).where(GroupMember.user == self)
		)
	def get_created_groups(self):
		return (
			Group.select().where(Group.creator == self)
		)
	def get_joined_groups(self):
		return (
			Group.select().join( GroupMember, on = GroupMember.group).where(GroupMember.user == self, Group.creator != self)
		)
	def get_active_group(self):
		return Group.select().join( GroupMember, on = GroupMember.group).where(GroupMember.user == self, GroupMember.active == True).get() 
	
	@classmethod
	def create_user(cls, username, email, password):
		try:
			with DATABASE.transaction():
				user = cls.create(
								username = username,
								email = email,
								password= generate_password_hash(password)
						 	 )
		  	return user
		except IntegrityError:
			raise ValueError('User already exists')

class Relationship(Model):
	from_user = ForeignKeyField(
		rel_model = User,
		related_name = 'relationships'
	)
	to_user = ForeignKeyField(
		rel_model = User,
		related_name = 'related_to'
	)
	confirmed = BooleanField(default = False)
	class Meta:
		database = DATABASE
		
		indexes = (
			(('from_user','to_user'), True),
		)
		
class Group(Model):
	name = CharField(unique=True)
	creator = ForeignKeyField(
		rel_model = User,
		related_name='creator'
	)
	private = BooleanField()
	class Meta:
		database = DATABASE
	def get_messages(self):
		messages = Message.select().order_by(-Message.id).where(Message.group == self).limit(20)
		return list(reversed(messages))

	def get_members(self):
		return GroupMember.select().where(GroupMember.group == self)
	def number_of_total_messages(self):
		number = Message.select().order_by(-Message.id).where(Message.group == self).count()
		return number


class GroupMember(Model):
	group = ForeignKeyField(
		rel_model = Group,
		related_name='group'
	)
	user = ForeignKeyField(
		rel_model = User,
		related_name='user'
	)
	active = BooleanField( default = False)
	class Meta:
		database = DATABASE
		indexes = (('group', 'user'), True)

class Message(Model):
	group = ForeignKeyField(
		rel_model = Group,
		related_name='message in group'
	)
	user = ForeignKeyField(
		rel_model = User,
		related_name = 'message owner'
	)
	content = CharField()
	timestamp = DateTimeField(default = datetime.datetime.now)
		
	class Meta:
		database = DATABASE
		ordering = ('-timestamp')

def initialize():
	DATABASE.connect()
	DATABASE.create_tables([User, Relationship, Group, GroupMember, Message], safe=True)
	DATABASE.close()



