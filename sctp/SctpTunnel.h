#ifndef _SCTPTUNNEL_H
#define _SCTPTUNNEL_H

#include <QtCore/qthread.h>

class SctpConnection;

#include "SctpConnection.h"

/**
 *  A generic tunnel endpoint.
 */
class SctpTunnel : public QThread {
	protected:
		int tcp_sockfd;
		int stream;
		
		SctpConnection *conn;
	
	public:
		bool shutdown;
	
	public:
		SctpTunnel( SctpConnection *conn, int stream, const char *addr, int port );
		~SctpTunnel();
		
		int send( void* data, int datalen );
};

/**
 *  A tunnel endpoint that acts as a client.
 */
class SctpTunnelClient : public SctpTunnel {
	public:
		SctpTunnelClient( SctpConnection *conn, int stream, const char* addr, int port );
		~SctpTunnelClient();
	
	protected:
		void run();
};

/**
 *  A tunnel endpoint that acts as a server.
 */
class SctpTunnelServer : public SctpTunnel {
	public:
		SctpTunnelServer( SctpConnection *conn, int stream, const char* addr, int port );
		~SctpTunnelServer();
	
	protected:
		void run();
};

#endif // _SCTPTUNNEL_H
