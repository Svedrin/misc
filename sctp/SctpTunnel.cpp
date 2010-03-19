
#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/sctp.h>
#include <netdb.h>
#include <arpa/inet.h>

#include <cerrno>

#include "config.h"
#include "SctpTunnel.h"


SctpTunnel::SctpTunnel( SctpConnection *conn, int stream, const char *addr, int port ){
	this->conn   = conn;
	this->stream = stream;
	this->shutdown = false;
}

SctpTunnel::~SctpTunnel(){
}

int SctpTunnel::send( void* data, int datalen ){
	return ::send( tcp_sockfd, data, datalen, 0 );
}


SctpTunnelClient::SctpTunnelClient( SctpConnection *conn, int stream, const char* addr, int port )
		: SctpTunnel( conn, stream, addr, port ){
	
	struct sockaddr_in servaddr;
	
	servaddr.sin_family      = AF_INET;
	servaddr.sin_addr.s_addr = inet_addr(addr);
	servaddr.sin_port        = htons(port);
	
	tcp_sockfd = socket( PF_INET, SOCK_STREAM, 0 );
	::connect( tcp_sockfd, (sockaddr*)&servaddr, sizeof(servaddr) );
}

SctpTunnelClient::~SctpTunnelClient(){
}

void SctpTunnelClient::run(){
	printf( "TunCli running!\n" );
	char buffer[BUFSIZE];
	int  datalen = 0;
	errno = 0;
	do{
		datalen = recv( tcp_sockfd, (void*)&buffer, BUFSIZE, 0 );
		if( datalen > 0 )
			conn->send( stream, (void*)&buffer, datalen );
	} while( datalen != -1 && errno != 0 && !shutdown );
	conn->err( stream, errno );
	close( tcp_sockfd );
	printf( "TunCli finished\n" );
}


SctpTunnelServer::SctpTunnelServer( SctpConnection *conn, int stream, const char* addr, int port )
		: SctpTunnel( conn, stream, addr, port ){
	
	struct sockaddr_in servaddr;
	
	servaddr.sin_family      = AF_INET;
	servaddr.sin_addr.s_addr = inet_addr(addr);
	servaddr.sin_port        = htons(port);
	
	tcp_sockfd = socket( PF_INET, SOCK_STREAM, 0 );
	bind(   tcp_sockfd, (sockaddr*)&servaddr, sizeof(servaddr) );
}

SctpTunnelServer::~SctpTunnelServer(){
}

void SctpTunnelServer::run(){
	printf( "TunSrv running!\n" );
	char buffer[BUFSIZE];
	int  datalen = 0;
	if( listen( tcp_sockfd, 5 ) == -1 ){
		perror( "listen fail" );
		return;
	}
	shutdown = false;
	errno = 0;
	while( !shutdown ){
		int connfd = accept( tcp_sockfd, NULL, 0 );
		if( listen( tcp_sockfd, 5 ) == -1 ){
			perror( "accept fail" );
			return;
		}
		do{
			datalen = recv( connfd, (void*)&buffer, BUFSIZE, 0 );
			if( datalen > 0 )
				conn->send( stream, (void*)&buffer, datalen );
		} while( datalen != -1 && errno == 0 && !shutdown );
		conn->err( stream, errno );
		close(connfd);
	}
	close( tcp_sockfd );
	printf( "TunSrv running!\n" );
}
