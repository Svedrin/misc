/*
** client.c -- a stream socket client demo
*/

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <netdb.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <sys/socket.h>

#include "versicheck.h"

#define PORT 80
#define HOST "mistagee.de"

#define MAXDATASIZE 100 // max number of bytes we can get at once

char*	versicheck::getVersionFromServer(){
	int sockfd, numbytes;
	char* buf = new char[MAXDATASIZE];
	struct hostent *he;
	struct sockaddr_in their_addr; // connector's address information
	
	if ( ( he = gethostbyname( HOST ) ) == NULL ) {
		return NULL;
		}
	
	if ( ( sockfd = socket( PF_INET, SOCK_STREAM, 0 ) ) == -1 ){
		return NULL;
		}
	
	their_addr.sin_family = AF_INET;    // host byte order
	their_addr.sin_port = htons(PORT);  // short, network byte order
	their_addr.sin_addr = *((struct in_addr *)he->h_addr);
	memset(&(their_addr.sin_zero), '\0', 8);  // zero the rest of the struct
	
	if( connect( sockfd, (struct sockaddr *)&their_addr, sizeof(struct sockaddr)) == -1 ){
		return NULL;
		}
	
	send( sockfd, "GET /version.txt\r\n", 18, 0 );
	
	if( ( numbytes = recv( sockfd, buf, MAXDATASIZE - 1, 0 ) ) == -1 ){
		return NULL;
		}
	
	// Jetzt alles was nicht Zahl oder Punkt ist rausscannen
	for( int i = 0; i < numbytes; i++)
		if( buf[i] != 0 && ( buf[i] < '0' || buf[i] > '9' ) && buf[i] != '.' )
			buf[i] = 0;
	
	buf[numbytes] = 0; // Null-terminieren
	
	close(sockfd);
	
	return buf;
	}
 
