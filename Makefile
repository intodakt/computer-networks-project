# Makefile for Network Whiteboard Project

# Variables
PYTHON = python
SERVER = whiteboard_server.py
CLIENT = whiteboard_client.py


all:
	@echo "Usage: make server OR make client"
	@echo "Ensure Python 3 and Tkinter are installed."

server:
	$(PYTHON) $(SERVER)

client:
	$(PYTHON) $(CLIENT)

clean:
	rm -rf __pycache__
	rm -rf *.pyc