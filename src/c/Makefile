# Makefile for PtyServer

# Compiler and flags
CC = gcc
CFLAGS = -O2 -Wall -Wextra -Wpedantic -luv -lutil

# Source files and executable
SRCS = PtyServer.c
EXEC = PtyServer

# Default target
all: $(EXEC)

# Build the executable
$(EXEC): $(SRCS)
	$(CC) $(CFLAGS) -o $(EXEC) $(SRCS)

# Run the program in the foreground with default port
run: $(EXEC)
	./$(EXEC) -p 5000

# Run the program as a daemon with default port
run-daemon: $(EXEC)
	./$(EXEC) -d -p 5000

# Clean up build files
clean:
	rm -f $(EXEC)

.PHONY: all clean run run-daemon
