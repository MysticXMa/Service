import socket
import threading
import pyautogui
import cv2
import numpy as np
import zlib
import struct
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import random
import string
import time
from datetime import datetime
import hashlib

SIGNALING_SERVER = "https://remote-desktop-server-u2np.onrender.com"


class DiscoveryServer:
    @staticmethod
    def register_host(session_code, host_ip, port, password=""):
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
            data = {
                'session_code': session_code,
                'host_ip': host_ip,
                'port': port,
                'password_hash': password_hash
            }
            response = requests.post(f"{SIGNALING_SERVER}/session", json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Registration error: {e}")
            return False

    @staticmethod
    def get_host_info(session_code):
        try:
            response = requests.get(f"{SIGNALING_SERVER}/session/{session_code}", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {'success': False, 'error': 'Session not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_active_hosts():
        try:
            response = requests.get(f"{SIGNALING_SERVER}/sessions", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {'success': False, 'error': 'Could not fetch hosts'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def unregister_host(session_code):
        try:
            response = requests.delete(f"{SIGNALING_SERVER}/session/{session_code}", timeout=10)
            return response.status_code == 200
        except:
            return False

    @staticmethod
    def ping_session(session_code):
        try:
            response = requests.post(f"{SIGNALING_SERVER}/session/{session_code}/ping", timeout=5)
            return response.status_code == 200
        except:
            return False

    @staticmethod
    def verify_password(session_code, password):
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            data = {
                'session_code': session_code,
                'password_hash': password_hash
            }
            response = requests.post(f"{SIGNALING_SERVER}/verify_password", json=data, timeout=10)
            return response.json().get('success', False)
        except:
            return False


class ModernRemoteDesktopApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Remote Desktop Pro")
        self.root.geometry("900x750")
        self.root.configure(bg='#f8f9fa')

        # Modern color scheme
        self.colors = {
            'primary': '#2c3e50',
            'secondary': '#34495e',
            'accent': '#3498db',
            'success': '#27ae60',
            'warning': '#f39c12',
            'error': '#e74c3c',
            'background': '#f8f9fa',
            'surface': '#ffffff',
            'text_primary': '#2c3e50',
            'text_secondary': '#7f8c8d',
            'border': '#bdc3c7'
        }

        self.socket = None
        self.client_socket = None
        self.running = False
        self.quality = 70
        self.session_code = None
        self.is_host = False
        self.active_hosts = []
        self.password = ""

        self.setup_styles()
        self.create_gui()
        self.start_periodic_updates()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Configure styles
        self.style.configure('Main.TFrame', background=self.colors['background'])

        self.style.configure('Title.TLabel',
                             background=self.colors['background'],
                             foreground=self.colors['primary'],
                             font=('Segoe UI', 20, 'bold'))

        self.style.configure('Card.TLabelframe',
                             background=self.colors['surface'],
                             foreground=self.colors['primary'],
                             bordercolor=self.colors['border'],
                             relief='solid',
                             borderwidth=1)

        self.style.configure('Card.TLabelframe.Label',
                             background=self.colors['surface'],
                             foreground=self.colors['primary'],
                             font=('Segoe UI', 10, 'bold'))

        self.style.configure('Primary.TButton',
                             background=self.colors['accent'],
                             foreground='white',
                             borderwidth=0,
                             focuscolor='none')

        self.style.configure('Secondary.TButton',
                             background=self.colors['surface'],
                             foreground=self.colors['primary'],
                             borderwidth=1,
                             bordercolor=self.colors['border'])

        self.style.configure('Success.TLabel',
                             background=self.colors['surface'],
                             foreground=self.colors['success'])

        self.style.configure('Warning.TLabel',
                             background=self.colors['surface'],
                             foreground=self.colors['warning'])

        self.style.configure('Error.TLabel',
                             background=self.colors['surface'],
                             foreground=self.colors['error'])

        self.style.configure('Info.TLabel',
                             background=self.colors['surface'],
                             foreground=self.colors['text_secondary'])

        # Treeview style
        self.style.configure('Treeview',
                             background=self.colors['surface'],
                             foreground=self.colors['text_primary'],
                             fieldbackground=self.colors['surface'],
                             borderwidth=0)

        self.style.configure('Treeview.Heading',
                             background=self.colors['secondary'],
                             foreground='white',
                             borderwidth=0,
                             font=('Segoe UI', 9, 'bold'))

    def create_gui(self):
        # Main container
        main_container = ttk.Frame(self.root, style='Main.TFrame', padding="0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header
        header_frame = ttk.Frame(main_container, style='Main.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = ttk.Label(header_frame,
                                text="🖥️ Remote Desktop Pro",
                                style='Title.TLabel')
        title_label.pack(side=tk.LEFT)

        # Main content area
        content_frame = ttk.Frame(main_container, style='Main.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel - Session Management
        left_panel = ttk.Frame(content_frame, style='Main.TFrame')
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Right panel - Active Hosts
        right_panel = ttk.Frame(content_frame, style='Main.TFrame')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        self.create_session_panel(left_panel)
        self.create_hosts_panel(right_panel)
        self.create_control_panel(main_container)

    def create_session_panel(self, parent):
        session_frame = ttk.LabelFrame(parent, text="Session Management", padding="20", style='Card.TLabelframe')
        session_frame.pack(fill=tk.BOTH, expand=True)

        # Session code section
        code_frame = ttk.Frame(session_frame, style='Main.TFrame')
        code_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(code_frame, text="Session Code", style='Info.TLabel').pack(anchor=tk.W)

        code_input_frame = ttk.Frame(code_frame, style='Main.TFrame')
        code_input_frame.pack(fill=tk.X, pady=(5, 0))

        self.session_entry = ttk.Entry(code_input_frame, font=('Segoe UI', 12), width=20)
        self.session_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        ttk.Button(code_input_frame, text="Generate",
                   command=self.generate_session_code,
                   style='Secondary.TButton').pack(side=tk.RIGHT)

        # Password section
        password_frame = ttk.Frame(session_frame, style='Main.TFrame')
        password_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(password_frame, text="Password Protection", style='Info.TLabel').pack(anchor=tk.W)
        self.password_entry = ttk.Entry(password_frame, font=('Segoe UI', 12), show="•")
        self.password_entry.pack(fill=tk.X, pady=(5, 0))

        # Quality section
        quality_frame = ttk.Frame(session_frame, style='Main.TFrame')
        quality_frame.pack(fill=tk.X)

        ttk.Label(quality_frame, text="Stream Quality", style='Info.TLabel').pack(anchor=tk.W)

        quality_control_frame = ttk.Frame(quality_frame, style='Main.TFrame')
        quality_control_frame.pack(fill=tk.X, pady=(5, 0))

        self.quality_scale = ttk.Scale(quality_control_frame, from_=30, to=90, orient=tk.HORIZONTAL)
        self.quality_scale.set(70)
        self.quality_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.quality_label = ttk.Label(quality_control_frame, text="70%", style='Info.TLabel', width=5)
        self.quality_label.pack(side=tk.RIGHT)

    def create_hosts_panel(self, parent):
        hosts_frame = ttk.LabelFrame(parent, text="Active Sessions", padding="20", style='Card.TLabelframe')
        hosts_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview with scrollbar
        tree_frame = ttk.Frame(hosts_frame, style='Main.TFrame')
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('session_code', 'status', 'ip', 'port', 'password')
        self.hosts_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)

        # Configure columns
        self.hosts_tree.heading('session_code', text='SESSION CODE')
        self.hosts_tree.heading('status', text='STATUS')
        self.hosts_tree.heading('ip', text='IP ADDRESS')
        self.hosts_tree.heading('port', text='PORT')
        self.hosts_tree.heading('password', text='SECURITY')

        self.hosts_tree.column('session_code', width=120, anchor=tk.CENTER)
        self.hosts_tree.column('status', width=100, anchor=tk.CENTER)
        self.hosts_tree.column('ip', width=140, anchor=tk.CENTER)
        self.hosts_tree.column('port', width=80, anchor=tk.CENTER)
        self.hosts_tree.column('password', width=100, anchor=tk.CENTER)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.hosts_tree.yview)
        self.hosts_tree.configure(yscroll=scrollbar.set)

        self.hosts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Refresh button
        refresh_frame = ttk.Frame(hosts_frame, style='Main.TFrame')
        refresh_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(refresh_frame, text="🔄 Refresh List",
                   command=self.refresh_hosts_list,
                   style='Secondary.TButton').pack()

        self.hosts_tree.bind('<Double-1>', self.on_host_select)

    def create_control_panel(self, parent):
        control_frame = ttk.Frame(parent, style='Main.TFrame')
        control_frame.pack(fill=tk.X, pady=(20, 0))

        # Action buttons
        button_frame = ttk.Frame(control_frame, style='Main.TFrame')
        button_frame.pack(fill=tk.X, pady=(0, 20))

        self.host_btn = ttk.Button(button_frame, text="Start Hosting",
                                   command=self.start_hosting,
                                   style='Primary.TButton',
                                   width=15)
        self.host_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.connect_btn = ttk.Button(button_frame, text="Connect to Session",
                                      command=self.connect_to_host,
                                      style='Primary.TButton',
                                      width=15)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = ttk.Button(button_frame, text="Stop",
                                   command=self.stop_connection,
                                   style='Secondary.TButton',
                                   width=10,
                                   state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

        # Status panel
        status_frame = ttk.LabelFrame(control_frame, text="Connection Status", padding="15", style='Card.TLabelframe')
        status_frame.pack(fill=tk.X)

        self.status_label = ttk.Label(status_frame, text="Ready to establish connection", style='Success.TLabel')
        self.status_label.pack(anchor=tk.W)

        self.info_label = ttk.Label(status_frame, text="Generate a session code or connect to an existing session",
                                    style='Info.TLabel')
        self.info_label.pack(anchor=tk.W)

        # Network info
        network_frame = ttk.LabelFrame(control_frame, text="Network Information", padding="15",
                                       style='Card.TLabelframe')
        network_frame.pack(fill=tk.X, pady=(10, 0))

        self.network_label = ttk.Label(network_frame, text=self.get_network_info(), style='Info.TLabel')
        self.network_label.pack(anchor=tk.W)

    def generate_session_code(self):
        session_code = ''.join(random.choices(string.ascii_uppercase, k=3)) + ''.join(
            random.choices(string.digits, k=3))
        self.session_entry.delete(0, tk.END)
        self.session_entry.insert(0, session_code)
        self.info_label.config(text=f"Session code generated: {session_code}")
        return session_code

    def refresh_hosts_list(self):
        try:
            result = DiscoveryServer.get_active_hosts()
            if result.get('success'):
                self.active_hosts = result.get('hosts', [])
                for item in self.hosts_tree.get_children():
                    self.hosts_tree.delete(item)

                for host in self.active_hosts:
                    status = host.get('status', 'Unknown')
                    status_icon = self.get_status_icon(status)
                    password_icon = "🔒 Protected" if host.get('has_password') else "🔓 Open"

                    self.hosts_tree.insert('', tk.END, values=(
                        host.get('session_code', ''),
                        f"{status_icon} {status}",
                        host.get('ip', ''),
                        host.get('port', ''),
                        password_icon
                    ))

                online_count = sum(1 for host in self.active_hosts if host.get('status') == 'Online')
                self.info_label.config(text=f"{online_count} online sessions available")
            else:
                self.info_label.config(text="Unable to fetch sessions list", style='Error.TLabel')
        except Exception as e:
            self.info_label.config(text=f"Connection error: {str(e)}", style='Error.TLabel')

    def get_status_icon(self, status):
        icons = {
            'Online': '●',
            'Away': '○',
            'Offline': '○',
            'Error': '⚠'
        }
        return icons.get(status, '?')

    def on_host_select(self, event):
        selection = self.hosts_tree.selection()
        if selection:
            item = self.hosts_tree.item(selection[0])
            session_code = item['values'][0]
            self.session_entry.delete(0, tk.END)
            self.session_entry.insert(0, session_code)

    def start_hosting(self):
        try:
            port = 5000
            session_code = self.session_entry.get().strip().upper()
            if not session_code:
                session_code = self.generate_session_code()

            self.password = self.password_entry.get()

            public_ip = self.get_public_ip()
            local_ip = self.get_local_ip()

            if DiscoveryServer.register_host(session_code, public_ip or local_ip, port, self.password):
                status_text = f"Hosting session: {session_code}"
                if self.password:
                    status_text += " (Password Protected)"
                self.info_label.config(text=status_text, style='Success.TLabel')
            else:
                self.info_label.config(text=f"Local session: {session_code}", style='Warning.TLabel')

            self.session_code = session_code
            self.is_host = True
            self.running = True

            threading.Thread(target=self.start_server, args=(port,), daemon=True).start()
            threading.Thread(target=self.keep_alive_ping, daemon=True).start()

            self.status_label.config(text="Waiting for incoming connections...", style='Success.TLabel')
            self.host_btn.config(state=tk.DISABLED)
            self.connect_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start hosting: {e}")

    def connect_to_host(self):
        try:
            session_code = self.session_entry.get().strip().upper()
            if not session_code:
                messagebox.showerror("Error", "Please enter a session code")
                return

            result = DiscoveryServer.get_host_info(session_code)
            if result.get('success'):
                host_info = result

                if host_info.get('password_hash'):
                    password = self.ask_for_password()
                    if password is None:
                        return

                    if not DiscoveryServer.verify_password(session_code, password):
                        messagebox.showerror("Error", "Invalid password")
                        return

                host = host_info['host_ip']
                port = host_info['port']
                self.info_label.config(text=f"Connecting to {host}:{port}", style='Success.TLabel')

                self.is_host = False
                self.running = True
                threading.Thread(target=self.start_client, args=(host, port), daemon=True).start()

                self.status_label.config(text="Establishing connection...", style='Warning.TLabel')
                self.host_btn.config(state=tk.DISABLED)
                self.connect_btn.config(state=tk.DISABLED)
                self.stop_btn.config(state=tk.NORMAL)

            else:
                messagebox.showerror("Error", f"Session not found: {result.get('error', 'Unknown error')}")

        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {e}")

    def ask_for_password(self):
        password_window = tk.Toplevel(self.root)
        password_window.title("Session Password")
        password_window.geometry("300x150")
        password_window.resizable(False, False)
        password_window.configure(bg=self.colors['background'])

        ttk.Label(password_window, text="This session requires a password", style='Info.TLabel').pack(pady=10)
        ttk.Label(password_window, text="Enter password:", style='Info.TLabel').pack(pady=5)

        password_entry = ttk.Entry(password_window, show="•", width=20, font=('Segoe UI', 11))
        password_entry.pack(pady=5)
        password_entry.focus()

        result = [None]

        def on_ok():
            result[0] = password_entry.get()
            password_window.destroy()

        def on_cancel():
            password_window.destroy()

        button_frame = ttk.Frame(password_window, style='Main.TFrame')
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="OK", command=on_ok, style='Primary.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel, style='Secondary.TButton').pack(side=tk.LEFT, padx=5)

        password_window.transient(self.root)
        password_window.grab_set()
        self.root.wait_window(password_window)

        return result[0]

    def keep_alive_ping(self):
        while self.running and self.is_host and self.session_code:
            try:
                DiscoveryServer.ping_session(self.session_code)
                time.sleep(20)
            except:
                time.sleep(5)

    def get_public_ip(self):
        try:
            response = requests.get('https://api.ipify.org', timeout=5)
            return response.text
        except:
            return None

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"

    def get_network_info(self):
        local_ip = self.get_local_ip()
        public_ip = self.get_public_ip()
        if public_ip:
            return f"Local: {local_ip} | Public: {public_ip}"
        else:
            return f"Local: {local_ip} | Public IP: Not available"

    def start_periodic_updates(self):
        def update_quality_label():
            self.quality = int(self.quality_scale.get())
            self.quality_label.config(text=f"{self.quality}%")
            self.root.after(100, update_quality_label)

        def refresh_hosts_periodically():
            self.refresh_hosts_list()
            self.root.after(10000, refresh_hosts_periodically)

        update_quality_label()
        refresh_hosts_periodically()

    def start_server(self, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', port))
            self.socket.listen(1)
            self.socket.settimeout(2.0)

            self.update_status(f"Server listening on port {port}")

            while self.running:
                try:
                    self.client_socket, addr = self.socket.accept()
                    self.update_status(f"Connected: {addr}")
                    self.send_screen_data()
                    break
                except socket.timeout:
                    continue

        except Exception as e:
            self.update_status(f"Server error: {e}")
        finally:
            self.cleanup()

    def start_client(self, host, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((host, port))
            self.socket.settimeout(None)

            self.update_status("Connected! Starting remote view...")
            self.receive_screen_data()

        except socket.timeout:
            self.update_status("Connection timeout - host unavailable")
            self.cleanup()
        except Exception as e:
            self.update_status(f"Connection failed: {e}")
            self.cleanup()

    def send_screen_data(self):
        try:
            while self.running and self.client_socket:
                screenshot = pyautogui.screenshot()
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
                result, encoded_frame = cv2.imencode('.jpg', frame, encode_param)

                if result:
                    compressed_data = zlib.compress(encoded_frame.tobytes())
                    data_size = len(compressed_data)

                    try:
                        self.client_socket.sendall(struct.pack(">L", data_size))
                        self.client_socket.sendall(compressed_data)
                    except:
                        break

                time.sleep(0.03)

        except Exception as e:
            self.update_status(f"Stream error: {e}")
        finally:
            self.cleanup()

    def receive_screen_data(self):
        try:
            data = b""
            payload_size = struct.calcsize(">L")

            while self.running and self.socket:
                while len(data) < payload_size:
                    packet = self.socket.recv(4096)
                    if not packet:
                        break
                    data += packet

                if len(data) < payload_size:
                    break

                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack(">L", packed_msg_size)[0]

                while len(data) < msg_size:
                    packet = self.socket.recv(4096)
                    if not packet:
                        break
                    data += packet

                if len(data) < msg_size:
                    break

                frame_data = data[:msg_size]
                data = data[msg_size:]

                decompressed_data = zlib.decompress(frame_data)
                frame_array = np.frombuffer(decompressed_data, dtype=np.uint8)
                frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

                if frame is not None:
                    cv2.imshow('Remote Desktop - Press Q to exit', frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except Exception as e:
            self.update_status(f"Stream error: {e}")
        finally:
            self.cleanup()
            cv2.destroyAllWindows()

    def update_status(self, message):
        def update():
            self.status_label.config(text=message)

        self.root.after(0, update)

    def stop_connection(self):
        if self.session_code and self.is_host:
            DiscoveryServer.unregister_host(self.session_code)

        self.running = False
        self.cleanup()

        self.status_label.config(text="Connection stopped", style='Error.TLabel')
        self.info_label.config(text="Ready for new connection", style='Info.TLabel')
        self.host_btn.config(state=tk.NORMAL)
        self.connect_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        cv2.destroyAllWindows()

    def cleanup(self):
        self.running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    try:
        import pyautogui
        import cv2
        import numpy as np
        import requests
    except ImportError as e:
        print(f"Missing dependencies: {e}")
        print("Please install: pip install opencv-python pyautogui pillow numpy requests")
        exit(1)

    app = ModernRemoteDesktopApp()
    app.run()