
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>
#include <cerrno>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/sctp.h>
#include <netdb.h>

#include "config.h"
#include "SctpConnection.h"

SctpConnection::SctpConnection( int sockfd ){
	sctp_sockfd = sockfd;
	shutdown = false;
}

SctpConnection::~SctpConnection(){
}

int SctpConnection::send( int stream, void *data, int datalen ){
	return sctp_sendmsg( sctp_sockfd, data, (size_t)datalen,
		NULL, 0, 0, 0, stream, 0, 0 );
}

void SctpConnection::run(){
	printf( "Conn running!\n" );
	char buffer[BUFSIZE];
	int  datalen = 0, flags, stream;
	sctp_sndrcvinfo sndrcvinfo;
	
	/* Enable receipt of SCTP Snd/Rcv Data via sctp_recvmsg */
	sctp_event_subscribe events;
	memset( (void *)&events, 0, sizeof(events) );
	events.sctp_data_io_event = 1;
	setsockopt( sctp_sockfd, SOL_SCTP, SCTP_EVENTS, (const void *)&events, sizeof(events) );
	
	errno = 0;
	do{
		datalen = sctp_recvmsg( sctp_sockfd, (void *)&buffer, BUFSIZE,
			(struct sockaddr *)NULL, 0, &sndrcvinfo, &flags );
		
		stream = sndrcvinfo.sinfo_stream;
		//printf( "Stream = %d!\n", stream );
		if( stream == 0 ){
			control( (void *)&buffer, datalen );
		}
		else if( stream <= MAXTUN && tunnels[stream - 1] != NULL ){
			tunnels[stream - 1]->send( (void *)&buffer, datalen );
		}
		else{
			printf( "Ignoring city stream (len %d)...\n", datalen );
			perror( "errno" );
		}
	} while( datalen != -1 && errno == 0 && !shutdown );
	
	close(sctp_sockfd);
	printf( "Conn finished\n" );
}

void SctpConnection::control( void *data, int datalen ){
	printf( "Control!\n" );
	SctpControlMessage *msg = (SctpControlMessage *)data;
	SctpControlMessage resp;
	
	switch( msg->opcode ){
		case OP_CREATETUN:
			msg->address[ msg->addrlen ] = 0;
			printf( "CREATE TUN: %s %d\n", msg->address, (int)msg->port );
			if( msg->flags & FLAG_CREATESRV ){
				tunnels[ msg->stream - 1 ] = new SctpTunnelServer( this, (int)msg->stream, msg->address, (int)msg->port );
				}
			else if( msg->flags & FLAG_CREATECLI ){
				tunnels[ msg->stream - 1 ] = new SctpTunnelClient( this, (int)msg->stream, msg->address, (int)msg->port );
				}
			
			tunnels[ msg->stream - 1 ]->start();
			
			resp.opcode  = OP_CREATEACK;
			resp.stream  = msg->stream;
			memcpy( resp.address, msg->address, msg->addrlen );
			resp.port    = msg->port;
			resp.flags   = 0;
			send( 0, (void *)&resp, sizeof(SctpControlMessage) );
			
			break;
		
		case OP_CREATEACK:
			tunnels[ msg->stream - 1 ]->start();
			break;
		
		case OP_DESTROYTUN:
			tunnels[ msg->stream - 1 ]->shutdown = true;
			tunnels[ msg->stream - 1 ]->wait();
			delete( tunnels[ msg->stream - 1 ] );
			tunnels[ msg->stream - 1 ] = NULL;
			
			resp.opcode  = OP_DESTROYACK;
			resp.stream  = msg->stream;
			memset( resp.address, 0, ADDRLEN );
			resp.port    = 0;
			resp.flags   = 0;
			send( 0, (void *)&resp, sizeof(SctpControlMessage) );
			
			break;
		
		case OP_DESTROYACK:
			tunnels[ msg->stream - 1 ]->shutdown = true;
			tunnels[ msg->stream - 1 ]->wait();
			delete( tunnels[ msg->stream - 1 ] );
			tunnels[ msg->stream - 1 ] = NULL;
			break;
		
		case OP_SHUTDOWN:
			for( int idx = 0; idx < MAXTUN; idx++ ){
				if( tunnels[idx] != NULL ){
					tunnels[idx]->shutdown = true;
					tunnels[idx]->wait();
					delete( tunnels[idx] );
					tunnels[idx] = NULL;
				}
			}
			
			resp.opcode  = OP_SHUTDOWNACK;
			resp.stream  = 0;
			memset( resp.address, 0, ADDRLEN );
			resp.port    = 0;
			resp.flags   = 0;
			send( 0, (void *)&resp, sizeof(SctpControlMessage) );
			
			shutdown = true;
			break;
	}
}

/**
 *  Create a new tunnel.
 *
 *  The tunnel endpoint address is either the bind IP for a server socket,
 *  or the IP to connect() to.
 *
 *  local_addr, local_port:   the local tunnel endpoint
 *  local_server:             true if the local endpoint is to act as a server
 *  remote_addr, remote_port: the remote endpoint
 */

void SctpConnection::cmd_createtun( const char *local_addr, int local_port, bool local_server,
		const char *remote_addr, int remote_port ){
	
	SctpControlMessage msg;
	
	msg.opcode  = OP_CREATETUN;
	
	for( int idx = 0; idx < MAXTUN; idx++ ){
		if( tunnels[idx] == NULL ){
			msg.stream = idx + 1;
			break;
		}
	}
	
	if( local_server ){
		tunnels[ msg.stream - 1 ] = new SctpTunnelServer( this, (int)msg.stream, local_addr, local_port );
		}
	else{
		tunnels[ msg.stream - 1 ] = new SctpTunnelClient( this, (int)msg.stream, local_addr, local_port );
		}
	
	msg.addrlen = strlen(remote_addr);
	memcpy( &msg.address, remote_addr, msg.addrlen );
	msg.address[ msg.addrlen ] = 0;
	msg.port    = remote_port;
	msg.flags   = ( local_server ? FLAG_CREATECLI : FLAG_CREATESRV );
	
	send( 0, (void *)&msg, sizeof(SctpControlMessage) );
}

void SctpConnection::cmd_destroytun( int stream ){
	SctpControlMessage msg;
	
	msg.opcode  = OP_CREATETUN;
	msg.stream  = stream;
	memset( msg.address, 0, ADDRLEN );
	msg.port    = 0;
	msg.flags   = 0;
	send( 0, (void *)&msg, sizeof(SctpControlMessage) );
}

void SctpConnection::cmd_shutdown(){
	
}


void SctpConnection::err( int stream, int err_no ){
	printf( "Error on stream %d: %s\n", stream, strerror( err_no ) );
}
