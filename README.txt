Collaborative Network Whiteboard

Team Members

[Name] - [ID]

[Name] - [ID]

[Name] - [ID]

[Name] - [ID]

Overview

This project is a real-time collaborative whiteboard application using Python's standard socket and threading libraries. It supports multiple simultaneous users, real-time drawing synchronization, shape tools, and a chat interface.

Run Commands

1. Start the Server

The server must be running first.

make server
# OR
python3 whiteboard_server.py


2. Start the Clients

Run this on as many terminals or computers as you like.

make client
# OR
python3 whiteboard_client.py


Protocol Specification: WBTP (Whiteboard Transfer Protocol)

To satisfy the course requirement for standard-based protocols, we have defined a rigorous Application Layer protocol named WBTP.

Transport Layer: TCP (SOCK_STREAM)

Port: 9090

Encoding: UTF-8

Delimiter: Newline (\n)

Message Format

All messages follow the format: COMMAND,param1,param2,...\n

Command Definitions

Command

Parameters

Description

JOIN

username

Sent by Client immediately upon connection to register name.

USER_LIST

u1,u2,u3...

Sent by Server to update the sidebar user list.

DRAW

x1,y1,x2,y2,col,size

Continuous brush stroke line segment.

LINE

x1,y1,x2,y2,col,size

Straight line shape.

RECT

x1,y1,x2,y2,col,size

Rectangle shape.

CIRCLE

x1,y1,x2,y2,col,size

Circle/Oval shape.

TRI

x1,y1...x3,y3,col,size

Triangle shape (3 coordinate pairs).

CHAT

sender,message

Chat text payload.

CLEAR

None

Clears the entire canvas for all users.

Technical Architecture

Concurrency: The server uses threading.Thread to handle each client connection independently.

Synchronization: A threading.Lock is used on the server to prevent race conditions when updating the global clients list.

Persistence: The server maintains a drawing_history list. When a new user joins, the server replays the history stream so the new user receives the current state of the whiteboard.

Interpolation: The client implements linear interpolation between mouse events to ensure drawing lines are smooth and continuous, rather than dotted.