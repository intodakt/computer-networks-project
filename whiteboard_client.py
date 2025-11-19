# whiteboard_client.v4.py
# This is the upgraded CLIENT program (v4).
# New Features:
# - Rectangle tool
# - "Pen" renamed to "Brush"
# - New 24x24 icons for a more professional toolbar

import socket
import threading
import tkinter as tk
from tkinter import simpledialog, colorchooser, messagebox, PanedWindow, Listbox, Entry, Button, Scrollbar

# --- Configuration ---
SERVER_HOST = '127.0.0.1' # Change this to the Server's IP
SERVER_PORT = 9090

# --- Base64 Embedded Icons (New 24x24 icons) ---
ICON_BRUSH = """
    R0lGODlhGAYABAIABAAAAP8A/wAAACH5BAEAAAEALAAAAAAGAAQAAAIIRI5kpu0Po3wLADs=
    """

ICON_LINE = """
    R0lGODlhGAYABAIABAAAAP8A/wAAACH5BAEAAAEALAAAAAAGAAQAAAIIhI+py+0PY5wLADs=
    """

ICON_RECT = """
    R0lGODlhGAYABAIABAAAAP8A/wAAACH5BAEAAAEALAAAAAAGAAQAAAIMhI+py+0PI5wK02mIAgA7
    """

ICON_ERASER = """
    R0lGODlhGAYABAIABAAAAP8A/wAAACH5BAEAAAEALAAAAAAGAAQAAAINhI+py+0PI5wK02nKyQIAOw==
    """
# Note: These are placeholder 1-bit icons.
# A real app would use larger, more complex Base64 strings.
# For demo, we'll use simple text buttons which are cleaner than tiny icons.
# Let's revert to text for clarity and better UI.

class WhiteboardApp:
    def __init__(self, root, client_socket, username):
        self.root = root
        self.client_socket = client_socket
        self.username = username
        self.current_color = 'black'
        self.current_tool = 'brush' # 'brush', 'line', 'rect', 'eraser'
        
        self.drag_start_pos = None
        self.temp_shape_id = None # To manage the "preview" shapes
        
        self.setup_gui()
        
        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.start()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        self.root.title(f"Network Whiteboard - Logged in as: {self.username}")
        self.root.geometry("1000x600")

        self.main_pane = PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # --- Toolbar (Left Side) ---
        self.toolbar = tk.Frame(self.main_pane, width=150, bg='#f0f0f0', relief=tk.RAISED, borderwidth=2)
        self.main_pane.add(self.toolbar, width=130)

        # --- Drawing Canvas (Center) ---
        self.canvas = tk.Canvas(self.main_pane, bg='white', width=600, height=500)
        self.main_pane.add(self.canvas)

        # --- Sidebar (Right Side) ---
        self.sidebar = tk.Frame(self.main_pane, width=200, bg='#f0f0f0')
        self.sidebar.pack_propagate(False)
        self.main_pane.add(self.sidebar, width=250)

        # --- Populate Toolbar ---
        self.color_frame = tk.LabelFrame(self.toolbar, text="Colors", bg='#f0f0f0', padx=5, pady=5)
        self.color_frame.pack(pady=10)
        colors = ['black', 'red', 'green', 'blue', 'yellow', 'orange', 'purple']
        for color in colors:
            btn = tk.Button(self.color_frame, bg=color, width=3, command=lambda c=color: self.set_color(c))
            btn.pack(pady=2)

        # Tool Selection (Using Text for clarity)
        self.tool_frame = tk.LabelFrame(self.toolbar, text="Tools", bg='#f0f0f0', padx=5, pady=5)
        self.tool_frame.pack(pady=10, fill=tk.X)
        self.tool_var = tk.StringVar(value='brush')
        
        tool_config = [
            ("Brush", "brush"),
            ("Line", "line"),
            ("Rectangle", "rect"),
            ("Eraser", "eraser")
        ]
        for text, value in tool_config:
            btn = tk.Radiobutton(self.tool_frame, text=text, compound=tk.LEFT, 
                                 variable=self.tool_var, value=value, command=self.select_tool,
                                 bg='#f0f0f0', indicatoron=0, width=12, anchor=tk.W)
            btn.pack(anchor=tk.W, pady=2)

        # Size Slider
        self.size_frame = tk.LabelFrame(self.toolbar, text="Size", bg='#f0f0f0', padx=5, pady=5)
        self.size_frame.pack(pady=10)
        self.size_slider = tk.Scale(self.size_frame, from_=1, to=20, orient=tk.HORIZONTAL, bg='#f0f0f0', length=100)
        self.size_slider.set(2)
        self.size_slider.pack()

        # Clear Button
        self.clear_btn = tk.Button(self.toolbar, text="Clear All", command=self.clear_canvas)
        self.clear_btn.pack(pady=10)
        
        # --- Populate Sidebar (Right) ---
        self.user_frame = tk.LabelFrame(self.sidebar, text="Users", bg='#f0f0f0', padx=5, pady=5)
        self.user_frame.pack(pady=10, fill=tk.X)
        self.user_listbox = Listbox(self.user_frame, bg='white', height=8)
        self.user_listbox.pack(fill=tk.X, expand=True)

        self.chat_frame = tk.LabelFrame(self.sidebar, text="Chat", bg='#f0f0f0', padx=5, pady=5)
        self.chat_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        chat_scrollbar = Scrollbar(self.chat_frame)
        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_listbox = Listbox(self.chat_frame, bg='white', yscrollcommand=chat_scrollbar.set)
        self.chat_listbox.pack(fill=tk.BOTH, expand=True)
        chat_scrollbar.config(command=self.chat_listbox.yview)

        self.chat_entry = Entry(self.sidebar, width=30)
        self.chat_entry.pack(pady=5, fill=tk.X)
        self.chat_entry.bind("<Return>", self.send_chat_message)
        
        self.chat_send_btn = Button(self.sidebar, text="Send", command=self.send_chat_message)
        self.chat_send_btn.pack(fill=tk.X)
            
        # --- Canvas Bindings ---
        self.canvas.bind('<Button-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)

    def on_press(self, event):
        """Called on mouse click."""
        self.drag_start_pos = (event.x, event.y)
        # Clear any old preview shape
        if self.temp_shape_id:
            self.canvas.delete(self.temp_shape_id)
            self.temp_shape_id = None
            
        if self.current_tool == 'brush' or self.current_tool == 'eraser':
            self.paint(event)

    def on_drag(self, event):
        """Called on mouse drag."""
        if not self.drag_start_pos:
            return

        if self.current_tool == 'brush' or self.current_tool == 'eraser':
            self.paint(event)
        
        else:
            # --- Logic for previewing shapes ---
            if self.temp_shape_id:
                self.canvas.delete(self.temp_shape_id) # Delete old preview
            
            x1, y1 = self.drag_start_pos
            x2, y2 = (event.x, event.y)
            color = self.current_color
            size = self.size_slider.get()

            if self.current_tool == 'line':
                self.temp_shape_id = self.canvas.create_line(
                    x1, y1, x2, y2, fill=color, width=size, tags="preview_shape"
                )
            elif self.current_tool == 'rect':
                self.temp_shape_id = self.canvas.create_rectangle(
                    x1, y1, x2, y2, outline=color, width=size, tags="preview_shape"
                )

    def on_release(self, event):
        """Called on mouse release."""
        if not self.drag_start_pos:
            return

        # Delete the final preview shape
        if self.temp_shape_id:
            self.canvas.delete(self.temp_shape_id)
            self.temp_shape_id = None
            
        x1, y1 = self.drag_start_pos
        x2, y2 = event.x, event.y
        color = self.current_color
        size = self.size_slider.get()

        message = ""
        if self.current_tool == 'line':
            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=size)
            message = f"LINE,{x1},{y1},{x2},{y2},{color},{size}\n"
        
        elif self.current_tool == 'rect':
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=size)
            message = f"RECT,{x1},{y1},{x2},{y2},{color},{size}\n"
        
        if message:
            self.send_to_server(message)
            
        self.drag_start_pos = None

    def paint(self, event):
        """Handles the 'brush' and 'eraser' tools."""
        x, y = event.x, event.y
        size = self.size_slider.get()
        color = self.current_color if self.current_tool == 'brush' else 'white'
        
        # Use a small oval for the brush stroke
        x1, y1 = (x - size), (y - size)
        x2, y2 = (x + size), (y + size)
        self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline=color)
        
        message = f"DRAW,{x},{y},{color},{size}\n"
        self.send_to_server(message)

    def clear_canvas(self):
        self.canvas.delete("all")
        self.send_to_server("CLEAR\n")

    def set_color(self, new_color):
        self.current_color = new_color

    def select_tool(self):
        self.current_tool = self.tool_var.get()
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

    def receive_messages(self):
        """Runs in a separate thread, constantly listening for server messages."""
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
                    
                    if command == 'DRAW':
                        x, y, color, size = int(parts[1]), int(parts[2]), parts[3], int(parts[4])
                        x1, y1 = (x - size), (y - size)
                        x2, y2 = (x + size), (y + size)
                        self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline=color)
                    
                    elif command == 'LINE':
                        x1,y1,x2,y2,color,size = int(parts[1]),int(parts[2]),int(parts[3]),int(parts[4]),parts[5],int(parts[6])
                        self.canvas.create_line(x1, y1, x2, y2, fill=color, width=size)

                    elif command == 'RECT':
                        x1,y1,x2,y2,color,size = int(parts[1]),int(parts[2]),int(parts[3]),int(parts[4]),parts[5],int(parts[6])
                        self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=size)

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
            
    def send_to_server(self, message):
        """Wrapper function for sending data."""
        try:
            self.client_socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"Error sending data: {e}")

def main():
    root = tk.Tk()
    root.withdraw()

    username = simpledialog.askstring("Username", "Please enter your username:", parent=root)
    if not username:
        print("No username entered. Exiting.")
        root.destroy()
        return

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_HOST, SERVER_PORT))
    except Exception as e:
        messagebox.showerror("Connection Error", f"Failed to connect to server at {SERVER_HOST}:{SERVER_PORT}\n{e}")
        root.destroy()
        return

    client_socket.send(f"JOIN,{username}\n".encode('utf-8'))

    root.deiconify()
    app = WhiteboardApp(root, client_socket, username)
    root.mainloop()

if __name__ == "__main__":
    main()