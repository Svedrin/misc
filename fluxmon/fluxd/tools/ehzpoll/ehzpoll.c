// Copyright 2011 Juri Glass, Mathias Runge, Nadim El Sayed
// DAI-Labor, TU-Berlin
//
// This file is part of libSML.
//
// libSML is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// libSML is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with libSML.  If not, see <http://www.gnu.org/licenses/>.
//
// Copy-pasted and adapted somewhat to query only one single time and then print
// the result as some poor man's JSON.
//
// you might wanna copy this to the examples directory in your libsml source
// tree (yeah, this is totally professional, I know) and compile using:
// cc -I../sml/include/ -g -Wall ehzpoll.c -luuid ../sml/lib/libsml.a -o ehzpoll


#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <termios.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>

#include <sml/sml_file.h>
#include <sml/sml_transport.h>

int serial_port_open(const char* device) {
	int bits;
	struct termios config;
	memset(&config, 0, sizeof(config));

	int fd = open(device, O_RDWR | O_NOCTTY | O_NDELAY);
	if (fd < 0) {
		printf("error: open(%s): %s\n", device, strerror(errno));
		return -1;
	}

	// set RTS
	ioctl(fd, TIOCMGET, &bits);
	bits |= TIOCM_RTS;
	ioctl(fd, TIOCMSET, &bits);

	tcgetattr( fd, &config ) ;

	// set 8-N-1
	config.c_iflag &= ~(IGNBRK | BRKINT | PARMRK | ISTRIP | INLCR | IGNCR | ICRNL | IXON);
	config.c_oflag &= ~OPOST;
	config.c_lflag &= ~(ECHO | ECHONL | ICANON | ISIG | IEXTEN);
	config.c_cflag &= ~(CSIZE | PARENB | PARODD | CSTOPB);
	config.c_cflag |= CS8;

	// set speed to 9600 baud
	cfsetispeed( &config, B9600);
	cfsetospeed( &config, B9600);

	tcsetattr(fd, TCSANOW, &config);
	return fd;
}

void transport_receiver(unsigned char *buffer, size_t buffer_len) {
	// the buffer contains the whole message, with transport escape sequences.
	// these escape sequences are stripped here.
	sml_file *file = sml_file_parse(buffer + 8, buffer_len - 16);
	// the sml file is parsed now

	if( file->messages_len == 3 ){
		sml_get_list_response *resp = file->messages[1]->message_body->data;
		
		char i = 0;
		double watts, rx, tx, rxwatts, txwatts, current;
		sml_list *entry = resp->val_list;
		while(entry != NULL){
			if( entry->value->type ){
				current = sml_value_to_double(entry->value);
				if( i == 2 ){
					rx = current / 10.0;
				}
				else if( i == 3 ){
					tx = current / 10.0;
				}
				else if( i == 8 ){
					watts = current / 10.0;
				}
			}
			entry = entry->next;
			i += 1;
		}
		if( watts >= 0 ){
			rxwatts = watts;
			txwatts = 0;
		}
		else{
			rxwatts = 0;
			txwatts = -watts;
		}
		printf("{ \"rx\": %f, \"tx\": %f, \"rxwatts\": %f, \"txwatts\": %f }\n",
		       rx, tx, rxwatts, txwatts);
		exit(0);
	}

	// free the malloc'd memory
	sml_file_free(file);
}

int main(int argc, char **argv) {
	// this example assumes that a EDL21 meter sending SML messages via a
	// serial device. Adjust as needed.
	if( argc != 2 ){
		fprintf(stderr, "Usage: %s <device>\n", argv[0]);
		return 1;
	}
	
	char *device = argv[1];
	
	int fd = serial_port_open(device);

	if (fd > 0) {
		// listen on the serial device, this call is blocking.
		sml_transport_listen(fd, &transport_receiver);
		close(fd);
	}

	return 0;
}

