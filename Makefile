# Makefile for Network Whiteboard Project

# Variables
PYTHON = python3
SERVER = whiteboard_server.py
CLIENT = whiteboard_client.py

# Default target
all:
	@echo "Usage: make server OR make client"
	@echo "Ensure Python 3 and Tkinter are installed."

# Run the Server
server:
	$(PYTHON) $(SERVER)

# Run the Client
client:
	$(PYTHON) $(CLIENT)

# Clean (removes compiled python files)
clean:
	rm -rf __pycache__
	rm -rf *.pyc