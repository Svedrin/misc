/**
 *  Exception handling helpers
 *
 *  <philipp> ist dir evtl. mal in den sinn gekommen
 *  <philipp> dass diese funktionen sowas wie schwarze magie sind? ;)
 *  <svedrin> ja schon
 *  <svedrin> aber die dunkle seite der macht hat einfach was, das muss man echt mal sagen -.-
 */

#include <setjmp.h>

#ifndef JUMPERCOUNT
#define JUMPERCOUNT 100
#endif

__thread jmp_buf jumperstack[JUMPERCOUNT];
__thread int jumperidx = -1;
__thread int finally_called = 0;
__thread int last_exception;

#define XRAISE( errcode ) if( jumperidx == -1 ){ \
		perror( "Uncaught exception!" );\
	} \
	else{ \
		longjmp( jumperstack[jumperidx], errcode ); \
	}

#define XTRY jumperidx++; \
	switch( last_exception = setjmp( jumperstack[jumperidx] ) ){\
		default: \
			finally_called = last_exception; \
			XRAISE( -1 ); \
			break; \
		case 0:

#define XCEPT( errcode ) break; \
		case errcode :

#define XFINALLY break; \
		case -1:

#define XEND break; \
	} \
	if( finally_called == 0){ \
		finally_called = -1; \
		XRAISE( -1 );\
	}\
	else if( finally_called > 0 ){ \
		jumperidx--; \
		last_exception = finally_called; \
		finally_called = 0;\
		XRAISE( last_exception ); \
	} \
	else{ \
		finally_called = 0;\
		jumperidx--; \
	}

