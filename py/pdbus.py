#!/usr/bin/python
# -*- coding: utf-8 -*-

import dbus
import sys, os
from xml.dom.minidom import parseString

import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

import simplejson

bus       = dbus.SystemBus()
busname   = None
buspath   = None
busmethod = None
busargs   = []

# Option parsing
for arg in sys.argv[1:]:
	if arg == '--system':
		bus = dbus.SystemBus()
	elif arg == '--session':
		bus = dbus.SessionBus()
	elif busname is None:
		busname = arg
	elif buspath is None:
		buspath = arg
	elif busmethod is None:
		busmethod = arg
	else:
		busargs.append( arg )



if busname is None:
	print "Registered Names:"
	dbusObj = dbus.Interface( bus.get_object( 'org.freedesktop.DBus', '/'), 'org.freedesktop.DBus' )
	for name in dbusObj.ListNames():
		if name[0] != ':':
			# This is a registered name, find the connection.
			print "\t%s (Owner: %s)" % ( name, dbusObj.GetNameOwner( name ) )
		else:
			print "\t%s" % name



elif busmethod is None:
	if buspath is None:
		buspath = '/'
	elif buspath[0] != '/':
		buspath = '/' + buspath
	
	print "Interfaces at %s:" % busname
	busobj = dbus.Interface( bus.get_object( busname, buspath ), 'org.freedesktop.DBus.Introspectable' )
	intro  = busobj.Introspect()
	xml    = parseString( intro )
	for iface in xml.getElementsByTagName( 'interface' ):
		print "\t%s" % iface.getAttribute( 'name' )
		for method in iface.getElementsByTagName( 'method' ):
			print "\t\t%s" % method.getAttribute( 'name' )
			for arg in method.getElementsByTagName( 'arg' ):
				print "\t\t\t%s:%s - %s" % ( arg.getAttribute( 'type' ), arg.getAttribute( 'name' ), arg.getAttribute( 'direction' ) )
		signodes = iface.getElementsByTagName( 'signal' )
		if signodes:
			print "\t    Signals:"
			for signal in signodes:
				print "\t\t%s" % signal.getAttribute( 'name' )
				for arg in signal.getElementsByTagName( 'arg' ):
					print "\t\t\t%s:%s - %s" % ( arg.getAttribute( 'type' ), arg.getAttribute( 'name' ), arg.getAttribute( 'direction' ) )
	
	print "Nodes:"
	for node  in xml.getElementsByTagName( 'node' ):
		print "\t/%s" % node.getAttribute( 'name' )



else:
	if buspath[0] != '/':
		buspath = '/' + buspath
	# Name, path, method and maybe args were given
	obj = dbus.Interface( bus.get_object( busname, buspath ), 'org.freedesktop.DBus.Introspectable' )
	
	# get Introspection
	xml  = parseString( obj.Introspect() )
	meth = None
	sig  = None
	ifc  = None
	for iface in xml.getElementsByTagName( 'interface' ):
		for method in iface.getElementsByTagName( 'method' ):
			if method.getAttribute( 'name' ) == busmethod:
				ifc  = iface
				meth = method
				break
		if meth is not None:
			break
		
		for signal in iface.getElementsByTagName( 'signal' ):
			if signal.getAttribute( 'name' ) == busmethod:
				ifc  = iface
				sig  = signal
				break
		if sig is not None:
			break
	
	if meth is None and sig is None:
		print "No such method or signal found at %s%s: %s" % ( busname, buspath, busmethod )
		sys.exit(1)
	
	if meth:
		# Check arg count
		xmlargs = [ ( arg.getAttribute('type'), arg.getAttribute('name') )
			for arg in meth.getElementsByTagName( 'arg' )
			if arg.getAttribute( 'direction' ) == 'in'
			]
		
		if len(busargs) != len(xmlargs):
			print "Wrong number of arguments given for method %s.%s; expected %d, got %d." %\
				( ifc.getAttribute('name'), busmethod, len(xmlargs), len(busargs) )
			for arg in xmlargs:
				print "%s:%s" % arg
			sys.exit(1)
		
		# format/convert arguments according to introspecshun
		datatype = {
			'i':	dbus.Int32,
			'b':	dbus.Boolean,
			'u':	dbus.UInt32,
			's':	dbus.String,
			'd':	dbus.Double,
			'f':	dbus.Double,
			'v':	dbus.String,
			}
		
		cmdargs = []
		for xmlspec in xmlargs:
			value = busargs[ xmlargs.index( xmlspec ) ]
			print "%s:%s = %s" % ( xmlspec[0], xmlspec[1], value )
			cmdargs.append( datatype[ xmlspec[0] ]( value ) )
		
		if cmdargs:
			print ""
		
		# Call DBus Method
		realobj = dbus.Interface( bus.get_object( busname, buspath ), ifc.getAttribute( 'name' ) )
		resp    = getattr( realobj, busmethod )(*cmdargs)
		
		print simplejson.dumps(resp, indent=4)
	
	elif sig:
		def signal_handler( *args ):
			print "Received signal '%s'! Args:" % busmethod
			print simplejson.dumps(args, indent=4)
		
		realobj = dbus.Interface( bus.get_object( busname, buspath ), ifc.getAttribute( 'name' ) )
		realobj.connect_to_signal( busmethod, signal_handler )
		
		print "Starting to listen. Hit ^c to exit."
		
		import gobject
		loop = gobject.MainLoop()
		try:
			loop.run()
		except KeyboardInterrupt:
			loop.quit()





