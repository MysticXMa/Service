from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import threading
import time
import hashlib

app = Flask(__name__)

sessions = {}
session_lock = threading.Lock()


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
        with session_lock:
            current_time = datetime.now()
            expired = []
            for code, data in sessions.items():
                if current_time - data['last_seen'] > timedelta(minutes=10):
                    expired.append(code)
            for code in expired:
                del sessions[code]
            if expired:
                print(f"Cleaned up {len(expired)} expired sessions")


threading.Thread(target=cleanup_expired_sessions, daemon=True).start()


@app.route('/session', methods=['POST'])
def register_session():
    data = request.json
    session_code = data.get('session_code')
    host_ip = data.get('host_ip')
    port = data.get('port')
    password_hash = data.get('password_hash', '')

    if not all([session_code, host_ip, port]):
        return jsonify({'success': False, 'error': 'Missing data'}), 400

    with session_lock:
        sessions[session_code] = {
            'host_ip': host_ip,
            'port': port,
            'password_hash': password_hash,
            'created': datetime.now(),
            'last_seen': datetime.now()
        }

    return jsonify({'success': True, 'message': 'Session registered'})


@app.route('/session/<session_code>', methods=['GET'])
def get_session(session_code):
    with session_lock:
        session = sessions.get(session_code)
        if session:
            session['last_seen'] = datetime.now()
            return jsonify({
                'success': True,
                'host_ip': session['host_ip'],
                'port': session['port'],
                'password_hash': session['password_hash'],
                'created': session['created'].isoformat()
            })
        return jsonify({'success': False, 'error': 'Session not found'}), 404


@app.route('/sessions', methods=['GET'])
def get_all_sessions():
    with session_lock:
        hosts = []
        for code, data in sessions.items():
            status = get_host_status(data)
            hosts.append({
                'session_code': code,
                'ip': data['host_ip'],
                'port': data['port'],
                'status': status,
                'created': data['created'].strftime('%H:%M:%S'),
                'has_password': bool(data['password_hash'])
            })
        return jsonify({'success': True, 'hosts': hosts})


@app.route('/session/<session_code>', methods=['DELETE'])
def delete_session(session_code):
    with session_lock:
        if session_code in sessions:
            del sessions[session_code]
            return jsonify({'success': True, 'message': 'Session deleted'})
        return jsonify({'success': False, 'error': 'Session not found'}), 404


@app.route('/session/<session_code>/ping', methods=['POST'])
def ping_session(session_code):
    with session_lock:
        session = sessions.get(session_code)
        if session:
            session['last_seen'] = datetime.now()
            return jsonify({'success': True})
        return jsonify({'success': False}), 404


@app.route('/verify_password', methods=['POST'])
def verify_password():
    data = request.json
    session_code = data.get('session_code')
    password_hash = data.get('password_hash')

    with session_lock:
        session = sessions.get(session_code)
        if session:
            if not session['password_hash'] or session['password_hash'] == password_hash:
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Invalid password'})
        return jsonify({'success': False, 'error': 'Session not found'})


@app.route('/health', methods=['GET'])
def health():
    online_count = sum(1 for data in sessions.values()
                       if get_host_status(data) == 'Online')
    return jsonify({
        'status': 'ok',
        'total_sessions': len(sessions),
        'online_sessions': online_count
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)