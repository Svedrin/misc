/**
 *  Exception handling helpers
 *
 *  <philipp> ist dir evtl. mal in den sinn gekommen
 *  <philipp> dass diese funktionen sowas wie schwarze magie sind? ;)
 *  <svedrin> ja schon
 *  <svedrin> aber die dunkle seite der macht hat einfach was, das muss man echt mal sagen -.-
 */

#include <setjmp.h>
#include <errno.h>
#include <signal.h>

#ifndef JUMPERCOUNT
#define JUMPERCOUNT 100
#endif

#define EX_FINALLY  -1
#define EX_SIGINT   -2

__thread jmp_buf jumperstack[JUMPERCOUNT];
__thread int jumperidx = -1;
__thread int finally_called = 0;
__thread int last_exception;

#define XRAISE( errcode ) if( jumperidx == -1 ){ \
		perror( "Uncaught exception" );\
		exit(1);\
	} \
	else{ \
		longjmp( jumperstack[jumperidx], errcode ); \
	}

#define XASSERT( retval ) if( retval == -1 ){ \
		XRAISE( errno ); \
	}

#define XTRY jumperidx++; \
	switch( last_exception = setjmp( jumperstack[jumperidx] ) ){\
		default: \
			if( last_exception != EX_FINALLY ){ \
				finally_called = last_exception; \
				XRAISE( EX_FINALLY ); \
			} \
			break; \
		case 0:

#define XCEPT( errcode ) break; \
		case errcode :

#define XFINALLY break; \
		case EX_FINALLY :

#define XEND break; \
	} \
	if( finally_called == 0){ \
		finally_called = EX_FINALLY; \
		XRAISE( EX_FINALLY );\
	}\
	else if( finally_called != EX_FINALLY ){ \
		jumperidx--; \
		last_exception = finally_called; \
		finally_called = 0;\
		XRAISE( last_exception ); \
	} \
	else{ \
		finally_called = 0;\
		jumperidx--; \
	}

#define XCATCHSIGINT signal(SIGINT, Xraise_sigint);

void Xraise_sigint( int sig ){
	XCATCHSIGINT
	XRAISE( EX_SIGINT );
}
