from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time

app = Flask(__name__)
CORS(app)

servers = {}
screenshots = {}
server_timeout = 300

class ServerManager:
    @staticmethod
    def cleanup_old_servers():
        current_time = time.time()
        expired_servers = []

        for server_id, server in servers.items():
            if current_time - server['last_updated'] > server_timeout:
                expired_servers.append(server_id)

        for server_id in expired_servers:
            del servers[server_id]
            if server_id in screenshots:
                del screenshots[server_id]

    @staticmethod
    def create_server(name, pin_code, max_users):
        server_id = str(uuid.uuid4())[:8].upper()

        servers[server_id] = {
            'id': server_id,
            'name': name,
            'pin': pin_code,
            'max_users': max_users,
            'current_users': 0,
            'status': 'Open',
            'created_at': time.time(),
            'last_updated': time.time(),
            'connections': []
        }

        return server_id

    @staticmethod
    def update_server_status(server_id, current_users=None, status=None):
        if server_id not in servers:
            return False

        if current_users is not None:
            servers[server_id]['current_users'] = current_users

        if status is not None:
            servers[server_id]['status'] = status

        servers[server_id]['last_updated'] = time.time()
        return True

    @staticmethod
    def delete_server(server_id):
        if server_id in servers:
            del servers[server_id]
            if server_id in screenshots:
                del screenshots[server_id]
            return True
        return False

    @staticmethod
    def get_all_servers():
        ServerManager.cleanup_old_servers()
        return list(servers.values())

    @staticmethod
    def add_connection(server_id, connection_data):
        if server_id not in servers:
            return False

        servers[server_id]['connections'].append({
            'id': str(uuid.uuid4()),
            'connected_at': time.time(),
            **connection_data
        })
        servers[server_id]['last_updated'] = time.time()
        return True

    @staticmethod
    def store_screenshot(server_id, screenshot_data):
        try:
            screenshots[server_id] = {
                'data': screenshot_data,
                'timestamp': time.time()
            }
            return True
        except Exception as e:
            print(f"Error storing screenshot: {e}")
            return False

    @staticmethod
    def get_screenshot(server_id):
        if server_id in screenshots:
            if time.time() - screenshots[server_id]['timestamp'] < 30:
                return screenshots[server_id]
            else:
                del screenshots[server_id]
        return None

@app.route('/api/servers', methods=['GET'])
def get_servers():
    servers_list = ServerManager.get_all_servers()
    return jsonify(servers_list)

@app.route('/api/servers', methods=['POST'])
def create_server():
    data = request.json
    name = data.get('name', '').strip()
    pin_code = data.get('pin', '').strip()
    max_users = data.get('max_users', 5)

    if not name:
        return jsonify({'error': 'Server name is required'}), 400

    server_id = ServerManager.create_server(name, pin_code, max_users)
    return jsonify({
        'server_id': server_id,
        'message': f'Server "{name}" created successfully'
    })

@app.route('/api/servers/<server_id>', methods=['PUT'])
def update_server(server_id):
    data = request.json
    current_users = data.get('current_users')
    status = data.get('status')

    if ServerManager.update_server_status(server_id, current_users, status):
        return jsonify({'message': 'Server updated successfully'})
    else:
        return jsonify({'error': 'Server not found'}), 404

@app.route('/api/servers/<server_id>', methods=['DELETE'])
def delete_server(server_id):
    if ServerManager.delete_server(server_id):
        return jsonify({'message': 'Server deleted successfully'})
    else:
        return jsonify({'error': 'Server not found'}), 404

@app.route('/api/servers/<server_id>/connect', methods=['POST'])
def connect_to_server(server_id):
    data = request.json
    pin_code = data.get('pin', '')

    if server_id not in servers:
        return jsonify({'error': 'Server not found'}), 404

    server = servers[server_id]

    if server['pin'] and server['pin'] != pin_code:
        return jsonify({'error': 'Invalid PIN code'}), 401

    if server['current_users'] >= server['max_users']:
        return jsonify({'error': 'Server is full'}), 400

    server['current_users'] += 1
    if server['current_users'] >= server['max_users']:
        server['status'] = 'Full'

    server['last_updated'] = time.time()

    ServerManager.add_connection(server_id, {
        'user_name': data.get('user_name', 'Anonymous')
    })

    return jsonify({
        'message': f'Connected to {server["name"]}',
        'server_name': server['name']
    })

@app.route('/api/servers/<server_id>/disconnect', methods=['POST'])
def disconnect_from_server(server_id):
    if server_id not in servers:
        return jsonify({'error': 'Server not found'}), 404

    server = servers[server_id]
    if server['current_users'] > 0:
        server['current_users'] -= 1

    if server['current_users'] < server['max_users'] and server['status'] == 'Full':
        server['status'] = 'Open'

    server['last_updated'] = time.time()

    return jsonify({'message': 'Disconnected successfully'})

@app.route('/api/servers/<server_id>/screenshot', methods=['POST'])
def upload_screenshot(server_id):
    data = request.json
    screenshot_data = data.get('screenshot')

    if not screenshot_data:
        return jsonify({'error': 'Screenshot data is required'}), 400

    if ServerManager.store_screenshot(server_id, screenshot_data):
        return jsonify({'message': 'Screenshot uploaded successfully'})
    else:
        return jsonify({'error': 'Failed to store screenshot'}), 500

@app.route('/api/servers/<server_id>/screenshot', methods=['GET'])
def get_screenshot(server_id):
    screenshot = ServerManager.get_screenshot(server_id)
    if screenshot:
        return jsonify(screenshot)
    else:
        return jsonify({'error': 'No screenshot available'}), 404

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'server_count': len(servers)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)