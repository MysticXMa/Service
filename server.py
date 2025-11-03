from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)

sessions = {}
session_lock = threading.Lock()


def cleanup_expired_sessions():
    while True:
        time.sleep(60)
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

    if not all([session_code, host_ip, port]):
        return jsonify({'success': False, 'error': 'Missing data'}), 400

    with session_lock:
        sessions[session_code] = {
            'host_ip': host_ip,
            'port': port,
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
                'created': session['created'].isoformat()
            })
        return jsonify({'success': False, 'error': 'Session not found'}), 404


@app.route('/sessions', methods=['GET'])
def get_all_sessions():
    with session_lock:
        hosts = []
        for code, data in sessions.items():
            hosts.append({
                'session_code': code,
                'ip': data['host_ip'],
                'port': data['port'],
                'created': data['created'].strftime('%H:%M:%S')
            })
        return jsonify({'success': True, 'hosts': hosts})


@app.route('/session/<session_code>', methods=['DELETE'])
def delete_session(session_code):
    with session_lock:
        if session_code in sessions:
            del sessions[session_code]
            return jsonify({'success': True, 'message': 'Session deleted'})
        return jsonify({'success': False, 'error': 'Session not found'}), 404


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'sessions': len(sessions)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)