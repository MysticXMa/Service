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

SIGNALING_SERVER = "https://remote-desktop-server-u2np.onrender.com"


class DiscoveryServer:
    @staticmethod
    def register_host(session_code, host_ip, port):
        try:
            data = {
                'action': 'register',
                'session_code': session_code,
                'host_ip': host_ip,
                'port': port,
                'timestamp': datetime.now().isoformat()
            }
            response = requests.post(f"{SIGNALING_SERVER}/session", json=data, timeout=10)
            return response.status_code == 200
        except:
            return False

    @staticmethod
    def get_host_info(session_code):
        try:
            response = requests.get(f"{SIGNALING_SERVER}/session/{session_code}", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {'success': False, 'error': 'Session not found'}
        except:
            return {'success': False, 'error': 'Server offline'}

    @staticmethod
    def get_active_hosts():
        try:
            response = requests.get(f"{SIGNALING_SERVER}/sessions", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {'success': False, 'error': 'Could not fetch hosts'}
        except:
            return {'success': False, 'error': 'Server offline'}

    @staticmethod
    def unregister_host(session_code):
        try:
            response = requests.delete(f"{SIGNALING_SERVER}/session/{session_code}", timeout=10)
            return response.status_code == 200
        except:
            return False


class RemoteDesktopApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Global Remote Desktop")
        self.root.geometry("700x600")
        self.socket = None
        self.client_socket = None
        self.running = False
        self.quality = 50
        self.session_code = None
        self.is_host = False
        self.active_hosts = []
        self.create_gui()
        self.refresh_hosts_list()

    def create_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        title_label = ttk.Label(main_frame, text="Global Remote Desktop", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)

        session_frame = ttk.LabelFrame(main_frame, text="Session Connection", padding="10")
        session_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(session_frame, text="Session Code:").grid(row=0, column=0, padx=5)
        self.session_entry = ttk.Entry(session_frame, width=15, font=("Arial", 12))
        self.session_entry.grid(row=0, column=1, padx=5)
        ttk.Button(session_frame, text="Generate Code", command=self.generate_session_code).grid(row=0, column=2,
                                                                                                 padx=10)

        hosts_frame = ttk.LabelFrame(main_frame, text="Active Hosts", padding="10")
        hosts_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        columns = ('session_code', 'ip', 'port', 'created')
        self.hosts_tree = ttk.Treeview(hosts_frame, columns=columns, show='headings', height=6)
        self.hosts_tree.heading('session_code', text='Session Code')
        self.hosts_tree.heading('ip', text='IP Address')
        self.hosts_tree.heading('port', text='Port')
        self.hosts_tree.heading('created', text='Created')
        self.hosts_tree.column('session_code', width=120)
        self.hosts_tree.column('ip', width=150)
        self.hosts_tree.column('port', width=80)
        self.hosts_tree.column('created', width=150)
        self.hosts_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar = ttk.Scrollbar(hosts_frame, orient=tk.VERTICAL, command=self.hosts_tree.yview)
        self.hosts_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        ttk.Button(hosts_frame, text="Refresh List", command=self.refresh_hosts_list).grid(row=1, column=0, pady=5)
        self.hosts_tree.bind('<Double-1>', self.on_host_select)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)
        self.host_btn = ttk.Button(button_frame, text="Start Hosting", command=self.start_hosting, width=20)
        self.host_btn.grid(row=0, column=0, padx=10)
        self.connect_btn = ttk.Button(button_frame, text="Connect", command=self.connect_to_host, width=20)
        self.connect_btn.grid(row=0, column=1, padx=10)
        self.stop_btn = ttk.Button(button_frame, text="Stop", command=self.stop_connection, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=2, padx=10)

        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.status_label = ttk.Label(status_frame, text="Ready to connect", foreground="blue")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        self.info_label = ttk.Label(status_frame, text="", foreground="green")
        self.info_label.grid(row=1, column=0, sticky=tk.W)

        network_frame = ttk.LabelFrame(main_frame, text="Network Info", padding="10")
        network_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.network_label = ttk.Label(network_frame, text=self.get_network_info())
        self.network_label.grid(row=0, column=0, sticky=tk.W)

        self.root.columnconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        hosts_frame.columnconfigure(0, weight=1)
        hosts_frame.rowconfigure(0, weight=1)

    def generate_session_code(self):
        session_code = ''.join(random.choices(string.ascii_uppercase, k=3)) + ''.join(
            random.choices(string.digits, k=3))
        self.session_entry.delete(0, tk.END)
        self.session_entry.insert(0, session_code)
        self.info_label.config(text=f"Session code: {session_code}")
        return session_code

    def refresh_hosts_list(self):
        try:
            result = DiscoveryServer.get_active_hosts()
            if result.get('success'):
                self.active_hosts = result.get('hosts', [])
                for item in self.hosts_tree.get_children():
                    self.hosts_tree.delete(item)
                for host in self.active_hosts:
                    self.hosts_tree.insert('', tk.END, values=(
                        host.get('session_code', ''),
                        host.get('ip', ''),
                        host.get('port', ''),
                        host.get('created', '')
                    ))
                self.info_label.config(text=f"Active hosts: {len(self.active_hosts)}")
            else:
                self.add_demo_hosts()
        except:
            self.add_demo_hosts()

    def add_demo_hosts(self):
        demo_hosts = [
            {'session_code': 'ABC123', 'ip': '192.168.1.100', 'port': '5000', 'created': 'Online'},
            {'session_code': 'XYZ789', 'ip': '192.168.1.101', 'port': '5001', 'created': 'Online'},
        ]
        for host in demo_hosts:
            self.hosts_tree.insert('', tk.END, values=(
                host['session_code'],
                host['ip'],
                host['port'],
                host['created']
            ))

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

            public_ip = self.get_public_ip()
            local_ip = self.get_local_ip()

            if DiscoveryServer.register_host(session_code, public_ip or local_ip, port):
                self.info_label.config(text=f"Hosting: {session_code}")
            else:
                self.info_label.config(text=f"Local hosting: {session_code}")

            self.session_code = session_code
            self.is_host = True
            self.running = True
            threading.Thread(target=self.start_server, args=(port,), daemon=True).start()
            self.status_label.config(text="Waiting for connections...")
            self.host_btn.config(state=tk.DISABLED)
            self.connect_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Hosting failed: {e}")

    def connect_to_host(self):
        try:
            session_code = self.session_entry.get().strip().upper()
            if not session_code:
                messagebox.showerror("Error", "Enter session code")
                return

            result = DiscoveryServer.get_host_info(session_code)
            if result.get('success'):
                host = result['host_ip']
                port = result['port']
                self.info_label.config(text=f"Connecting to {host}:{port}")
            else:
                messagebox.showinfo("Info", "Using demo mode - deploy server for global use")
                host = "192.168.1.100"
                port = 5000

            self.is_host = False
            self.running = True
            threading.Thread(target=self.start_client, args=(host, port), daemon=True).start()
            self.status_label.config(text="Connecting...")
            self.host_btn.config(state=tk.DISABLED)
            self.connect_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {e}")

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
            return f"Local: {local_ip} | No public IP detected"

    def start_server(self, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', port))
            self.socket.listen(1)
            self.update_status(f"Server on port {port}")
            self.client_socket, addr = self.socket.accept()
            self.update_status(f"Connected: {addr}")
            self.send_screen_data()
        except Exception as e:
            self.update_status(f"Server error: {e}")
            self.cleanup()

    def start_client(self, host, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((host, port))
            self.socket.settimeout(None)
            self.update_status("Connected - starting remote view")
            self.receive_screen_data()
        except socket.timeout:
            self.update_status("Timeout - host offline")
            self.cleanup()
        except Exception as e:
            self.update_status(f"Connection error: {e}")
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
                    self.client_socket.sendall(struct.pack(">L", data_size))
                    self.client_socket.sendall(compressed_data)
                time.sleep(0.05)
        except Exception as e:
            self.update_status(f"Send error: {e}")
            self.cleanup()

    def receive_screen_data(self):
        try:
            data = b""
            payload_size = struct.calcsize(">L")
            while self.running and self.socket:
                while len(data) < payload_size:
                    data += self.socket.recv(4096)
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack(">L", packed_msg_size)[0]
                while len(data) < msg_size:
                    data += self.socket.recv(4096)
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
            self.update_status(f"Receive error: {e}")
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
        self.status_label.config(text="Stopped")
        self.info_label.config(text="")
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
        print(f"Missing: {e}")
        print("Install: pip install opencv-python pyautogui pillow numpy requests")
        exit(1)
    app = RemoteDesktopApp()
    app.run()