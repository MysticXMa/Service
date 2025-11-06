import tkinter as tk
from tkinter import ttk, messagebox
import requests
import base64
import threading
import time
from PIL import Image, ImageTk
import io
import pyautogui


class SimpleConnectionApp:
    def __init__(self, window):
        self.root = window
        self.root.title("PC Connection Hub")
        self.root.geometry("1000x600")
        self.root.configure(bg='white')

        self.backend_url = "https://service-zopk.onrender.com"
        self.servers = []
        self.hosting_server = None
        self.current_connection = None
        self.screenshot_window = None
        self.update_interval = 3000
        self.screenshot_interval = 2000

        self.name_entry = None
        self.pin_entry = None
        self.users_var = None
        self.host_button = None
        self.stop_button = None
        self.status_label = None
        self.search_entry = None
        self.connect_button = None
        self.disconnect_button = None
        self.screenshot_button = None
        self.auto_screenshot_var = None
        self.server_tree = None
        self.screenshot_thread = None
        self.screenshot_label = None

        self.setup_ui()
        self.start_server_updates()

    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg='white', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)

        title_label = tk.Label(
            main_frame,
            text="PC Connection Hub",
            font=('Arial', 24, 'bold'),
            bg='white',
            fg='black'
        )
        title_label.pack(pady=(0, 20))

        host_frame = tk.LabelFrame(
            main_frame,
            text=" Host Your Server ",
            font=('Arial', 12, 'bold'),
            bg='white',
            fg='black',
            bd=2,
            relief='solid'
        )
        host_frame.pack(fill='x', pady=(0, 20))

        form_frame = tk.Frame(host_frame, bg='white', padx=10, pady=10)
        form_frame.pack(fill='x')

        tk.Label(form_frame, text="Server Name:", bg='white', fg='black', font=('Arial', 10)).grid(row=0, column=0,
                                                                                                   sticky='w', pady=5)
        self.name_entry = tk.Entry(form_frame, font=('Arial', 10), width=20, bd=1, relief='solid')
        self.name_entry.grid(row=0, column=1, sticky='w', padx=5, pady=5)

        tk.Label(form_frame, text="PIN (optional):", bg='white', fg='black', font=('Arial', 10)).grid(row=1, column=0,
                                                                                                      sticky='w',
                                                                                                      pady=5)
        self.pin_entry = tk.Entry(form_frame, font=('Arial', 10), show="*", width=20, bd=1, relief='solid')
        self.pin_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)

        tk.Label(form_frame, text="Max Users:", bg='white', fg='black', font=('Arial', 10)).grid(row=2, column=0,
                                                                                                 sticky='w', pady=5)
        self.users_var = tk.StringVar(value="5")
        users_spinbox = tk.Spinbox(
            form_frame,
            from_=1,
            to=50,
            textvariable=self.users_var,
            font=('Arial', 10),
            width=18,
            bd=1,
            relief='solid'
        )
        users_spinbox.grid(row=2, column=1, sticky='w', padx=5, pady=5)

        button_frame = tk.Frame(form_frame, bg='white')
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        self.host_button = tk.Button(
            button_frame,
            text="Start Hosting",
            font=('Arial', 10, 'bold'),
            bg='#4CAF50',
            fg='white',
            relief='solid',
            bd=1,
            padx=20,
            pady=5,
            command=self.start_hosting
        )
        self.host_button.pack(side='left', padx=5)

        self.stop_button = tk.Button(
            button_frame,
            text="Stop Hosting",
            font=('Arial', 10, 'bold'),
            bg='#f44336',
            fg='white',
            relief='solid',
            bd=1,
            padx=20,
            pady=5,
            command=self.stop_hosting,
            state='disabled'
        )
        self.stop_button.pack(side='left', padx=5)

        self.status_label = tk.Label(
            form_frame,
            text="Status: Not hosting",
            font=('Arial', 9),
            bg='white',
            fg='black'
        )
        self.status_label.grid(row=4, column=0, columnspan=2, sticky='w', pady=5)

        servers_frame = tk.LabelFrame(
            main_frame,
            text=" Available Servers ",
            font=('Arial', 12, 'bold'),
            bg='white',
            fg='black',
            bd=2,
            relief='solid'
        )
        servers_frame.pack(fill='both', expand=True)

        search_frame = tk.Frame(servers_frame, bg='white', padx=10, pady=10)
        search_frame.pack(fill='x')

        tk.Label(search_frame, text="Search:", bg='white', fg='black', font=('Arial', 10)).pack(side='left')
        self.search_entry = tk.Entry(
            search_frame,
            font=('Arial', 10),
            width=30,
            bd=1,
            relief='solid'
        )
        self.search_entry.pack(side='left', padx=5)
        self.search_entry.bind('<KeyRelease>', self.filter_servers)

        self.setup_server_table(servers_frame)

        control_frame = tk.Frame(servers_frame, bg='white', padx=10, pady=10)
        control_frame.pack(fill='x')

        self.connect_button = tk.Button(
            control_frame,
            text="Connect to Server",
            font=('Arial', 10, 'bold'),
            bg='#2196F3',
            fg='white',
            relief='solid',
            bd=1,
            padx=15,
            pady=5,
            command=self.connect_to_server
        )
        self.connect_button.pack(side='left', padx=5)

        self.disconnect_button = tk.Button(
            control_frame,
            text="Disconnect",
            font=('Arial', 10),
            bg='#ff9800',
            fg='white',
            relief='solid',
            bd=1,
            padx=15,
            pady=5,
            command=self.disconnect_from_server,
            state='disabled'
        )
        self.disconnect_button.pack(side='left', padx=5)

        self.screenshot_button = tk.Button(
            control_frame,
            text="View Screen",
            font=('Arial', 10),
            bg='#9c27b0',
            fg='white',
            relief='solid',
            bd=1,
            padx=15,
            pady=5,
            command=self.show_screenshot,
            state='disabled'
        )
        self.screenshot_button.pack(side='left', padx=5)

        self.auto_screenshot_var = tk.BooleanVar(value=True)
        auto_screenshot_cb = tk.Checkbutton(
            control_frame,
            text="Auto Upload Screenshots",
            variable=self.auto_screenshot_var,
            bg='white',
            fg='black',
            font=('Arial', 9),
            command=self.toggle_screenshot_upload
        )
        auto_screenshot_cb.pack(side='right', padx=5)

    def setup_server_table(self, parent):
        table_frame = tk.Frame(parent, bg='white')
        table_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        style = ttk.Style()
        style.configure("Treeview",
                        background="white",
                        foreground="black",
                        fieldbackground="white",
                        borderwidth=1,
                        relief='solid')
        style.configure("Treeview.Heading",
                        background="white",
                        foreground="black",
                        borderwidth=1,
                        relief='solid')
        style.map('Treeview', background=[('selected', '#e0e0e0')])

        columns = ('ID', 'Name', 'Players', 'Status')
        self.server_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=8,
            style="Treeview"
        )

        self.server_tree.heading('ID', text='Server ID')
        self.server_tree.heading('Name', text='Server Name')
        self.server_tree.heading('Players', text='Players')
        self.server_tree.heading('Status', text='Status')

        self.server_tree.column('ID', width=120)
        self.server_tree.column('Name', width=200)
        self.server_tree.column('Players', width=80)
        self.server_tree.column('Status', width=100)

        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.server_tree.yview)
        self.server_tree.configure(yscrollcommand=scrollbar.set)

        self.server_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self.server_tree.bind('<Double-1>', self.on_double_click)

    def api_request(self, endpoint, method='GET', data=None):
        try:
            url = f"{self.backend_url}{endpoint}"
            headers = {'Content-Type': 'application/json'}
            response = None

            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            if response:
                return response.json() if response.content else {}
            return {}
        except Exception as e:
            print(f"API Error: {e}")
            return {'error': str(e)}

    def capture_and_upload_screenshot(self):
        if self.hosting_server and self.auto_screenshot_var.get():
            try:
                screenshot = pyautogui.screenshot()
                buffered = io.BytesIO()
                screenshot.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                data = {'screenshot': img_str}
                self.api_request(f'/api/servers/{self.hosting_server["id"]}/screenshot', 'POST', data)
            except Exception as e:
                print(f"Screenshot error: {e}")

    def toggle_screenshot_upload(self):
        if self.hosting_server and self.auto_screenshot_var.get():
            self.start_screenshot_upload()

    def start_screenshot_upload(self):
        def upload_loop():
            while (self.hosting_server and
                   self.auto_screenshot_var.get()):
                self.capture_and_upload_screenshot()
                time.sleep(self.screenshot_interval / 1000)

        self.screenshot_thread = threading.Thread(target=upload_loop, daemon=True)
        self.screenshot_thread.start()

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

        if self.auto_screenshot_var.get():
            self.start_screenshot_upload()

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
            self.server_tree.insert(
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

    def filter_servers(self, event=None):
        search_text = self.search_entry.get().lower()

        for item in self.server_tree.get_children():
            self.server_tree.item(item, tags=('visible',))

        if search_text:
            for item in self.server_tree.get_children():
                values = self.server_tree.item(item)['values']
                server_name = values[1].lower() if len(values) > 1 else ""
                server_id = values[0].lower() if len(values) > 0 else ""

                if search_text not in server_name and search_text not in server_id:
                    self.server_tree.item(item, tags=('hidden',))

        self.server_tree.tag_configure('visible', background='white')
        self.server_tree.tag_configure('hidden', background='#f0f0f0')

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

        pin_code = ""
        if server.get('pin'):
            pin_code = self.ask_for_pin()
            if pin_code is None:
                return

        data = {
            'pin': pin_code,
            'user_name': 'User'
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
        self.screenshot_window.configure(bg='white')

        screenshot_frame = tk.Frame(self.screenshot_window, bg='white')
        screenshot_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.screenshot_label = tk.Label(
            screenshot_frame,
            text="Waiting for screen data...",
            font=('Arial', 12),
            bg='white',
            fg='black'
        )
        self.screenshot_label.pack(expand=True)

        self.start_screenshot_viewer()

    def start_screenshot_viewer(self):
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
                        self.screenshot_label.image_ref = photo
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

        viewer_thread = threading.Thread(target=update_screenshot, daemon=True)
        viewer_thread.start()

    def on_double_click(self, event=None):
        self.connect_to_server()

    @staticmethod
    def ask_for_pin():
        import tkinter.simpledialog
        pin = tkinter.simpledialog.askstring("PIN Required", "Enter PIN code:", show='*')
        return pin if pin else ""


if __name__ == "__main__":
    root_window = tk.Tk()
    SimpleConnectionApp(root_window)
    root_window.mainloop()