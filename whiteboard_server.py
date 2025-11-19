# whiteboard_server.v5.py
# -----------------------------------------------------------------------------
# SERVER PROGRAM
# -----------------------------------------------------------------------------
# This program acts as the central "hub" for the whiteboard application.
# Its main job is to:
# 1. Listen for new clients connecting.
# 2. When a client sends a message (like "DRAW..."), receive it.
# 3. IMMEDIATELY send that same message to every OTHER connected client.
#
# Concepts used:
# - TCP Sockets (SOCK_STREAM): For reliable, ordered delivery of data.
# - Threading: To handle multiple clients at the same time.
# -----------------------------------------------------------------------------

import socket
import threading

# Configuration
HOST = '0.0.0.0'  # '0.0.0.0' means "listen on all available network interfaces" (WiFi, Ethernet, etc.)
PORT = 9090       # The port number. Must match the client's port.

# Global Variables
# 'clients' dictionary stores the connection info: {client_socket: "username"}
clients = {}
# 'clients_lock' is a Thread Lock. It prevents two threads from trying to 
# add/remove items from the 'clients' dictionary at the exact same time, 
# which would cause a crash.
clients_lock = threading.Lock() 

def broadcast(message, sender_socket):
    """
    Sends a raw message to ALL connected clients EXCEPT the one who sent it.
    This is the core logic that makes the whiteboard "collaborative".
    """
    disconnected_clients = []
    
    with clients_lock: # Acquire the lock before accessing the shared dictionary
        current_clients = list(clients.keys()) # Create a temporary list of keys
        for client in current_clients:
            if client != sender_socket:
                try:
                    # Send the message (it's already bytes)
                    client.send(message)
                except Exception as e:
                    # If sending fails, the client likely crashed or disconnected without telling us.
                    print(f"[ERROR] Broadcasting to {clients.get(client, 'Unknown')}: {e}")
                    client.close()
                    disconnected_clients.append(client) # Mark for removal

    # Cleanup any dead connections we found
    if disconnected_clients:
        with clients_lock:
            for client in disconnected_clients:
                if client in clients:
                    username = clients.pop(client) # Remove from dictionary
                    print(f"[DISCONNECTED] {username} has left (detected on broadcast).")
        send_user_list() # Tell everyone the user list has changed


def send_user_list():
    """
    Creates a list of all connected usernames and sends it to everyone.
    The client uses this to update its "Users" sidebar list.
    Protocol Format: "USER_LIST,Alice,Bob,Charlie\n"
    """
    with clients_lock:
        if not clients: 
            return
        # Create the protocol string
        user_list = "USER_LIST," + ",".join(clients.values()) + "\n"
        print(f"Sending user list: {user_list.strip()}")
        
        # Send to everyone (including the sender this time)
        for client in clients.keys():
            try:
                client.send(user_list.encode('utf-8'))
            except:
                pass 

def handle_client(client_socket):
    """
    This function runs in a SEPARATE THREAD for every single client.
    It acts as a dedicated listener for one specific user.
    """
    username = ""
    try:
        # --- STEP 1: HANDSHAKE ---
        # The first thing a client sends MUST be the JOIN command.
        join_message_bytes = client_socket.recv(1024)
        if not join_message_bytes:
            print("[INVALID JOIN] Client disconnected before sending JOIN.")
            client_socket.close()
            return
            
        join_message = join_message_bytes.decode('utf-8')
        # Protocol Check: Does it start with "JOIN,"?
        if join_message.startswith("JOIN,"):
            username = join_message.split(',', 1)[1].strip()
            
            # Success! Add them to our list.
            with clients_lock:
                clients[client_socket] = username
            print(f"[NEW CONNECTION] {username} has connected.")
            send_user_list() # Update everyone's list
        else:
            print(f"[INVALID JOIN] Client sent: {join_message}")
            client_socket.close()
            return
            
        # --- STEP 2: MAIN LOOP ---
        # Listen for commands forever until they disconnect
        buffer = ""
        while True:
            data_bytes = client_socket.recv(1024)
            if not data_bytes:
                break # recv returning Empty means they disconnected
            
            buffer += data_bytes.decode('utf-8')
            
            # Handle "TCP Fragmentation":
            # Sometimes multiple messages arrive at once ("DRAW...DRAW...").
            # We split by '\n' to process them one by one.
            while '\n' in buffer:
                message, buffer = buffer.split('\n', 1)
                message_with_newline = message + '\n'
                
                # --- PROTOCOL HANDLER ---
                
                # 1. Drawing Commands (Broadcast these raw)
                if message.startswith(("DRAW,", "LINE,", "RECT,", "CIRCLE,", "TRI,", "CLEAR")):
                    broadcast(message_with_newline.encode('utf-8'), client_socket)
                
                # 2. Chat Messages (Format nicely then broadcast)
                elif message.startswith("CHAT,"):
                    # Client sends: "CHAT,hello world"
                    # We convert to: "CHAT,Alice,hello world" (so others know WHO said it)
                    chat_text = message.split(',', 1)[1]
                    chat_message = f"CHAT,{username},{chat_text}\n"
                    print(f"[CHAT] {username}: {chat_text}")
                    broadcast(chat_message.encode('utf-8'), client_socket)
            
    except Exception as e:
        print(f"[ERROR] {e}")
    
    # --- STEP 3: DISCONNECT ---
    with clients_lock:
        if client_socket in clients:
            username = clients.pop(client_socket)
            print(f"[CONNECTION CLOSED] {username} has disconnected.")
            send_user_list()
    client_socket.close()

def start_server():
    """Initializes the socket and starts the acceptance loop."""
    # Create the socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # This option prevents "Address already in use" errors if you restart quickly
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind and Listen
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"[*] Server is listening on {HOST}:{PORT}...")
    
    while True:
        # Accept new connection
        client_socket, address = server_socket.accept()
        
        # Spin up a new thread for this client
        thread = threading.Thread(target=handle_client, args=(client_socket,))
        thread.start()

if __name__ == "__main__":
    start_server()