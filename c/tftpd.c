#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <pthread.h>

#include "exceptions.h"

#define TFTPD_ADDR "0.0.0.0"
#define TFTPD_PORT 69

#define CLIENT_PORT_MIN 30000
#define CLIENT_PORT_MAX 40000

#define CHUNKLEN 512

#define UnknownOpcodeException 1

#define TFTP_OP_RRQ 1
#define TFTP_OP_WRQ 2
#define TFTP_OP_DTA 3
#define TFTP_OP_ACK 4
#define TFTP_OP_ERR 5

#define TFTP_MD_ASCII 1
#define TFTP_MD_OCTET 2
#define TFTP_MD_MAIL  3

#ifdef linux
#define stricmp strcasecmp
#endif

typedef struct str_handler_args {
	struct sockaddr_in *clientaddr;
	FILE *fd;
	int mode;
	int port;
	} handler_args;

void tftp_handle_rrq( handler_args *args );
void tftp_handle_wrq( handler_args *args );

int main( int argc, char *argv[] ){
	struct sockaddr_in servaddr;
	struct sockaddr_in clientaddr;
	socklen_t clientlen = sizeof(struct sockaddr_in);
	handler_args *args;
	
	pthread_attr_t threadattr;
	pthread_t thr_id;
	
	servaddr.sin_family      = AF_INET;
	servaddr.sin_port        = htons(TFTPD_PORT);
	servaddr.sin_addr.s_addr = inet_addr(TFTPD_ADDR);
	
	int cliport = CLIENT_PORT_MIN;
	int sockfd, datalen;
	char buffer[CHUNKLEN+1];
	
	sockfd = socket( PF_INET, SOCK_DGRAM, 0 );
	XASSERT(sockfd != -1);
	
	XASSERT( pthread_attr_init( &threadattr ) == 0 );
	XASSERT( pthread_attr_setdetachstate( &threadattr, PTHREAD_CREATE_DETACHED ) == 0 );
	XASSERT( pthread_attr_setscope( &threadattr, PTHREAD_SCOPE_SYSTEM ) == 0 );
	
	XCATCHSIGINT
	
	unsigned short opcode;
	
	XTRY{
		int current_uid = getuid();
		if( TFTPD_PORT < 1024 && current_uid != 0 ){
			// Needz root plzkthx
			printf( "S: Becoming root (am %d now).\n", current_uid );
			XASSERT( setuid(0) == 0 );
		}
		XASSERT( bind( sockfd, (struct sockaddr *)&servaddr, sizeof(struct sockaddr) ) != -1 );
		printf( "S: Successfully bound to port %d.\n", TFTPD_PORT );
		
		if( current_uid != 0 ){
			// Dropz root plzkthx
			printf( "S: Dropping root.\n" );
			XASSERT( setuid(current_uid) == 0 );
		}
		
		while(1){
			XTRY{
				char *filename, *modestr;
				FILE *fd;
				int mode;
				
				datalen = recvfrom( sockfd, buffer, CHUNKLEN, 0, (struct sockaddr*)&clientaddr, &clientlen );
				XASSERT( datalen != -1 );
				
				/* Get the opcode: first two bytes = 16bit short int in big endian */
				opcode = ( buffer[0] << 8 ) | buffer[1];
				
				switch( opcode ){
					case TFTP_OP_RRQ:
						/* skip the 2 opcode bytes */
						filename = buffer + 2;
						printf( "Received RRQ for file \"%s\"\n", filename );
						modestr = buffer + 2 + strlen( filename ) + 1;
						printf( "Received RRQ for mode \"%s\"\n", modestr );
						
						fd = fopen( filename, "rb" );
						XASSERT( fd != NULL );
						
						if( stricmp( modestr, "netascii" ) == 0 )
							mode = TFTP_MD_ASCII;
						else if( stricmp( modestr, "mail" ) == 0 )
							mode = TFTP_MD_MAIL;
						else
							mode = TFTP_MD_OCTET;
						
						printf( "S: Calling RRQ handler.\n" );
						
						args = malloc( sizeof( handler_args ) );
						args->clientaddr = &clientaddr;
						args->fd   = fd;
						args->mode = mode;
						args->port = cliport++;
						
						if( cliport >= CLIENT_PORT_MAX )
							cliport = CLIENT_PORT_MIN;
						
						XASSERT( pthread_create( &thr_id, &threadattr,
									 (void *(*) (void *))tftp_handle_rrq,
									 (void*)args ) == 0 );
						
						break;
					case TFTP_OP_WRQ:
						/* skip the 2 opcode bytes */
						filename = buffer + 2;
						printf( "Received WRQ for file \"%s\"\n", filename );
						modestr = buffer + 2 + strlen( filename ) + 1;
						printf( "Received WRQ for mode \"%s\"\n", modestr );
						
						fd = fopen( filename, "wb" );
						XASSERT( fd != NULL );
						
						if( stricmp( modestr, "netascii" ) == 0 )
							mode = TFTP_MD_ASCII;
						else if( stricmp( modestr, "mail" ) == 0 )
							mode = TFTP_MD_MAIL;
						else
							mode = TFTP_MD_OCTET;
						
						printf( "S: Calling WRQ handler.\n" );
						
						args = malloc( sizeof( handler_args ) );
						args->clientaddr = &clientaddr;
						args->fd   = fd;
						args->mode = mode;
						args->port = cliport++;
						
						if( cliport >= CLIENT_PORT_MAX )
							cliport = CLIENT_PORT_MIN;
						
						XASSERT( pthread_create( &thr_id, &threadattr,
									 (void *(*) (void *))tftp_handle_wrq,
									 (void*)args ) == 0 );
						
						break;
					default:
						printf( "Received unknown/invalid OpCode 0x%X\n", opcode );
						buffer[0] = (TFTP_OP_ERR>>8);
						buffer[1] = (TFTP_OP_ERR & 0xFF);
						buffer[2] = 0x0;
						buffer[3] = 0x0;
						XASSERT( sendto( sockfd, buffer, 4, 0,
								 (struct sockaddr *)&clientaddr, sizeof(struct sockaddr) ) != -1 );
						break;
				}
			}
			XEND
		}
	}
	XCEPT( EX_SIGINT ){
		printf( "Hast thou hit ^c?\n" );
		XEXITSIGINT
	}
	XFINALLY{
		printf( "Closing server socket.\n" );
		close(sockfd);
	}
	XEND
	
	return 0;
}


void tftp_handle_rrq( handler_args *args ){
	FILE *fd = args->fd;
	int mode = args->mode;
	
	struct sockaddr_in cliaddr;
	struct sockaddr_in servaddr;
	int sockfd, readlen, datalen;
	socklen_t clientlen = sizeof(struct sockaddr_in);
	
	memcpy( &cliaddr, args->clientaddr, sizeof( struct sockaddr_in ) );
	
	free(args);
	
	servaddr.sin_family      = AF_INET;
	servaddr.sin_port        = htons(args->port);
	servaddr.sin_addr.s_addr = inet_addr(TFTPD_ADDR);
	
	sockfd = socket( PF_INET, SOCK_DGRAM, 0 );
	XASSERT( sockfd != -1 );
	XASSERT( bind( sockfd, (struct sockaddr *)&servaddr, sizeof(struct sockaddr) ) != -1 );
	printf( "H: Bound to port %d\n", args->port );
	
	char buffer[CHUNKLEN+1];
	unsigned short blockno = 1;
	
	XTRY{
		do{
			buffer[0] = 0x0;
			buffer[1] = TFTP_OP_DTA;
			
			// Write block number
			buffer[2] = (char)( blockno >> 8 );
			buffer[3] = (char)(blockno & 0xFF);
			
			// Seek the file to the start of the current block (necessary when retransmitting)
			printf( "H: Going to file position %d.\n", ((CHUNKLEN)*(blockno-1)) );
			fseek( fd, (CHUNKLEN*(blockno-1)), SEEK_SET );
			
			// Now copy 512-4=508 bytes of the file into the buffer
			readlen = fread( buffer+4, sizeof(char), (CHUNKLEN), fd );
			
			printf( "H: Sending block %d (read %d bytes from file)...\n", blockno, readlen );
			XASSERT( sendto( sockfd, buffer, readlen+4, 0, (struct sockaddr *)&cliaddr, sizeof(struct sockaddr) ) != -1 );
			
			// Fetch response that is an ack to the previously sent block.
			printf( "H: Waiting...\n" );
			datalen = recvfrom( sockfd, buffer, 4, 0, NULL, NULL );
			XASSERT( datalen != -1 );
			
			if( ( (buffer[0]<<8) | (buffer[1] & 0xFF) ) == TFTP_OP_ACK ){
				if( ( (buffer[2]<<8) | (buffer[3] & 0xFF) ) == blockno ){
					printf( "H: Got ACK for block %d!\n", blockno );
					blockno++;
				}
				else{
					printf( "H: Got ACK for block %d!\n", ( (buffer[2]<<8) | (buffer[3] & 0xFF) ) );
				}
			}
			else{
				printf( "H: Got Non-Ack (0x%x) for block %d!\n",
					( (buffer[0]<<8) | buffer[1] ),
					( (buffer[2]<<8) | buffer[3] )
					);
			}
			
			
		} while( readlen >= (CHUNKLEN) );
	}
	XFINALLY{
		printf( "Closing handler sockets\n" );
		fclose(fd);
		close(sockfd);
	}
	XEND
}


void tftp_handle_wrq( handler_args *args ){
	FILE *fd = args->fd;
	int mode = args->mode;
	
	struct sockaddr_in cliaddr;
	struct sockaddr_in servaddr;
	int sockfd, writtenlen, datalen;
	socklen_t clientlen = sizeof(struct sockaddr_in);
	
	memcpy( &cliaddr, args->clientaddr, sizeof( struct sockaddr_in ) );
	
	free(args);
	
	servaddr.sin_family      = AF_INET;
	servaddr.sin_port        = htons(args->port);
	servaddr.sin_addr.s_addr = inet_addr(TFTPD_ADDR);
	
	sockfd = socket( PF_INET, SOCK_DGRAM, 0 );
	XASSERT( sockfd != -1 );
	XASSERT( bind( sockfd, (struct sockaddr *)&servaddr, sizeof(struct sockaddr) ) != -1 );
	printf( "H: Bound to port %d\n", args->port );
	
	char buffer[CHUNKLEN+1];
	unsigned short blockno = 1;
	
	// Send first ACK (packet no=0)
	buffer[0] = (TFTP_OP_ACK>>8);
	buffer[1] = (TFTP_OP_ACK & 0xFF);
	buffer[2] = 0x0;
	buffer[3] = 0x0;
	XASSERT( sendto( sockfd, buffer, 4, 0, (struct sockaddr *)&cliaddr, sizeof(struct sockaddr) ) != -1 );
	
	XTRY{
		do{
			// Fetch response that is an ack to the previously sent block.
			printf( "H: Waiting for data...\n" );
			datalen = recvfrom( sockfd, buffer, CHUNKLEN+4, 0, NULL, NULL );
			XASSERT( datalen != -1 );
			
			if( ( (buffer[0]<<8) | (buffer[1] & 0xFF) ) == TFTP_OP_DTA ){
				// Seek the file to the start of the current block (necessary when retransmitting)
				// Write block number
				blockno = ( (buffer[2]<<8) | (buffer[3] & 0xFF) );
				printf( "H: Going to file position %d (blockno %d).\n", ((CHUNKLEN)*(blockno-1)), blockno );
				fseek( fd, (CHUNKLEN*(blockno-1)), SEEK_SET );
				
				// Now copy 512-4=508 bytes of the file into the buffer
				writtenlen = fwrite( buffer+4, sizeof(char), datalen-4, fd );
				
				buffer[0] = (TFTP_OP_ACK>>8);
				buffer[1] = (TFTP_OP_ACK & 0xFF);
				XASSERT( sendto( sockfd, buffer, 4, 0, (struct sockaddr *)&cliaddr, sizeof(struct sockaddr) ) != -1 );
			}
			else{
				buffer[0] = (TFTP_OP_ERR>>8);
				buffer[1] = (TFTP_OP_ERR & 0xFF);
				buffer[2] = 0x0;
				buffer[3] = 0x0;
				XASSERT( sendto( sockfd, buffer, 4, 0, (struct sockaddr *)&cliaddr, sizeof(struct sockaddr) ) != -1 );
			}
		} while( writtenlen >= (CHUNKLEN) );
	}
	XFINALLY{
		printf( "Closing handler sockets\n" );
		fclose(fd);
		close(sockfd);
	}
	XEND
}

