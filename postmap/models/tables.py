#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  postmap/models/tables.py
#

from postmap import db
from datetime import datetime

class Image(db.Model):
	__tablename__ = 'Images'
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.String(16))
	name = db.Column(db.String(80))
	img = db.Column(db.Text)
	width = db.Column(db.Integer)
	height = db.Column(db.Integer)
	lat = db.Column(db.Text)
	lon = db.Column(db.Text)
	shoot_time=db.Column(db.DateTime)
	time = db.Column(db.DateTime)
	
	def __init__(self, user_id=None, name=None, img=None, width=0,
	height=0, lat = None, lon = None, shoot_time = None):
		self.user_id = user_id
		self.name = name
		self.img = img
		self.width = width
		self.height = height
		self.lat = lat
		self.lon = lon
		self.shoot_time = shoot_time
		self.time = datetime.utcnow()
		
		
	def to_dict(self):
		return {'id': self.id, 'user_id': self.user_id,
		'name': self.name, 'img': self.img, 'time': self.time}
		
	def __repr__(self):
		return f'<Entry id:{self.id} user_id: {self.user_id} name:{self.name}>'

class Track(db.Model):
	__tablename__ = 'Tracks'
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.String(16))
	name = db.Column(db.String(80))
	trk = db.Column(db.Text)
	info = db.Column(db.Text)
	time = db.Column(db.DateTime)
	role = db.Column(db.String(10))
	
	def __init__(self, user_id=None, name=None, trk=None, 
	info=None, role=None):
		self.user_id = user_id
		self.name = name
		self.trk = trk
		self.info = info
		self.time = datetime.utcnow()
		self.role = role
		
		
	def to_dict(self):
		return {'id': self.id, 'user_id': self.user_id,
		'name': self.name, 'info': self.info, 'time': self.time, 'role': self.role}
		
	def __repr__(self):
		return f'<Entry id:{self.id} user_id: {self.user_id} name:{self.name}>'

class Result(db.Model):
	__tablename__ = 'Results'
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.String(16))
	role_id = db.Column(db.String(5))
	content = db.Column(db.Text)
	time = db.Column(db.DateTime)
		
	def __init__(self, user_id=None, role_id=None, content=None):
		self.user_id = user_id
		self.role_id = role_id
		self.content = content
		self.time = datetime.utcnow()
			
	def to_dict(self):
		return {'id': self.id, 'user_id': self.user_id,
		'role_id': self.role_id, 'content': self.content, 'time': self.time}
		
	def __repr__(self):
		return f'<Entry id:{self.id} user_id: {self.user_id} role_id:{self.name}>'
