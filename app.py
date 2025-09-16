from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'videochat_production_secret_key_2024')
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Store user and room data
users = {}
rooms = {}
active_connections = set()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

@socketio.on('connect')
def on_connect():
    active_connections.add(request.sid)
    logger.info(f'User {request.sid} connected. Total connections: {len(active_connections)}')
    emit('connection_status', {'status': 'connected', 'id': request.sid})

@socketio.on('disconnect')
def on_disconnect():
    active_connections.discard(request.sid)
    logger.info(f'User {request.sid} disconnected. Total connections: {len(active_connections)}')
    
    if request.sid in users:
        user_data = users[request.sid]
        room = user_data['room']
        username = user_data['username']
        
        # Remove user from room
        if room in rooms and request.sid in rooms[room]:
            rooms[room].remove(request.sid)
            if not rooms[room]:  # Remove empty room
                del rooms[room]
        
        # Notify other users
        emit('user_left', {
            'user': username,
            'sid': request.sid,
            'timestamp': datetime.now().isoformat()
        }, room=room)
        
        # Update room user count
        if room in rooms:
            emit('room_users', {
                'users': [users[sid]['username'] for sid in rooms[room] if sid in users],
                'count': len(rooms[room])
            }, room=room)
        
        del users[request.sid]
        logger.info(f'User {username} left room {room}')

@socketio.on('join_room')
def on_join_room(data):
    try:
        room = data.get('room', '').strip()
        username = data.get('username', '').strip()
        
        if not room or not username:
            emit('error', {'message': 'Room name and username are required'})
            return
        
        # Validate input lengths
        if len(username) > 50 or len(room) > 50:
            emit('error', {'message': 'Username and room name must be less than 50 characters'})
            return
        
        join_room(room)
        users[request.sid] = {
            'username': username,
            'room': room,
            'joined_at': datetime.now().isoformat()
        }
        
        if room not in rooms:
            rooms[room] = []
        rooms[room].append(request.sid)
        
        # Notify room about new user
        emit('user_joined', {
            'user': username,
            'sid': request.sid,
            'timestamp': datetime.now().isoformat()
        }, room=room)
        
        # Send current room users to new user
        emit('room_users', {
            'users': [users[sid]['username'] for sid in rooms[room] if sid in users],
            'count': len(rooms[room])
        }, room=room)
        
        logger.info(f'User {username} joined room {room}. Room size: {len(rooms[room])}')
        
    except Exception as e:
        logger.error(f'Error in join_room: {str(e)}')
        emit('error', {'message': 'Failed to join room'})

@socketio.on('send_message')
def handle_message(data):
    try:
        if request.sid not in users:
            emit('error', {'message': 'User not in any room'})
            return
        
        message = data.get('message', '').strip()
        if not message:
            return
        
        # Validate message length
        if len(message) > 1000:
            emit('error', {'message': 'Message too long (max 1000 characters)'})
            return
        
        user_data = users[request.sid]
        room = user_data['room']
        username = user_data['username']
        
        message_data = {
            'username': username,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'sid': request.sid
        }
        
        emit('receive_message', message_data, room=room)
        logger.info(f'Message from {username} in room {room}: {message[:50]}...')
        
    except Exception as e:
        logger.error(f'Error in send_message: {str(e)}')
        emit('error', {'message': 'Failed to send message'})

@socketio.on('typing_start')
def handle_typing_start():
    if request.sid in users:
        user_data = users[request.sid]
        emit('user_typing', {
            'user': user_data['username'],
            'typing': True
        }, room=user_data['room'], include_self=False)

@socketio.on('typing_stop')
def handle_typing_stop():
    if request.sid in users:
        user_data = users[request.sid]
        emit('user_typing', {
            'user': user_data['username'],
            'typing': False
        }, room=user_data['room'], include_self=False)

# WebRTC signaling events
@socketio.on('offer')
def handle_offer(data):
    try:
        target_sid = data.get('target')
        if target_sid and target_sid in active_connections:
            emit('offer', {
                'offer': data.get('offer'),
                'from': request.sid
            }, room=target_sid)
    except Exception as e:
        logger.error(f'Error in offer: {str(e)}')

@socketio.on('answer')
def handle_answer(data):
    try:
        target_sid = data.get('target')
        if target_sid and target_sid in active_connections:
            emit('answer', {
                'answer': data.get('answer'),
                'from': request.sid
            }, room=target_sid)
    except Exception as e:
        logger.error(f'Error in answer: {str(e)}')

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    try:
        target_sid = data.get('target')
        if target_sid and target_sid in active_connections:
            emit('ice_candidate', {
                'candidate': data.get('candidate'),
                'from': request.sid
            }, room=target_sid)
    except Exception as e:
        logger.error(f'Error in ice_candidate: {str(e)}')

@socketio.on('video_started')
def handle_video_started(data):
    if request.sid in users:
        user_data = users[request.sid]
        emit('user_video_started', {
            'user': user_data['username'],
            'sid': request.sid
        }, room=user_data['room'], include_self=False)

@socketio.on('video_stopped')
def handle_video_stopped(data):
    if request.sid in users:
        user_data = users[request.sid]
        emit('user_video_stopped', {
            'user': user_data['username'],
            'sid': request.sid
        }, room=user_data['room'], include_self=False)

@socketio.on_error_default
def default_error_handler(e):
    logger.error(f'SocketIO error: {str(e)}')
    emit('error', {'message': 'An unexpected error occurred'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    logger.info(f'Starting VideoChat server on port {port}')
    socketio.run(
        app, 
        debug=debug, 
        host='0.0.0.0', 
        port=port,
        allow_unsafe_werkzeug=True
    )
