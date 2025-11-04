import tkinter as tk
from tkinter import ttk, messagebox
import requests
import time
import base64
import io
import threading
from PIL import Image, ImageTk
import pyautogui
import json

SERVER_URL = "https://service-zopk.onrender.com"


class ModernScreenShareApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NeonShare - Modern Screen Sharing")
        self.root.geometry("1200x800")
        self.root.configure(bg='#0a0a0a')

        # Application state
        self.server_name = ""
        self.server_password = ""
        self.server_id = ""
        self.connected_servers = []
        self.connected_clients = []
        self.is_hosting = False
        self.is_viewing = False
        self.fullscreen = False
        self.current_viewer_id = None
        self.control_access = False

        # Performance settings
        self.frame_rate = 60
        self.quality = 85
        self.last_frame_time = 0

        self.setup_styles()
        self.create_main_interface()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Modern dark theme with neon accents
        self.style.configure('.', background='#0a0a0a', foreground='#ffffff')
        self.style.configure('TFrame', background='#0a0a0a')
        self.style.configure('TLabel', background='#0a0a0a', foreground='#e0e0e0', font=('Segoe UI', 10))
        self.style.configure('Title.TLabel', font=('Segoe UI', 28, 'bold'), foreground='#00ff88')
        self.style.configure('Subtitle.TLabel', font=('Segoe UI', 12), foreground='#888888')

        # Modern buttons with hover effects
        self.style.configure('Neon.TButton', background='#1a1a1a', foreground='#00ff88',
                             borderwidth=0, focuscolor='none')
        self.style.map('Neon.TButton',
                       background=[('active', '#00ff88'), ('pressed', '#00cc66')],
                       foreground=[('active', '#000000'), ('pressed', '#000000')]
                       )

        self.style.configure('Danger.TButton', background='#1a1a1a', foreground='#ff4444')
        self.style.map('Danger.TButton',
                       background=[('active', '#ff4444'), ('pressed', '#cc0000')],
                       foreground=[('active', '#000000'), ('pressed', '#000000')]
                       )

        # Entry styling
        self.style.configure('Modern.TEntry', fieldbackground='#1a1a1a', foreground='#ffffff',
                             borderwidth=1, focusthickness=1, focuscolor='#00ff88')

        # Treeview styling
        self.style.configure('Modern.Treeview', background='#1a1a1a', foreground='#ffffff',
                             fieldbackground='#1a1a1a', borderwidth=0, rowheight=25)
        self.style.configure('Modern.Treeview.Heading', background='#2a2a2a', foreground='#00ff88')
        self.style.map('Modern.Treeview', background=[('selected', '#00ff88')])

    def create_main_interface(self):
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Header
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill='x', pady=(0, 30))

        title = ttk.Label(header_frame, text="NEONSHARE", style='Title.TLabel')
        title.pack(side='left')

        subtitle = ttk.Label(header_frame, text="Ultra-Fast 60FPS Screen Sharing",
                             style='Subtitle.TLabel')
        subtitle.pack(side='left', padx=(10, 0), pady=10)

        # Settings button
        ttk.Button(header_frame, text="⚙️", command=self.show_settings,
                   style='Neon.TButton', width=3).pack(side='right')

        # Main content area
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill='both', expand=True)

        # Left panel - Server creation
        left_panel = ttk.Frame(content_frame, width=400)
        left_panel.pack(side='left', fill='y', padx=(0, 20))
        left_panel.pack_propagate(False)

        self.create_server_panel(left_panel)

        # Right panel - Server list
        right_panel = ttk.Frame(content_frame)
        right_panel.pack(side='left', fill='both', expand=True)

        self.create_servers_panel(right_panel)

    def create_server_panel(self, parent):
        # Server creation section
        server_frame = ttk.LabelFrame(parent, text="CREATE SERVER", padding=20)
        server_frame.pack(fill='x', pady=(0, 20))

        ttk.Label(server_frame, text="Server Name:", font=('Segoe UI', 11)).pack(anchor='w', pady=(0, 5))
        self.server_name_entry = ttk.Entry(server_frame, font=('Segoe UI', 11), style='Modern.TEntry')
        self.server_name_entry.pack(fill='x', pady=(0, 15))

        ttk.Label(server_frame, text="Password (optional):", font=('Segoe UI', 11)).pack(anchor='w', pady=(0, 5))
        self.server_password_entry = ttk.Entry(server_frame, show="•", font=('Segoe UI', 11), style='Modern.TEntry')
        self.server_password_entry.pack(fill='x', pady=(0, 20))

        ttk.Button(server_frame, text="🎮 START HOSTING", command=self.start_hosting,
                   style='Neon.TButton').pack(fill='x', pady=5)

        # Host controls (visible when hosting)
        self.host_controls_frame = ttk.Frame(parent)

        ttk.Label(self.host_controls_frame, text="Connected Clients:",
                  font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 10))

        self.clients_tree = ttk.Treeview(self.host_controls_frame, columns=('name', 'control'),
                                         show='headings', height=8, style='Modern.Treeview')
        self.clients_tree.heading('name', text='CLIENT NAME')
        self.clients_tree.heading('control', text='CONTROL ACCESS')
        self.clients_tree.column('name', width=200)
        self.clients_tree.column('control', width=150)
        self.clients_tree.pack(fill='both', expand=True)

        control_buttons = ttk.Frame(self.host_controls_frame)
        control_buttons.pack(fill='x', pady=10)

        ttk.Button(control_buttons, text="Grant Control",
                   command=self.grant_control, style='Neon.TButton').pack(side='left', padx=(0, 10))
        ttk.Button(control_buttons, text="Revoke Control",
                   command=self.revoke_control, style='Neon.TButton').pack(side='left', padx=(0, 10))
        ttk.Button(control_buttons, text="Kick Client",
                   command=self.kick_client, style='Danger.TButton').pack(side='left')

        ttk.Button(self.host_controls_frame, text="🛑 STOP HOSTING",
                   command=self.stop_hosting, style='Danger.TButton').pack(fill='x', pady=10)

    def create_servers_panel(self, parent):
        # Available servers section
        servers_frame = ttk.LabelFrame(parent, text="AVAILABLE SERVERS", padding=10)
        servers_frame.pack(fill='both', expand=True)

        # Server list with refresh
        list_header = ttk.Frame(servers_frame)
        list_header.pack(fill='x', pady=(0, 10))

        ttk.Label(list_header, text="Double-click to connect",
                  style='Subtitle.TLabel').pack(side='left')
        ttk.Button(list_header, text="🔄 REFRESH", command=self.refresh_servers,
                   style='Neon.TButton').pack(side='right')

        self.servers_tree = ttk.Treeview(servers_frame, columns=('name', 'clients', 'password'),
                                         show='headings', style='Modern.Treeview')
        self.servers_tree.heading('name', text='SERVER NAME')
        self.servers_tree.heading('clients', text='CLIENTS')
        self.servers_tree.heading('password', text='PASSWORD PROTECTED')
        self.servers_tree.column('name', width=300)
        self.servers_tree.column('clients', width=100)
        self.servers_tree.column('password', width=150)

        scrollbar = ttk.Scrollbar(servers_frame, orient='vertical', command=self.servers_tree.yview)
        self.servers_tree.configure(yscrollcommand=scrollbar.set)

        self.servers_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self.servers_tree.bind('<Double-1>', self.connect_to_server)

        # Viewer controls
        self.viewer_controls_frame = ttk.Frame(servers_frame)

        control_info = ttk.Label(self.viewer_controls_frame,
                                 text="Remote Control: Waiting for host permission...",
                                 foreground='#ffaa00', font=('Segoe UI', 11))
        control_info.pack(pady=10)

        ttk.Button(self.viewer_controls_frame, text="⛶ FULLSCREEN",
                   command=self.toggle_fullscreen, style='Neon.TButton').pack(side='left', padx=(0, 10))
        ttk.Button(self.viewer_controls_frame, text="📱 REQUEST CONTROL",
                   command=self.request_control, style='Neon.TButton').pack(side='left', padx=(0, 10))
        ttk.Button(self.viewer_controls_frame, text="🔌 DISCONNECT",
                   command=self.disconnect_viewer, style='Danger.TButton').pack(side='left')

    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        settings_window.configure(bg='#0a0a0a')
        settings_window.transient(self.root)
        settings_window.grab_set()

        ttk.Label(settings_window, text="Performance Settings",
                  style='Title.TLabel').pack(pady=20)

        # Frame rate setting
        frame_rate_frame = ttk.Frame(settings_window)
        frame_rate_frame.pack(fill='x', padx=20, pady=10)

        ttk.Label(frame_rate_frame, text="Frame Rate:").pack(side='left')
        frame_rate_var = tk.StringVar(value=str(self.frame_rate))
        frame_rate_combo = ttk.Combobox(frame_rate_frame, textvariable=frame_rate_var,
                                        values=['30', '45', '60', '75'], state='readonly')
        frame_rate_combo.pack(side='right')

        # Quality setting
        quality_frame = ttk.Frame(settings_window)
        quality_frame.pack(fill='x', padx=20, pady=10)

        ttk.Label(quality_frame, text="Quality:").pack(side='left')
        quality_var = tk.StringVar(value=str(self.quality))
        quality_scale = ttk.Scale(quality_frame, from_=50, to=95, variable=quality_var)
        quality_scale.pack(side='right', fill='x', expand=True)

        def apply_settings():
            self.frame_rate = int(frame_rate_var.get())
            self.quality = int(quality_var.get())
            settings_window.destroy()
            messagebox.showinfo("Settings", "Settings applied successfully!")

        ttk.Button(settings_window, text="APPLY", command=apply_settings,
                   style='Neon.TButton').pack(pady=20)

    def start_hosting(self):
        self.server_name = self.server_name_entry.get().strip()
        self.server_password = self.server_password_entry.get().strip()

        if not self.server_name:
            messagebox.showerror("Error", "Please enter a server name")
            return

        try:
            response = requests.post(f"{SERVER_URL}/create_server", json={
                'name': self.server_name,
                'password': self.server_password,
                'max_clients': 10
            })

            if response.status_code == 200:
                data = response.json()
                self.server_id = data['server_id']
                self.is_hosting = True
                self.show_host_interface()
                self.start_streaming()
            else:
                messagebox.showerror("Error", "Failed to create server")

        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {str(e)}")

    def show_host_interface(self):
        # Hide server creation, show host controls
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        host_frame = ttk.Frame(self.main_frame)
        host_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Header
        header = ttk.Frame(host_frame)
        header.pack(fill='x', pady=(0, 20))

        ttk.Label(header, text=f"HOSTING: {self.server_name}",
                  style='Title.TLabel').pack(side='left')

        ttk.Button(header, text="⚙️", command=self.show_settings,
                   style='Neon.TButton', width=3).pack(side='right')

        # Client list and controls
        self.create_host_controls(host_frame)

    def create_host_controls(self, parent):
        # Client management
        clients_frame = ttk.LabelFrame(parent, text="CONNECTED CLIENTS", padding=15)
        clients_frame.pack(fill='both', expand=True)

        self.clients_tree = ttk.Treeview(clients_frame, columns=('name', 'control', 'id'),
                                         show='headings', style='Modern.Treeview')
        self.clients_tree.heading('name', text='CLIENT NAME')
        self.clients_tree.heading('control', text='CONTROL STATUS')
        self.clients_tree.heading('id', text='ID')
        self.clients_tree.column('name', width=250)
        self.clients_tree.column('control', width=150)
        self.clients_tree.column('id', width=100)

        scrollbar = ttk.Scrollbar(clients_frame, orient='vertical', command=self.clients_tree.yview)
        self.clients_tree.configure(yscrollcommand=scrollbar.set)

        self.clients_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Control buttons
        control_frame = ttk.Frame(clients_frame)
        control_frame.pack(fill='x', pady=10)

        ttk.Button(control_frame, text="Grant Control",
                   command=self.grant_control, style='Neon.TButton').pack(side='left', padx=5)
        ttk.Button(control_frame, text="Revoke Control",
                   command=self.revoke_control, style='Neon.TButton').pack(side='left', padx=5)
        ttk.Button(control_frame, text="Kick Client",
                   command=self.kick_client, style='Danger.TButton').pack(side='left', padx=5)

        ttk.Button(clients_frame, text="🛑 STOP HOSTING",
                   command=self.stop_hosting, style='Danger.TButton').pack(pady=10)

        # Start client monitoring
        self.monitor_clients()

    def start_streaming(self):
        def stream_loop():
            while self.is_hosting:
                try:
                    # Capture screen
                    screenshot = pyautogui.screenshot()

                    # Optimize image
                    img_bytes = io.BytesIO()
                    screenshot.save(img_bytes, format='JPEG', quality=self.quality, optimize=True)
                    img_b64 = base64.b64encode(img_bytes.getvalue()).decode()

                    # Update server with new frame
                    requests.post(f"{SERVER_URL}/update_frame", json={
                        'server_id': self.server_id,
                        'frame': img_b64,
                        'timestamp': time.time()
                    })

                    # Maintain frame rate
                    frame_delay = 1.0 / self.frame_rate
                    elapsed = time.time() - self.last_frame_time
                    if elapsed < frame_delay:
                        time.sleep(frame_delay - elapsed)
                    self.last_frame_time = time.time()

                except Exception as e:
                    print(f"Streaming error: {e}")
                    time.sleep(0.1)

        stream_thread = threading.Thread(target=stream_loop, daemon=True)
        stream_thread.start()

    def monitor_clients(self):
        def update_loop():
            while self.is_hosting:
                try:
                    response = requests.get(f"{SERVER_URL}/server_clients/{self.server_id}")
                    if response.status_code == 200:
                        clients = response.json().get('clients', [])
                        self.update_clients_list(clients)
                    time.sleep(1)
                except:
                    time.sleep(2)

        monitor_thread = threading.Thread(target=update_loop, daemon=True)
        monitor_thread.start()

    def update_clients_list(self, clients):
        self.clients_tree.delete(*self.clients_tree.get_children())
        for client in clients:
            self.clients_tree.insert('', 'end', values=(
                client.get('name', 'Unknown'),
                '✅' if client.get('has_control') else '❌',
                client.get('id', '')
            ))

    def grant_control(self):
        selection = self.clients_tree.selection()
        if selection:
            client_id = self.clients_tree.item(selection[0])['values'][2]
            requests.post(f"{SERVER_URL}/grant_control", json={
                'server_id': self.server_id,
                'client_id': client_id
            })

    def revoke_control(self):
        selection = self.clients_tree.selection()
        if selection:
            client_id = self.clients_tree.item(selection[0])['values'][2]
            requests.post(f"{SERVER_URL}/revoke_control", json={
                'server_id': self.server_id,
                'client_id': client_id
            })

    def kick_client(self):
        selection = self.clients_tree.selection()
        if selection:
            client_id = self.clients_tree.item(selection[0])['values'][2]
            requests.post(f"{SERVER_URL}/kick_client", json={
                'server_id': self.server_id,
                'client_id': client_id
            })

    def stop_hosting(self):
        self.is_hosting = False
        if self.server_id:
            requests.post(f"{SERVER_URL}/stop_server", json={'server_id': self.server_id})
        self.server_id = ""
        self.create_main_interface()

    def refresh_servers(self):
        try:
            response = requests.get(f"{SERVER_URL}/servers")
            if response.status_code == 200:
                servers = response.json().get('servers', [])
                self.update_servers_list(servers)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh: {str(e)}")

    def update_servers_list(self, servers):
        self.servers_tree.delete(*self.servers_tree.get_children())
        for server in servers:
            self.servers_tree.insert('', 'end', values=(
                server['name'],
                f"{server.get('client_count', 0)}/10",
                '🔒' if server.get('password') else '🔓'
            ), tags=(server['id'],))

    def connect_to_server(self, event):
        selection = self.servers_tree.selection()
        if selection:
            server_id = self.servers_tree.item(selection[0])['tags'][0]
            server_name = self.servers_tree.item(selection[0])['values'][0]
            has_password = self.servers_tree.item(selection[0])['values'][2] == '🔒'

            password = ""
            if has_password:
                password = tk.simpledialog.askstring("Password",
                                                     f"Enter password for '{server_name}':", show='•')
                if password is None:
                    return

            self.start_viewing(server_id, password)

    def start_viewing(self, server_id, password):
        try:
            response = requests.post(f"{SERVER_URL}/join_server", json={
                'server_id': server_id,
                'password': password,
                'client_name': f"Viewer_{int(time.time())}"
            })

            if response.status_code == 200:
                self.is_viewing = True
                self.current_viewer_id = response.json().get('client_id')
                self.show_viewer_interface(server_id)
            else:
                messagebox.showerror("Error", "Failed to connect to server")

        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {str(e)}")

    def show_viewer_interface(self, server_id):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        viewer_frame = ttk.Frame(self.main_frame)
        viewer_frame.pack(fill='both', expand=True)

        # Header with controls
        header = ttk.Frame(viewer_frame)
        header.pack(fill='x', pady=10)

        ttk.Button(header, text="⛶ FULLSCREEN",
                   command=self.toggle_fullscreen, style='Neon.TButton').pack(side='left', padx=5)
        ttk.Button(header, text="📱 REQUEST CONTROL",
                   command=self.request_control, style='Neon.TButton').pack(side='left', padx=5)
        ttk.Button(header, text="🔌 DISCONNECT",
                   command=self.disconnect_viewer, style='Danger.TButton').pack(side='left', padx=5)

        # Screen display
        self.screen_label = ttk.Label(viewer_frame, text="Connecting...",
                                      background='#000000', foreground='#ffffff')
        self.screen_label.pack(fill='both', expand=True, padx=20, pady=20)

        # Start receiving frames
        self.start_receiving_frames(server_id)

    def start_receiving_frames(self, server_id):
        def receive_loop():
            while self.is_viewing:
                try:
                    response = requests.get(f"{SERVER_URL}/server_frame/{server_id}")
                    if response.status_code == 200:
                        frame_data = response.json().get('frame')
                        if frame_data:
                            img_data = base64.b64decode(frame_data)
                            image = Image.open(io.BytesIO(img_data))

                            # Get current window size for optimal scaling
                            width = self.screen_label.winfo_width()
                            height = self.screen_label.winfo_height()

                            if width > 1 and height > 1:
                                image.thumbnail((width, height), Image.Resampling.LANCZOS)

                            photo = ImageTk.PhotoImage(image)
                            self.screen_label.configure(image=photo, text="")
                            self.screen_label.image = photo

                    # Control frame rate
                    time.sleep(1.0 / self.frame_rate)

                except Exception as e:
                    print(f"Viewing error: {e}")
                    time.sleep(0.1)

        receive_thread = threading.Thread(target=receive_loop, daemon=True)
        receive_thread.start()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.root.attributes('-fullscreen', self.fullscreen)

        if not self.fullscreen:
            self.root.geometry("1200x800")

    def request_control(self):
        if self.current_viewer_id:
            requests.post(f"{SERVER_URL}/request_control", json={
                'client_id': self.current_viewer_id
            })
            messagebox.showinfo("Control", "Control request sent to host")

    def disconnect_viewer(self):
        self.is_viewing = False
        self.current_viewer_id = None
        self.create_main_interface()


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernScreenShareApp(root)
    root.mainloop()