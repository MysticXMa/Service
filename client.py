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
        self.root.title("🌐 Global Remote Desktop")
        self.root.geometry("800x700")
        self.root.configure(bg='#2c3e50')

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

        self.style.configure('Title.TLabel',
                             background='#2c3e50',
                             foreground='#ecf0f1',
                             font=('Arial', 18, 'bold'))

        self.style.configure('Card.TLabelframe',
                             background='#34495e',
                             foreground='#ecf0f1',
                             bordercolor='#7f8c8d')

        self.style.configure('Card.TLabelframe.Label',
                             background='#34495e',
                             foreground='#ecf0f1',
                             font=('Arial', 10, 'bold'))

        self.style.configure('Success.TLabel',
                             background='#34495e',
                             foreground='#2ecc71')

        self.style.configure('Warning.TLabel',
                             background='#34495e',
                             foreground='#f39c12')

        self.style.configure('Error.TLabel',
                             background='#34495e',
                             foreground='#e74c3c')

    def create_gui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.configure(style='Card.TLabelframe')

        title_label = ttk.Label(main_frame,
                                text="🌐 Global Remote Desktop",
                                style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.create_session_frame(left_frame)
        self.create_hosts_frame(right_frame)
        self.create_control_frame(main_frame)

        self.root.columnconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

    def create_session_frame(self, parent):
        session_frame = ttk.LabelFrame(parent, text="🎯 Session Management", padding="15", style='Card.TLabelframe')
        session_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        ttk.Label(session_frame, text="Session Code:", background='#34495e', foreground='#ecf0f1').grid(row=0, column=0,
                                                                                                        sticky=tk.W,
                                                                                                        pady=5)
        self.session_entry = ttk.Entry(session_frame, width=20, font=('Arial', 12))
        self.session_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Button(session_frame, text="🎲 Generate",
                   command=self.generate_session_code, width=12).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(session_frame, text="Password (Optional):", background='#34495e', foreground='#ecf0f1').grid(row=1,
                                                                                                               column=0,
                                                                                                               sticky=tk.W,
                                                                                                               pady=5)
        self.password_entry = ttk.Entry(session_frame, width=20, font=('Arial', 12), show="•")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(session_frame, text="Quality:", background='#34495e', foreground='#ecf0f1').grid(row=2, column=0,
                                                                                                   sticky=tk.W, pady=5)
        self.quality_scale = ttk.Scale(session_frame, from_=30, to=90, orient=tk.HORIZONTAL, length=200)
        self.quality_scale.set(70)
        self.quality_scale.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W)

        self.quality_label = ttk.Label(session_frame, text="70%", background='#34495e', foreground='#3498db')
        self.quality_label.grid(row=2, column=2, padx=5, pady=5)

        parent.columnconfigure(0, weight=1)
        session_frame.columnconfigure(1, weight=1)

    def create_hosts_frame(self, parent):
        hosts_frame = ttk.LabelFrame(parent, text="🖥️ Active Hosts", padding="15", style='Card.TLabelframe')
        hosts_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        columns = ('session_code', 'status', 'ip', 'port', 'password')
        self.hosts_tree = ttk.Treeview(hosts_frame, columns=columns, show='headings', height=12)

        self.hosts_tree.heading('session_code', text='Session Code')
        self.hosts_tree.heading('status', text='Status')
        self.hosts_tree.heading('ip', text='IP Address')
        self.hosts_tree.heading('port', text='Port')
        self.hosts_tree.heading('password', text='Protected')

        self.hosts_tree.column('session_code', width=120)
        self.hosts_tree.column('status', width=80)
        self.hosts_tree.column('ip', width=120)
        self.hosts_tree.column('port', width=60)
        self.hosts_tree.column('password', width=80)

        self.hosts_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar = ttk.Scrollbar(hosts_frame, orient=tk.VERTICAL, command=self.hosts_tree.yview)
        self.hosts_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        ttk.Button(hosts_frame, text="🔄 Refresh",
                   command=self.refresh_hosts_list).grid(row=1, column=0, pady=10)

        self.hosts_tree.bind('<Double-1>', self.on_host_select)

        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        hosts_frame.columnconfigure(0, weight=1)
        hosts_frame.rowconfigure(0, weight=1)

    def create_control_frame(self, parent):
        control_frame = ttk.Frame(parent, style='Card.TLabelframe')
        control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        self.host_btn = ttk.Button(control_frame, text="🚀 Start Hosting",
                                   command=self.start_hosting, width=20)
        self.host_btn.grid(row=0, column=0, padx=10, pady=10)

        self.connect_btn = ttk.Button(control_frame, text="🔗 Connect",
                                      command=self.connect_to_host, width=20)
        self.connect_btn.grid(row=0, column=1, padx=10, pady=10)

        self.stop_btn = ttk.Button(control_frame, text="🛑 Stop",
                                   command=self.stop_connection, width=20, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=2, padx=10, pady=10)

        status_frame = ttk.LabelFrame(parent, text="📊 Status", padding="10", style='Card.TLabelframe')
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.status_label = ttk.Label(status_frame, text="✅ Ready to connect", style='Success.TLabel')
        self.status_label.grid(row=0, column=0, sticky=tk.W)

        self.info_label = ttk.Label(status_frame, text="Generate a session code to start", style='Warning.TLabel')
        self.info_label.grid(row=1, column=0, sticky=tk.W)

        network_frame = ttk.LabelFrame(parent, text="🌐 Network Information", padding="10", style='Card.TLabelframe')
        network_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.network_label = ttk.Label(network_frame, text=self.get_network_info(), style='Success.TLabel')
        self.network_label.grid(row=0, column=0, sticky=tk.W)

        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
        control_frame.columnconfigure(2, weight=1)

    def generate_session_code(self):
        session_code = ''.join(random.choices(string.ascii_uppercase, k=3)) + ''.join(
            random.choices(string.digits, k=3))
        self.session_entry.delete(0, tk.END)
        self.session_entry.insert(0, session_code)
        self.info_label.config(text=f"🎯 Session code generated: {session_code}")
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
                    password_icon = "🔒" if host.get('has_password') else "🔓"

                    self.hosts_tree.insert('', tk.END, values=(
                        host.get('session_code', ''),
                        f"{status_icon} {status}",
                        host.get('ip', ''),
                        host.get('port', ''),
                        password_icon
                    ))

                online_count = sum(1 for host in self.active_hosts if host.get('status') == 'Online')
                self.info_label.config(text=f"📊 {online_count} online, {len(self.active_hosts)} total hosts")
            else:
                self.info_label.config(text="❌ Could not fetch hosts list", style='Error.TLabel')
        except Exception as e:
            self.info_label.config(text=f"❌ Error: {str(e)}", style='Error.TLabel')

    def get_status_icon(self, status):
        icons = {
            'Online': '🟢',
            'Away': '🟡',
            'Offline': '🔴',
            'Error': '⚫'
        }
        return icons.get(status, '❓')

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
                self.info_label.config(text=f"🚀 Hosting globally: {session_code}", style='Success.TLabel')
                if self.password:
                    self.info_label.config(text=f"🚀 Hosting: {session_code} (Password Protected)",
                                           style='Success.TLabel')
            else:
                self.info_label.config(text=f"⚠️ Hosting locally: {session_code}", style='Warning.TLabel')

            self.session_code = session_code
            self.is_host = True
            self.running = True

            threading.Thread(target=self.start_server, args=(port,), daemon=True).start()
            threading.Thread(target=self.keep_alive_ping, daemon=True).start()

            self.status_label.config(text="🟢 Waiting for connections...", style='Success.TLabel')
            self.host_btn.config(state=tk.DISABLED)
            self.connect_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("Error", f"Hosting failed: {e}")

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
                self.info_label.config(text=f"🔗 Connecting to {host}:{port}", style='Success.TLabel')

                self.is_host = False
                self.running = True
                threading.Thread(target=self.start_client, args=(host, port), daemon=True).start()

                self.status_label.config(text="🟡 Connecting...", style='Warning.TLabel')
                self.host_btn.config(state=tk.DISABLED)
                self.connect_btn.config(state=tk.DISABLED)
                self.stop_btn.config(state=tk.NORMAL)

            else:
                messagebox.showerror("Error", f"Could not find host: {result.get('error', 'Unknown error')}")

        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {e}")

    def ask_for_password(self):
        password_window = tk.Toplevel(self.root)
        password_window.title("Password Required")
        password_window.geometry("300x150")
        password_window.resizable(False, False)

        ttk.Label(password_window, text="This session is password protected").pack(pady=10)
        ttk.Label(password_window, text="Enter password:").pack(pady=5)

        password_entry = ttk.Entry(password_window, show="•", width=20)
        password_entry.pack(pady=5)
        password_entry.focus()

        result = [None]

        def on_ok():
            result[0] = password_entry.get()
            password_window.destroy()

        def on_cancel():
            password_window.destroy()

        button_frame = ttk.Frame(password_window)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)

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
            return f"📍 Local: {local_ip} | 🌐 Public: {public_ip}"
        else:
            return f"📍 Local: {local_ip} | ❌ No public IP detected"

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

            self.update_status(f"🟢 Server listening on port {port}")

            while self.running:
                try:
                    self.client_socket, addr = self.socket.accept()
                    self.update_status(f"✅ Connected by {addr}")
                    self.send_screen_data()
                    break
                except socket.timeout:
                    continue

        except Exception as e:
            self.update_status(f"❌ Server error: {e}")
        finally:
            self.cleanup()

    def start_client(self, host, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((host, port))
            self.socket.settimeout(None)

            self.update_status("✅ Connected! Starting remote view...")
            self.receive_screen_data()

        except socket.timeout:
            self.update_status("❌ Connection timeout - host may be offline")
            self.cleanup()
        except Exception as e:
            self.update_status(f"❌ Connection failed: {e}")
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
            self.update_status(f"❌ Send error: {e}")
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
                    cv2.imshow('Remote Desktop - Press Q to quit', frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except Exception as e:
            self.update_status(f"❌ Receive error: {e}")
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

        self.status_label.config(text="🛑 Connection stopped", style='Error.TLabel')
        self.info_label.config(text="Ready for new connection", style='Warning.TLabel')
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