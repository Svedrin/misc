#include <stdio.h>
#include "exceptions.h"

#define KlukException 1
#define OhNoezException 2
#define EpicFailException 3

int main( int argc, char *argv[] ){
	if( argc > 4 )
		XRAISE( EpicFailException );
	
	XTRY{
		printf( "Ich bin so klug!\n" );
		
		XTRY{
			if( argc > 3 )
				XRAISE( EpicFailException );
			
			if( argc > 2 )
				XRAISE( KlukException );
			
			if( argc > 1 )
				XRAISE( OhNoezException );
		}
		XCEPT( OhNoezException ){
			printf( "Oh noez!\n" );
		}
		XFINALLY{
			printf( "Na endlich innen\n" );
		}
		XEND
	}
	XCEPT( KlukException ){
		printf( "K l u k!\n" );
	}
	XFINALLY{
		printf( "Na endlich außen\n" );
	}
	XEND
	
	return 0;
}
