from flask import Flask, request, jsonify, render_template
import requests
import os

app = Flask(__name__)

WEBSOCKET_SERVICE = os.getenv('WEBSOCKET_SERVICE_URL', 'http://localhost:5001')
MESSAGING_SERVICE = os.getenv('MESSAGING_SERVICE_URL', 'http://localhost:5002')
GROUP_SERVICE = os.getenv('GROUP_SERVICE_URL', 'http://localhost:5003')
SESSION_SERVICE = os.getenv('SESSION_SERVICE_URL', 'http://localhost:5004')

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/api/login', methods=['POST'])
def login():
    response = requests.post(f'{SESSION_SERVICE}/login', json=request.json)
    return jsonify(response.json())

@app.route('/api/logout', methods=['POST'])
def logout():
    response = requests.post(f'{SESSION_SERVICE}/logout', json=request.json)
    return jsonify(response.json())

@app.route('/api/create_group', methods=['POST'])
def create_group():
    response = requests.post(f'{GROUP_SERVICE}/create_group', json=request.json)
    return jsonify(response.json())

@app.route('/api/join_group', methods=['POST'])
def join_group():
    response = requests.post(f'{GROUP_SERVICE}/join_group', json=request.json)
    return jsonify(response.json())

@app.route('/api/groups/<user_id>')
def get_groups(user_id):
    response = requests.get(f'{GROUP_SERVICE}/get_groups/{user_id}')
    return jsonify(response.json())

@app.route('/api/users')
def get_users():
    try:
        response = requests.get(f'{SESSION_SERVICE}/users')
        return jsonify(response.json())
    except:
        return jsonify([])

@app.route('/api/direct_chat', methods=['POST'])
def create_direct_chat():
    data = request.json
    user1 = data['user1']
    user2 = data['user2']
    
    # Create deterministic room ID for direct chat
    users = sorted([user1, user2])
    room_id = f"dm_{users[0]}_{users[1]}"
    
    return jsonify({'room_id': room_id, 'type': 'direct'})

@app.route('/api/messages/<room_id>')
def get_messages(room_id):
    try:
        response = requests.get(f'{MESSAGING_SERVICE}/get_messages/{room_id}')
        return jsonify(response.json())
    except:
        return jsonify([])

@app.route('/api/messages', methods=['POST'])
def store_message():
    try:
        response = requests.post(f'{MESSAGING_SERVICE}/send_message', json=request.json)
        return jsonify(response.json())
    except:
        return jsonify({'status': 'error'})

@app.route('/api/status/<user_id>')
def get_status(user_id):
    response = requests.get(f'{SESSION_SERVICE}/status/{user_id}')
    return jsonify(response.json())

@app.route('/health')
def health():
    services = {
        'websocket': f'{WEBSOCKET_SERVICE}/health',
        'messaging': f'{MESSAGING_SERVICE}/health',
        'group': f'{GROUP_SERVICE}/health',
        'session': f'{SESSION_SERVICE}/health'
    }
    
    status = {}
    for service, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            status[service] = 'healthy' if response.status_code == 200 else 'unhealthy'
        except:
            status[service] = 'unhealthy'
    
    return jsonify(status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
