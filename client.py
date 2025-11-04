import tkinter as tk
from tkinter import ttk, messagebox
import requests
import time
import base64
import io
from PIL import Image, ImageTk
import threading

SERVER_URL = "https://service-zopk.onrender.com"


class ScreenShareApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Screen Share Pro")
        self.root.geometry("900x700")
        self.root.configure(bg='#2c3e50')

        self.name = ""
        self.password = ""
        self.code = ""
        self.connected = False
        self.mode = "menu"
        self.server_list = []
        self.last_update = 0
        self.current_image = None

        self.setup_styles()
        self.show_menu()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#2c3e50')
        self.style.configure('TLabel', background='#2c3e50', foreground='white', font=('Arial', 11))
        self.style.configure('Title.TLabel', font=('Arial', 24, 'bold'), foreground='#3498db')
        self.style.configure('TButton', font=('Arial', 10), padding=10)
        self.style.configure('Primary.TButton', background='#3498db', foreground='white')
        self.style.configure('Success.TButton', background='#2ecc71', foreground='white')
        self.style.configure('Danger.TButton', background='#e74c3c', foreground='white')
        self.style.configure('TEntry', padding=8)

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_menu(self):
        self.clear_window()
        self.mode = "menu"

        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill='both', padx=50, pady=50)

        title = ttk.Label(main_frame, text="Screen Share Pro", style='Title.TLabel')
        title.pack(pady=(0, 40))

        input_frame = ttk.Frame(main_frame)
        input_frame.pack(pady=20, fill='x')

        ttk.Label(input_frame, text="Your Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.name_entry = ttk.Entry(input_frame, width=30, font=('Arial', 11))
        self.name_entry.grid(row=0, column=1, padx=10, pady=5, sticky='ew')
        self.name_entry.insert(0, self.name)

        ttk.Label(input_frame, text="Password:").grid(row=1, column=0, sticky='w', pady=5)
        self.password_entry = ttk.Entry(input_frame, width=30, show="*", font=('Arial', 11))
        self.password_entry.grid(row=1, column=1, padx=10, pady=5, sticky='ew')
        self.password_entry.insert(0, self.password)

        input_frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=30, fill='x')

        ttk.Button(button_frame, text="Start Sharing",
                   command=self.start_sharing, style='Success.TButton').pack(fill='x', pady=10)

        ttk.Button(button_frame, text="View Available Servers",
                   command=self.show_servers, style='Primary.TButton').pack(fill='x', pady=10)

        if self.code:
            code_frame = ttk.Frame(main_frame)
            code_frame.pack(pady=20)

            ttk.Label(code_frame, text=f"Your Share Code: {self.code}",
                      font=('Arial', 12, 'bold'), foreground='#2ecc71').pack()

    def start_sharing(self):
        self.name = self.name_entry.get()
        self.password = self.password_entry.get()

        if not self.name:
            messagebox.showerror("Error", "Please enter your name")
            return

        if self.generate_code():
            self.show_host_screen()

    def generate_code(self):
        try:
            response = requests.post(f"{SERVER_URL}/generate_code",
                                     json={"name": self.name, "password": self.password})
            if response.status_code == 200:
                self.code = response.json()["code"]
                return True
            else:
                messagebox.showerror("Error", "Failed to generate code")
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {str(e)}")
        return False

    def show_host_screen(self):
        self.clear_window()
        self.mode = "host"

        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill='both', padx=30, pady=30)

        title = ttk.Label(main_frame, text="Sharing Your Screen", style='Title.TLabel')
        title.pack(pady=(0, 20))

        code_frame = ttk.Frame(main_frame)
        code_frame.pack(pady=20)

        ttk.Label(code_frame, text="Share this code with others:",
                  font=('Arial', 14)).pack()

        ttk.Label(code_frame, text=self.code,
                  font=('Arial', 28, 'bold'), foreground='#2ecc71').pack(pady=10)

        ttk.Button(main_frame, text="Stop Sharing",
                   command=self.stop_sharing, style='Danger.TButton').pack(pady=20)

        self.status_label = ttk.Label(main_frame, text="Status: Sharing...",
                                      foreground='#2ecc71', font=('Arial', 12))
        self.status_label.pack()

        self.start_screen_update()

    def start_screen_update(self):
        def update_loop():
            while self.mode == "host" and self.connected:
                self.update_screen()
                time.sleep(0.5)

        self.connected = True
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()

    def update_screen(self):
        if self.code and time.time() - self.last_update > 0.5:
            try:
                import pyautogui
                screenshot = pyautogui.screenshot()
                img_bytes = io.BytesIO()
                screenshot.save(img_bytes, format='JPEG')
                img_b64 = base64.b64encode(img_bytes.getvalue()).decode()

                requests.post(f"{SERVER_URL}/update_screen",
                              json={"code": self.code, "password": self.password, "screen": img_b64})
                self.last_update = time.time()

                self.root.after(0, lambda: self.status_label.config(
                    text=f"Status: Sharing... Last update: {time.strftime('%H:%M:%S')}"))
            except Exception as e:
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Status: Error - {str(e)}"))

    def stop_sharing(self):
        self.connected = False
        self.code = ""
        self.show_menu()

    def show_servers(self):
        self.clear_window()
        self.mode = "server_list"

        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill='both', padx=30, pady=30)

        title = ttk.Label(main_frame, text="Available Servers", style='Title.TLabel')
        title.pack(pady=(0, 20))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=10)

        ttk.Button(button_frame, text="Refresh",
                   command=self.refresh_servers, style='Primary.TButton').pack(side='left')

        ttk.Button(button_frame, text="Back",
                   command=self.show_menu, style='Danger.TButton').pack(side='right')

        self.server_tree = ttk.Treeview(main_frame, columns=('name', 'code'), show='headings', height=15)
        self.server_tree.heading('name', text='Server Name')
        self.server_tree.heading('code', text='Share Code')
        self.server_tree.column('name', width=400)
        self.server_tree.column('code', width=200)
        self.server_tree.pack(fill='both', expand=True, pady=10)

        self.server_tree.bind('<Double-1>', self.connect_to_selected_server)

        self.refresh_servers()

    def refresh_servers(self):
        try:
            response = requests.get(f"{SERVER_URL}/servers")
            if response.status_code == 200:
                self.server_list = response.json()["servers"]
                self.update_server_list()
            else:
                messagebox.showerror("Error", "Failed to fetch servers")
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {str(e)}")

    def update_server_list(self):
        for item in self.server_tree.get_children():
            self.server_tree.delete(item)

        for server in self.server_list:
            self.server_tree.insert('', 'end', values=(server['name'], server['code']))

    def connect_to_selected_server(self, event):
        selection = self.server_tree.selection()
        if selection:
            item = self.server_tree.item(selection[0])
            self.code = item['values'][1]
            self.show_client_screen()

    def show_client_screen(self):
        self.clear_window()
        self.mode = "client"

        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill='both', padx=30, pady=30)

        title = ttk.Label(main_frame, text="Viewing Remote Screen", style='Title.TLabel')
        title.pack(pady=(0, 20))

        ttk.Button(main_frame, text="Disconnect",
                   command=self.disconnect_client, style='Danger.TButton').pack(pady=10)

        self.screen_label = ttk.Label(main_frame, text="Loading...", background='black')
        self.screen_label.pack(fill='both', expand=True, pady=10)

        self.status_label_client = ttk.Label(main_frame, text="Status: Connecting...")
        self.status_label_client.pack()

        self.start_screen_viewing()

    def start_screen_viewing(self):
        def view_loop():
            while self.mode == "client":
                self.view_screen()
                time.sleep(1)

        view_thread = threading.Thread(target=view_loop, daemon=True)
        view_thread.start()

    def view_screen(self):
        try:
            response = requests.get(f"{SERVER_URL}/screen/{self.code}")
            if response.status_code == 200:
                data = response.json()
                img_data = base64.b64decode(data["screen"])
                image = Image.open(io.BytesIO(img_data))

                max_width = 800
                max_height = 500
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

                photo = ImageTk.PhotoImage(image)

                self.root.after(0, lambda: self.update_display(photo, "Status: Connected"))
            else:
                self.root.after(0, lambda: self.status_label_client.config(
                    text="Status: Failed to load screen"))
        except Exception as e:
            self.root.after(0, lambda: self.status_label_client.config(
                text=f"Status: Error - {str(e)}"))

    def update_display(self, photo, status):
        self.current_image = photo
        self.screen_label.configure(image=photo, text="")
        self.status_label_client.configure(text=status)

    def disconnect_client(self):
        self.mode = "menu"
        self.code = ""
        self.show_menu()


if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenShareApp(root)
    root.mainloop()