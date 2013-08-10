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
sys.path.append( join( PROJECT_ROOT, 'fluxmon' ) )
os.environ['DJANGO_SETTINGS_MODULE'] = 'fluxmon.settings'

from django.contrib.auth.models import User
from django import db

def check_password(environ, user, password):
	db.reset_queries()
	
	try:
		try:
			user = User.objects.get(username=user, is_active=True)
		except User.DoesNotExist:
			return None
		
		if user.check_password(password):
			return True
		
		if user.apikey_set.filter(apikey=password).count() == 1:
			return True
		
		return False
		
	finally:
		db.connection.close()
