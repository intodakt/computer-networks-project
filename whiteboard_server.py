# SERVER PROGRAM (whiteboard_server.py)
# -----------------------------------------------------------------------------
# Hoonhee Jang 21011676
#
# DESCRIPTION:
# This program initializes a multi-threaded server acting as a central hub to manage users within isolated rooms. 
# It utilizes a UDP socket method for automatic IP discovery.
# It maintains a complete history of drawing commands to ensure state synchronization for new clients.
#
# -----------------------------------------------------------------------------
import sys
import socket
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
# --- CONFIGURATION ---
# Listen on ALL network interfaces.
HOST = '0.0.0.0'
PORT = 8000

# --- GLOBAL STATE ---
# 'rooms': maps room_code -> {"clients": {socket: username}, "history": [bytes]}
rooms = {}
rooms_lock = threading.Lock()
log_widget = None

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
            log("Failed to send message to {client}. Disconnecting")
            client.close()



def handle_client(client_socket):
    #JOIN,Name,RoomCode
    username = ""
    room_code = None
    try:
        parts = decode_message(client_socket)
        if parts is None:
            log("Handshake failed")
            client_socket.close()
            return
        
        username = parts[1].strip()
        room_code = parts[2].strip()    
        join_room(client_socket, username,room_code)
        load_history(client_socket, username,room_code)

    except Exception as e:
        log(f"ERROR: {e}")

    finally:
        if room_code:
            with rooms_lock:
                room = rooms.get(room_code)
                if room and client_socket in room["clients"]:
                    username_removed = room["clients"][client_socket]
                    log(f"Disconnected: {username_removed} left room {room_code}.")      
                    #remove clients
                    del room["clients"][client_socket]
                    #delete room if empty
                    if not room["clients"]:
                        del rooms[room_code]
                    else:
                        users = list(room["clients"].values())
                        recieve = list(room["clients"].keys())
            if recieve:
                msg = "USER_LIST," + ",".join(users) + "\n"
                encoded_msg = msg.encode('utf-8')     
            
            for client in recieve:
                try:
                    #send a new user list to all clients
                    client.send(encoded_msg)
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
    log(f"New Connection: {username} joined room {room_code}.")
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

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8',1))
        log("Got IP")
        IP = s.getsockname()[0]
    except Exception:
        log("Failed to get IP")
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((HOST, PORT))
    except OSError:
        log(f"Error: Port {PORT} is busy. Is the server already running?")
        return
    server_socket.listen(5)
    lan_ip = get_ip()
    log(f"Server listening on {HOST}:{PORT}")
    log(f"IP: {lan_ip}")
    while True:
        try:
            client_socket, addr = server_socket.accept()
            threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()
        except OSError:
            break

def stop_server():
    if window:
        window.destroy()
    sys.exit()

def server_gui():
    global log_widget, window
    window = tk.Tk()
    window.geometry("500x400")
    control_frame = tk.Frame(window)
    control_frame.pack(side = tk.TOP, fill = tk.X, padx = 10, pady = 5)
    
    window.title(f"Whiteboard Server ({get_ip()})")

    button_stop = tk.Button(
        control_frame,
        text = "Stop Server",
        font = ("Consolas", 10),
        command = stop_server
    )
    button_stop.pack(side = tk.RIGHT)

    log_widget = ScrolledText(window, state = 'disabled', font =("Consolas", 10))
    log_widget.pack(padx = 10, pady = 10, fill = tk.BOTH, expand = True)

    
    server_thread = threading.Thread(target = start_server, daemon = True)
    server_thread.start()

    window.mainloop()

def log(msg):
    if log_widget:
        log_widget.configure(state = "normal")
        log_widget.insert(tk.END, msg + '\n')
        log_widget.see(tk.END)
        log_widget.configure(state = "disabled")
    else:
        print(msg)

if __name__ == "__main__":
    server_gui()