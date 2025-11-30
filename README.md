# Network Whiteboard

A multi‑room collaborative whiteboard built with Python sockets and Tkinter.

## Team Members

- Hoonhee Jang - 21011676
- [Name] - [ID]
- [Name] - [ID]
- [Name] - [ID]


## Features
- Multiple isolated rooms (4‑digit code)
- Real‑time drawing (brush, line, rectangle, circle, triangle, eraser)
- Chat per room
- History synchronization for new participants
- Server GUI showing logs and LAN IP

## Prerequisites
- Python 3.x
- Tkinter

## Running the Server
```bash
cd computer-networks-project
python whiteboard_server.py
```
OR
```bash
cd computer-networks-project
make server
```

The server GUI will display the LAN IP and logs.

## Running the Client
```bash
cd computer-networks-project
python whiteboard_client.py
```
OR
```bash
cd computer-networks-project
make client
```
- Enter the server IP (default `127.0.0.1`).
- Choose "Create Room" (generates a random 4‑digit code) or "Join Room" (enter an existing code).
- Your username will appear in the sidebar.

## Controls
- Toolbar icons for brush, line, rectangle, circle, triangle, eraser.
- Color picker and size slider.
- "Clear All" button to clear the canvas.
- Chat entry at the bottom of the sidebar.