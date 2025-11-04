import socket
import threading
import json
import time
from datetime import datetime

class GameServer:
    def __init__(self, host='0.0.0.0', port=5555, max_players=4, password=None):
        self.host = host
        self.port = port
        self.max_players = max_players
        self.password = password
        self.clients = []
        self.running = False
        self.server_socket = None
        self.registered_servers = []

    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            print(f"Server started on {self.host}:{self.port}")
            print(f"Max players: {self.max_players}")
            print(f"Password protected: {self.password is not None}")

            self.register_with_central_server()

            accept_thread = threading.Thread(target=self.accept_clients)
            accept_thread.daemon = True
            accept_thread.start()

            heartbeat_thread = threading.Thread(target=self.send_heartbeat)
            heartbeat_thread.daemon = True
            heartbeat_thread.start()

            return True

        except Exception as e:
            print(f"Failed to start server: {e}")
            return False

    def register_with_central_server(self):
        try:
            central_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            central_socket.connect(('service-zopk.onrender.com', 5555))

            server_info = {
                'action': 'register',
                'name': f"Game Server {self.port}",
                'host': self.host,
                'port': self.port,
                'max_players': self.max_players,
                'has_password': self.password is not None,
                'current_players': len(self.clients),
                'status': 'online'
            }

            central_socket.send(json.dumps(server_info).encode('utf-8'))
            response = central_socket.recv(1024).decode('utf-8')
            print(f"Registration response: {response}")
            central_socket.close()

        except Exception as e:
            print(f"Failed to register with central server: {e}")

    def send_heartbeat(self):
        while self.running:
            try:
                central_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                central_socket.connect(('service-zopk.onrender.com', 5555))

                heartbeat_info = {
                    'action': 'heartbeat',
                    'port': self.port,
                    'current_players': len(self.clients),
                    'status': 'online'
                }

                central_socket.send(json.dumps(heartbeat_info).encode('utf-8'))
                central_socket.close()

            except Exception as e:
                print(f"Heartbeat failed: {e}")

            time.sleep(30)

    def accept_clients(self):
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"New connection from {address}")

                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                client_thread.daemon = True
                client_thread.start()

            except Exception as e:
                if self.running:
                    print(f"Error accepting client: {e}")

    def handle_client(self, client_socket, address):
        try:
            welcome_msg = {
                'type': 'welcome',
                'message': 'Connected to game server',
                'max_players': self.max_players,
                'requires_password': self.password is not None
            }
            client_socket.send(json.dumps(welcome_msg).encode('utf-8'))

            if self.password:
                auth_msg = json.loads(client_socket.recv(1024).decode('utf-8'))
                if auth_msg.get('password') != self.password:
                    error_msg = {'type': 'error', 'message': 'Invalid password'}
                    client_socket.send(json.dumps(error_msg).encode('utf-8'))
                    client_socket.close()
                    return

            client_info = {
                'socket': client_socket,
                'address': address,
                'joined_at': datetime.now()
            }
            self.clients.append(client_info)

            success_msg = {
                'type': 'success',
                'message': f'Successfully joined server! Players: {len(self.clients)}/{self.max_players}'
            }
            client_socket.send(json.dumps(success_msg).encode('utf-8'))

            self.broadcast_player_count()

            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break

                    message = json.loads(data.decode('utf-8'))
                    if message.get('type') == 'chat':
                        self.broadcast_chat(message, address)

                except:
                    break

        except Exception as e:
            print(f"Error handling client {address}: {e}")
        finally:
            self.clients = [c for c in self.clients if c['socket'] != client_socket]
            self.broadcast_player_count()
            client_socket.close()

    def broadcast_player_count(self):
        update_msg = {
            'type': 'player_count',
            'count': len(self.clients),
            'max_players': self.max_players
        }

        for client in self.clients:
            try:
                client['socket'].send(json.dumps(update_msg).encode('utf-8'))
            except:
                continue

    def broadcast_chat(self, message, sender_address):
        chat_msg = {
            'type': 'chat',
            'message': message['message'],
            'sender': str(sender_address),
            'timestamp': datetime.now().strftime("%H:%M:%S")
        }

        for client in self.clients:
            try:
                client['socket'].send(json.dumps(chat_msg).encode('utf-8'))
            except:
                continue

    def stop_server(self):
        self.running = False

        disconnect_msg = {'type': 'disconnect', 'message': 'Server is shutting down'}
        for client in self.clients:
            try:
                client['socket'].send(json.dumps(disconnect_msg).encode('utf-8'))
                client['socket'].close()
            except:
                continue

        if self.server_socket:
            self.server_socket.close()

        try:
            central_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            central_socket.connect(('service-zopk.onrender.com', 5555))

            unregister_info = {
                'action': 'unregister',
                'port': self.port
            }

            central_socket.send(json.dumps(unregister_info).encode('utf-8'))
            central_socket.close()

        except Exception as e:
            print(f"Failed to unregister from central server: {e}")

        print("Server stopped")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        port = int(sys.argv[1])
        max_players = int(sys.argv[2]) if len(sys.argv) > 2 else 4
        password = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        port = 5555
        max_players = 4
        password = None

    server = GameServer(port=port, max_players=max_players, password=password)

    try:
        if server.start_server():
            print("Press Ctrl+C to stop the server")
            while server.running:
                time.sleep(1)
        else:
            print("Failed to start server")
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.stop_server()