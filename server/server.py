from flask import Flask, request, jsonify, render_template
import base64
import io
import time
import random
import string
from datetime import datetime
import threading

app = Flask(__name__)

# Enhanced data structures
servers = {}
clients = {}
server_list = []


def generate_id(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


@app.route('/create_server', methods=['POST'])
def create_server():
    data = request.json
    name = data.get('name', 'Unnamed Server')
    password = data.get('password', '')
    max_clients = data.get('max_clients', 10)

    server_id = generate_id()

    servers[server_id] = {
        'name': name,
        'password': password,
        'max_clients': max_clients,
        'created_at': time.time(),
        'last_update': time.time(),
        'clients': [],
        'frame': '',
        'host_online': True
    }

    update_server_list()

    return jsonify({
        'server_id': server_id,
        'name': name,
        'status': 'created'
    })


@app.route('/join_server', methods=['POST'])
def join_server():
    data = request.json
    server_id = data.get('server_id')
    password = data.get('password', '')
    client_name = data.get('client_name', 'Anonymous')

    if server_id not in servers:
        return jsonify({'error': 'Server not found'}), 404

    server = servers[server_id]

    # Check password
    if server['password'] and server['password'] != password:
        return jsonify({'error': 'Invalid password'}), 403

    # Check client limit
    if len(server['clients']) >= server['max_clients']:
        return jsonify({'error': 'Server is full'}), 409

    # Create client
    client_id = generate_id()
    clients[client_id] = {
        'name': client_name,
        'server_id': server_id,
        'joined_at': time.time(),
        'last_active': time.time(),
        'has_control': False,
        'control_requested': False
    }

    # Add client to server
    server['clients'].append(client_id)
    server['last_update'] = time.time()

    update_server_list()

    return jsonify({
        'client_id': client_id,
        'server_name': server['name'],
        'status': 'joined'
    })


@app.route('/update_frame', methods=['POST'])
def update_frame():
    data = request.json
    server_id = data.get('server_id')
    frame_data = data.get('frame')
    timestamp = data.get('timestamp')

    if server_id not in servers:
        return jsonify({'error': 'Server not found'}), 404

    server = servers[server_id]
    server['frame'] = frame_data
    server['last_update'] = time.time()
    server['host_online'] = True

    return jsonify({'status': 'success'})


@app.route('/server_frame/<server_id>')
def get_server_frame(server_id):
    if server_id not in servers:
        return jsonify({'error': 'Server not found'}), 404

    server = servers[server_id]

    # Check if frame is too old
    if time.time() - server['last_update'] > 10:
        return jsonify({'error': 'Server offline'}), 408

    return jsonify({
        'frame': server['frame'],
        'timestamp': server['last_update'],
        'server_name': server['name']
    })


@app.route('/server_clients/<server_id>')
def get_server_clients(server_id):
    if server_id not in servers:
        return jsonify({'error': 'Server not found'}), 404

    server = servers[server_id]
    client_list = []

    # Clean up disconnected clients
    active_clients = []
    for client_id in server['clients']:
        if client_id in clients and time.time() - clients[client_id]['last_active'] < 30:
            active_clients.append(client_id)
            client_data = clients[client_id]
            client_list.append({
                'id': client_id,
                'name': client_data['name'],
                'has_control': client_data['has_control'],
                'control_requested': client_data['control_requested'],
                'last_active': client_data['last_active']
            })
        else:
            # Remove disconnected client
            if client_id in clients:
                del clients[client_id]

    server['clients'] = active_clients
    server['last_update'] = time.time()

    return jsonify({'clients': client_list})


@app.route('/grant_control', methods=['POST'])
def grant_control():
    data = request.json
    server_id = data.get('server_id')
    client_id = data.get('client_id')

    if server_id not in servers:
        return jsonify({'error': 'Server not found'}), 404

    if client_id not in clients or clients[client_id]['server_id'] != server_id:
        return jsonify({'error': 'Client not found'}), 404

    # Revoke control from all other clients in this server
    for cid in servers[server_id]['clients']:
        if cid in clients:
            clients[cid]['has_control'] = False

    # Grant control to specified client
    clients[client_id]['has_control'] = True
    clients[client_id]['control_requested'] = False

    servers[server_id]['last_update'] = time.time()

    return jsonify({'status': 'control_granted'})


@app.route('/revoke_control', methods=['POST'])
def revoke_control():
    data = request.json
    server_id = data.get('server_id')
    client_id = data.get('client_id')

    if server_id not in servers:
        return jsonify({'error': 'Server not found'}), 404

    if client_id not in clients or clients[client_id]['server_id'] != server_id:
        return jsonify({'error': 'Client not found'}), 404

    clients[client_id]['has_control'] = False
    servers[server_id]['last_update'] = time.time()

    return jsonify({'status': 'control_revoked'})


@app.route('/request_control', methods=['POST'])
def request_control():
    data = request.json
    client_id = data.get('client_id')

    if client_id not in clients:
        return jsonify({'error': 'Client not found'}), 404

    clients[client_id]['control_requested'] = True
    clients[client_id]['last_active'] = time.time()

    return jsonify({'status': 'control_requested'})


@app.route('/kick_client', methods=['POST'])
def kick_client():
    data = request.json
    server_id = data.get('server_id')
    client_id = data.get('client_id')

    if server_id not in servers:
        return jsonify({'error': 'Server not found'}), 404

    if client_id in servers[server_id]['clients']:
        servers[server_id]['clients'].remove(client_id)

    if client_id in clients:
        del clients[client_id]

    servers[server_id]['last_update'] = time.time()
    update_server_list()

    return jsonify({'status': 'client_kicked'})


@app.route('/stop_server', methods=['POST'])
def stop_server():
    data = request.json
    server_id = data.get('server_id')

    if server_id not in servers:
        return jsonify({'error': 'Server not found'}), 404

    # Remove all clients from this server
    for client_id in servers[server_id]['clients'][:]:
        if client_id in clients:
            del clients[client_id]
        servers[server_id]['clients'].remove(client_id)

    # Remove server
    del servers[server_id]
    update_server_list()

    return jsonify({'status': 'server_stopped'})


@app.route('/servers')
def get_servers_list():
    cleanup_old_servers()
    return jsonify({'servers': server_list})


def update_server_list():
    global server_list
    cleanup_old_servers()

    server_list = []
    for server_id, server in servers.items():
        if time.time() - server['last_update'] < 30:  # Server is active
            server_list.append({
                'id': server_id,
                'name': server['name'],
                'password': bool(server['password']),
                'client_count': len(server['clients']),
                'max_clients': server['max_clients'],
                'created_at': server['created_at'],
                'last_active': server['last_update']
            })


def cleanup_old_servers():
    current_time = time.time()
    servers_to_remove = []
    clients_to_remove = []

    # Remove old servers
    for server_id, server in servers.items():
        if current_time - server['last_update'] > 30:  # 30 seconds timeout
            servers_to_remove.append(server_id)
            # Mark all clients for removal
            clients_to_remove.extend(server['clients'])

    # Remove old clients
    for client_id, client in clients.items():
        if current_time - client['last_active'] > 30:
            clients_to_remove.append(client_id)

    # Perform cleanup
    for server_id in servers_to_remove:
        del servers[server_id]

    for client_id in clients_to_remove:
        if client_id in clients:
            del clients[client_id]


# Background cleanup thread
def background_cleanup():
    while True:
        try:
            cleanup_old_servers()
            update_server_list()
            time.sleep(10)  # Run every 10 seconds
        except:
            time.sleep(10)


@app.route('/')
def home():
    cleanup_old_servers()
    return jsonify({
        'status': 'NeonShare Server is running',
        'active_servers': len(servers),
        'active_clients': len(clients),
        'total_connections': len(server_list),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/status')
def status():
    cleanup_old_servers()
    return jsonify({
        'servers': {
            'total': len(servers),
            'details': {server_id: {
                'name': server['name'],
                'clients': len(server['clients']),
                'last_update': server['last_update']
            } for server_id, server in servers.items()}
        },
        'clients': {
            'total': len(clients),
            'details': {client_id: {
                'name': client['name'],
                'server': client['server_id'],
                'has_control': client['has_control']
            } for client_id, client in clients.items()}
        }
    })


if __name__ == '__main__':
    # Start background cleanup thread
    cleanup_thread = threading.Thread(target=background_cleanup, daemon=True)
    cleanup_thread.start()

    app.run(host='0.0.0.0', port=5000, debug=False)