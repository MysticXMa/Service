import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import socket
import json
import threading
import time

class ModernServerBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("Game Server Browser")
        self.root.geometry("1000x750")
        self.root.configure(bg='#1a1a1a')

        self.root.minsize(900, 650)

        self.colors = {
            'bg_primary': '#1a1a1a',
            'bg_secondary': '#2d2d2d',
            'bg_tertiary': '#3d3d3d',
            'accent': '#4a90e2',
            'accent_hover': '#357abd',
            'success': '#27ae60',
            'warning': '#e67e22',
            'error': '#e74c3c',
            'text_primary': '#ffffff',
            'text_secondary': '#b3b3b3',
            'text_muted': '#888888',
            'border': '#404040'
        }

        self.current_server = None
        self.connected = False
        self.server_socket = None
        self.listen_thread = None
        self.hosting = False
        self.hosted_server = None

        self.setup_styles()

        self.create_widgets()

        self.refresh_servers()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('Modern.TFrame',
                        background=self.colors['bg_primary'])

        style.configure('Card.TFrame',
                        background=self.colors['bg_secondary'],
                        relief='raised',
                        borderwidth=1)

        style.configure('Title.TLabel',
                        background=self.colors['bg_primary'],
                        foreground=self.colors['text_primary'],
                        font=('Segoe UI', 18, 'bold'))

        style.configure('Subtitle.TLabel',
                        background=self.colors['bg_secondary'],
                        foreground=self.colors['text_primary'],
                        font=('Segoe UI', 12, 'bold'))

        style.configure('Body.TLabel',
                        background=self.colors['bg_secondary'],
                        foreground=self.colors['text_primary'],
                        font=('Segoe UI', 10))

        style.configure('Muted.TLabel',
                        background=self.colors['bg_secondary'],
                        foreground=self.colors['text_muted'],
                        font=('Segoe UI', 9))

        style.configure('Accent.TButton',
                        background=self.colors['accent'],
                        foreground=self.colors['text_primary'],
                        borderwidth=0,
                        focuscolor='none',
                        font=('Segoe UI', 10, 'bold'))

        style.map('Accent.TButton',
                  background=[('active', self.colors['accent_hover']),
                              ('pressed', self.colors['accent_hover'])])

        style.configure('Secondary.TButton',
                        background=self.colors['bg_tertiary'],
                        foreground=self.colors['text_primary'],
                        borderwidth=0,
                        focuscolor='none',
                        font=('Segoe UI', 9))

        style.map('Secondary.TButton',
                  background=[('active', self.colors['accent']),
                              ('pressed', self.colors['accent'])])

        style.configure('Modern.Treeview',
                        background=self.colors['bg_secondary'],
                        foreground=self.colors['text_primary'],
                        fieldbackground=self.colors['bg_secondary'],
                        borderwidth=0,
                        rowheight=25)

        style.configure('Modern.Treeview.Heading',
                        background=self.colors['bg_tertiary'],
                        foreground=self.colors['text_primary'],
                        borderwidth=0,
                        font=('Segoe UI', 10, 'bold'))

        style.map('Modern.Treeview',
                  background=[('selected', self.colors['accent'])])

        style.configure('Modern.TEntry',
                        fieldbackground=self.colors['bg_tertiary'],
                        foreground=self.colors['text_primary'],
                        borderwidth=1,
                        relief='solid')

        style.configure('Modern.TCombobox',
                        fieldbackground=self.colors['bg_tertiary'],
                        foreground=self.colors['text_primary'],
                        background=self.colors['bg_tertiary'])

        style.configure('Modern.Vertical.TScrollbar',
                        background=self.colors['bg_tertiary'],
                        troughcolor=self.colors['bg_primary'],
                        borderwidth=0,
                        arrowsize=12)

    def create_widgets(self):
        main_container = ttk.Frame(self.root, style='Modern.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.create_header(main_container)

        content_frame = ttk.Frame(main_container, style='Modern.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))

        left_panel = ttk.Frame(content_frame, style='Modern.TFrame')
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.create_server_list(left_panel)

        right_panel = ttk.Frame(content_frame, style='Modern.TFrame')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(10, 0))
        right_panel.configure(width=350)

        self.create_controls_panel(right_panel)
        self.create_chat_panel(right_panel)

    def create_header(self, parent):
        header_frame = ttk.Frame(parent, style='Modern.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_frame = ttk.Frame(header_frame, style='Modern.TFrame')
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        title_label = ttk.Label(title_frame, text="Game Server Browser", style='Title.TLabel')
        title_label.pack(anchor=tk.W)

        subtitle_label = ttk.Label(title_frame, text="Discover and join multiplayer game servers",
                                   style='Muted.TLabel')
        subtitle_label.pack(anchor=tk.W, pady=(2, 0))

        refresh_btn = ttk.Button(header_frame, text="🔄 Refresh",
                                 command=self.refresh_servers, style='Secondary.TButton')
        refresh_btn.pack(side=tk.RIGHT, padx=(10, 0))

    def create_server_list(self, parent):
        list_card = ttk.Frame(parent, style='Card.TFrame')
        list_card.pack(fill=tk.BOTH, expand=True)
        list_card.configure(padding=15)

        header_frame = ttk.Frame(list_card, style='Card.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(header_frame, text="Available Servers", style='Subtitle.TLabel').pack(side=tk.LEFT)

        server_count_label = ttk.Label(header_frame, text="0 servers", style='Muted.TLabel')
        server_count_label.pack(side=tk.RIGHT)
        self.server_count_label = server_count_label

        columns = ('name', 'players', 'status', 'password', 'host')
        self.server_tree = ttk.Treeview(list_card, columns=columns, show='headings',
                                        style='Modern.Treeview', height=15)

        column_config = {
            'name': {'text': 'Server Name', 'width': 200, 'anchor': tk.W},
            'players': {'text': 'Players', 'width': 80, 'anchor': tk.CENTER},
            'status': {'text': 'Status', 'width': 80, 'anchor': tk.CENTER},
            'password': {'text': 'Password', 'width': 80, 'anchor': tk.CENTER},
            'host': {'text': 'Host', 'width': 120, 'anchor': tk.W}
        }

        for col, config in column_config.items():
            self.server_tree.heading(col, text=config['text'])
            self.server_tree.column(col, width=config['width'], anchor=config['anchor'])

        self.server_tree.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_card, orient=tk.VERTICAL, command=self.server_tree.yview,
                                  style='Modern.Vertical.TScrollbar')
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.server_tree.configure(yscrollcommand=scrollbar.set)

        self.server_tree.bind('<Double-1>', self.on_server_double_click)

        connect_btn = ttk.Button(list_card, text="Connect to Server",
                                 command=self.on_connect_click, style='Accent.TButton')
        connect_btn.pack(fill=tk.X, pady=(12, 0))

    def create_controls_panel(self, parent):
        controls_card = ttk.Frame(parent, style='Card.TFrame')
        controls_card.pack(fill=tk.X, pady=(0, 15))
        controls_card.configure(padding=15)

        ttk.Label(controls_card, text="Host Your Server", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 12))

        settings_frame = ttk.Frame(controls_card, style='Card.TFrame')
        settings_frame.pack(fill=tk.X, pady=(0, 15))

        port_frame = ttk.Frame(settings_frame, style='Card.TFrame')
        port_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(port_frame, text="Port:", style='Body.TLabel').pack(side=tk.LEFT)
        self.port_entry = ttk.Entry(port_frame, width=10, style='Modern.TEntry')
        self.port_entry.pack(side=tk.RIGHT)
        self.port_entry.insert(0, "5556")

        players_frame = ttk.Frame(settings_frame, style='Card.TFrame')
        players_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(players_frame, text="Max Players:", style='Body.TLabel').pack(side=tk.LEFT)
        self.max_players_combo = ttk.Combobox(players_frame, values=[2, 4, 6, 8, 10, 16, 32],
                                              width=8, style='Modern.TCombobox', state='readonly')
        self.max_players_combo.pack(side=tk.RIGHT)
        self.max_players_combo.set("8")

        password_frame = ttk.Frame(settings_frame, style='Card.TFrame')
        password_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(password_frame, text="Password:", style='Body.TLabel').pack(side=tk.LEFT)
        self.password_entry = ttk.Entry(password_frame, width=15, show="•", style='Modern.TEntry')
        self.password_entry.pack(side=tk.RIGHT)

        self.host_btn = ttk.Button(controls_card, text="Start Hosting",
                                   command=self.toggle_hosting, style='Accent.TButton')
        self.host_btn.pack(fill=tk.X)

        status_card = ttk.Frame(parent, style='Card.TFrame')
        status_card.pack(fill=tk.X)
        status_card.configure(padding=15)

        ttk.Label(status_card, text="Connection Status", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 8))

        self.status_label = ttk.Label(status_card, text="● Not Connected",
                                      style='Body.TLabel', foreground=self.colors['error'])
        self.status_label.pack(anchor=tk.W)

        self.server_info_label = ttk.Label(status_card, text="No server selected",
                                           style='Muted.TLabel')
        self.server_info_label.pack(anchor=tk.W, pady=(2, 0))

    def create_chat_panel(self, parent):
        chat_card = ttk.Frame(parent, style='Card.TFrame')
        chat_card.pack(fill=tk.BOTH, expand=True)
        chat_card.configure(padding=15)

        ttk.Label(chat_card, text="Server Messages", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 8))

        self.chat_area = scrolledtext.ScrolledText(
            chat_card,
            bg=self.colors['bg_tertiary'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            wrap=tk.WORD,
            font=('Segoe UI', 9),
            padx=10,
            pady=10,
            relief='flat',
            borderwidth=0
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        self.chat_area.config(state=tk.DISABLED)

    def refresh_servers(self):
        try:
            # Clear existing servers
            for item in self.server_tree.get_children():
                self.server_tree.delete(item)

            central_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            central_socket.settimeout(5)
            central_socket.connect(('service-zopk.onrender.com', 5555))

            request = {'action': 'get_servers'}
            central_socket.send(json.dumps(request).encode('utf-8'))

            response = central_socket.recv(4096).decode('utf-8')
            servers = json.loads(response)

            central_socket.close()

            for server in servers:
                players_text = f"{server['current_players']}/{server['max_players']}"
                password_text = "✓" if server['has_password'] else "✗"
                status_text = server['status'].capitalize()

                self.server_tree.insert('', tk.END, values=(
                    server['name'],
                    players_text,
                    status_text,
                    password_text,
                    f"{server['host']}:{server['port']}"
                ), tags=(server['port'],))

            self.server_count_label.config(text=f"{len(servers)} servers available")
            self.log_message(f"✓ Refreshed server list - found {len(servers)} servers")

        except Exception as e:
            self.log_message(f"✗ Error refreshing servers: {e}")
            messagebox.showerror("Connection Error", f"Failed to refresh server list: {e}")

    def on_server_double_click(self, event):
        self.on_connect_click()

    def on_connect_click(self):
        selection = self.server_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a server from the list first.")
            return

        item = selection[0]
        server_values = self.server_tree.item(item)['values']

        if server_values:
            host_port = server_values[4]
            has_password = server_values[3] == "✓"

            if has_password:
                password = self.ask_for_password()
                if password is None:
                    return
            else:
                password = None

            self.connect_to_server(host_port, password)

    def ask_for_password(self):
        return tk.simpledialog.askstring("Server Password", "This server requires a password:", show='•')

    def connect_to_server(self, host_port, password=None):
        try:
            host, port = host_port.split(':')
            port = int(port)

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.settimeout(5)
            self.server_socket.connect((host, port))

            welcome_data = self.server_socket.recv(1024).decode('utf-8')
            welcome_msg = json.loads(welcome_data)

            if welcome_msg['type'] == 'welcome':
                self.log_message(f"✓ Connected to server: {welcome_msg['message']}")

                if welcome_msg.get('requires_password') and password:
                    auth_msg = {'password': password}
                    self.server_socket.send(json.dumps(auth_msg).encode('utf-8'))

                    auth_response = self.server_socket.recv(1024).decode('utf-8')
                    auth_result = json.loads(auth_response)

                    if auth_result['type'] == 'error':
                        self.log_message(f"✗ Authentication failed: {auth_result['message']}")
                        self.server_socket.close()
                        return

                self.connected = True
                self.current_server = host_port
                self.update_status(f"● Connected to {host_port}", self.colors['success'])
                self.server_info_label.config(
                    text=f"Players: {welcome_msg.get('current_players', '?')}/{welcome_msg.get('max_players', '?')}")

                self.listen_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
                self.listen_thread.start()

                self.log_message("✓ Successfully joined the server!")

        except Exception as e:
            self.log_message(f"✗ Failed to connect: {e}")
            messagebox.showerror("Connection Error", f"Failed to connect to server: {e}")

    def listen_for_messages(self):
        while self.connected:
            try:
                data = self.server_socket.recv(1024).decode('utf-8')
                if not data:
                    break

                message = json.loads(data)

                if message['type'] == 'chat':
                    self.log_message(f"[{message['timestamp']}] {message['sender']}: {message['message']}")
                elif message['type'] == 'player_count':
                    self.log_message(f"↻ Player count: {message['count']}/{message['max_players']}")
                    self.server_info_label.config(text=f"Players: {message['count']}/{message['max_players']}")
                elif message['type'] == 'disconnect':
                    self.log_message(f"⚠ Server: {message['message']}")
                    self.disconnect_from_server()
                    break

            except:
                break

    def disconnect_from_server(self):
        if self.connected:
            self.connected = False
            if self.server_socket:
                self.server_socket.close()
            self.update_status("● Not Connected", self.colors['error'])
            self.server_info_label.config(text="No server selected")
            self.log_message("⚠ Disconnected from server")

    def update_status(self, text, color=None):
        self.status_label.config(text=text)
        if color:
            self.status_label.config(foreground=color)

    def toggle_hosting(self):
        if not self.hosting:
            self.start_hosting()
        else:
            self.stop_hosting()

    def start_hosting(self):
        try:
            port = int(self.port_entry.get())
            max_players = int(self.max_players_combo.get())
            password = self.password_entry.get() or None

            import subprocess
            import sys

            cmd = [sys.executable, 'server.py', str(port), str(max_players)]
            if password:
                cmd.append(password)

            self.hosted_server = subprocess.Popen(cmd)
            self.hosting = True
            self.host_btn.config(text="Stop Hosting")
            self.log_message(f"✓ Started hosting server on port {port}")
            self.update_status(f"● Hosting on port {port}", self.colors['success'])

        except Exception as e:
            self.log_message(f"✗ Failed to start hosting: {e}")
            messagebox.showerror("Hosting Error", f"Failed to start server: {e}")

    def stop_hosting(self):
        if self.hosted_server:
            self.hosted_server.terminate()
            self.hosted_server.wait()
            self.hosted_server = None

        self.hosting = False
        self.host_btn.config(text="Start Hosting")
        self.log_message("⚠ Stopped hosting server")
        if not self.connected:
            self.update_status("● Not Connected", self.colors['error'])

    def log_message(self, message):
        self.chat_area.config(state=tk.NORMAL)

        if message.startswith('✓'):
            tag_color = self.colors['success']
        elif message.startswith('✗') or message.startswith('⚠'):
            tag_color = self.colors['error']
        else:
            tag_color = self.colors['text_primary']

        self.chat_area.insert(tk.END, f"{message}\n")

        start_index = self.chat_area.index("end-2l")
        end_index = self.chat_area.index("end-1l")
        self.chat_area.tag_add("colored", start_index, end_index)
        self.chat_area.tag_config("colored", foreground=tag_color)

        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def on_closing(self):
        self.disconnect_from_server()
        if self.hosting:
            self.stop_hosting()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernServerBrowser(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()