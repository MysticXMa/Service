from flask import Flask, request, jsonify
import base64
import io
from PIL import Image
import time
import random
import string

app = Flask(__name__)

screens = {}
server_list = []


def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


@app.route('/generate_code', methods=['POST'])
def generate_share_code():
    data = request.json
    name = data.get('name', 'Anonymous')
    password = data.get('password', '')

    code = generate_code()

    screens[code] = {
        'name': name,
        'password': password,
        'screen': '',
        'last_update': time.time()
    }

    update_server_list()

    return jsonify({'code': code})


@app.route('/update_screen', methods=['POST'])
def update_screen():
    data = request.json
    code = data.get('code')
    password = data.get('password')
    screen_data = data.get('screen')

    if code not in screens:
        return jsonify({'error': 'Invalid code'}), 404

    if screens[code]['password'] != password:
        return jsonify({'error': 'Invalid password'}), 403

    try:
        screens[code]['screen'] = screen_data
        screens[code]['last_update'] = time.time()

        update_server_list()

        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/screen/<code>')
def get_screen(code):
    if code not in screens:
        return jsonify({'error': 'Screen not found'}), 404

    screen_data = screens[code]

    if time.time() - screen_data['last_update'] > 30:
        return jsonify({'error': 'Screen data expired'}), 408

    return jsonify({
        'screen': screen_data['screen'],
        'name': screen_data['name'],
        'last_update': screen_data['last_update']
    })


@app.route('/servers')
def get_servers():
    cleanup_old_servers()
    return jsonify({'servers': server_list})


def update_server_list():
    global server_list
    cleanup_old_servers()

    server_list = []
    for code, data in screens.items():
        if time.time() - data['last_update'] < 30:
            server_list.append({
                'code': code,
                'name': data['name'],
                'last_active': data['last_update']
            })


def cleanup_old_servers():
    current_time = time.time()
    codes_to_remove = []

    for code, data in screens.items():
        if current_time - data['last_update'] > 30:
            codes_to_remove.append(code)

    for code in codes_to_remove:
        del screens[code]


@app.route('/')
def home():
    return jsonify({
        'status': 'Screen Share Server is running',
        'active_screens': len([s for s in screens.values() if time.time() - s['last_update'] < 30]),
        'total_servers': len(server_list)
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)