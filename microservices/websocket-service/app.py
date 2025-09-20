from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import redis
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'websocket-secret'
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")
    emit('connected', {'status': 'success'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

@socketio.on('join_room')
def handle_join_room(data):
    print(f"Join room event: {data}")
    room_id = str(data['room_id'])
    user_id = data['user_id']
    join_room(room_id)
    print(f"User {user_id} joined room {room_id}")
    emit('room_joined', {'room_id': room_id, 'user_id': user_id}, room=room_id)

@socketio.on('send_message')
def handle_message(data):
    print(f"Message event: {data}")
    room_id = str(data['room_id'])
    user_id = data['user_id']
    message = data['message']
    timestamp = data.get('timestamp')
    
    # Broadcast message to all users in the room
    emit('receive_message', {
        'user_id': user_id,
        'message': message,
        'timestamp': timestamp,
        'room_id': room_id
    }, room=room_id)
    print(f"Message broadcasted to room {room_id}")

@socketio.on('typing_start')
def handle_typing_start(data):
    print(f"Typing start: {data}")
    room_id = str(data['room_id'])
    user_id = data['user_id']
    
    # Broadcast typing indicator to others in room
    emit('user_typing', {
        'user_id': user_id,
        'room_id': room_id,
        'typing': True
    }, room=room_id, include_self=False)

@socketio.on('typing_stop')
def handle_typing_stop(data):
    print(f"Typing stop: {data}")
    room_id = str(data['room_id'])
    user_id = data['user_id']
    
    # Broadcast stop typing to others in room
    emit('user_typing', {
        'user_id': user_id,
        'room_id': room_id,
        'typing': False
    }, room=room_id, include_self=False)

@app.route('/health')
def health():
    return {'status': 'healthy'}

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
