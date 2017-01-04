libCanDrive.so: CanDrive.cpp CanDrive.h
	g++ -shared -Wall -Werror -o libCanDrive.so CanDrive.cpp -lwiringPi -lrt

install: libCanDrive.so
	libtool --mode=install install -c libCanDrive.so /usr/local/lib/libCanDrive.so
	install CanDrive.h /usr/local/include/CanDrive.h
