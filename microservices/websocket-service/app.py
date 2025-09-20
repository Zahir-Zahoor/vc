from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import redis
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'websocket-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

@socketio.on('connect')
def handle_connect():
    user_id = request.sid
    redis_client.hset('active_connections', user_id, 'connected')
    emit('connected', {'status': 'success'})

@socketio.on('disconnect')
def handle_disconnect():
    user_id = request.sid
    redis_client.hdel('active_connections', user_id)

@socketio.on('join_room')
def handle_join_room(data):
    room_id = str(data['room_id'])
    user_id = data['user_id']
    join_room(room_id)
    redis_client.sadd(f'room:{room_id}', user_id)
    emit('room_joined', {'room_id': room_id, 'user_id': user_id}, room=room_id)

@socketio.on('send_message')
def handle_message(data):
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

@app.route('/health')
def health():
    return {'status': 'healthy'}

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
