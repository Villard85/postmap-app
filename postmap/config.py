#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  fload/config.py
# 
import os

DEBUG = os.environ.get("DEBUG")
SECRET_KEY = os.environ.get("SECRET_KEY")
SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE")
SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")
SQLALCHEMY_TRACK_MODIFICATIONS = False
MAX_CONTENT_LENGTH = 1024*1024*20
UPLOAD_EXTENSIONS = ['gpx']
IMG_EXTENSIONS = ['jpg']
