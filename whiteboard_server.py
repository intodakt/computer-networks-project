# SERVER PROGRAM (whiteboard_server.py)
# -----------------------------------------------------------------------------
# TEAM MEMBER RESPONSIBILITY: Hoonhee Jang 21011676
#
# DESCRIPTION:
# This program acts as the central hub. It uses TCP Sockets to accept connections.
# It uses Multi-threading to handle multiple clients simultaneously.
# It maintains a "History" of all drawing commands to sync new users.
# -----------------------------------------------------------------------------

import socket
import threading

# --- CONFIGURATION ---
# Listen on ALL network interfaces.
HOST = '0.0.0.0'
PORT = 9090

# --- GLOBAL STATE ---
# 'rooms': maps room_code -> {"clients": {socket: username}, "history": [bytes]}
rooms = {}
rooms_lock = threading.Lock()

def broadcast(message, sender_socket, room_code):
    with rooms_lock:
        room = rooms.get(room_code)
        if not room:
            return
        room_list = list(room["clients"].keys())
    for client in room_list:
        if client == sender_socket:
            continue
        try:
            client.send(message)

        except:
            client.close()

def send_user_list(room_code):
    with rooms_lock:
        room = rooms.get(room_code)
        if not room:
            return
        users = list(room["clients"].values())
        recipeients  = list(room["clients"].keys())
    if not users:
        return
    msg = "USER_LIST," + ",".join(users) + "\n"
    encoded_msg = msg.encode('utf-8')
    for client in recipeients:
        try:
            client.send(encoded_msg)

        except:
            print("Failed to send message to {client}. Disconnecting")
            client.close()



def handle_client(client_socket):
    #JOIN,Name,RoomCode
    username = ""
    room_code = None
    try:
        parts = decode_message(client_socket)
        if parts is None:
            print("Handshake failed")
            client_socket.close()
            return
        
        username = parts[1].strip()
        room_code = parts[2].strip()    
        join_room(client_socket, username,room_code)
        load_history(client_socket, username,room_code)

    except Exception as e:
        print(f"ERROR: {e}")

    finally:
        if room_code:
            with rooms_lock:
                room = rooms.get(room_code)
                # Check if the client is actually in the room before removing
                if room and client_socket in room["clients"]:
                    username_removed = room["clients"][client_socket]
                    print(f"Disconnected: {username_removed} left room {room_code}.")
                    
                    # 1. Remove the client
                    del room["clients"][client_socket]
                    
                    # 2. If room is empty, delete the room
                    if not room["clients"]:
                        del rooms[room_code]
                    else:
                        # 3. CRITICAL: Broadcast the new User List to remaining people
                        # We must do this INSIDE the lock so everyone gets the update immediately
                        users = list(room["clients"].values())
                        msg = "USER_LIST," + ",".join(users) + "\n"
                        
                        # Send to all remaining clients
                        for client in room["clients"]:
                            try:
                                client.send(msg.encode('utf-8'))

                            except:
                                client.close()
                                
        client_socket.close()

def decode_message(client_socket):
    try:
        data = client_socket.recv(1024)
        if not data:
            return None
        
        join_msg = data.decode('utf-8')
        if not join_msg.startswith("JOIN,"):
            return None
        
        parts = join_msg.split(',' , 2)
        if len(parts) < 3:
            client_socket.close()
            return None
        
        return parts
    except:
            return None

def join_room(client_socket, username, room_code):
    with rooms_lock:
        if room_code not in rooms:
            rooms[room_code] = {"clients": {}, "history": []}
        rooms[room_code]["clients"][client_socket] = username
    print(f"[NEW CONNECTION] {username} joined room {room_code}.")
    send_user_list(room_code)

def load_history(client_socket, username, room_code):
    with rooms_lock:
        history_cp = list(rooms[room_code]["history"])

    for hist in history_cp:
        try:
            client_socket.send(hist)

        except:
            return

    buffer = b""
    while True:
        data = client_socket.recv(1024)
        if not data:
            break

        buffer += data
        while b'\n' in buffer:
            raw_msg, buffer = buffer.split(b'\n', 1)
            try:
                message = raw_msg.decode('utf-8')

            except UnicodeDecodeError:
                continue
                
            msg_nl = message + '\n'
            encoded = msg_nl.encode('utf-8')
            if message.startswith(("DRAW,", "LINE,", "RECT,", "CIRCLE,", "TRI,")):
                with rooms_lock:
                    rooms[room_code]["history"].append(encoded)
                broadcast(encoded, client_socket, room_code)
            elif message.startswith("CLEAR"):
                with rooms_lock:
                    rooms[room_code]["history"].clear()
                broadcast(encoded, client_socket, room_code)
            elif message.startswith("CHAT,"):
                _, _, text = message.partition(',')
                full = f"CHAT,{username},{text}\n"
                broadcast(full.encode('utf-8'), client_socket, room_code)


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((HOST, PORT))
    except OSError:
        print(f"Error: Port {PORT} is busy. Is the server already running?")
        return
    server_socket.listen(5)
    print(f"Server listening on {HOST}:{PORT}")
    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,)).start()

if __name__ == "__main__":
    start_server()