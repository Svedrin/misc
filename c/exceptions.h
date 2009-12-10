/**
 *  Exception handling helpers
 *
 *  Copyright © Michael "Svedrin" Ziegler
 *
 *  <philipp> ist dir evtl. mal in den sinn gekommen
 *  <philipp> dass diese funktionen sowas wie schwarze magie sind? ;)
 *  <svedrin> ja schon
 *  <svedrin> aber die dunkle seite der macht hat einfach was, das muss man echt mal sagen -.-
 */

#ifndef _EXCEPTIONS_H_
#define _EXCEPTIONS_H_

#include <stdlib.h>
#include <setjmp.h>
#include <errno.h>
#include <signal.h>
#include <string.h>

#ifndef JUMPERCOUNT
#define JUMPERCOUNT 100
#endif

#ifndef ERRSTRLEN
#define ERRSTRLEN 512
#endif

#define EX_FINALLY  -1
#define EX_SIGINT   -2

__thread jmp_buf ex_jumperstack[JUMPERCOUNT];
__thread int     ex_jumperidx        = -1;
__thread int     ex_finally_state    =  0;
__thread int     ex_orig_exception   =  0;
__thread char    ex_exception_string[ERRSTRLEN];

/**
 *  XRAISE, XRAISESTR: Raise an exception.
 *
 *  If after an XTRY, jumps back to it; otherwise prints an error message
 *  and exits the process.
 */
#define XRAISESTR( errcode, message ) { \
		if( errcode != EX_FINALLY && errcode != ex_orig_exception ){ \
			memcpy( &ex_exception_string, message, ERRSTRLEN ); \
			} \
		if( ex_jumperidx == -1 ){ \
			fprintf( stderr, "Uncaught exception %s\n", (char *)&ex_exception_string );\
			exit(1);\
		} \
		else{ \
			longjmp( ex_jumperstack[ex_jumperidx], errcode ); \
		} \
	}

#define XRAISE( errcode ) XRAISESTR( errcode, #errcode )

/**
 *  XASSERT: Shortcut to XRAISE( errno ) if the assertion fails.
 */
#define XASSERT( boolval ) { \
		if( !(boolval) ){ \
			XRAISESTR( errno, strerror( errno ) ); \
		} \
	}

/**
 *  XTRY: Sets up the jumper.
 *
 *  Since the currently raised exception is evaluated using a switch(), setjmp
 *  is called in the switch's conditional statement.
 *  The "default" handler is used to reraise an exception after FINALLY has been called.
 */
#define XTRY ex_jumperidx++; \
	switch( ex_orig_exception = setjmp( ex_jumperstack[ex_jumperidx] ) ){\
		default: \
			if( ex_orig_exception != EX_FINALLY ){ \
				ex_finally_state = ex_orig_exception; \
				XRAISE( EX_FINALLY ); \
			} \
			else{ \
				ex_jumperidx--; \
			} \
			break; \
		case 0:

/**
 *  XCEPT: Define an exception handler.
 */
#define XCEPT( errcode ) break; \
		case errcode :

/**
 *  XFINALLY: Define a handler that is called regardless of whether or not an exception
 *  has been raised.
 *
 *  This decrements the jumperidx in order to allow XRAISEs inside the XFINALLY handler.
 */
#define XFINALLY break; \
		case EX_FINALLY : \
			ex_jumperidx--;

/**
 *  XEND: Mark the end of the "try/except" block.
 *
 *  This is also the place where calling the FINALLY handler is implemented.
 */
#define XEND break; \
	} \
	if( ex_finally_state == 0){ \
		ex_finally_state = EX_FINALLY; \
		XRAISE( EX_FINALLY );\
	}\
	else if( ex_finally_state != EX_FINALLY ){ \
		ex_orig_exception = ex_finally_state; \
		ex_finally_state = 0;\
		XRAISE( ex_orig_exception ); \
	} \
	else{ \
		ex_finally_state = 0;\
	}

/**
 *  XCATCHSIGINT: Installs an exception handler to raise EX_SIGINT when SIGINT occurs.
 */
#define XCATCHSIGINT signal(SIGINT, Xraise_sigint);

void Xraise_sigint( int sig ){
	XCATCHSIGINT
	XRAISE( EX_SIGINT );
}

#endif
