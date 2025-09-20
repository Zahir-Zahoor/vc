from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

# Service URLs
GROUP_SERVICE_URL = os.getenv('GROUP_SERVICE_URL', 'http://group-service:5000')
SESSION_SERVICE_URL = os.getenv('SESSION_SERVICE_URL', 'http://session-service:5000')
MESSAGING_SERVICE_URL = os.getenv('MESSAGING_SERVICE_URL', 'http://messaging-service:5000')
WEBSOCKET_SERVICE_URL = os.getenv('WEBSOCKET_SERVICE_URL', 'http://websocket-service:5000')

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/health')
def health():
    services = {
        'websocket': check_service_health(WEBSOCKET_SERVICE_URL),
        'messaging': check_service_health(MESSAGING_SERVICE_URL),
        'group': check_service_health(GROUP_SERVICE_URL),
        'session': check_service_health(SESSION_SERVICE_URL)
    }
    return jsonify(services)

def check_service_health(service_url):
    try:
        response = requests.get(f'{service_url}/health', timeout=5)
        return 'healthy' if response.status_code == 200 else 'unhealthy'
    except:
        return 'unhealthy'

@app.route('/api/login', methods=['POST'])
def login():
    try:
        response = requests.post(f'{SESSION_SERVICE_URL}/login', json=request.json)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create_group', methods=['POST'])
def create_group():
    try:
        response = requests.post(f'{GROUP_SERVICE_URL}/create_group', json=request.json)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/join_group', methods=['POST'])
def join_group():
    try:
        response = requests.post(f'{GROUP_SERVICE_URL}/join_group', json=request.json)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/groups/<user_id>')
def get_groups(user_id):
    try:
        response = requests.get(f'{GROUP_SERVICE_URL}/user_groups/{user_id}')
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/group_members/<group_id>')
def get_group_members(group_id):
    try:
        response = requests.get(f'{GROUP_SERVICE_URL}/group_members/{group_id}')
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users')
def get_users():
    try:
        response = requests.get(f'{SESSION_SERVICE_URL}/users')
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/direct_chat', methods=['POST'])
def create_direct_chat():
    try:
        response = requests.post(f'{GROUP_SERVICE_URL}/direct_chat', json=request.json)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/messages', methods=['POST'])
def send_message():
    try:
        response = requests.post(f'{MESSAGING_SERVICE_URL}/send_message', json=request.json)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/messages/<room_id>')
def get_messages(room_id):
    try:
        response = requests.get(f'{MESSAGING_SERVICE_URL}/get_messages/{room_id}')
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_message_status', methods=['POST'])
def update_message_status():
    try:
        response = requests.post(f'{MESSAGING_SERVICE_URL}/update_message_status', json=request.json)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
