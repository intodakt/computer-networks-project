# -----------------------------------------------------------------------------
# SERVER PROGRAM (whiteboard_server.py)
# -----------------------------------------------------------------------------
# TEAM MEMBER RESPONSIBILITY: [Member Name 1]
#
# DESCRIPTION:
# This program acts as the central hub. It uses TCP Sockets to accept connections.
# It uses Multi-threading to handle multiple clients simultaneously.
# It maintains a "History" of all drawing commands to sync new users.
# -----------------------------------------------------------------------------

import socket
import threading

# --- CONFIGURATION ---
# '0.0.0.0' tells the socket to listen on ALL network interfaces.
# This enables connections from Localhost, Wi-Fi, and Ethernet.
HOST = '0.0.0.0'
PORT = 9090

# --- GLOBAL STATE ---
# 'clients': A dictionary mapping {socket_object: "username_string"}
clients = {}

# 'drawing_history': A list of bytes.
# We store every "DRAW", "RECT", "LINE" command here.
# When a new person joins, we replay this list so their canvas looks like ours.
drawing_history = []

# 'clients_lock': A Thread Lock.
# Since multiple threads (clients) run at the same time, two threads might try
# to modify the 'clients' list simultaneously, causing a crash.
# The lock forces threads to wait their turn.
clients_lock = threading.Lock()

def broadcast(message, sender_socket):
    """
    Sends a raw message to ALL connected clients EXCEPT the sender.
    This is the core 'Collaborative' logic.
    """
    disconnected_clients = []
    
    # 1. Acquire lock to safely read the shared 'clients' dictionary
    with clients_lock:
        for client_sock in clients.keys():
            # Don't send the drawing back to the person who drew it
            # (They already drew it locally on their screen)
            if client_sock != sender_socket:
                try:
                    client_sock.send(message)
                except:
                    # If sending fails, the client probably disconnected abruptly.
                    client_sock.close()
                    disconnected_clients.append(client_sock)

    # 2. Clean up any dead connections found during the broadcast
    if disconnected_clients:
        with clients_lock:
            for client in disconnected_clients:
                if client in clients:
                    clients.pop(client)
        # Update everyone's user list sidebar
        send_user_list()

def send_user_list():
    """
    Generates a comma-separated list of usernames and sends it to everyone.
    Format: "USER_LIST,Alice,Bob,Charlie\n"
    """
    with clients_lock:
        if not clients: return
        # Join all usernames with commas
        user_list_str = "USER_LIST," + ",".join(clients.values()) + "\n"
        
        # Send to ALL clients (including the sender)
        for client in clients.keys():
            try:
                client.send(user_list_str.encode('utf-8'))
            except:
                pass

def handle_client(client_socket):
    """
    The MAIN LOOP for a single client.
    Run inside a separate thread.
    """
    username = ""
    try:
        # --- STEP 1: HANDSHAKE ---
        # The first message MUST be "JOIN,Name"
        join_msg_bytes = client_socket.recv(1024)
        if not join_msg_bytes: return
        
        join_msg = join_msg_bytes.decode('utf-8')
        
        if join_msg.startswith("JOIN,"):
            username = join_msg.split(',', 1)[1].strip()
            
            # Add to global list safely
            with clients_lock:
                clients[client_socket] = username
            
            print(f"[NEW CONNECTION] {username} connected.")
            send_user_list()

            # --- CRITICAL FEATURE: STATE SYNCHRONIZATION ---
            # Replay the entire drawing history for this NEW user only.
            # This ensures they see what was drawn before they arrived.
            for historical_command in drawing_history:
                try:
                    client_socket.send(historical_command)
                except:
                    break
        else:
            # If protocol is wrong, disconnect them
            client_socket.close()
            return

        # --- STEP 2: LISTENING LOOP ---
        buffer = ""
        while True:
            try:
                # Receive data (blocking call - waits for data)
                data_bytes = client_socket.recv(1024)
                if not data_bytes: break # Connection closed
                
                buffer += data_bytes.decode('utf-8')
                
                # TCP FRAGMENTATION HANDLER:
                # Messages might arrive bunched together ("DRAW...DRAW...").
                # We split them by newline '\n' to process one by one.
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    message_with_newline = message + '\n'
                    encoded_msg = message_with_newline.encode('utf-8')
                    
                    # 1. Drawing Commands -> Save to History & Broadcast
                    if message.startswith(("DRAW,", "LINE,", "RECT,", "CIRCLE,", "TRI,")):
                        drawing_history.append(encoded_msg)
                        broadcast(encoded_msg, client_socket)
                    
                    # 2. Clear Command -> Wipe History & Broadcast
                    elif message.startswith("CLEAR"):
                        drawing_history.clear()
                        broadcast(encoded_msg, client_socket)
                    
                    # 3. Chat -> Just Broadcast (Don't save chat to history)
                    elif message.startswith("CHAT,"):
                        # Protocol: CHAT,SenderName,Message
                        text = message.split(',', 1)[1]
                        full_chat = f"CHAT,{username},{text}\n"
                        broadcast(full_chat.encode('utf-8'), client_socket)

            except ConnectionResetError:
                break # Client force closed

    except Exception as e:
        print(f"[ERROR] {e}")
    
    # --- STEP 3: CLEANUP ---
    # Remove client from list and notify others
    with clients_lock:
        if client_socket in clients:
            print(f"[DISCONNECT] {clients[client_socket]} left.")
            clients.pop(client_socket)
            send_user_list()
    client_socket.close()

def start_server():
    """Initializes the socket and starts the main acceptance loop."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # SO_REUSEADDR allows us to restart the server immediately without waiting for timeout
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
    except OSError as e:
        print(f"Error: Port {PORT} is busy. Is the server already running?")
        return

    server_socket.listen(5) # Backlog of 5 connections
    print(f"[*] Server listening on {HOST}:{PORT}")
    print("    (Share your IP address with teammates to connect)")
    
    while True:
        # Wait for a new connection
        client_socket, addr = server_socket.accept()
        
        # Create a NEW THREAD for this client
        # This allows the main loop to go back and wait for the NEXT person
        thread = threading.Thread(target=handle_client, args=(client_socket,))
        thread.start()

if __name__ == "__main__":
    start_server()