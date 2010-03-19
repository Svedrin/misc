INCLUDE=-I/usr/include/qt4
LINK=-lsctp -lQtCore

.PHONY: clean server.h client.h

release: bin/server bin/client

bin/%.o: %.cpp %.h
	g++ $(INCLUDE) $(CFLAGS) $(CPPFLAGS) -o $@ -c $<

bin/%: bin/SctpTunnel.o bin/SctpConnection.o bin/%.o
	g++ $(LINK) -o $@ $^

clean:
	rm bin/*
