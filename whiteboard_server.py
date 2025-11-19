import socket
import threading

HOST = '0.0.0.0'
PORT = 9090

clients = {}
clients_lock = threading.Lock()

# --- NEW: HISTORY STORAGE ---
# We will store all drawing commands here so new users can see the picture.
drawing_history = [] 

def broadcast(message, sender_socket):
    """Sends a raw message to all clients EXCEPT the sender."""
    disconnected_clients = []
    with clients_lock:
        for client in clients.keys():
            if client != sender_socket:
                try:
                    client.send(message)
                except:
                    client.close()
                    disconnected_clients.append(client)

    if disconnected_clients:
        with clients_lock:
            for client in disconnected_clients:
                if client in clients:
                    clients.pop(client)
        send_user_list()

def send_user_list():
    with clients_lock:
        if not clients: return
        user_list = "USER_LIST," + ",".join(clients.values()) + "\n"
        for client in clients.keys():
            try: client.send(user_list.encode('utf-8'))
            except: pass

def handle_client(client_socket):
    username = ""
    try:
        # --- STEP 1: HANDSHAKE ---
        join_message_bytes = client_socket.recv(1024)
        if not join_message_bytes: return
        
        join_message = join_message_bytes.decode('utf-8')
        if join_message.startswith("JOIN,"):
            username = join_message.split(',', 1)[1].strip()
            with clients_lock:
                clients[client_socket] = username
            print(f"[NEW CONNECTION] {username} connected.")
            send_user_list()

            # --- NEW: SEND HISTORY TO NEW USER ---
            # Replay all previous drawing commands for this specific user
            print(f"Sending {len(drawing_history)} history items to {username}...")
            for cmd in drawing_history:
                try:
                    client_socket.send(cmd)
                except:
                    break
        else:
            client_socket.close()
            return

        # --- STEP 2: MAIN LOOP ---
        buffer = ""
        while True:
            data_bytes = client_socket.recv(1024)
            if not data_bytes: break
            
            buffer += data_bytes.decode('utf-8')
            
            while '\n' in buffer:
                message, buffer = buffer.split('\n', 1)
                message_with_newline = message + '\n'
                encoded_msg = message_with_newline.encode('utf-8')
                
                # --- LOGIC UPDATE: HISTORY ---
                # If it's a drawing command, save it to history!
                if message.startswith(("DRAW,", "LINE,", "RECT,", "CIRCLE,", "TRI,")):
                    drawing_history.append(encoded_msg)
                    broadcast(encoded_msg, client_socket)
                
                elif message.startswith("CLEAR"):
                    drawing_history.clear() # Wipe history if someone clears
                    broadcast(encoded_msg, client_socket)
                
                elif message.startswith("CHAT,"):
                    chat_text = message.split(',', 1)[1]
                    chat_message = f"CHAT,{username},{chat_text}\n"
                    broadcast(chat_message.encode('utf-8'), client_socket)

    except Exception as e:
        print(f"[ERROR] {e}")
    
    with clients_lock:
        if client_socket in clients:
            clients.pop(client_socket)
            send_user_list()
    client_socket.close()

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"[*] Server listening on {HOST}:{PORT}")
    while True:
        client, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client,)).start()

if __name__ == "__main__":
    start_server()