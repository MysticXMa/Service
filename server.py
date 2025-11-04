import os
import secrets
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import threading
import time
import hashlib
from flask_socketio import SocketIO, emit
import eventlet

app = Flask(__name__)

secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    secret_key = secrets.token_hex(24)
    print(f"Generated SECRET_KEY: {secret_key}")

app.config['SECRET_KEY'] = secret_key
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

sessions = {}
pending_connections = {}
connection_lock = threading.Lock()


def get_host_status(session_data):
    last_seen = session_data['last_seen']
    time_diff = datetime.now() - last_seen
    if time_diff < timedelta(seconds=30):
        return 'Online'
    elif time_diff < timedelta(minutes=2):
        return 'Away'
    elif time_diff < timedelta(minutes=5):
        return 'Offline'
    else:
        return 'Error'


def cleanup_expired_sessions():
    while True:
        time.sleep(30)
        with connection_lock:
            current_time = datetime.now()
            expired_sessions = []
            expired_connections = []

            for code, data in sessions.items():
                if current_time - data['last_seen'] > timedelta(minutes=10):
                    expired_sessions.append(code)

            for conn_id, conn_data in pending_connections.items():
                if current_time - conn_data['created'] > timedelta(minutes=2):
                    expired_connections.append(conn_id)

            for code in expired_sessions:
                del sessions[code]
            for conn_id in expired_connections:
                del pending_connections[conn_id]


threading.Thread(target=cleanup_expired_sessions, daemon=True).start()


@app.route('/session', methods=['POST'])
def register_session():
    data = request.json
    session_code = data.get('session_code')
    host_name = data.get('host_name', 'Unknown Host')
    password_hash = data.get('password_hash', '')

    if not session_code:
        return jsonify({'success': False, 'error': 'Missing session code'}), 400

    with connection_lock:
        sessions[session_code] = {
            'host_name': host_name,
            'password_hash': password_hash,
            'host_sid': None,
            'created': datetime.now(),
            'last_seen': datetime.now()
        }

    return jsonify({'success': True, 'message': 'Session registered'})


@app.route('/session/<session_code>', methods=['GET'])
def get_session(session_code):
    with connection_lock:
        session = sessions.get(session_code)
        if session:
            session['last_seen'] = datetime.now()
            return jsonify({
                'success': True,
                'host_name': session['host_name'],
                'has_password': bool(session['password_hash']),
                'created': session['created'].isoformat()
            })
        return jsonify({'success': False, 'error': 'Session not found'}), 404


@app.route('/sessions', methods=['GET'])
def get_all_sessions():
    with connection_lock:
        hosts = []
        for code, data in sessions.items():
            status = get_host_status(data)
            hosts.append({
                'session_code': code,
                'host_name': data['host_name'],
                'status': status,
                'created': data['created'].strftime('%H:%M:%S'),
                'has_password': bool(data['password_hash'])
            })
        return jsonify({'success': True, 'hosts': hosts})


@app.route('/session/<session_code>', methods=['DELETE'])
def delete_session(session_code):
    with connection_lock:
        if session_code in sessions:
            session_data = sessions[session_code]
            if session_data['host_sid']:
                socketio.emit('session_terminated', {'message': 'Session deleted'}, room=session_data['host_sid'])
            del sessions[session_code]
            return jsonify({'success': True, 'message': 'Session deleted'})
        return jsonify({'success': False, 'error': 'Session not found'}), 404


@app.route('/verify_password', methods=['POST'])
def verify_password():
    data = request.json
    session_code = data.get('session_code')
    password_hash = data.get('password_hash')

    with connection_lock:
        session = sessions.get(session_code)
        if session:
            if not session['password_hash'] or session['password_hash'] == password_hash:
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Invalid password'})
        return jsonify({'success': False, 'error': 'Session not found'})


@app.route('/health', methods=['GET'])
def health():
    online_count = sum(1 for data in sessions.values() if get_host_status(data) == 'Online')
    return jsonify({
        'status': 'ok',
        'total_sessions': len(sessions),
        'online_sessions': online_count,
        'pending_connections': len(pending_connections)
    })


@socketio.on('host_register')
def handle_host_register(data):
    session_code = data.get('session_code')
    with connection_lock:
        if session_code in sessions:
            sessions[session_code]['host_sid'] = request.sid
            sessions[session_code]['last_seen'] = datetime.now()
            emit('registration_success', {'message': 'Host registered successfully'})
        else:
            emit('registration_error', {'error': 'Session not found'})


@socketio.on('client_connect_request')
def handle_client_connect(data):
    session_code = data.get('session_code')
    client_name = data.get('client_name', 'Unknown Client')

    with connection_lock:
        session = sessions.get(session_code)
        if not session:
            emit('connection_error', {'error': 'Session not found'})
            return

        conn_id = f"{session_code}_{request.sid}"
        pending_connections[conn_id] = {
            'client_sid': request.sid,
            'client_name': client_name,
            'session_code': session_code,
            'created': datetime.now()
        }

        if session['host_sid']:
            socketio.emit('connection_request', {
                'connection_id': conn_id,
                'client_name': client_name,
                'session_code': session_code,
                'timestamp': datetime.now().isoformat()
            }, room=session['host_sid'])
            emit('pending_approval', {'message': 'Connection request sent to host'})
        else:
            emit('connection_error', {'error': 'Host not available'})


@socketio.on('host_decision')
def handle_host_decision(data):
    connection_id = data.get('connection_id')
    approved = data.get('approved')

    with connection_lock:
        connection = pending_connections.get(connection_id)
        if not connection:
            emit('decision_error', {'error': 'Connection request not found'})
            return

        if approved:
            socketio.emit('connection_approved', {
                'message': 'Connection approved by host',
                'connection_id': connection_id
            }, room=connection['client_sid'])

            session = sessions.get(connection['session_code'])
            if session and session['host_sid']:
                socketio.emit('start_streaming', {
                    'client_sid': connection['client_sid'],
                    'client_name': connection['client_name']
                }, room=session['host_sid'])
        else:
            socketio.emit('connection_rejected', {
                'message': 'Connection rejected by host'
            }, room=connection['client_sid'])

        del pending_connections[connection_id]


@socketio.on('stream_data')
def handle_stream_data(data):
    target_sid = data.get('target_sid')
    stream_data = data.get('data')

    if target_sid:
        emit('stream_data', {'data': stream_data}, room=target_sid)


@socketio.on('disconnect')
def handle_disconnect():
    with connection_lock:
        for session_code, session_data in sessions.items():
            if session_data['host_sid'] == request.sid:
                session_data['host_sid'] = None
                break

        expired_connections = []
        for conn_id, conn_data in pending_connections.items():
            if conn_data['client_sid'] == request.sid:
                expired_connections.append(conn_id)

        for conn_id in expired_connections:
            del pending_connections[conn_id]


@socketio.on('ping')
def handle_ping():
    emit('pong', {'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    print("Starting Signaling Server on port 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)