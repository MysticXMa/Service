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
import socketio
import os

SIGNALING_SERVER = os.environ.get('SIGNALING_SERVER_URL')


class SignalingClient:
    def __init__(self, app_instance):
        self.sio = socketio.Client()
        self.app = app_instance
        self.connected = False
        self.current_session = None
        self.pending_connection_id = None

        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('connection_request', self.on_connection_request)
        self.sio.on('connection_approved', self.on_connection_approved)
        self.sio.on('connection_rejected', self.on_connection_rejected)
        self.sio.on('start_streaming', self.on_start_streaming)
        self.sio.on('stream_data', self.on_stream_data)
        self.sio.on('pending_approval', self.on_pending_approval)
        self.sio.on('session_terminated', self.on_session_terminated)

    def on_connect(self):
        self.connected = True
        self.app.update_status("Connected to signaling server", "success")

    def on_disconnect(self):
        self.connected = False
        self.app.update_status("Disconnected from signaling server", "error")

    def on_connection_request(self, data):
        def show_request_dialog():
            result = self.app.show_connection_request(
                data['client_name'],
                data['session_code'],
                data['connection_id']
            )
            if result is not None:
                self.sio.emit('host_decision', {
                    'connection_id': data['connection_id'],
                    'approved': result
                })

        self.app.root.after(0, show_request_dialog)

    def on_connection_approved(self, data):
        self.pending_connection_id = data.get('connection_id')
        self.app.update_status("Connection approved! Starting session...", "success")
        self.app.start_streaming_to_client()

    def on_connection_rejected(self, data):
        self.app.update_status("Connection was rejected by host", "error")
        self.app.stop_connection()

    def on_start_streaming(self, data):
        self.app.target_client_sid = data['client_sid']
        self.app.update_status(f"Connected to {data['client_name']}", "success")
        self.app.start_receiving_stream()

    def on_stream_data(self, data):
        if hasattr(self.app, 'process_stream_data'):
            self.app.process_stream_data(data['data'])

    def on_pending_approval(self, data):
        self.app.update_status("Waiting for host approval...", "warning")

    def on_session_terminated(self, data):
        self.app.update_status("Session terminated by host", "error")
        self.app.stop_connection()

    def connect(self):
        try:
            self.sio.connect(SIGNALING_SERVER)
            return True
        except Exception as e:
            print(f"Signaling connection failed: {e}")
            return False

    def disconnect(self):
        self.sio.disconnect()

    def register_host(self, session_code, host_name):
        self.current_session = session_code
        self.sio.emit('host_register', {
            'session_code': session_code,
            'host_name': host_name
        })

    def request_connection(self, session_code, client_name):
        self.current_session = session_code
        self.sio.emit('client_connect_request', {
            'session_code': session_code,
            'client_name': client_name
        })

    def send_stream_data(self, target_sid, data):
        self.sio.emit('stream_data', {
            'target_sid': target_sid,
            'data': data
        })


class ModernRemoteDesktopApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Remote Desktop Pro - Signaling Version")
        self.root.geometry("900x750")
        self.root.configure(bg='#f8f9fa')

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

        self.signaling = SignalingClient(self)

        self.running = False
        self.quality = 70
        self.session_code = None
        self.is_host = False
        self.active_hosts = []
        self.password = ""
        self.target_client_sid = None
        self.client_name = "Remote Client"

        self.setup_styles()
        self.create_gui()
        self.start_periodic_updates()
        self.connect_to_signaling()

    def connect_to_signaling(self):
        def connect_async():
            if self.signaling.connect():
                self.update_status("Connected to signaling server", "success")
            else:
                self.update_status("Failed to connect to signaling server", "error")

        threading.Thread(target=connect_async, daemon=True).start()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.style.configure('Main.TFrame', background=self.colors['background'])
        self.style.configure('Title.TLabel', background=self.colors['background'],
                             foreground=self.colors['primary'], font=('Segoe UI', 20, 'bold'))
        self.style.configure('Card.TLabelframe', background=self.colors['surface'],
                             foreground=self.colors['primary'], relief='solid', borderwidth=1)
        self.style.configure('Primary.TButton', background=self.colors['accent'],
                             foreground='white', borderwidth=0)
        self.style.configure('Secondary.TButton', background=self.colors['surface'],
                             foreground=self.colors['primary'], borderwidth=1)

        self.style.configure('Success.TLabel', foreground=self.colors['success'])
        self.style.configure('Warning.TLabel', foreground=self.colors['warning'])
        self.style.configure('Error.TLabel', foreground=self.colors['error'])
        self.style.configure('Info.TLabel', foreground=self.colors['text_secondary'])

    def create_gui(self):
        main_container = ttk.Frame(self.root, style='Main.TFrame', padding="0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        header_frame = ttk.Frame(main_container, style='Main.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = ttk.Label(header_frame,
                                text="🖥️ Remote Desktop Pro",
                                style='Title.TLabel')
        title_label.pack(side=tk.LEFT)

        content_frame = ttk.Frame(main_container, style='Main.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(content_frame, style='Main.TFrame')
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        right_panel = ttk.Frame(content_frame, style='Main.TFrame')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        self.create_session_panel(left_panel)
        self.create_hosts_panel(right_panel)
        self.create_control_panel(main_container)

    def create_session_panel(self, parent):
        session_frame = ttk.LabelFrame(parent, text="Session Management", padding="20", style='Card.TLabelframe')
        session_frame.pack(fill=tk.BOTH, expand=True)

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

        name_frame = ttk.Frame(session_frame, style='Main.TFrame')
        name_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(name_frame, text="Your Name", style='Info.TLabel').pack(anchor=tk.W)
        self.name_entry = ttk.Entry(name_frame, font=('Segoe UI', 12))
        self.name_entry.pack(fill=tk.X, pady=(5, 0))
        self.name_entry.insert(0, self.client_name)

        password_frame = ttk.Frame(session_frame, style='Main.TFrame')
        password_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(password_frame, text="Password Protection", style='Info.TLabel').pack(anchor=tk.W)
        self.password_entry = ttk.Entry(password_frame, font=('Segoe UI', 12), show="•")
        self.password_entry.pack(fill=tk.X, pady=(5, 0))

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

        tree_frame = ttk.Frame(hosts_frame, style='Main.TFrame')
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('session_code', 'status', 'host_name', 'security')
        self.hosts_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)

        self.hosts_tree.heading('session_code', text='SESSION CODE')
        self.hosts_tree.heading('status', text='STATUS')
        self.hosts_tree.heading('host_name', text='HOST NAME')
        self.hosts_tree.heading('security', text='SECURITY')

        self.hosts_tree.column('session_code', width=120, anchor=tk.CENTER)
        self.hosts_tree.column('status', width=100, anchor=tk.CENTER)
        self.hosts_tree.column('host_name', width=140, anchor=tk.CENTER)
        self.hosts_tree.column('security', width=100, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.hosts_tree.yview)
        self.hosts_tree.configure(yscroll=scrollbar.set)

        self.hosts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        refresh_frame = ttk.Frame(hosts_frame, style='Main.TFrame')
        refresh_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(refresh_frame, text="🔄 Refresh List",
                   command=self.refresh_hosts_list,
                   style='Secondary.TButton').pack()

        self.hosts_tree.bind('<Double-1>', self.on_host_select)

    def create_control_panel(self, parent):
        control_frame = ttk.Frame(parent, style='Main.TFrame')
        control_frame.pack(fill=tk.X, pady=(20, 0))

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

        status_frame = ttk.LabelFrame(control_frame, text="Connection Status", padding="15", style='Card.TLabelframe')
        status_frame.pack(fill=tk.X)

        self.status_label = ttk.Label(status_frame, text="Connecting to signaling server...", style='Info.TLabel')
        self.status_label.pack(anchor=tk.W)

        self.info_label = ttk.Label(status_frame, text="Establishing connection with signaling server",
                                    style='Info.TLabel')
        self.info_label.pack(anchor=tk.W)

    def generate_session_code(self):
        session_code = ''.join(random.choices(string.ascii_uppercase, k=3)) + ''.join(
            random.choices(string.digits, k=3))
        self.session_entry.delete(0, tk.END)
        self.session_entry.insert(0, session_code)
        self.update_info(f"Session code generated: {session_code}")
        return session_code

    def refresh_hosts_list(self):
        try:
            response = requests.get(f"{SIGNALING_SERVER}/sessions", timeout=10)
            if response.status_code == 200:
                result = response.json()
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
                            host.get('host_name', ''),
                            password_icon
                        ))

                    online_count = sum(1 for host in self.active_hosts if host.get('status') == 'Online')
                    self.update_info(f"{online_count} online sessions available")
                else:
                    self.update_info("Unable to fetch sessions list", "error")
            else:
                self.update_info("Unable to fetch sessions list", "error")
        except Exception as e:
            self.update_info(f"Connection error: {str(e)}", "error")

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
            session_code = self.session_entry.get().strip().upper()
            if not session_code:
                session_code = self.generate_session_code()

            host_name = self.name_entry.get().strip() or "Unknown Host"
            self.password = self.password_entry.get()

            password_hash = hashlib.sha256(self.password.encode()).hexdigest() if self.password else ""
            data = {
                'session_code': session_code,
                'host_name': host_name,
                'password_hash': password_hash
            }

            response = requests.post(f"{SIGNALING_SERVER}/session", json=data, timeout=10)
            if response.status_code == 200:
                self.session_code = session_code
                self.is_host = True
                self.running = True

                self.signaling.register_host(session_code, host_name)

                status_text = f"Hosting session: {session_code}"
                if self.password:
                    status_text += " (Password Protected)"

                self.update_status(status_text, "success")
                self.update_info("Waiting for connection requests...")

                self.host_btn.config(state=tk.DISABLED)
                self.connect_btn.config(state=tk.DISABLED)
                self.stop_btn.config(state=tk.NORMAL)

            else:
                self.update_status("Failed to register session", "error")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start hosting: {e}")

    def connect_to_host(self):
        try:
            session_code = self.session_entry.get().strip().upper()
            if not session_code:
                messagebox.showerror("Error", "Please enter a session code")
                return

            client_name = self.name_entry.get().strip() or "Unknown Client"
            self.client_name = client_name

            response = requests.get(f"{SIGNALING_SERVER}/session/{session_code}", timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    host_info = result

                    if host_info.get('has_password'):
                        password = self.ask_for_password()
                        if password is None:
                            return

                        password_hash = hashlib.sha256(password.encode()).hexdigest()
                        verify_response = requests.post(f"{SIGNALING_SERVER}/verify_password",
                                                        json={'session_code': session_code,
                                                              'password_hash': password_hash})

                        if not verify_response.json().get('success'):
                            messagebox.showerror("Error", "Invalid password")
                            return

                    self.session_code = session_code
                    self.is_host = False
                    self.running = True

                    self.signaling.request_connection(session_code, client_name)

                    self.update_status("Connection request sent to host", "warning")
                    self.host_btn.config(state=tk.DISABLED)
                    self.connect_btn.config(state=tk.DISABLED)
                    self.stop_btn.config(state=tk.NORMAL)

                else:
                    messagebox.showerror("Error", f"Session not found: {result.get('error', 'Unknown error')}")
            else:
                messagebox.showerror("Error", "Session not found")

        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {e}")

    def show_connection_request(self, client_name, session_code, connection_id):
        result = [None]

        def on_accept():
            result[0] = True
            dialog.destroy()

        def on_decline():
            result[0] = False
            dialog.destroy()

        dialog = tk.Toplevel(self.root)
        dialog.title("Connection Request")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['background'])
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))

        ttk.Label(dialog, text="🖥️ Incoming Connection Request",
                  style='Title.TLabel', font=('Segoe UI', 14, 'bold')).pack(pady=20)

        ttk.Label(dialog, text=f"Client: {client_name}", style='Info.TLabel',
                  font=('Segoe UI', 11)).pack(pady=5)
        ttk.Label(dialog, text=f"Session: {session_code}", style='Info.TLabel',
                  font=('Segoe UI', 11)).pack(pady=5)
        ttk.Label(dialog, text="Do you want to accept this connection?",
                  style='Info.TLabel', font=('Segoe UI', 10)).pack(pady=10)

        button_frame = ttk.Frame(dialog, style='Main.TFrame')
        button_frame.pack(pady=20)

        ttk.Button(button_frame, text="✅ Accept", command=on_accept,
                   style='Primary.TButton', width=10).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="❌ Decline", command=on_decline,
                   style='Secondary.TButton', width=10).pack(side=tk.LEFT, padx=10)

        self.root.wait_window(dialog)
        return result[0]

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

    def start_streaming_to_client(self):
        def stream_loop():
            try:
                while self.running and self.target_client_sid:
                    screenshot = pyautogui.screenshot()
                    frame = np.array(screenshot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
                    result, encoded_frame = cv2.imencode('.jpg', frame, encode_param)

                    if result:
                        compressed_data = zlib.compress(encoded_frame.tobytes())

                        self.signaling.send_stream_data(self.target_client_sid, compressed_data)

                    time.sleep(0.03)

            except Exception as e:
                self.update_status(f"Stream error: {e}", "error")
            finally:
                self.stop_connection()

        threading.Thread(target=stream_loop, daemon=True).start()

    def start_receiving_stream(self):
        def receive_loop():
            pass

        threading.Thread(target=receive_loop, daemon=True).start()

    def process_stream_data(self, compressed_data):
        try:
            decompressed_data = zlib.decompress(compressed_data)
            frame_array = np.frombuffer(decompressed_data, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

            if frame is not None:
                cv2.imshow('Remote Desktop - Press Q to exit', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.stop_connection()

        except Exception as e:
            print(f"Stream processing error: {e}")

    def update_status(self, message, status_type="info"):
        def update():
            self.status_label.config(text=message)
            if status_type == "success":
                self.status_label.config(style='Success.TLabel')
            elif status_type == "warning":
                self.status_label.config(style='Warning.TLabel')
            elif status_type == "error":
                self.status_label.config(style='Error.TLabel')
            else:
                self.status_label.config(style='Info.TLabel')

        self.root.after(0, update)

    def update_info(self, message, status_type="info"):
        def update():
            self.info_label.config(text=message)
            if status_type == "error":
                self.info_label.config(style='Error.TLabel')
            else:
                self.info_label.config(style='Info.TLabel')

        self.root.after(0, update)

    def stop_connection(self):
        if self.session_code and self.is_host:
            try:
                requests.delete(f"{SIGNALING_SERVER}/session/{self.session_code}", timeout=5)
            except:
                pass

        self.running = False
        self.is_host = False
        self.session_code = None
        self.target_client_sid = None

        self.update_status("Connection stopped", "error")
        self.update_info("Ready for new connection")
        self.host_btn.config(state=tk.NORMAL)
        self.connect_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        cv2.destroyAllWindows()

    def start_periodic_updates(self):
        def update_quality_label():
            self.quality = int(self.quality_scale.get())
            self.quality_label.config(text=f"{self.quality}%")
            self.root.after(100, update_quality_label)

        def refresh_hosts_periodically():
            if self.running and not self.is_host:
                self.refresh_hosts_list()
            self.root.after(10000, refresh_hosts_periodically)

        update_quality_label()
        refresh_hosts_periodically()

    def run(self):
        try:
            self.root.mainloop()
        finally:
            self.signaling.disconnect()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        import pyautogui
        import cv2
        import numpy as np
        import requests
        import socketio
    except ImportError as e:
        print(f"Missing dependencies: {e}")
        print("Please install: pip install opencv-python pyautogui pillow numpy requests python-socketio eventlet")
        exit(1)

    app = ModernRemoteDesktopApp()
    app.run()