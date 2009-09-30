
BIN_DIR = bin

PROGS = $(shell ls *.c )

INCLUDE+= -I /usr/include/GL/
LINK   += -lglut -lGL -lGLU -lXmu -lXext -lXi -lX11 -lm
CPP     = g++
CFLAGS += -Wall

all: $(BIN_DIR) $(PROGS:%.c=$(BIN_DIR)/%)

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

clean:
	rm -rf $(BIN_DIR)/*

$(BIN_DIR)/%: %.c
	$(CPP) $(INCLUDE) $(CFLAGS) $(CPPFLAGS) $(LINK) -o $@ $<

dep:
	apt-get install libglu1-mesa-dev freeglut3-dev libxmu-dev libxi-dev
