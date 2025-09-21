from flask import Flask, render_template, request, jsonify
import requests
import os
import jwt

app = Flask(__name__)

# Service URLs
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth-service:5000')
USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://user-service:5000')
GROUP_SERVICE_URL = os.getenv('GROUP_SERVICE_URL', 'http://group-service:5000')
SESSION_SERVICE_URL = os.getenv('SESSION_SERVICE_URL', 'http://session-service:5000')
MESSAGING_SERVICE_URL = os.getenv('MESSAGING_SERVICE_URL', 'http://messaging-service:5000')
WEBSOCKET_SERVICE_URL = os.getenv('WEBSOCKET_SERVICE_URL', 'http://websocket-service:5000')

JWT_SECRET = os.getenv('JWT_SECRET', 'your-super-secret-jwt-key-change-in-production')

def get_user_from_token(token):
    """Extract user info from JWT token"""
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload.get('user_id'), payload.get('email')
    except:
        return None, None

def check_service_health(service_url):
    try:
        response = requests.get(f'{service_url}/health', timeout=5)
        return 'healthy' if response.status_code == 200 else 'unhealthy'
    except:
        return 'unhealthy'

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/health')
def health():
    services = {
        'auth': check_service_health(AUTH_SERVICE_URL),
        'user': check_service_health(USER_SERVICE_URL),
        'websocket': check_service_health(WEBSOCKET_SERVICE_URL),
        'messaging': check_service_health(MESSAGING_SERVICE_URL),
        'group': check_service_health(GROUP_SERVICE_URL),
        'session': check_service_health(SESSION_SERVICE_URL)
    }
    return jsonify(services)

# Authentication endpoints
@app.route('/api/register', methods=['POST'])
def register():
    try:
        response = requests.post(f'{AUTH_SERVICE_URL}/register', json=request.json)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        response = requests.post(f'{AUTH_SERVICE_URL}/login', json=request.json)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        headers = {'Authorization': request.headers.get('Authorization', '')}
        response = requests.post(f'{AUTH_SERVICE_URL}/logout', headers=headers)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify_token', methods=['POST'])
def verify_token():
    try:
        headers = {'Authorization': request.headers.get('Authorization', '')}
        response = requests.post(f'{AUTH_SERVICE_URL}/verify_token', headers=headers)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# User management endpoints
@app.route('/api/search_users')
def search_users():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id, _ = get_user_from_token(token)
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
            
        headers = {'X-User-ID': user_id}
        response = requests.get(f'{USER_SERVICE_URL}/search_users', 
                              params=request.args, headers=headers)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invite_user', methods=['POST'])
def invite_user():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id, _ = get_user_from_token(token)
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
            
        headers = {'X-User-ID': user_id}
        response = requests.post(f'{USER_SERVICE_URL}/invite_user', 
                               json=request.json, headers=headers)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accept_invite', methods=['POST'])
def accept_invite():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id, _ = get_user_from_token(token)
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
            
        headers = {'X-User-ID': user_id}
        response = requests.post(f'{USER_SERVICE_URL}/accept_invite', 
                               json=request.json, headers=headers)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contacts')
def get_contacts():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id, _ = get_user_from_token(token)
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
            
        headers = {'X-User-ID': user_id}
        response = requests.get(f'{USER_SERVICE_URL}/contacts', headers=headers)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invites')
def get_invites():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id, _ = get_user_from_token(token)
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
            
        headers = {'X-User-ID': user_id}
        response = requests.get(f'{USER_SERVICE_URL}/invites', 
                              params=request.args, headers=headers)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Legacy endpoints (keeping for backward compatibility)
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

@app.route('/api/users')
def get_users():
    try:
        response = requests.get(f'{AUTH_SERVICE_URL}/users')
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user_status/<user_id>')
def get_user_status(user_id):
    try:
        response = requests.get(f'{USER_SERVICE_URL}/user_status/{user_id}')
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent_chats')
def get_recent_chats():
    try:
        token = request.headers.get('Authorization')
        user_id, email = get_user_from_token(token)
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401
            
        response = requests.get(f'{MESSAGING_SERVICE_URL}/recent_chats/{user_id}')
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

@app.route('/api/mark_read', methods=['POST'])
def mark_read():
    try:
        response = requests.post(f'{MESSAGING_SERVICE_URL}/mark_read', json=request.json)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/unread_counts/<user_id>')
def get_unread_counts(user_id):
    try:
        response = requests.get(f'{MESSAGING_SERVICE_URL}/unread_counts/{user_id}')
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
