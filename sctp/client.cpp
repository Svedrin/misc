
#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <cerrno>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/sctp.h>
#include <netdb.h>
#include <arpa/inet.h>

#include "config.h"
#include "SctpConnection.h"

int main( int argc, char** argv ){
	if( argc != 3 ){
		printf( "Usage: %s <address> <port>\n", argv[0] );
		return 1;
	}
	
	int connfd;
	struct sockaddr_in servaddr;
	
	servaddr.sin_family      = AF_INET;
	servaddr.sin_addr.s_addr = inet_addr( argv[1] );
	servaddr.sin_port        = htons( atoi(argv[2]) );
	
	connfd = socket( PF_INET, SOCK_STREAM, IPPROTO_SCTP );
	printf( "Isch kandidiere\n" );
	if( ::connect( connfd, (struct sockaddr *)&servaddr, sizeof(struct sockaddr) ) == -1 ){
		perror( "connect fail" );
		return 1;
	}
	printf( "funzt\n" );
	
	SctpConnection conn( connfd );
	conn.start();
	
	conn.cmd_createtun( "0.0.0.0", 31337, false, "127.0.0.1", 54321 );
	
	conn.wait();
	
	return 0;
}

