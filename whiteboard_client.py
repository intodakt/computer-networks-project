# whiteboard_client.v5.py
# -----------------------------------------------------------------------------
# CLIENT PROGRAM
# -----------------------------------------------------------------------------
# This program handles the user interface and sending/receiving data.
# It consists of two main threads running at the same time:
# 1. Main Thread (GUI): Handles mouse clicks, drawing, and button presses.
# 2. Network Thread: Listens for incoming messages from the server.
# -----------------------------------------------------------------------------

import socket
import threading
import tkinter as tk
from tkinter import simpledialog, colorchooser, messagebox, PanedWindow, Listbox, Entry, Button, Scrollbar

# --- NETWORK CONFIGURATION ---
# IMPORTANT: Change this IP to the computer running the server!
# Use '127.0.0.1' if running on the same computer.
SERVER_HOST = '127.0.0.1' 
SERVER_PORT = 9090

class WhiteboardApp:
    def __init__(self, root, client_socket, username):
        self.root = root
        self.client_socket = client_socket
        self.username = username
        
        # Default settings
        self.current_color = 'black'
        self.current_tool = 'brush' 
        self.brush_size = 2
        
        # Variables for shape drawing (click-and-drag)
        self.drag_start_pos = None
        self.temp_shape_id = None 
        
        # Build the User Interface
        self.setup_gui()
        
        # Start the Network Thread
        # daemon=True means this thread dies automatically when the main window closes
        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.start()
        
        # Handle window closing safely
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        """Builds the entire window layout using Tkinter frames."""
        self.root.title(f"Network Whiteboard - User: {self.username}")
        self.root.geometry("1100x600")

        # Use a PanedWindow to allow resizing between Canvas and Sidebar
        self.main_pane = PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # --- LEFT: THE CANVAS ---
        self.canvas_frame = tk.Frame(self.main_pane, bg='white')
        self.canvas = tk.Canvas(self.canvas_frame, bg='white', cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.main_pane.add(self.canvas_frame, width=850)

        # --- RIGHT: THE SIDEBAR ---
        self.sidebar = tk.Frame(self.main_pane, width=250, bg='#f0f0f0')
        self.sidebar.pack_propagate(False) # Force the frame to stay 250px wide
        self.main_pane.add(self.sidebar)

        # --- SIDEBAR SECTION 1: TOOLS ---
        self.tools_frame = tk.LabelFrame(self.sidebar, text="Drawing Tools", bg='#f0f0f0', padx=5, pady=5)
        self.tools_frame.pack(pady=5, fill=tk.X)
        
        # Helper to create grid of buttons
        tools = [
            ("✏️ Brush", "brush"), ("📏 Line", "line"),
            ("⬜ Rect", "rect"), ("⭕ Circle", "circle"),
            ("🔺 Tri", "tri"), ("🧼 Eraser", "eraser")
        ]
        
        # Create a grid of buttons
        row = 0
        col = 0
        for text, value in tools:
            # We use a lambda to capture the specific 'value' for each button
            btn = tk.Button(self.tools_frame, text=text, width=8,
                            command=lambda v=value: self.select_tool(v))
            btn.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col > 1: # Wrap to next row every 2 buttons
                col = 0
                row += 1

        # --- SIDEBAR SECTION 2: PROPERTIES ---
        self.props_frame = tk.LabelFrame(self.sidebar, text="Properties", bg='#f0f0f0', padx=5, pady=5)
        self.props_frame.pack(pady=5, fill=tk.X)

        # Size Slider
        tk.Label(self.props_frame, text="Size:", bg='#f0f0f0').pack(anchor=tk.W)
        self.size_slider = tk.Scale(self.props_frame, from_=1, to=20, orient=tk.HORIZONTAL, bg='#f0f0f0')
        self.size_slider.set(2)
        self.size_slider.pack(fill=tk.X)

        # Color Palette
        tk.Label(self.props_frame, text="Colors:", bg='#f0f0f0').pack(anchor=tk.W, pady=(5,0))
        self.palette_frame = tk.Frame(self.props_frame, bg='#f0f0f0')
        self.palette_frame.pack()
        
        colors = ['black', 'red', 'green', 'blue', 'orange', 'purple']
        for color in colors:
            btn = tk.Button(self.palette_frame, bg=color, width=2,
                            command=lambda c=color: self.set_color(c))
            btn.pack(side=tk.LEFT, padx=2)
        
        # Custom Color Picker
        tk.Button(self.props_frame, text="Custom Color...", command=self.choose_color).pack(fill=tk.X, pady=5)

        # --- SIDEBAR SECTION 3: ACTIONS ---
        self.action_frame = tk.LabelFrame(self.sidebar, text="Actions", bg='#f0f0f0', padx=5, pady=5)
        self.action_frame.pack(pady=5, fill=tk.X)
        tk.Button(self.action_frame, text="🗑️ Clear Canvas", command=self.clear_canvas, bg="#ffcccc").pack(fill=tk.X)

        # --- SIDEBAR SECTION 4: USERS & CHAT ---
        self.chat_container = tk.Frame(self.sidebar, bg='#f0f0f0')
        self.chat_container.pack(pady=5, fill=tk.BOTH, expand=True)

        # User List
        tk.Label(self.chat_container, text="Online Users:", bg='#f0f0f0').pack(anchor=tk.W)
        self.user_listbox = Listbox(self.chat_container, height=4, bg='white')
        self.user_listbox.pack(fill=tk.X)

        # Chat History
        tk.Label(self.chat_container, text="Chat:", bg='#f0f0f0').pack(anchor=tk.W)
        self.chat_listbox = Listbox(self.chat_container, bg='white')
        self.chat_listbox.pack(fill=tk.BOTH, expand=True)

        # Chat Entry
        self.chat_entry = Entry(self.chat_container)
        self.chat_entry.pack(fill=tk.X, pady=2)
        self.chat_entry.bind("<Return>", self.send_chat_message)
            
        # --- MOUSE BINDINGS ---
        # These connect mouse actions to our functions
        self.canvas.bind('<Button-1>', self.on_press)      # Click
        self.canvas.bind('<B1-Motion>', self.on_drag)      # Drag
        self.canvas.bind('<ButtonRelease-1>', self.on_release) # Release

    # -------------------------------------------------------------------------
    # MOUSE EVENT HANDLERS
    # -------------------------------------------------------------------------
    def on_press(self, event):
        """Triggered when user clicks the mouse button."""
        self.drag_start_pos = (event.x, event.y)
        
        # Brush/Eraser start drawing immediately
        if self.current_tool in ['brush', 'eraser']:
            self.paint(event)

    def on_drag(self, event):
        """Triggered when user moves mouse while holding button."""
        if not self.drag_start_pos:
            return

        if self.current_tool in ['brush', 'eraser']:
            self.paint(event) # Continuous drawing
        else:
            # Shape Preview Logic
            # We draw a temporary shape that gets deleted and redrawn as the mouse moves
            if self.temp_shape_id:
                self.canvas.delete(self.temp_shape_id)
            
            x1, y1 = self.drag_start_pos
            x2, y2 = (event.x, event.y)
            color = self.current_color
            size = self.size_slider.get()
            
            # Determine which shape to preview
            if self.current_tool == 'line':
                self.temp_shape_id = self.canvas.create_line(x1, y1, x2, y2, fill=color, width=size)
            elif self.current_tool == 'rect':
                self.temp_shape_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=size)
            elif self.current_tool == 'circle':
                self.temp_shape_id = self.canvas.create_oval(x1, y1, x2, y2, outline=color, width=size)
            elif self.current_tool == 'tri':
                # Triangle calculation
                x3 = x1 + (x2 - x1) / 2 # Top point x
                self.temp_shape_id = self.canvas.create_polygon(x1, y2, x2, y2, x3, y1, outline=color, width=size, fill='')

    def on_release(self, event):
        """Triggered when user releases the mouse button."""
        if not self.drag_start_pos:
            return

        # Delete the preview shape
        if self.temp_shape_id:
            self.canvas.delete(self.temp_shape_id)
            self.temp_shape_id = None
            
        # Finalize coordinates
        x1, y1 = self.drag_start_pos
        x2, y2 = event.x, event.y
        color = self.current_color
        size = self.size_slider.get()
        
        message = ""
        
        # 1. Draw locally (so we see it instantly)
        # 2. Construct the protocol message to send to server
        if self.current_tool == 'line':
            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=size)
            message = f"LINE,{x1},{y1},{x2},{y2},{color},{size}\n"
        elif self.current_tool == 'rect':
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=size)
            message = f"RECT,{x1},{y1},{x2},{y2},{color},{size}\n"
        elif self.current_tool == 'circle':
            self.canvas.create_oval(x1, y1, x2, y2, outline=color, width=size)
            message = f"CIRCLE,{x1},{y1},{x2},{y2},{color},{size}\n"
        elif self.current_tool == 'tri':
            x3 = x1 + (x2 - x1) / 2
            self.canvas.create_polygon(x1, y2, x2, y2, x3, y1, outline=color, width=size, fill='')
            # Triangle protocol sends 3 coordinates
            message = f"TRI,{x1},{y2},{x2},{y2},{x3},{y1},{color},{size}\n"
        
        if message:
            self.send_to_server(message)
            
        self.drag_start_pos = None

    def paint(self, event):
        """Handles continuous drawing for Brush and Eraser."""
        x, y = event.x, event.y
        size = self.size_slider.get()
        color = self.current_color if self.current_tool == 'brush' else 'white'
        
        x1, y1 = (x - size), (y - size)
        x2, y2 = (x + size), (y + size)
        self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline=color)
        
        message = f"DRAW,{x},{y},{color},{size}\n"
        self.send_to_server(message)

    # -------------------------------------------------------------------------
    # HELPER FUNCTIONS
    # -------------------------------------------------------------------------
    def clear_canvas(self):
        self.canvas.delete("all")
        self.send_to_server("CLEAR\n")

    def set_color(self, new_color):
        self.current_color = new_color

    def choose_color(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.current_color = color

    def select_tool(self, tool_name):
        self.current_tool = tool_name
        print(f"Tool selected: {self.current_tool}")

    def send_chat_message(self, event=None):
        message_text = self.chat_entry.get()
        if message_text:
            self.send_to_server(f"CHAT,{message_text}\n")
            self.chat_entry.delete(0, tk.END)
            self.display_chat_message(self.username, message_text)

    def display_chat_message(self, user, text):
        self.chat_listbox.insert(tk.END, f"{user}: {text}")
        self.chat_listbox.yview(tk.END)

    # -------------------------------------------------------------------------
    # NETWORK LOGIC
    # -------------------------------------------------------------------------
    def send_to_server(self, message):
        try:
            self.client_socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"Error sending data: {e}")

    def receive_messages(self):
        """
        Listens for messages from the server.
        This runs in the background thread.
        """
        buffer = ""
        while True:
            try:
                data = self.client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                buffer += data
                
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    parts = message.split(',')
                    command = parts[0]
                    
                    # PROTOCOL PARSER
                    if command == 'DRAW':
                        x, y, color, size = int(parts[1]), int(parts[2]), parts[3], int(parts[4])
                        x1, y1 = (x - size), (y - size)
                        x2, y2 = (x + size), (y + size)
                        self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline=color)
                    
                    elif command == 'LINE':
                        x1,y1,x2,y2 = int(parts[1]),int(parts[2]),int(parts[3]),int(parts[4])
                        color, size = parts[5], int(parts[6])
                        self.canvas.create_line(x1, y1, x2, y2, fill=color, width=size)

                    elif command == 'RECT':
                        x1,y1,x2,y2 = int(parts[1]),int(parts[2]),int(parts[3]),int(parts[4])
                        color, size = parts[5], int(parts[6])
                        self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=size)
                        
                    elif command == 'CIRCLE':
                        x1,y1,x2,y2 = int(parts[1]),int(parts[2]),int(parts[3]),int(parts[4])
                        color, size = parts[5], int(parts[6])
                        self.canvas.create_oval(x1, y1, x2, y2, outline=color, width=size)

                    elif command == 'TRI':
                        # Triangle receives 3 coordinate pairs
                        x1,y1,x2,y2,x3,y3 = int(parts[1]),int(parts[2]),int(parts[3]),int(parts[4]),int(parts[5]),int(parts[6])
                        color, size = parts[7], int(parts[8])
                        self.canvas.create_polygon(x1, y1, x2, y2, x3, y3, outline=color, width=size, fill='')

                    elif command == 'CLEAR':
                        self.canvas.delete("all")
                    
                    elif command == 'USER_LIST':
                        self.update_user_list(parts[1:])
                    
                    elif command == 'CHAT':
                        user = parts[1]
                        text = ','.join(parts[2:])
                        self.display_chat_message(user, text)
                        
            except Exception as e:
                print(f"Connection error: {e}")
                break
        
        messagebox.showinfo("Disconnected", "Lost connection to the server.")
        self.client_socket.close()
        self.root.destroy()

    def update_user_list(self, users):
        self.user_listbox.delete(0, tk.END)
        for user in users:
            self.user_listbox.insert(tk.END, user)

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.client_socket.close()
            self.root.destroy()

# -------------------------------------------------------------------------
# MAIN ENTRY POINT
# -------------------------------------------------------------------------
def main():
    root = tk.Tk()
    root.withdraw()

    # 1. Get Username
    username = simpledialog.askstring("Username", "Please enter your username:", parent=root)
    if not username:
        root.destroy()
        return

    # 2. Connect to Server
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_HOST, SERVER_PORT))
    except Exception as e:
        messagebox.showerror("Connection Error", f"Failed to connect to server at {SERVER_HOST}:{SERVER_PORT}\n{e}")
        root.destroy()
        return

    # 3. Send JOIN
    client_socket.send(f"JOIN,{username}\n".encode('utf-8'))

    # 4. Launch App
    root.deiconify()
    app = WhiteboardApp(root, client_socket, username)
    root.mainloop()

if __name__ == "__main__":
    main()