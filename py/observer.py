#!/usr/bin/python

# Example implementation of the Observer pattern
# http://de.wikipedia.org/w/index.php?title=Observer_(Entwurfsmuster)&stableid=59263476
# Michael "Svedrin" Ziegler <michael@mumble-django.org>

class Subject( object ):
	'Subject class that observers can register with.'
	
	def __init__( self ):
		self.observers = [];
		self._x = None;
	
	# Observer management
	
	def register( self, observer ):
		'Registers an observer.'
		if observer not in self.observers:
			self.observers.append( observer );
	
	def unregister( self, observer ):
		'Unregisters an observer.'
		if observer in self.observers:
			self.observers.remove( observer );
	
	def notify( self, event, *args, **kwargs ):
		'Notify registered observers about an event'
		for observer in self.observers:
			# Get and call the method associated with this event.
			func = getattr( observer, event );
			func( *args, **kwargs );
	
	# Some events to fire
	
	def firstEvent( self, arg ):
		'Simulate an event'
		self.notify( 'onFirstEvent', arg );
	
	def secondEvent( self, **kwargs ):
		'Simulate another event'
		self.notify( 'onSecondEvent', **kwargs );
	
	def set_x( self, x ):
		'Setter for the x field, that fires an event when the value is changed.'
		oldValue = self._x;
		self._x = x;
		self.notify( 'onX', old = oldValue, new = x );
	
	x = property( lambda self: self._x, set_x );
	

class Observer( object ):
	'Observer class to be registered with our Subject.'
	
	def __init__( self, name ):
		self.name = name;
	
	def onFirstEvent( self, arg ):
		'Notification about first event'
		print "%s: First Event fired. Arg: %s" % ( self.name, arg );
	
	def onSecondEvent( self, arg, argOne = None, argTwo = None ):
		'Notification about second event'
		print "%s: Second Event fired. Arg: %s, ArgOne: %s, ArgTwo: %s" % ( self.name, arg, argOne, argTwo );
	
	def onX( self, old, new ):
		'Notification about changed value'
		print "%s: X changed from %s to %s." % ( self.name, str(old), str(new) );


if __name__ == '__main__':
	# Instantiate Subject
	subj = Subject();
	
	# Instantiate Observers
	obs1 = Observer( 'FirstObs' );
	obs2 = Observer( 'SecndObs' );
	
	# Fire a few events without any observers regged
	subj.secondEvent( arg = "No-one", argOne = "will ever", argTwo = "know" );
	subj.x = 10;
	
	# Register an observer
	subj.register( obs1 );
	
	subj.firstEvent( "Fire" );
	
	# Register another one
	subj.register( obs2 );
	
	subj.secondEvent( arg = "in", argTwo = "the" );
	subj.x += 15;
	
	# Unregister the first one
	subj.unregister( obs1 );
	
	subj.firstEvent( "hole!" );

