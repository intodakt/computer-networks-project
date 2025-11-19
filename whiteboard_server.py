# whiteboard_server.v4.py
# This is the upgraded SERVER program.
# It now handles 'RECT' (Rectangle) commands.

import socket
import threading

HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 9090       # A port not in use

clients = {}
clients_lock = threading.Lock() 

def broadcast(message, sender_socket):
    """Sends a message to all clients except the sender."""
    disconnected_clients = []
    
    with clients_lock:
        current_clients = list(clients.keys())
        for client in current_clients:
            if client != sender_socket:
                try:
                    client.send(message)
                except Exception as e:
                    print(f"[ERROR] Broadcasting to {clients.get(client, 'Unknown')}: {e}")
                    client.close()
                    disconnected_clients.append(client)

    if disconnected_clients:
        with clients_lock:
            for client in disconnected_clients:
                if client in clients:
                    username = clients.pop(client)
                    print(f"[DISCONNECTED] {username} has left (detected on broadcast).")
        send_user_list() 


def send_user_list():
    """Builds and broadcasts an updated user list to all clients."""
    with clients_lock:
        if not clients: 
            return
        user_list = "USER_LIST," + ",".join(clients.values()) + "\n"
        print(f"Sending user list: {user_list.strip()}")
        for client in clients.keys():
            try:
                client.send(user_list.encode('utf-8'))
            except:
                pass 

def handle_client(client_socket):
    """This function runs in a separate thread for each client."""
    
    username = ""
    try:
        join_message_bytes = client_socket.recv(1024)
        if not join_message_bytes:
            print("[INVALID JOIN] Client disconnected before sending JOIN.")
            client_socket.close()
            return
            
        join_message = join_message_bytes.decode('utf-8')
        if join_message.startswith("JOIN,"):
            username = join_message.split(',', 1)[1].strip()
            with clients_lock:
                clients[client_socket] = username
            print(f"[NEW CONNECTION] {username} has connected.")
            send_user_list()
        else:
            print(f"[INVALID JOIN] Client sent: {join_message}")
            client_socket.close()
            return
            
        buffer = ""
        while True:
            data_bytes = client_socket.recv(1024)
            if not data_bytes:
                break 
            
            buffer += data_bytes.decode('utf-8')
            
            while '\n' in buffer:
                message, buffer = buffer.split('\n', 1)
                message_with_newline = message + '\n'
                
                # --- THIS IS THE ONLY PART THAT CHANGED ---
                # Added "RECT," to the list of draw commands to broadcast
                if message.startswith("DRAW,") or \
                   message.startswith("LINE,") or \
                   message.startswith("RECT,") or \
                   message.startswith("CLEAR"):
                    # This is a drawing command, broadcast it
                    broadcast(message_with_newline.encode('utf-8'), client_socket)
                
                elif message.startswith("CHAT,"):
                    chat_text = message.split(',', 1)[1]
                    chat_message = f"CHAT,{username},{chat_text}\n"
                    print(f"[CHAT] {username}: {chat_text}")
                    broadcast(chat_message.encode('utf-8'), client_socket)
            
    except Exception as e:
        print(f"[ERROR] {e}")
    
    with clients_lock:
        if client_socket in clients:
            username = clients.pop(client_socket)
            print(f"[CONNECTION CLOSED] {username} has disconnected.")
            send_user_list()
    client_socket.close()

def start_server():
    """Main function to start the server."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"[*] Server is listening on {HOST}:{PORT}...")
    
    while True:
        client_socket, address = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(client_socket,))
        thread.start()

if __name__ == "__main__":
    start_server()