#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  postmap/__init__.py
#  
#  
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object('postmap.config')

db = SQLAlchemy(app)

with app.app_context():
    db.create_all()

from postmap.views import views
from postmap.models import tables
