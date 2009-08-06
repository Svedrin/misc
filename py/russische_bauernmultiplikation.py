# -*- coding: utf-8 -*-
#
# http://thedailywtf.com/Articles/Programming-Praxis-Russian-Peasant-Multiplication.aspx
#
# russische Bauernmultiplikation - nicht mehr ganz so simple iterative Implementierung,
# die ohne Multiplikation und Modulo-Operation auskommt und nur Bit-Operationen verwendet.
#
# a * b multiplizieren:
#
# 18 * 23
#
# 18 *  23
#  9 *  46      46
#  4 *  92        ` +  = 414
#  2 * 184        /
#  1 * 368     386
#
# solange a halbieren und b verdoppeln, bis a = 1, und dann alle bs addieren,
# die in zeilen mit ungradem a stehen.
#

def mult( a, b ):
	sum = 0;
	while a > 0:
		if ( a & 1 ) == 1:
			sum += b;
		a >>= 1;
		b <<= 1;
	return sum;


if __name__ == '__main__':
	import sys
	args = sys.argv[-2:];
	if len( args ) == 2:
		intargs = [ int(arg) for arg in args ];
	else:
		intargs = ( 18, 23 );
	
	print u"%d · %d = %d" % ( intargs[0], intargs[1], mult( *intargs ) );


# ja, mir war langweilig.
