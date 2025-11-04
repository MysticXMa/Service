import socket
import threading
import json
import time
import os
from datetime import datetime, timedelta


class CentralServer:
    def __init__(self):
        # Use Render's PORT environment variable
        self.port = int(os.environ.get('PORT', 10000))
        self.host = '0.0.0.0'
        self.registered_servers = {}
        self.heartbeat_timeout = 60
        print(f"Initializing Central Server on port: {self.port}")

    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(20)
            self.server_socket.settimeout(1.0)

            print(f"✅ Central Server started on {self.host}:{self.port}")
            print(f"🔗 Server URL: https://service-zopk.onrender.com")
            print(f"📡 Ready to accept connections from game servers and clients...")

            # Start cleanup thread for dead servers
            cleanup_thread = threading.Thread(target=self.cleanup_old_servers, daemon=True)
            cleanup_thread.start()

            # Main connection loop
            while True:
                try:
                    client_socket, address = self.server_socket.accept()

                    # Handle each client in separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except socket.timeout:
                    continue
                except Exception as e:
                    if "closed" not in str(e):
                        print(f"❌ Error accepting connection: {e}")
                    break

        except Exception as e:
            print(f"❌ Failed to start central server: {e}")
        finally:
            if hasattr(self, 'server_socket'):
                self.server_socket.close()

    def handle_client(self, client_socket, address):
        try:
            client_socket.settimeout(5.0)
            data = client_socket.recv(4096).decode('utf-8')

            if not data:
                return

            # Check if this is an HTTP request (Render health checks)
            if data.startswith(('GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS')):
                print(f"🌐 HTTP request from {address}")
                self.handle_http_request(client_socket, address, data)
                return

            # Try to parse as JSON (game server/client communication)
            try:
                message = json.loads(data)
                action = message.get('action')

                print(f"🔄 Processing {action} from {address}")

                if action == 'register':
                    self.register_server(message, client_socket)
                elif action == 'heartbeat':
                    self.update_heartbeat(message)
                elif action == 'unregister':
                    self.unregister_server(message)
                elif action == 'get_servers':
                    self.send_server_list(client_socket)
                else:
                    print(f"⚠️ Unknown action: {action}")
                    response = {'status': 'error', 'message': f'Unknown action: {action}'}
                    client_socket.send(json.dumps(response).encode('utf-8'))

            except json.JSONDecodeError:
                print(f"📨 Raw data from {address}: {data[:100]}...")
                # Send helpful error message
                error_response = {
                    'status': 'error',
                    'message': 'Invalid JSON. This is a game server central server.',
                    'expected_format': {'action': 'register|heartbeat|get_servers|unregister', '...': 'other fields'}
                }
                client_socket.send(json.dumps(error_response).encode('utf-8'))

        except socket.timeout:
            print(f"⏰ Timeout handling client {address}")
        except Exception as e:
            print(f"❌ Error handling client {address}: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass

    def handle_http_request(self, client_socket, address, http_data):
        """Handle HTTP requests (Render health checks)"""
        try:
            # Simple HTTP response for health checks
            response = f"""HTTP/1.1 200 OK
Content-Type: application/json
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type

{json.dumps({
                "status": "online",
                "service": "Game Server Central Server",
                "active_servers": len(self.registered_servers),
                "total_players": sum(server['current_players'] for server in self.registered_servers.values()),
                "timestamp": datetime.now().isoformat()
            })}"""

            client_socket.send(response.encode('utf-8'))
            print(f"✅ HTTP health check responded to {address}")

        except Exception as e:
            print(f"❌ Error handling HTTP request: {e}")

    def register_server(self, server_info, client_socket):
        try:
            server_port = server_info['port']
            server_host = server_info.get('host', 'unknown')
            server_key = f"{server_host}:{server_port}"

            server_data = {
                'name': server_info.get('name', f'Game Server {server_port}'),
                'host': server_host,
                'port': server_port,
                'max_players': server_info.get('max_players', 4),
                'current_players': server_info.get('current_players', 0),
                'has_password': server_info.get('has_password', False),
                'status': server_info.get('status', 'online'),
                'last_heartbeat': datetime.now(),
                'registered_at': datetime.now(),
                'public_url': f"{server_host}:{server_port}"
            }

            self.registered_servers[server_key] = server_data
            print(f"✅ Registered server: {server_key} - {server_data['name']}")
            print(f"   Players: {server_data['current_players']}/{server_data['max_players']}")
            print(f"   Password: {'Yes' if server_data['has_password'] else 'No'}")

            response = {
                'status': 'success',
                'message': 'Server registered successfully',
                'assigned_port': server_port,
                'central_server': 'service-zopk.onrender.com'
            }
            client_socket.send(json.dumps(response).encode('utf-8'))

        except Exception as e:
            print(f"❌ Error registering server: {e}")
            response = {'status': 'error', 'message': str(e)}
            client_socket.send(json.dumps(response).encode('utf-8'))

    def update_heartbeat(self, heartbeat_info):
        try:
            server_port = heartbeat_info['port']
            server_host = heartbeat_info.get('host', 'unknown')
            server_key = f"{server_host}:{server_port}"

            if server_key in self.registered_servers:
                self.registered_servers[server_key]['last_heartbeat'] = datetime.now()
                self.registered_servers[server_key]['current_players'] = heartbeat_info.get('current_players', 0)
                self.registered_servers[server_key]['status'] = heartbeat_info.get('status', 'online')

                # Print heartbeat info occasionally
                if heartbeat_info.get('current_players', 0) > 0:
                    print(f"💓 Heartbeat: {server_key} - {heartbeat_info['current_players']} players")

        except Exception as e:
            print(f"❌ Error updating heartbeat: {e}")

    def unregister_server(self, server_info):
        try:
            server_port = server_info['port']
            server_host = server_info.get('host', 'unknown')
            server_key = f"{server_host}:{server_port}"

            if server_key in self.registered_servers:
                del self.registered_servers[server_key]
                print(f"🗑️ Unregistered server: {server_key}")

        except Exception as e:
            print(f"❌ Error unregistering server: {e}")

    def send_server_list(self, client_socket):
        try:
            server_list = []
            for server_key, server_data in self.registered_servers.items():
                # Create a copy without datetime objects for JSON serialization
                server_copy = server_data.copy()
                server_copy.pop('last_heartbeat', None)
                server_copy.pop('registered_at', None)
                server_list.append(server_copy)

            print(f"📊 Sending server list: {len(server_list)} servers available")
            client_socket.send(json.dumps(server_list).encode('utf-8'))

        except Exception as e:
            print(f"❌ Error sending server list: {e}")
            client_socket.send(json.dumps([]).encode('utf-8'))

    def cleanup_old_servers(self):
        """Remove servers that haven't sent heartbeat in timeout period"""
        while True:
            try:
                current_time = datetime.now()
                servers_to_remove = []

                for server_key, server_data in self.registered_servers.items():
                    time_since_heartbeat = current_time - server_data['last_heartbeat']
                    if time_since_heartbeat.total_seconds() > self.heartbeat_timeout:
                        servers_to_remove.append(server_key)

                for server_key in servers_to_remove:
                    print(f"🧹 Removing inactive server: {server_key}")
                    del self.registered_servers[server_key]

                # Print server count every cleanup cycle
                active_servers = len(self.registered_servers)
                total_players = sum(server['current_players'] for server in self.registered_servers.values())
                if active_servers > 0:
                    print(f"📈 Server Stats: {active_servers} active servers, {total_players} total players")

                time.sleep(30)

            except Exception as e:
                print(f"❌ Error in cleanup thread: {e}")
                time.sleep(30)


if __name__ == "__main__":
    print("🚀 Starting Game Server Central Server...")
    print("📍 Domain: https://service-zopk.onrender.com")
    print("⏰ Server will handle port management and server discovery")
    print("🌐 This server handles both HTTP health checks and JSON socket connections")

    server = CentralServer()
    server.start()