#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys

#import os
#os.system('whoami')

from me42 import Me42

try:
	m = Me42();
	mode, value, unit = m.readOnce();

except ValueError:
	pass;

else:
	if sys.argv[-1] == 'config':
		print """graph_vlabel %s %s
graph_args --base 1000
graph_title Multimeter value
graph_category sensors
ttyS0.label Stromstaerke Gatekeeper""" % ( mode, unit );
	
	else:
		print "ttyS0.value %f" % value;

finally:
	m.close();

