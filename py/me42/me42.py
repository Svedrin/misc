# -*- coding: utf-8 -*-

# Impfos:   http://home.arcor.de/bernd_kunze/selfprog.htm
# pySerial: http://pyserial.wiki.sourceforge.net/pySerial

import datetime, time, serial, re
from serial import *


class Me42( serial.Serial ):
	# Multiplikatoren, um z.b. mV in V umzurechnen
	mult = {
		'':           1.0,
		'm': 1.0 / 1000.0,
		'k':       1000.0,
		'M':    1000000.0,
		'G': 1000000000.0,
		};
	
	# Messgerät returned:
	# AC  133.0  mA   - Wechselstrom
	# AC  00.00   A   - Wechselstrom 20A
	# DC -000.0  mA   - Gleichstrom
	# DC -00.00   A   - Gleichstrom 20A
	# OH   O.L MOhm   - Widerstand
	# DI    OL   mV   - Diode
	# AC  049.6  mV   - Wechselspannung
	# DC  000.2  mV   - Gleichspannung
	regex = re.compile( r'(?P<mode>AC|DC|OH|DI)\s*(?P<value>-?[\d.L]+)\s*(?P<fac>(m|k|M|G)?)(?P<unit>A|V|Ohm)' );
	
	def __init__( self, tty = "/dev/ttyS0", baud = 600, timeout = 5 ):
		serial.Serial.__init__( self,
			tty,
			baudrate = baud, # populaer sind hier 600, 1200, 2400, 4800, 9600
			bytesize = SEVENBITS,
			parity   = PARITY_NONE,
			stopbits = STOPBITS_TWO,
			timeout  = timeout
			);
		
		# Stromversorgung des Optokopplers im DMM erfolgt über die serielle Schnittstelle
		# des PCs, daher: DTR auf +12V, RTS auf -12V
		self.setDTR( True  );
		self.setRTS( False );
	
	def readOnce( self ):
		self.write("D\n");   # Befehl zum DMM senden
		msg = self.read(14); # Antwort: ein 14 byte großer String
		
		match = Me42.regex.match( msg );
		
		if match is None:
			raise ValueError( "Message is empty or malformed - is DMM on?", msg );
		
		val = match.group( 'value' );
		if val.find( 'L' ) >= 0:
			val = None;
		else:
			val = float(val) * Me42.mult[match.group('fac')];
		
		return (match.group( 'mode' ),
			val,
			match.group( 'unit' ));
	
	def readInterval( self, callback, interval=0.5 ):
		while(True):
			callback( *self.readOnce() );
			time.sleep( interval );


if __name__ == '__main__':
	me42 = Me42();
	
	def ausgabe( mode, value, unit ):
		print "%s -- Modus: %s -- %f %s" % ( datetime.datetime.now(), mode, value, unit );
	
	
	try:
		me42.readInterval( ausgabe );
	
	except KeyboardInterrupt:
		print "\nCaugt ^c, bye";
	
	finally:
		me42.close();


