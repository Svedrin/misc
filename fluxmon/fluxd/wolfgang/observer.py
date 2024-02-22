# -*- coding: utf-8 -*-

"""
 *  Copyright (C) 2009, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
 *
 *  Omikron is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This package is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
"""

from copy import deepcopy

class OperationCanceled( Exception ):
    """ Can be fired by a listener function to cancel the signal. """
    pass

class Listener( object ):
    """ Prepares args for and calls the observer function. """

    def __init__( self, func, args, kwargs ):
        """ Creates a listener associated with func, and stores base args to be
            passed to func when the event is fired.
        """
        self.func     = func
        self.args     = args
        self.kwargs   = kwargs

    def __call__( self, *args, **kwargs ):
        """ Call the associated listener function and merge our args to the base args. """
        origkw = deepcopy( self.kwargs )
        origkw.update( kwargs )
        return self.func( *( self.args + args ), **origkw )


class Signal( object ):
    """ Handles calling the Listener functions and canceling of events. """

    def __init__( self, cancel = True ):
        self.cancel    = cancel
        self.exception = None
        self.listeners = []

    def __call__( self, *args, **kwargs ):
        """ Call observers. If this signal can be canceled and one of the listeners
            returns False, cancel execution and return False, otherwise return True.
        """
        self.exception = None
        for lst in self.listeners:
            try:
                ret = lst( *args, **kwargs )
            except OperationCanceled, instance:
                self.exception = instance
                return False
            else:
                if self.cancel and ret == False:
                    return False
        return True

    def addListener( self, func, *args, **kwargs ):
        """ Add func as a listener to this signal. """
        assert callable( func ), "Listeners must be callable!"
        self.listeners.append( Listener( func, args, kwargs ) )

    def removeListener( self, func ):
        """ Remove the first listener that is associated to func. """
        entry = None
        for lst in self.listeners:
            if lst.func == func:
                entry = lst
                break
        if entry:
            self.listeners.remove( entry )
        return entry


class Dispatcher( object ):
    """ Keeps track of existing events and handles firing. """

    def __init__( self ):
        self.signals = {}

    def addEvent( self, event, cancel = True ):
        """ Add a Signal handler for an event.

            This does NOT check if another handler already exists. If so, the old one will be overwritten.
        """
        self.signals[event] = Signal( cancel )

    def removeEvent( self, event ):
        """ Remove the Signal handler for the given event. """
        sig = self.signals[event]
        del self.signals[event]
        return sig

    def fireEvent( self, event, *args, **kwargs ):
        """ Fire an event. """
        sig = self.signals[event]
        return sig( *args, **kwargs )

    def hasEvent( self, event ):
        """ Return True if an event of the given name is known. """
        return ( event in self.signals )

    def __getitem__( self, event ):
        """ Get an event handler. """
        return self.signals[event]

    def __setitem__( self, event, cancel ):
        """ Shortcut for addEvent. """
        self.addEvent( event, cancel )

    def __contains__( self, event ):
        """ Shortcut for hasEvent. """
        return self.hasEvent( event )

    def __delitem__( self, event ):
        """ Shortcut for removeEvent. """
        return self.removeEvent( event )

    def __call__( self, event, *args, **kwargs ):
        """ Shortcut for fireEvent. """
        return self.fireEvent( event, *args, **kwargs )
