import tkinter as tk
from tkinter import ttk, messagebox
import requests
import base64
import threading
import time
from PIL import Image, ImageTk
import io


class ConnectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PC Connection Hub - Cloud Edition")
        self.root.geometry("1400x800")
        self.root.configure(bg='#000000')

        self.backend_url = "https://service-zopk.onrender.com"
        self.servers = []
        self.hosting_server = None
        self.current_connection = None
        self.screenshot_window = None
        self.update_interval = 3000  # 3 seconds
        self.screenshot_interval = 100  # 0.1 seconds = 10/s

        self.setup_ui()
        self.start_server_updates()

    def setup_ui(self):
        main_container = tk.PanedWindow(self.root, orient='horizontal', bg='#000000', sashwidth=8)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)

        self.setup_left_panel(main_container)
        self.setup_right_panel(main_container)

        main_container.add(self.left_frame)
        main_container.add(self.right_frame)

    def setup_left_panel(self, main_container):
        self.left_frame = tk.Frame(main_container, bg='#1a1a1a', width=300)

        header_frame = tk.Frame(self.left_frame, bg='#1a1a1a', padx=25, pady=25)
        header_frame.pack(fill='x', anchor='n')

        tk.Label(
            header_frame,
            text="Host Server",
            font=('Segoe UI', 20, 'bold'),
            bg='#1a1a1a',
            fg='#ffffff'
        ).pack(anchor='w', pady=(0, 10))

        tk.Label(
            header_frame,
            text="Configure and manage your server",
            font=('Segoe UI', 10),
            bg='#1a1a1a',
            fg='#ffffff'
        ).pack(anchor='w')

        separator = tk.Frame(self.left_frame, height=1, bg='#333333')
        separator.pack(fill='x', padx=20, pady=20)

        self.setup_host_form()

    def setup_host_form(self):
        form_frame = tk.Frame(self.left_frame, bg='#1a1a1a', padx=25)
        form_frame.pack(fill='both', expand=True, anchor='w')

        name_frame = tk.Frame(form_frame, bg='#1a1a1a', pady=15)
        name_frame.pack(fill='x', anchor='w')

        tk.Label(
            name_frame,
            text="Server Name:",
            font=('Segoe UI', 11, 'bold'),
            bg='#1a1a1a',
            fg='#ffffff',
            anchor='w'
        ).pack(fill='x', pady=(0, 5))

        self.name_entry = tk.Entry(
            name_frame,
            font=('Segoe UI', 11),
            bg='#2a2a2a',
            fg='#ffffff',
            insertbackground='white',
            relief='flat'
        )
        self.name_entry.pack(fill='x', pady=(5, 0))

        pin_frame = tk.Frame(form_frame, bg='#1a1a1a', pady=15)
        pin_frame.pack(fill='x', anchor='w')

        tk.Label(
            pin_frame,
            text="Pin Code (Optional):",
            font=('Segoe UI', 11, 'bold'),
            bg='#1a1a1a',
            fg='#ffffff',
            anchor='w'
        ).pack(fill='x', pady=(0, 5))

        self.pin_entry = tk.Entry(
            pin_frame,
            font=('Segoe UI', 11),
            show="*",
            bg='#2a2a2a',
            fg='#ffffff',
            insertbackground='white',
            relief='flat'
        )
        self.pin_entry.pack(fill='x', pady=(5, 0))

        users_frame = tk.Frame(form_frame, bg='#1a1a1a', pady=15)
        users_frame.pack(fill='x', anchor='w')

        tk.Label(
            users_frame,
            text="Max Users:",
            font=('Segoe UI', 11, 'bold'),
            bg='#1a1a1a',
            fg='#ffffff',
            anchor='w'
        ).pack(fill='x', pady=(0, 5))

        self.users_var = tk.StringVar(value="5")
        users_spinbox = tk.Spinbox(
            users_frame,
            from_=1,
            to=50,
            textvariable=self.users_var,
            font=('Segoe UI', 11),
            bg='#2a2a2a',
            fg='#ffffff',
            buttonbackground='#333333',
            relief='flat'
        )
        users_spinbox.pack(fill='x', pady=(5, 0))

        button_frame = tk.Frame(form_frame, bg='#1a1a1a', pady=30)
        button_frame.pack(fill='x', anchor='w')

        self.host_button = tk.Button(
            button_frame,
            text="Start Hosting",
            font=('Segoe UI', 12, 'bold'),
            bg='#4CAF50',
            fg='white',
            relief='flat',
            padx=30,
            pady=12,
            command=self.start_hosting
        )
        self.host_button.pack(fill='x', pady=(0, 10))

        self.stop_button = tk.Button(
            button_frame,
            text="Stop Hosting",
            font=('Segoe UI', 12),
            bg='#f44336',
            fg='white',
            relief='flat',
            padx=30,
            pady=12,
            command=self.stop_hosting,
            state='disabled'
        )
        self.stop_button.pack(fill='x')

        status_frame = tk.Frame(form_frame, bg='#1a1a1a', pady=20)
        status_frame.pack(fill='x', anchor='w')

        self.status_label = tk.Label(
            status_frame,
            text="Status: Not Hosting",
            font=('Segoe UI', 10),
            bg='#1a1a1a',
            fg='#ffffff',
            anchor='w'
        )
        self.status_label.pack(fill='x')

    def setup_right_panel(self, main_container):
        self.right_frame = tk.Frame(main_container, bg='#000000')

        header_frame = tk.Frame(self.right_frame, bg='#000000', padx=25, pady=25)
        header_frame.pack(fill='x')

        self.header_label = tk.Label(
            header_frame,
            text="Available Servers",
            font=('Segoe UI', 20, 'bold'),
            bg='#000000',
            fg='#ffffff'
        )
        self.header_label.pack(anchor='w')

        search_frame = tk.Frame(self.right_frame, bg='#000000', padx=25, pady=15)
        search_frame.pack(fill='x')

        tk.Label(
            search_frame,
            text="Search:",
            font=('Segoe UI', 11),
            bg='#000000',
            fg='#ffffff'
        ).pack(side='left')

        self.search_entry = tk.Entry(
            search_frame,
            font=('Segoe UI', 11),
            width=40,
            bg='#2a2a2a',
            fg='#ffffff',
            insertbackground='white',
            relief='flat'
        )
        self.search_entry.pack(side='left', padx=(10, 0))
        self.search_entry.bind('<KeyRelease>', self.filter_servers)

        self.setup_server_table()

    def setup_server_table(self):
        table_frame = tk.Frame(self.right_frame, bg='#000000')
        table_frame.pack(fill='both', expand=True, padx=25, pady=10)

        style = ttk.Style()
        style.configure("Treeview",
                        background="#000000",
                        foreground="#ffffff",
                        fieldbackground="#000000",
                        borderwidth=0,
                        relief='flat')
        style.configure("Treeview.Heading",
                        background="#000000",
                        foreground="#ffffff",
                        borderwidth=0,
                        relief='flat')
        style.map('Treeview', background=[('selected', '#333333')])

        columns = ('ID', 'Name', 'Players', 'Status')
        self.server_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=15,
            style="Treeview"
        )

        self.server_tree.heading('ID', text='Server ID')
        self.server_tree.heading('Name', text='Server Name')
        self.server_tree.heading('Players', text='Players')
        self.server_tree.heading('Status', text='Status')

        self.server_tree.column('ID', width=120)
        self.server_tree.column('Name', width=200)
        self.server_tree.column('Players', width=100)
        self.server_tree.column('Status', width=120)

        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.server_tree.yview)
        self.server_tree.configure(yscrollcommand=scrollbar.set)

        self.server_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        connection_frame = tk.Frame(self.right_frame, bg='#000000', pady=10)
        connection_frame.pack(fill='x', padx=25)

        button_container = tk.Frame(connection_frame, bg='#000000')
        button_container.pack(fill='x')

        self.connect_button = tk.Button(
            button_container,
            text="Connect to Server",
            font=('Segoe UI', 12, 'bold'),
            bg='#2196F3',
            fg='white',
            relief='flat',
            padx=20,
            pady=10,
            command=self.connect_to_server
        )
        self.connect_button.pack(side='left', padx=(0, 10))

        self.disconnect_button = tk.Button(
            button_container,
            text="Disconnect",
            font=('Segoe UI', 12),
            bg='#ff9800',
            fg='white',
            relief='flat',
            padx=20,
            pady=10,
            command=self.disconnect_from_server,
            state='disabled'
        )
        self.disconnect_button.pack(side='left', padx=(0, 10))

        self.screenshot_button = tk.Button(
            button_container,
            text="View Screen",
            font=('Segoe UI', 12),
            bg='#9c27b0',
            fg='white',
            relief='flat',
            padx=20,
            pady=10,
            command=self.show_screenshot,
            state='disabled'
        )
        self.screenshot_button.pack(side='left')

        self.server_tree.bind('<Double-1>', self.on_double_click)

    def api_request(self, endpoint, method='GET', data=None):
        try:
            url = f"{self.backend_url}{endpoint}"
            headers = {'Content-Type': 'application/json'}

            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            return response.json() if response.content else {}
        except Exception as e:
            print(f"API Error: {e}")
            return {'error': str(e)}

    def start_hosting(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter a server name")
            return

        pin_code = self.pin_entry.get().strip()
        max_users = self.users_var.get()

        data = {
            'name': name,
            'pin': pin_code,
            'max_users': int(max_users)
        }

        result = self.api_request('/api/servers', 'POST', data)

        if 'error' in result:
            messagebox.showerror("Error", f"Failed to create server: {result['error']}")
            return

        server_id = result['server_id']
        self.hosting_server = {
            'id': server_id,
            'name': name,
            'pin': pin_code,
            'max_users': max_users,
            'current_users': 0,
            'status': 'Open'
        }

        self.host_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.name_entry.config(state='disabled')
        self.pin_entry.config(state='disabled')
        self.status_label.config(text=f"Status: Hosting - {server_id}")

        messagebox.showinfo("Success", f"Server '{name}' started!\nServer ID: {server_id}")
        self.refresh_server_list()

    def stop_hosting(self):
        if self.hosting_server:
            result = self.api_request(f"/api/servers/{self.hosting_server['id']}", 'DELETE')

            if 'error' in result:
                messagebox.showerror("Error", f"Failed to stop server: {result['error']}")
                return

            self.host_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.name_entry.config(state='normal')
            self.pin_entry.config(state='normal')
            self.status_label.config(text="Status: Not Hosting")

            self.hosting_server = None
            self.refresh_server_list()

    def refresh_server_list(self):
        result = self.api_request('/api/servers')

        if 'error' in result:
            print(f"Error fetching servers: {result['error']}")
            return

        self.servers = result if isinstance(result, list) else []

        for item in self.server_tree.get_children():
            self.server_tree.delete(item)

        for server in self.servers:
            players_text = f"{server['current_users']}/{server['max_users']}"
            item = self.server_tree.insert(
                '', 'end',
                values=(
                    server['id'],
                    server['name'],
                    players_text,
                    server['status']
                )
            )

    def start_server_updates(self):
        def update_loop():
            while True:
                self.refresh_server_list()
                time.sleep(self.update_interval / 1000)

        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()

    def filter_servers(self, event):
        search_text = self.search_entry.get().lower()

        for item in self.server_tree.get_children():
            values = self.server_tree.item(item)['values']
            server_name = values[1].lower() if len(values) > 1 else ""
            server_id = values[0].lower() if len(values) > 0 else ""

            if search_text in server_name or search_text in server_id:
                self.server_tree.item(item, tags=('visible',))
            else:
                self.server_tree.item(item, tags=('hidden',))

        self.server_tree.tag_configure('visible', background='#000000')
        self.server_tree.tag_configure('hidden', background='#1a1a1a')

    def connect_to_server(self):
        selected = self.server_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a server to connect")
            return

        item = selected[0]
        server_id = self.server_tree.item(item)['values'][0]
        server_name = self.server_tree.item(item)['values'][1]

        server = next((s for s in self.servers if s['id'] == server_id), None)
        if not server:
            messagebox.showerror("Error", "Server not found")
            return

        if server['status'] != 'Open':
            messagebox.showerror("Error", f"Cannot connect. Status: {server['status']}")
            return

        # Ask for PIN if required
        pin_code = ""
        if server.get('pin'):
            pin_code = self.ask_for_pin()
            if pin_code is None:  # User cancelled
                return

        # Connect to server
        data = {
            'pin': pin_code,
            'user_name': 'User'  # In a real app, you'd ask for username
        }

        result = self.api_request(f'/api/servers/{server_id}/connect', 'POST', data)

        if 'error' in result:
            messagebox.showerror("Error", result['error'])
            return

        self.current_connection = server_id
        self.connect_button.config(state='disabled')
        self.disconnect_button.config(state='normal')
        self.screenshot_button.config(state='normal')

        messagebox.showinfo("Success", f"Connected to {server_name}!")
        self.refresh_server_list()

    def disconnect_from_server(self):
        if self.current_connection:
            result = self.api_request(f'/api/servers/{self.current_connection}/disconnect', 'POST')

            if 'error' not in result:
                messagebox.showinfo("Disconnected", "Disconnected from server")

            self.current_connection = None
            self.connect_button.config(state='normal')
            self.disconnect_button.config(state='disabled')
            self.screenshot_button.config(state='disabled')

            if self.screenshot_window:
                self.screenshot_window.destroy()
                self.screenshot_window = None

            self.refresh_server_list()

    def show_screenshot(self):
        if not self.current_connection:
            return

        if self.screenshot_window and self.screenshot_window.winfo_exists():
            self.screenshot_window.lift()
            return

        self.screenshot_window = tk.Toplevel(self.root)
        self.screenshot_window.title(f"Screen View - {self.current_connection}")
        self.screenshot_window.geometry("800x600")
        self.screenshot_window.configure(bg='#000000')

        # Screenshot display
        screenshot_frame = tk.Frame(self.screenshot_window, bg='#000000')
        screenshot_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.screenshot_label = tk.Label(
            screenshot_frame,
            text="Waiting for screen data...",
            font=('Segoe UI', 12),
            bg='#000000',
            fg='#ffffff'
        )
        self.screenshot_label.pack(expand=True)

        self.start_screenshot_updates()

    def start_screenshot_updates(self):
        def update_screenshot():
            while (self.screenshot_window and
                   self.screenshot_window.winfo_exists() and
                   self.current_connection):

                result = self.api_request(f'/api/servers/{self.current_connection}/screenshot')

                if 'data' in result:
                    try:
                        image_data = base64.b64decode(result['data'])
                        image = Image.open(io.BytesIO(image_data))

                        image.thumbnail((780, 580), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(image)

                        self.screenshot_label.configure(image=photo, text="")
                        self.screenshot_label.image = photo
                    except Exception as e:
                        self.screenshot_label.configure(
                            text=f"Error displaying image: {e}",
                            image=""
                        )
                else:
                    self.screenshot_label.configure(
                        text="No screen data available",
                        image=""
                    )

                time.sleep(self.screenshot_interval / 1000)

        screenshot_thread = threading.Thread(target=update_screenshot, daemon=True)
        screenshot_thread.start()

    def on_double_click(self, event):
        self.connect_to_server()

    def ask_for_pin(self):
        import tkinter.simpledialog as simpledialog
        pin = simpledialog.askstring("PIN Required", "Enter PIN code:", show='*')
        return pin if pin else ""


def main():
    root = tk.Tk()
    app = ConnectionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()