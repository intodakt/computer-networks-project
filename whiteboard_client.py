import socket
import threading
import tkinter as tk
from tkinter import simpledialog, colorchooser, messagebox, PanedWindow, Listbox, Entry

# CONFIG
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 9090

class WhiteboardApp:
    def __init__(self, root, client_socket, username):
        self.root = root
        self.client_socket = client_socket
        self.username = username
        
        self.current_color = 'black'
        self.current_tool = 'brush'
        self.brush_size = 2
        
        self.drag_start_pos = None
        self.last_pos = None 
        self.temp_shape_id = None 
        
        self.setup_gui()
        
        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        self.root.title(f"Network Whiteboard - {self.username}")
        self.root.geometry("1000x600")
        self.root.minsize(800, 500) # Prevent window from getting too small

        # Main container (Split Screen)
        self.main_pane = PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=5, bg="#999")
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # --- LEFT: CANVAS ---
        self.canvas_frame = tk.Frame(self.main_pane, bg='white')
        self.canvas = tk.Canvas(self.canvas_frame, bg='white', cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.main_pane.add(self.canvas_frame, width=750)

        # --- RIGHT: SIDEBAR ---
        # We use a dedicated frame for the sidebar
        self.sidebar = tk.Frame(self.main_pane, width=250, bg='#f0f0f0')
        self.main_pane.add(self.sidebar)

        # ==============================================================
        # LAYOUT STRATEGY: THE SANDWICH
        # 1. Pack fixed-height items to the TOP
        # 2. Pack the input field to the BOTTOM (so it's always visible)
        # 3. Pack the Chat History in the remaining space (EXPAND)
        # ==============================================================

        # --- 1. TOP SECTIONS (Tools, Properties, Actions, User List) ---
        
        # Tools
        self.tools_frame = tk.LabelFrame(self.sidebar, text="Tools", bg='#f0f0f0', padx=2, pady=2)
        self.tools_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        tools = [("✏️", "brush"), ("📏", "line"), ("⬜", "rect"), 
                 ("⭕", "circle"), ("🔺", "tri"), ("🧼", "eraser")]
        c = 0
        for text, value in tools:
            tk.Button(self.tools_frame, text=text, width=4, command=lambda v=value: self.select_tool(v)).grid(row=0, column=c, padx=1)
            c += 1

        # Properties (Size & Color)
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

        # Clear Button
        tk.Button(self.sidebar, text="🗑️ Clear All", command=self.clear_canvas, bg="#ffcccc").pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        # User List
        tk.Label(self.sidebar, text="Online Users:", bg='#f0f0f0', font=("Arial", 8, "bold")).pack(side=tk.TOP, anchor=tk.W, padx=5)
        self.user_listbox = Listbox(self.sidebar, height=3, bg='white', font=("Arial", 8))
        self.user_listbox.pack(side=tk.TOP, fill=tk.X, padx=5)

        # --- 2. BOTTOM SECTION (Chat Entry) ---
        # IMPORTANT: We pack this to the BOTTOM *before* the chat history.
        # This forces Tkinter to reserve space for it at the bottom edge.
        self.chat_entry = Entry(self.sidebar, font=("Arial", 10))
        self.chat_entry.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        self.chat_entry.bind("<Return>", self.send_chat_message)
        
        tk.Label(self.sidebar, text="Type Message:", bg='#f0f0f0', font=("Arial", 8)).pack(side=tk.BOTTOM, anchor=tk.W, padx=5)

        # --- 3. MIDDLE SECTION (Chat History) ---
        # Now we pack the listbox to fill whatever space is LEFT.
        tk.Label(self.sidebar, text="Chat History:", bg='#f0f0f0', font=("Arial", 8, "bold")).pack(side=tk.TOP, anchor=tk.W, padx=5, pady=(5,0))
        
        self.chat_listbox = Listbox(self.sidebar, bg='white', font=("Arial", 9))
        self.chat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        # Add a scrollbar for chat
        scrollbar = tk.Scrollbar(self.sidebar)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.chat_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.chat_listbox.yview)

        # Bindings
        self.canvas.bind('<Button-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)

    # --- MOUSE LOGIC (Smooth Lines) ---
    def on_press(self, event):
        self.drag_start_pos = (event.x, event.y)
        self.last_pos = (event.x, event.y)
        if self.current_tool in ['brush', 'eraser']:
            self.paint_segment(event.x, event.y, event.x, event.y)

    def on_drag(self, event):
        if self.current_tool in ['brush', 'eraser']:
            x1, y1 = self.last_pos
            x2, y2 = event.x, event.y
            self.paint_segment(x1, y1, x2, y2)
            self.last_pos = (x2, y2)
        else:
            if self.temp_shape_id: self.canvas.delete(self.temp_shape_id)
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
            if msg: self.send_to_server(msg)

    def paint_segment(self, x1, y1, x2, y2):
        size = self.size_slider.get()
        color = self.current_color if self.current_tool == 'brush' else 'white'
        self.canvas.create_line(x1, y1, x2, y2, fill=color, width=size, capstyle=tk.ROUND, smooth=True)
        message = f"DRAW,{x1},{y1},{x2},{y2},{color},{size}\n"
        self.send_to_server(message)

    # --- HELPERS ---
    def clear_canvas(self):
        self.canvas.delete("all")
        self.send_to_server("CLEAR\n")
    def set_color(self, c): self.current_color = c
    def select_tool(self, t): self.current_tool = t
    def choose_color(self):
        c = colorchooser.askcolor()[1]
        if c: self.current_color = c
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
        try: self.client_socket.send(msg.encode('utf-8'))
        except: pass

    # --- NETWORK ---
    def receive_messages(self):
        buffer = ""
        while True:
            try:
                data = self.client_socket.recv(1024).decode('utf-8')
                if not data: break
                buffer += data
                while '\n' in buffer:
                    msg, buffer = buffer.split('\n', 1)
                    parts = msg.split(',')
                    cmd = parts[0]
                    
                    if cmd == 'DRAW':
                        x1, y1, x2, y2 = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
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
                    elif cmd == 'CLEAR': self.canvas.delete("all")
                    elif cmd == 'USER_LIST': self.update_user_list(parts[1:])
                    elif cmd == 'CHAT': 
                        if parts[1] != self.username: # Don't double post own messages
                            self.display_chat_message(parts[1], ','.join(parts[2:]))
            except: break
        
        messagebox.showinfo("Error", "Disconnected from server")
        self.client_socket.close()
        self.root.destroy()

    def update_user_list(self, users):
        self.user_listbox.delete(0, tk.END)
        for u in users: self.user_listbox.insert(tk.END, u)
    
    def on_closing(self):
        self.client_socket.close()
        self.root.destroy()

def main():
    root = tk.Tk()
    root.withdraw()
    u = simpledialog.askstring("Username", "Enter Name:", parent=root)
    if not u: return
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((SERVER_HOST, SERVER_PORT))
        s.send(f"JOIN,{u}\n".encode('utf-8'))
        root.deiconify()
        WhiteboardApp(root, s, u)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error", f"Cannot connect: {e}")

if __name__ == "__main__":
    main()