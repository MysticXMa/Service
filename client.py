import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import base64
from PIL import Image, ImageTk
import io
import time
import uuid


class RemoteScreenWindow:
    def __init__(self, parent, session_id, device_id, backend_url):
        self.window = tk.Toplevel(parent)
        self.window.title(f"Remote Screen - {device_id}")
        self.window.geometry("800x600")
        self.window.configure(bg='#1e1e1e')

        self.session_id = session_id
        self.device_id = device_id
        self.backend_url = backend_url
        self.streaming_active = True

        screen_frame = ttk.Frame(self.window)
        screen_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.screen_label = tk.Label(
            screen_frame,
            text="🔄 Connecting to remote screen...",
            bg='#2d2d2d',
            fg='#ffffff',
            font=('Arial', 12),
            justify=tk.CENTER
        )
        self.screen_label.pack(fill=tk.BOTH, expand=True)

        controls_frame = ttk.Frame(screen_frame)
        controls_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            controls_frame,
            text="⌨️ Send Ctrl+Alt+Del",
            command=self.send_special_key
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            controls_frame,
            text="🔒 Disconnect",
            command=self.disconnect
        ).pack(side=tk.LEFT)

        self.start_screen_stream()

        self.window.protocol("WM_DELETE_WINDOW", self.disconnect)

    def start_screen_stream(self):
        def stream_thread():
            while self.streaming_active:
                try:
                    response = requests.get(
                        f"{self.backend_url}/screen",
                        params={"session_id": self.session_id},
                        timeout=5
                    )

                    if response.status_code == 200:
                        data = response.json()
                        screenshot_data = data.get('screenshot')

                        if screenshot_data:
                            image_data = base64.b64decode(screenshot_data)
                            image = Image.open(io.BytesIO(image_data))

                            display_width = 780
                            display_height = 500
                            image = image.resize((display_width, display_height), Image.Resampling.LANCZOS)

                            photo = ImageTk.PhotoImage(image)
                            self.window.after(0, lambda: self.update_screen_display(photo))
                        else:
                            self.window.after(0, lambda: self.screen_label.config(
                                text="🔄 Waiting for screen data..."
                            ))
                    time.sleep(0.1)
                except Exception as e:
                    if self.streaming_active:
                        self.window.after(0, lambda: self.screen_label.config(
                            text=f"❌ Connection error: {str(e)}"
                        ))
                        time.sleep(1)
                    else:
                        break

        threading.Thread(target=stream_thread, daemon=True).start()

    def update_screen_display(self, photo_image):
        self.screen_label.config(image=photo_image, text="")
        self.screen_label.image = photo_image

    def send_special_key(self):
        try:
            requests.post(
                f"{self.backend_url}/send_keys",
                json={"session_id": self.session_id, "keys": "ctrl_alt_del"},
                timeout=5
            )
        except:
            pass

    def disconnect(self):
        self.streaming_active = False
        try:
            requests.post(
                f"{self.backend_url}/disconnect",
                json={"session_id": self.session_id},
                timeout=5
            )
        except:
            pass
        self.window.destroy()


class ParsecLikeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote Desktop - Screen Sharing")
        self.root.geometry("1000x700")
        self.root.configure(bg='#1e1e1e')

        self.backend_url = "http://localhost:5000"
        self.my_servers = []
        self.remote_windows = []

        self.setup_ui()

    def setup_ui(self):
        self.setup_styles()

        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        header_frame = ttk.Frame(main_container, style='Header.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = tk.Label(
            header_frame,
            text="🔗 Remote Desktop Hub",
            font=('Arial', 20, 'bold'),
            fg='#ffffff',
            bg='#2d2d2d'
        )
        title_label.pack(side=tk.LEFT)

        self.status_label = tk.Label(
            header_frame,
            text="🟢 Connected",
            font=('Arial', 11, 'bold'),
            fg='#28a745',
            bg='#2d2d2d'
        )
        self.status_label.pack(side=tk.RIGHT)

        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(content_frame, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        left_panel.pack_propagate(False)

        create_server_frame = ttk.LabelFrame(
            left_panel,
            text="🚀 Create Server",
            padding=15,
            style='Card.TLabelframe'
        )
        create_server_frame.pack(fill=tk.X, pady=(0, 15))

        server_name_label = tk.Label(
            create_server_frame,
            text="Server Name:",
            font=('Arial', 9, 'bold'),
            fg='#cccccc',
            bg='#2d2d2d'
        )
        server_name_label.pack(anchor=tk.W, pady=(0, 5))

        self.server_name_entry = ttk.Entry(
            create_server_frame,
            font=('Arial', 10),
            style='Custom.TEntry'
        )
        self.server_name_entry.pack(fill=tk.X, pady=(0, 10))
        self.server_name_entry.insert(0, f"My Server {int(time.time()) % 10000}")

        password_label = tk.Label(
            create_server_frame,
            text="Password (optional):",
            font=('Arial', 9, 'bold'),
            fg='#cccccc',
            bg='#2d2d2d'
        )
        password_label.pack(anchor=tk.W, pady=(0, 5))

        self.server_password_entry = ttk.Entry(
            create_server_frame,
            font=('Arial', 10),
            style='Custom.TEntry',
            show="*"
        )
        self.server_password_entry.pack(fill=tk.X, pady=(0, 15))

        ttk.Button(
            create_server_frame,
            text="🖥️ Start Server",
            command=self.create_server,
            style='Success.TButton'
        ).pack(fill=tk.X)

        my_servers_frame = ttk.LabelFrame(
            left_panel,
            text="📋 My Servers",
            padding=10,
            style='Card.TLabelframe'
        )
        my_servers_frame.pack(fill=tk.BOTH, expand=True)

        list_frame = ttk.Frame(my_servers_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.my_servers_listbox = tk.Listbox(
            list_frame,
            bg='#3d3d3d',
            fg='#ffffff',
            selectbackground='#007acc',
            selectforeground='#ffffff',
            font=('Arial', 9),
            relief='flat',
            highlightthickness=0
        )

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.my_servers_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.my_servers_listbox.yview)

        self.my_servers_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.my_servers_listbox.bind('<Double-Button-1>', self.on_my_server_double_click)

        servers_buttons_frame = ttk.Frame(my_servers_frame)
        servers_buttons_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            servers_buttons_frame,
            text="🛑 Stop Server",
            command=self.stop_server,
            style='Danger.TButton'
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ttk.Button(
            servers_buttons_frame,
            text="📋 Copy ID",
            command=self.copy_server_id,
            style='Secondary.TButton'
        ).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        right_panel = ttk.Frame(content_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        available_servers_frame = ttk.LabelFrame(
            right_panel,
            text="🌐 Available Servers",
            padding=15,
            style='Card.TLabelframe'
        )
        available_servers_frame.pack(fill=tk.BOTH, expand=True)

        servers_list_frame = ttk.Frame(available_servers_frame)
        servers_list_frame.pack(fill=tk.BOTH, expand=True)

        self.servers_tree = ttk.Treeview(
            servers_list_frame,
            columns=('name', 'status', 'password', 'id'),
            show='headings',
            height=15
        )

        self.servers_tree.heading('name', text='Server Name')
        self.servers_tree.heading('status', text='Status')
        self.servers_tree.heading('password', text='Protection')
        self.servers_tree.heading('id', text='ID')

        self.servers_tree.column('name', width=200)
        self.servers_tree.column('status', width=100)
        self.servers_tree.column('password', width=100)
        self.servers_tree.column('id', width=150)

        style = ttk.Style()
        style.configure("Treeview",
                        background="#3d3d3d",
                        foreground="white",
                        fieldbackground="#3d3d3d")
        style.configure("Treeview.Heading",
                        background="#2d2d2d",
                        foreground="white")

        tree_scrollbar = ttk.Scrollbar(servers_list_frame, orient=tk.VERTICAL)
        self.servers_tree.configure(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.configure(command=self.servers_tree.yview)

        self.servers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.servers_tree.bind('<Double-Button-1>', self.on_server_double_click)

        connect_frame = ttk.Frame(available_servers_frame)
        connect_frame.pack(fill=tk.X, pady=(15, 0))

        password_connect_label = tk.Label(
            connect_frame,
            text="Password (if required):",
            font=('Arial', 9, 'bold'),
            fg='#cccccc',
            bg='#2d2d2d'
        )
        password_connect_label.pack(anchor=tk.W, pady=(0, 5))

        self.connect_password_entry = ttk.Entry(
            connect_frame,
            font=('Arial', 10),
            style='Custom.TEntry',
            show="*"
        )
        self.connect_password_entry.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(
            connect_frame,
            text="🔌 Connect to Selected Server",
            command=self.connect_to_server,
            style='Accent.TButton'
        ).pack(fill=tk.X)

        self.refresh_servers()
        self.auto_refresh_servers()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        bg_color = '#1e1e1e'
        card_bg = '#2d2d2d'
        accent_color = '#007acc'
        success_color = '#28a745'
        danger_color = '#dc3545'

        style.configure('TFrame', background=bg_color)
        style.configure('Header.TFrame', background=card_bg)
        style.configure('Card.TLabelframe', background=card_bg, foreground='white', bordercolor='#444444')
        style.configure('Card.TLabelframe.Label', background=card_bg, foreground='white')
        style.configure('Accent.TButton', background=accent_color, foreground='white')
        style.configure('Success.TButton', background=success_color, foreground='white')
        style.configure('Secondary.TButton', background='#495057', foreground='white')
        style.configure('Danger.TButton', background=danger_color, foreground='white')
        style.configure('Custom.TEntry', fieldbackground='#3d3d3d', foreground='white', bordercolor='#555555')

    def create_server(self):
        server_name = self.server_name_entry.get().strip()
        if not server_name:
            messagebox.showerror("Error", "Please enter a server name")
            return

        password = self.server_password_entry.get().strip()

        def create_thread():
            try:
                data = {"name": server_name}
                if password:
                    data["password"] = password

                response = requests.post(f"{self.backend_url}/share", json=data, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    device_id = data.get('device_id')
                    self.root.after(0, lambda: self.on_server_created(device_id, server_name, password))
                    self.refresh_servers()
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Failed to create server"))
            except requests.exceptions.RequestException as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Cannot connect to backend: {str(e)}"))

        threading.Thread(target=create_thread, daemon=True).start()

    def on_server_created(self, device_id, server_name, password):
        server_info = {
            'id': device_id,
            'name': server_name,
            'password': bool(password)
        }
        self.my_servers.append(server_info)
        self.update_my_servers_list()

        messagebox.showinfo(
            "Server Created",
            f"Server '{server_name}' created successfully!\n\n"
            f"Server ID: {device_id}\n"
            f"Password Protected: {'Yes' if password else 'No'}\n\n"
            "Share the Server ID with others to allow connections."
        )

    def stop_server(self):
        selection = self.my_servers_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a server to stop")
            return

        server_info = self.my_servers[selection[0]]

        def stop_thread():
            try:
                response = requests.post(
                    f"{self.backend_url}/stop_sharing",
                    json={"device_id": server_info['id']},
                    timeout=5
                )
                if response.status_code == 200:
                    self.root.after(0, lambda: self.on_server_stopped(server_info['id']))
                    self.refresh_servers()
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Failed to stop server"))
            except:
                self.root.after(0, lambda: messagebox.showerror("Error", "Failed to connect to backend"))

        threading.Thread(target=stop_thread, daemon=True).start()

    def on_server_stopped(self, device_id):
        self.my_servers = [s for s in self.my_servers if s['id'] != device_id]
        self.update_my_servers_list()
        messagebox.showinfo("Success", "Server stopped successfully")

    def copy_server_id(self):
        selection = self.my_servers_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a server")
            return

        server_info = self.my_servers[selection[0]]
        self.root.clipboard_clear()
        self.root.clipboard_append(server_info['id'])
        messagebox.showinfo("Copied", f"Server ID '{server_info['id']}' copied to clipboard")

    def update_my_servers_list(self):
        self.my_servers_listbox.delete(0, tk.END)
        for server in self.my_servers:
            status = "🔒" if server['password'] else "🔓"
            self.my_servers_listbox.insert(tk.END, f"{status} {server['name']} ({server['id']})")

    def on_my_server_double_click(self, event):
        self.copy_server_id()

    def connect_to_server(self):
        selection = self.servers_tree.selection()
        if not selection:
            messagebox.showerror("Error", "Please select a server to connect to")
            return

        item = selection[0]
        server_id = self.servers_tree.item(item, 'values')[3]
        password = self.connect_password_entry.get().strip()

        def connect_thread():
            try:
                data = {"device_id": server_id}
                if password:
                    data["password"] = password

                response = requests.post(f"{self.backend_url}/connect", json=data, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    session_id = data.get('session_id')
                    self.root.after(0, lambda: self.on_connect_success(session_id, server_id))
                else:
                    error_msg = response.json().get('error', 'Connection failed')
                    self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            except requests.exceptions.RequestException as e:
                self.root.after(0,
                                lambda: messagebox.showerror("Connection Error", f"Cannot connect to server: {str(e)}"))

        threading.Thread(target=connect_thread, daemon=True).start()

    def on_connect_success(self, session_id, device_id):
        remote_window = RemoteScreenWindow(self.root, session_id, device_id, self.backend_url)
        self.remote_windows.append(remote_window)
        messagebox.showinfo("Success", f"Connected to server {device_id}")

    def on_server_double_click(self, event):
        self.connect_to_server()

    def refresh_servers(self):
        def refresh_thread():
            try:
                response = requests.get(f"{self.backend_url}/devices", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    servers = data.get('devices', [])
                    self.root.after(0, lambda: self.update_servers_list(servers))
            except:
                pass

        threading.Thread(target=refresh_thread, daemon=True).start()

    def auto_refresh_servers(self):
        self.refresh_servers()
        self.root.after(5000, self.auto_refresh_servers)

    def update_servers_list(self, servers):
        for item in self.servers_tree.get_children():
            self.servers_tree.delete(item)

        for server in servers:
            status = server.get('status', 'offline')
            status_icon = "🟢" if status == 'online' else "🟡" if status == 'busy' else "🔴"
            password_protected = "🔒 Yes" if server.get('password_protected') else "🔓 No"

            self.servers_tree.insert('', 'end', values=(
                server.get('name', 'Unknown'),
                f"{status_icon} {status}",
                password_protected,
                server['id']
            ))


def main():
    root = tk.Tk()
    app = ParsecLikeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()