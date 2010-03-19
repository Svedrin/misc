
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
	int listenfd, connfd;
	struct sockaddr_in servaddr;
	
	servaddr.sin_family      = AF_INET;
	servaddr.sin_addr.s_addr = inet_addr(BIND_ADDR);
	servaddr.sin_port        = htons(BIND_PORT);
	
	listenfd = socket( PF_INET, SOCK_STREAM, IPPROTO_SCTP );
	if( bind( listenfd, (struct sockaddr *)&servaddr, sizeof(struct sockaddr) ) == -1 ){
		perror( "Bind fail" );
		return 1;
	}
	
	if( listen( listenfd, 5 ) == -1 ){
		perror( "listen fail" );
		return 1;
	}
	
	while( true ){
		printf( "We accept him one of us!\n" );
		connfd = accept( listenfd, NULL, 0 );
		printf( "Got one!\n" );
		SctpConnection conn( connfd );
		conn.start();
		conn.wait();
	}
	
	close( listenfd );
	return 0;
}

