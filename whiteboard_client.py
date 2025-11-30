# -----------------------------------------------------------------------------
# CLIENT PROGRAM (whiteboard_client.py)
# -----------------------------------------------------------------------------
# TEAM MEMBER RESPONSIBILITY: Erkinov Shakhzodjon 23013094 & Zubaydullayev Asliddin - 25013371 & 
#
# DESCRIPTION:
# This program handles the GUI (Tkinter) and Network logic.
# It separates networking into a background thread to prevent the GUI from freezing.
# It implements "Interpolation" for smooth drawing lines.
# -----------------------------------------------------------------------------

import socket
import threading
import tkinter as tk
import whiteboard_server

from tkinter import simpledialog, colorchooser, messagebox, PanedWindow, Listbox, Entry
import random


# --- NETWORK CONFIGURATION ---
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8000

class WhiteboardApp:
    def __init__(self, root, client_socket, username, room_code=""):
        self.root = root
        self.client_socket = client_socket
        self.username = username
        self.room_code = room_code

        # Drawing State
        self.current_color = 'black'
        self.current_tool = 'brush'
        self.brush_size = 2

        # "last_pos" is used for Smooth Drawing (connecting A to B)
        self.last_pos = None
        self.drag_start_pos = None
        self.temp_shape_id = None

        # 1. Build the UI
        self.setup_gui()

        # 2. Start Listening for network messages
        # daemon=True ensures this thread dies when the main window closes
        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.start()

        # 3. Handle window close button
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        """Builds the window layout."""
        self.root.title(f"Network Whiteboard - {self.username} (Room: {self.room_code})")
        self.root.geometry("1000x600")
        self.root.minsize(800, 500)  # Minimum size to prevent UI breaking

        # PanedWindow creates a draggable divider between Canvas and Sidebar
        self.main_pane = PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=5, bg="#999")
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # --- LEFT: CANVAS ---
        self.canvas_frame = tk.Frame(self.main_pane, bg='white')
        self.canvas = tk.Canvas(self.canvas_frame, bg='white', cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.main_pane.add(self.canvas_frame, width=750)

        # --- RIGHT: SIDEBAR ---
        self.sidebar = tk.Frame(self.main_pane, width=250, bg='#f0f0f0')
        self.main_pane.add(self.sidebar)

        # === UI SANDWICH LAYOUT ===

        # [TOP] Tools Section
        self.tools_frame = tk.LabelFrame(self.sidebar, text="Tools", bg='#f0f0f0', padx=2, pady=2)
        self.tools_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        tools = [("✏️", "brush"), ("📏", "line"), ("⬜", "rect"),
                 ("⭕", "circle"), ("🔺", "tri"), ("🧼", "eraser")]
        c = 0
        for text, value in tools:
            tk.Button(self.tools_frame, text=text, width=4,
                      command=lambda v=value: self.select_tool(v)).grid(row=0, column=c, padx=1)
            c += 1

        # [TOP] Properties (Size/Color)
        self.props_frame = tk.LabelFrame(self.sidebar, text="Properties", bg='#f0f0f0', padx=2, pady=2)
        self.props_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        self.size_slider = tk.Scale(self.props_frame, from_=1, to=20, orient=tk.HORIZONTAL, bg='#f0f0f0', label="Size")
        self.size_slider.set(2)
        self.size_slider.pack(fill=tk.X)

        btn_row = tk.Frame(self.props_frame, bg='#f0f0f0')
        btn_row.pack(fill=tk.X, pady=2)
        colors = ['black', 'red', 'green', 'blue', 'orange']
        for col in colors:
            tk.Button(btn_row, bg=col, width=2, command=lambda c=col: self.set_color(c)).pack(side=tk.LEFT, padx=1)
        tk.Button(btn_row, text="🎨", command=self.choose_color).pack(side=tk.LEFT, padx=1)

        # [TOP] Clear & User List
        tk.Button(self.sidebar, text="🗑️ Clear All", command=self.clear_canvas, bg="#ffcccc").pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        tk.Label(self.sidebar, text="Online Users:", bg='#f0f0f0', font=("Arial", 8, "bold")).pack(side=tk.TOP, anchor=tk.W, padx=5)
        self.user_listbox = Listbox(self.sidebar, height=3, bg='white', font=("Arial", 8))
        self.user_listbox.pack(side=tk.TOP, fill=tk.X, padx=5)

        # [BOTTOM] Chat Entry
        self.chat_entry = Entry(self.sidebar, font=("Arial", 10))
        self.chat_entry.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        self.chat_entry.bind("<Return>", self.send_chat_message)
        tk.Label(self.sidebar, text="Type Message:", bg='#f0f0f0', font=("Arial", 8)).pack(side=tk.BOTTOM, anchor=tk.W, padx=5)

        # [MIDDLE] Chat History
        tk.Label(self.sidebar, text="Chat History:", bg='#f0f0f0', font=("Arial", 8, "bold")).pack(side=tk.TOP, anchor=tk.W, padx=5, pady=(5,0))
        self.chat_listbox = Listbox(self.sidebar, bg='white', font=("Arial", 9))
        self.chat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=2)

        # Scrollbar for chat
        scrollbar = tk.Scrollbar(self.sidebar)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.chat_listbox.yview)

        # Event Bindings
        self.canvas.bind('<Button-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)

    # --- LOGIC: MOUSE & DRAWING ---
    def on_press(self, event):
        self.drag_start_pos = (event.x, event.y)
        self.last_pos = (event.x, event.y)
        if self.current_tool in ['brush', 'eraser']:
            self.paint_segment(event.x, event.y, event.x, event.y)

    def on_drag(self, event):
        # Smooth Drawing Logic:
        # Instead of drawing a dot at event.x/y, we draw a LINE from
        # the last mouse position to the current one. This fills the gaps.
        if self.current_tool in ['brush', 'eraser']:
            x1, y1 = self.last_pos
            x2, y2 = event.x, event.y
            self.paint_segment(x1, y1, x2, y2)
            self.last_pos = (x2, y2)  # Update last position
        else:
            # Shape Preview Logic (Draws temporary shape)
            if self.temp_shape_id:
                self.canvas.delete(self.temp_shape_id)
            x1, y1 = self.drag_start_pos
            x2, y2 = event.x, event.y
            c, s = self.current_color, self.size_slider.get()

            if self.current_tool == 'line':
                self.temp_shape_id = self.canvas.create_line(x1, y1, x2, y2, fill=c, width=s)
            elif self.current_tool == 'rect':
                self.temp_shape_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline=c, width=s)
            elif self.current_tool == 'circle':
                self.temp_shape_id = self.canvas.create_oval(x1, y1, x2, y2, outline=c, width=s)
            elif self.current_tool == 'tri':
                x3 = x1 + (x2 - x1) / 2
                self.temp_shape_id = self.canvas.create_polygon(x1, y2, x2, y2, x3, y1, outline=c, width=s, fill='')

    def on_release(self, event):
        self.last_pos = None
        if self.temp_shape_id:
            self.canvas.delete(self.temp_shape_id)
            self.temp_shape_id = None

        # If it was a shape tool, finalize the shape and send to server
        if self.current_tool not in ['brush', 'eraser'] and self.drag_start_pos:
            x1, y1 = self.drag_start_pos
            x2, y2 = event.x, event.y
            c, s = self.current_color, self.size_slider.get()
            msg = ""
            if self.current_tool == 'line':
                self.canvas.create_line(x1, y1, x2, y2, fill=c, width=s)
                msg = f"LINE,{x1},{y1},{x2},{y2},{c},{s}\n"
            elif self.current_tool == 'rect':
                self.canvas.create_rectangle(x1, y1, x2, y2, outline=c, width=s)
                msg = f"RECT,{x1},{y1},{x2},{y2},{c},{s}\n"
            elif self.current_tool == 'circle':
                self.canvas.create_oval(x1, y1, x2, y2, outline=c, width=s)
                msg = f"CIRCLE,{x1},{y1},{x2},{y2},{c},{s}\n"
            elif self.current_tool == 'tri':
                x3 = x1 + (x2 - x1) / 2
                self.canvas.create_polygon(x1, y2, x2, y2, x3, y1, outline=c, width=s, fill='')
                msg = f"TRI,{x1},{y2},{x2},{y2},{x3},{y1},{c},{s}\n"
            if msg:
                self.send_to_server(msg)

    def paint_segment(self, x1, y1, x2, y2):
        """Draws a line locally and notifies server."""
        size = self.size_slider.get()
        color = self.current_color if self.current_tool == 'brush' else 'white'
        self.canvas.create_line(x1, y1, x2, y2, fill=color, width=size, capstyle=tk.ROUND, smooth=True)
        message = f"DRAW,{x1},{y1},{x2},{y2},{color},{size}\n"
        self.send_to_server(message)

    # --- LOGIC: HELPERS ---
    def clear_canvas(self):
        self.canvas.delete("all")
        self.send_to_server("CLEAR\n")
    def set_color(self, c):
        self.current_color = c
    def select_tool(self, t):
        self.current_tool = t
    def choose_color(self):
        c = colorchooser.askcolor()[1]
        if c:
            self.current_color = c
    def send_chat_message(self, e=None):
        txt = self.chat_entry.get()
        if txt:
            self.send_to_server(f"CHAT,{txt}\n")
            self.chat_entry.delete(0, tk.END)
            self.display_chat_message("Me", txt)
    def display_chat_message(self, user, text):
        self.chat_listbox.insert(tk.END, f"{user}: {text}")
        self.chat_listbox.yview(tk.END)
    def send_to_server(self, msg):
        try:
            self.client_socket.send(msg.encode('utf-8'))
        except:
            pass

    # --- LOGIC: NETWORKING (Background Thread) ---
    def receive_messages(self):
        """Listens for incoming messages."""
        buffer = ""
        while True:
            try:
                data = self.client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    msg, buffer = buffer.split('\n', 1)
                    parts = msg.split(',')
                    cmd = parts[0]
                    if cmd == 'DRAW':
                        x1, y1, x2, y2 = map(int, parts[1:5])
                        c, s = parts[5], int(parts[6])
                        self.canvas.create_line(x1, y1, x2, y2, fill=c, width=s, capstyle=tk.ROUND)
                    elif cmd == 'LINE':
                        self.canvas.create_line(int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), fill=parts[5], width=int(parts[6]))
                    elif cmd == 'RECT':
                        self.canvas.create_rectangle(int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), outline=parts[5], width=int(parts[6]))
                    elif cmd == 'CIRCLE':
                        self.canvas.create_oval(int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), outline=parts[5], width=int(parts[6]))
                    elif cmd == 'TRI':
                        self.canvas.create_polygon(int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5]), int(parts[6]), outline=parts[7], width=int(parts[8]), fill='')
                    elif cmd == 'CLEAR':
                        self.canvas.delete("all")
                    elif cmd == 'USER_LIST':
                        self.update_user_list(parts[1:])
                    elif cmd == 'CHAT':
                        if parts[1] != self.username:
                            self.display_chat_message(parts[1], ','.join(parts[2:]))
            except:
                break
        messagebox.showinfo("Error", "Disconnected from server")
        self.client_socket.close()
        self.root.destroy()
        sys.exit(0)
    
    

    def update_user_list(self, users):
        self.user_listbox.delete(0, tk.END)
        for u in users:
            self.user_listbox.insert(tk.END, u)

    def on_closing(self):
        self.client_socket.close()
        self.root.destroy()

def main():
    root = tk.Tk()
    root.withdraw()
    input_ip = simpledialog.askstring("IP Adress", "Enter Host IP ", parent=root)
    
    if input_ip:
        SERVER_HOST = input_ip
    else:
        SERVER_HOST = '127.0.0.1'

    
    username = simpledialog.askstring("Username", "Enter Name:", parent=root)
    if not username:
        return
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((SERVER_HOST, SERVER_PORT))
        # Ask user to create or join a room
        create = messagebox.askyesno("Room", "Create a new room? (Yes = Create, No = Join)")
        if create:
            room_code = str(random.randint(1000, 9999))
            messagebox.showinfo("Room Created", f"Room code: {room_code}")
        else:
            room_code = simpledialog.askstring("Join", "Enter Room Code:")
            if not room_code:
                return
        # Send JOIN with room code
        s.send(f"JOIN,{username},{room_code}\n".encode('utf-8'))
        root.deiconify()
        WhiteboardApp(root, s, username, room_code)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error", f"Cannot connect: {e}")

    


if __name__ == "__main__":
    main()
