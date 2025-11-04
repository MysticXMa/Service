from flask import Flask, request, jsonify
import threading
import time
import base64
import io
from PIL import Image, ImageGrab
import uuid
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

devices = {}
sessions = {}
screen_streams = {}
passwords = {}


class ScreenStreamer:
    def __init__(self, device_id):
        self.device_id = device_id
        self.active = True
        self.last_screenshot = None

    def start_streaming(self):
        def capture_screen():
            while self.active:
                try:
                    screenshot = ImageGrab.grab()
                    buffered = io.BytesIO()
                    screenshot.save(buffered, format="JPEG", quality=50)
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    self.last_screenshot = img_str
                    time.sleep(0.1)
                except Exception as e:
                    time.sleep(1)

        thread = threading.Thread(target=capture_screen, daemon=True)
        thread.start()


@app.route('/share', methods=['POST'])
def share_device():
    data = request.json or {}
    device_id = str(uuid.uuid4())[:8]
    password = data.get('password')
    name = data.get('name', f'Server-{device_id}')

    streamer = ScreenStreamer(device_id)
    streamer.start_streaming()
    screen_streams[device_id] = streamer

    if password:
        passwords[device_id] = password
        status = 'password_protected'
    else:
        status = 'online'

    devices[device_id] = {
        'id': device_id,
        'name': name,
        'status': status,
        'password_protected': bool(password),
        'created_at': time.time()
    }

    return jsonify({
        'device_id': device_id,
        'message': 'Server created successfully',
        'status': status,
        'name': name
    })


@app.route('/stop_sharing', methods=['POST'])
def stop_sharing():
    data = request.json
    device_id = data.get('device_id')

    if device_id in devices:
        del devices[device_id]
    if device_id in screen_streams:
        screen_streams[device_id].active = False
        del screen_streams[device_id]
    if device_id in passwords:
        del passwords[device_id]

    return jsonify({'message': 'Server stopped successfully'})


@app.route('/devices', methods=['GET'])
def get_devices():
    current_time = time.time()
    expired_devices = []

    for device_id, device in devices.items():
        if current_time - device['created_at'] > 3600:
            expired_devices.append(device_id)

    for device_id in expired_devices:
        if device_id in devices:
            del devices[device_id]
        if device_id in screen_streams:
            screen_streams[device_id].active = False
            del screen_streams[device_id]
        if device_id in passwords:
            del passwords[device_id]

    for device_id in devices:
        if device_id in screen_streams and screen_streams[device_id].active:
            if device_id in passwords:
                devices[device_id]['status'] = 'password_protected'
            else:
                devices[device_id]['status'] = 'online'
        else:
            devices[device_id]['status'] = 'offline'

    return jsonify({
        'devices': list(devices.values())
    })


@app.route('/connect', methods=['POST'])
def connect_to_device():
    data = request.json
    device_id = data.get('device_id')
    password = data.get('password')

    if device_id not in devices:
        return jsonify({'error': 'Server not found'}), 404

    if device_id not in screen_streams:
        return jsonify({'error': 'Server not available'}), 400

    if device_id in passwords:
        if not password or passwords[device_id] != password:
            return jsonify({'error': 'Invalid password'}), 401

    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        'device_id': device_id,
        'created_at': time.time(),
        'active': True
    }

    devices[device_id]['status'] = 'busy'

    return jsonify({
        'session_id': session_id,
        'device_id': device_id,
        'message': 'Connected successfully'
    })


@app.route('/screen', methods=['GET'])
def get_screen():
    session_id = request.args.get('session_id')

    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid session'}), 401

    session = sessions[session_id]
    device_id = session['device_id']

    if device_id not in screen_streams:
        return jsonify({'error': 'Server not available'}), 404

    streamer = screen_streams[device_id]

    if streamer.last_screenshot:
        return jsonify({
            'screenshot': streamer.last_screenshot,
            'timestamp': time.time()
        })
    else:
        return jsonify({
            'screenshot': None,
            'message': 'No screen data available'
        })


@app.route('/disconnect', methods=['POST'])
def disconnect():
    data = request.json
    session_id = data.get('session_id')

    if session_id in sessions:
        device_id = sessions[session_id]['device_id']
        if device_id in devices:
            if device_id in passwords:
                devices[device_id]['status'] = 'password_protected'
            else:
                devices[device_id]['status'] = 'online'
        del sessions[session_id]

    return jsonify({'message': 'Disconnected successfully'})


@app.route('/send_keys', methods=['POST'])
def send_keys():
    data = request.json
    session_id = data.get('session_id')
    keys = data.get('keys')

    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid session'}), 401

    return jsonify({'message': 'Keys sent successfully'})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'online',
        'servers_count': len(devices),
        'sessions_count': len(sessions)
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)