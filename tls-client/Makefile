CC = gcc
CXXFLAGS = -Wall -Wextra -Wpedantic
CXXFLAGS += -O3 -march=native
LDLIBS = -lssl -lcrypto

.PHONY: all
all: s_timer

s_timer: s_timer.c
	$(CC) $(CXXFLAGS) -o $@ $< $(LDFLAGS) $(LDLIBS)

.PHONY: clean
clean:
	rm -f s_timer
