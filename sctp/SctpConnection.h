#ifndef _SCTPCONNECTION_H
#define _SCTPCONNECTION_H

class SctpTunnel;

#include "config.h"
#include "SctpTunnel.h"

#define OP_CREATETUN     0
#define OP_CREATEACK     1
#define OP_DESTROYTUN    2
#define OP_DESTROYACK    3
#define OP_SHUTDOWN      4
#define OP_SHUTDOWNACK   5

#define FLAG_CREATESRV   (1<<1)
#define FLAG_CREATECLI   (1<<2)

struct SctpControlMessage {
	unsigned int   opcode;
	unsigned short stream;
	char           address[ADDRLEN];
	unsigned short addrlen;
	unsigned short port;
	unsigned short flags;
};

class SctpConnection : public QThread {
	private:
		int sctp_sockfd;
		SctpTunnel *tunnels[MAXTUN];
	
	public:
		SctpConnection( int sockfd );
		~SctpConnection();
		
		void err(  int stream, int err_no );
		int send( int stream, void *data, int datalen );
		
		void control( void *data, int datalen );
		
		void cmd_createtun( const char *local_addr, int local_port, bool local_server, const char *remote_addr, int remote_port );
		void cmd_destroytun( int stream );
		void cmd_shutdown();
		
		bool shutdown;
	
	protected:
		void run();
};

#endif // _SCTPCONNECTION_H
