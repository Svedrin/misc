# -*- coding: utf-8 -*-

# http://thedailywtf.com/Articles/Programming-Praxis-Russian-Peasant-Multiplication.aspx
# russische Bauernmultiplikation - sehr simple rekursive Implementierung. :)
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

def mult( a, b ):
	if a == 1:
		return b;
	ret = mult( int(a / 2), b * 2 );
	if a % 2 == 0:
		return ret;
	else:
		return ret + b;

if __name__ == '__main__':
	print mult( 18, 23 );


# ja, mir war langweilig.
