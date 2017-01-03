libCanDrive.so: CanDrive.cpp CanDrive.h
	g++ -o libCanDrive.so CanDrive.cpp -lwiringPi -shared

install: libCanDrive.so
	libtool --mode=install install -c libCanDrive.so /usr/local/lib/libCanDrive.so
