# -*- coding: utf-8 -*-

# Set this to the same path you used in settings.py, or None for auto-detection.
PROJECT_ROOT = None;

### DO NOT CHANGE ANYTHING BELOW THIS LINE ###

import os, sys
from os.path import join, dirname, abspath, exists

# Path auto-detection
if not PROJECT_ROOT or not exists( PROJECT_ROOT ):
	PROJECT_ROOT = dirname(abspath(__file__));

# environment variables
sys.path.append( PROJECT_ROOT )
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.contrib.auth.models import User
from django import db

def check_password(environ, user, password):
	db.reset_queries() 
	
	kwargs = {'username': user, 'is_active':True, 'is_staff': True}
	
	try:
		try:
			user = User.objects.get(**kwargs)
		except User.DoesNotExist:
			return None
		
		return user.check_password(password)
	finally:
		db.connection.close()
