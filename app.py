from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os
import redis
import json
from datetime import datetime, timedelta
import uuid
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'videochat_production_secret_key_2024')

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
limiter.init_app(app)

# Redis connection with retry logic
def connect_redis():
    import time
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            redis_client = redis.Redis(
                host=os.environ.get('REDIS_HOST', 'localhost'),
                port=int(os.environ.get('REDIS_PORT', 6379)),
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                retry_on_timeout=True,
                health_check_interval=30
            )
            redis_client.ping()
            logger.info(f"Connected to Redis at {redis_client.connection_pool.connection_kwargs['host']}:{redis_client.connection_pool.connection_kwargs['port']}")
            return redis_client, True
        except Exception as e:
            logger.warning(f"Redis connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            
    logger.error("Failed to connect to Redis, using in-memory storage")
    return None, False

redis_client, USE_REDIS = connect_redis()

socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# In-memory fallback storage
users = {}
rooms = {}
active_connections = set()

class DataStore:
    @staticmethod
    def set_user(sid, data):
        if USE_REDIS:
            redis_client.hset(f"user:{sid}", mapping=data)
            redis_client.expire(f"user:{sid}", 3600)  # 1 hour expiry
        else:
            users[sid] = data
    
    @staticmethod
    def get_user(sid):
        if USE_REDIS:
            data = redis_client.hgetall(f"user:{sid}")
            return data if data else None
        else:
            return users.get(sid)
    
    @staticmethod
    def delete_user(sid):
        if USE_REDIS:
            redis_client.delete(f"user:{sid}")
        else:
            users.pop(sid, None)
    
    @staticmethod
    def add_to_room(room, sid):
        if USE_REDIS:
            redis_client.sadd(f"room:{room}", sid)
            redis_client.expire(f"room:{room}", 3600)
        else:
            if room not in rooms:
                rooms[room] = []
            if sid not in rooms[room]:
                rooms[room].append(sid)
    
    @staticmethod
    def remove_from_room(room, sid):
        if USE_REDIS:
            redis_client.srem(f"room:{room}", sid)
        else:
            if room in rooms and sid in rooms[room]:
                rooms[room].remove(sid)
                if not rooms[room]:
                    del rooms[room]
    
    @staticmethod
    def get_room_users(room):
        if USE_REDIS:
            return list(redis_client.smembers(f"room:{room}"))
        else:
            return rooms.get(room, [])
    
    @staticmethod
    def add_connection(sid):
        if USE_REDIS:
            redis_client.sadd("active_connections", sid)
        else:
            active_connections.add(sid)
    
    @staticmethod
    def remove_connection(sid):
        if USE_REDIS:
            redis_client.srem("active_connections", sid)
        else:
            active_connections.discard(sid)
    
    @staticmethod
    def is_connected(sid):
        if USE_REDIS:
            return redis_client.sismember("active_connections", sid)
        else:
            return sid in active_connections

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    return render_template('test.html')

@app.route('/health')
def health_check():
    redis_status = 'disconnected'
    redis_info = None
    
    if USE_REDIS and redis_client:
        try:
            redis_client.ping()
            redis_status = 'connected'
            redis_info = {
                'host': os.environ.get('REDIS_HOST', 'localhost'),
                'port': int(os.environ.get('REDIS_PORT', 6379)),
                'memory_usage': redis_client.info('memory').get('used_memory_human', 'unknown')
            }
        except:
            redis_status = 'error'
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'redis': {
            'enabled': USE_REDIS,
            'status': redis_status,
            'info': redis_info
        },
        'connections': len(active_connections) if not USE_REDIS else (redis_client.scard("active_connections") if redis_client else 0)
    })

@app.route('/api/room/<room_id>/info')
@limiter.limit("10 per minute")
def room_info(room_id):
    users_in_room = DataStore.get_room_users(room_id)
    user_details = []
    for sid in users_in_room:
        user_data = DataStore.get_user(sid)
        if user_data:
            user_details.append({
                'username': user_data.get('username'),
                'joined_at': user_data.get('joined_at')
            })
    
    return jsonify({
        'room_id': room_id,
        'participant_count': len(users_in_room),
        'participants': user_details
    })

@socketio.on('connect')
def on_connect():
    DataStore.add_connection(request.sid)
    logger.info(f'User {request.sid} connected')
    emit('connection_status', {
        'status': 'connected', 
        'id': request.sid,
        'server_time': datetime.now().isoformat()
    })

@socketio.on('disconnect')
def on_disconnect():
    DataStore.remove_connection(request.sid)
    user_data = DataStore.get_user(request.sid)
    
    if user_data:
        room = user_data.get('room')
        username = user_data.get('username')
        
        DataStore.remove_from_room(room, request.sid)
        DataStore.delete_user(request.sid)
        
        # Notify room
        emit('user_left', {
            'user': username,
            'sid': request.sid,
            'timestamp': datetime.now().isoformat()
        }, room=room)
        
        # Update room count
        remaining_users = DataStore.get_room_users(room)
        emit('room_users_updated', {
            'count': len(remaining_users)
        }, room=room)
        
        logger.info(f'User {username} left room {room}')

@socketio.on('join_room')
@limiter.limit("5 per minute")
def on_join_room(data):
    try:
        room = data.get('room', '').strip()
        username = data.get('username', '').strip()
        
        logger.info(f'JOIN_ROOM received: username={username}, room={room}, sid={request.sid}')
        
        # Enhanced validation
        if not room or not username:
            logger.warning(f'Invalid join_room data: {data}')
            emit('error', {'message': 'Room name and username are required'})
            return
        
        if len(username) > 50 or len(room) > 50:
            emit('error', {'message': 'Username and room name must be less than 50 characters'})
            return
        
        if len(username) < 2:
            emit('error', {'message': 'Username must be at least 2 characters'})
            return
        
        # Check room capacity (max 50 users)
        current_users = DataStore.get_room_users(room)
        if len(current_users) >= 50:
            emit('error', {'message': 'Room is full (maximum 50 participants)'})
            return
        
        # Generate user session
        session_id = str(uuid.uuid4())
        user_data = {
            'username': username,
            'room': room,
            'joined_at': datetime.now().isoformat(),
            'session_id': session_id
        }
        
        join_room(room)
        DataStore.set_user(request.sid, user_data)
        DataStore.add_to_room(room, request.sid)
        
        logger.info(f'User {username} successfully joined room {room}')
        
        # Success response
        emit('room_joined', {
            'room': room,
            'username': username,
            'session_id': session_id,
            'participant_count': len(DataStore.get_room_users(room))
        })
        
        # Notify others
        emit('user_joined', {
            'user': username,
            'sid': request.sid,
            'timestamp': datetime.now().isoformat()
        }, room=room, include_self=False)
        
        logger.info(f'Notified room {room} about new user {username}')
        
    except Exception as e:
        logger.error(f'Error in join_room: {str(e)}')
        emit('error', {'message': 'Failed to join room'})

@socketio.on('send_message')
@limiter.limit("30 per minute")
def handle_message(data):
    try:
        user_data = DataStore.get_user(request.sid)
        if not user_data:
            emit('error', {'message': 'User not in any room'})
            return
        
        message = data.get('message', '').strip()
        if not message or len(message) > 1000:
            emit('error', {'message': 'Invalid message length'})
            return
        
        # Message with enhanced data
        message_data = {
            'id': str(uuid.uuid4()),
            'username': user_data['username'],
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'sid': request.sid
        }
        
        emit('receive_message', message_data, room=user_data['room'])
        logger.info(f'Message from {user_data["username"]}: {message[:50]}...')
        
    except Exception as e:
        logger.error(f'Error handling message: {e}')
        emit('error', {'message': 'Failed to send message'})

# Enhanced WebRTC signaling with validation
@socketio.on('offer')
def handle_offer(data):
    try:
        target_sid = data.get('target')
        if not target_sid or not DataStore.is_connected(target_sid):
            emit('error', {'message': 'Target user not available'})
            return
        
        emit('offer', {
            'from': request.sid,
            'offer': data['offer'],
            'timestamp': datetime.now().isoformat()
        }, room=target_sid)
        
    except Exception as e:
        logger.error(f'Error handling offer: {e}')

@socketio.on('answer')
def handle_answer(data):
    try:
        target_sid = data.get('target')
        if not target_sid or not DataStore.is_connected(target_sid):
            return
        
        emit('answer', {
            'from': request.sid,
            'answer': data['answer'],
            'timestamp': datetime.now().isoformat()
        }, room=target_sid)
        
    except Exception as e:
        logger.error(f'Error handling answer: {e}')

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    try:
        target_sid = data.get('target')
        if not target_sid or not DataStore.is_connected(target_sid):
            return
        
        emit('ice_candidate', {
            'from': request.sid,
            'candidate': data['candidate']
        }, room=target_sid)
        
    except Exception as e:
        logger.error(f'Error handling ICE candidate: {e}')

@socketio.on('video_started')
def handle_video_started():
    logger.info(f'VIDEO_STARTED received from {request.sid}')
    user_data = DataStore.get_user(request.sid)
    if user_data:
        logger.info(f'Notifying room {user_data["room"]} that {user_data["username"]} started video')
        emit('user_video_started', {
            'user': user_data['username'],
            'sid': request.sid,
            'timestamp': datetime.now().isoformat()
        }, room=user_data['room'], include_self=False)
    else:
        logger.warning(f'video_started from unknown user: {request.sid}')

@socketio.on('video_stopped')
def handle_video_stopped():
    logger.info(f'VIDEO_STOPPED received from {request.sid}')
    user_data = DataStore.get_user(request.sid)
    if user_data:
        logger.info(f'Notifying room {user_data["room"]} that {user_data["username"]} stopped video')
        emit('user_video_stopped', {
            'user': user_data['username'],
            'sid': request.sid,
            'timestamp': datetime.now().isoformat()
        }, room=user_data['room'], include_self=False)
    else:
        logger.warning(f'video_stopped from unknown user: {request.sid}')

@socketio.on('typing_start')
def handle_typing_start():
    user_data = DataStore.get_user(request.sid)
    if user_data:
        emit('user_typing', {
            'user': user_data['username'],
            'typing': True
        }, room=user_data['room'], include_self=False)

@socketio.on('typing_stop')
def handle_typing_stop():
    user_data = DataStore.get_user(request.sid)
    if user_data:
        emit('user_typing', {
            'user': user_data['username'],
            'typing': False
        }, room=user_data['room'], include_self=False)

@socketio.on('ping')
def handle_ping(data):
    emit('pong', {'timestamp': datetime.now().isoformat()})

@socketio.on_error_default
def default_error_handler(e):
    logger.error(f'SocketIO error: {str(e)}')
    emit('error', {'message': 'An unexpected error occurred'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f'Starting Enhanced VideoChat server on port {port}')
    logger.info(f'Redis enabled: {USE_REDIS}')
    
    socketio.run(
        app, 
        debug=debug, 
        host='0.0.0.0', 
        port=port,
        allow_unsafe_werkzeug=True
    )
