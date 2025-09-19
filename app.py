from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os
import redis
import json
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chatapp_secret_key_2024')

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["500 per day", "100 per hour"]
)
limiter.init_app(app)

# Redis connection
def connect_redis():
    try:
        redis_client = redis.Redis(
            host=os.environ.get('REDIS_HOST', 'localhost'),
            port=int(os.environ.get('REDIS_PORT', 6379)),
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
            retry_on_timeout=True
        )
        redis_client.ping()
        logger.info("Connected to Redis")
        return redis_client, True
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        return None, False

redis_client, USE_REDIS = connect_redis()
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory storage
users = {}
rooms = {}
active_calls = {}

class ChatStore:
    @staticmethod
    def set_user(sid, data):
        if USE_REDIS:
            redis_client.hset(f"user:{sid}", mapping=data)
            redis_client.expire(f"user:{sid}", 7200)
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
            redis_client.expire(f"room:{room}", 7200)
        else:
            if room not in rooms:
                rooms[room] = set()
            rooms[room].add(sid)
    
    @staticmethod
    def remove_from_room(room, sid):
        if USE_REDIS:
            redis_client.srem(f"room:{room}", sid)
        else:
            if room in rooms:
                rooms[room].discard(sid)
                if not rooms[room]:
                    del rooms[room]
    
    @staticmethod
    def get_room_users(room):
        if USE_REDIS:
            return list(redis_client.smembers(f"room:{room}"))
        else:
            return list(rooms.get(room, set()))

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'redis': USE_REDIS,
        'active_users': len(users) if not USE_REDIS else 'redis'
    })

@socketio.on('connect')
def on_connect():
    logger.info(f'User {request.sid} connected')

@socketio.on('disconnect')
def on_disconnect():
    user_data = ChatStore.get_user(request.sid)
    
    if user_data:
        room = user_data.get('room')
        username = user_data.get('username')
        
        ChatStore.remove_from_room(room, request.sid)
        ChatStore.delete_user(request.sid)
        
        # End any active calls
        if request.sid in active_calls:
            call_partner = active_calls[request.sid]
            emit('call_ended', room=call_partner)
            active_calls.pop(request.sid, None)
            active_calls.pop(call_partner, None)
        
        # Notify room
        emit('user_left', {
            'user': username,
            'sid': request.sid,
            'timestamp': datetime.now().isoformat()
        }, room=room)
        
        logger.info(f'User {username} left room {room}')

@socketio.on('join_room')
@limiter.limit("10 per minute")
def on_join_room(data):
    try:
        room = data.get('room', '').strip()
        username = data.get('username', '').strip()
        
        if not room or not username:
            emit('error', {'message': 'Room and username required'})
            return
        
        if len(username) > 50 or len(room) > 50:
            emit('error', {'message': 'Username and room name too long'})
            return
        
        # Check room capacity
        current_users = ChatStore.get_room_users(room)
        if len(current_users) >= 100:
            emit('error', {'message': 'Room is full'})
            return
        
        user_data = {
            'username': username,
            'room': room,
            'joined_at': datetime.now().isoformat(),
            'status': 'online'
        }
        
        join_room(room)
        ChatStore.set_user(request.sid, user_data)
        ChatStore.add_to_room(room, request.sid)
        
        # Success response
        emit('room_joined', {
            'room': room,
            'username': username,
            'users_count': len(ChatStore.get_room_users(room))
        })
        
        # Notify others
        emit('user_joined', {
            'user': username,
            'sid': request.sid,
            'timestamp': datetime.now().isoformat()
        }, room=room, include_self=False)
        
        logger.info(f'User {username} joined room {room}')
        
    except Exception as e:
        logger.error(f'Error in join_room: {str(e)}')
        emit('error', {'message': 'Failed to join room'})

@socketio.on('send_message')
@limiter.limit("60 per minute")
def handle_message(data):
    try:
        user_data = ChatStore.get_user(request.sid)
        if not user_data:
            emit('error', {'message': 'Not in any room'})
            return
        
        message = data.get('message', '').strip()
        if not message or len(message) > 2000:
            emit('error', {'message': 'Invalid message'})
            return
        
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

# WebRTC Call Signaling
@socketio.on('call_offer')
def handle_call_offer(data):
    try:
        user_data = ChatStore.get_user(request.sid)
        if not user_data:
            return
        
        offer = data.get('offer')
        call_type = data.get('type', 'audio')
        room = data.get('room') or user_data.get('room')
        
        if not offer or not room:
            return
        
        # Send offer to all other users in room
        emit('call_offer', {
            'from': request.sid,
            'username': user_data['username'],
            'offer': offer,
            'type': call_type,
            'timestamp': datetime.now().isoformat()
        }, room=room, include_self=False)
        
        logger.info(f'Call offer from {user_data["username"]} ({call_type}) in room {room}')
        
    except Exception as e:
        logger.error(f'Error handling call offer: {e}')

@socketio.on('call_answer')
def handle_call_answer(data):
    try:
        target_sid = data.get('target')
        answer = data.get('answer')
        room = data.get('room')
        
        if not target_sid or not answer:
            return
        
        # Send answer to the specific target
        emit('call_answer', {
            'from': request.sid,
            'answer': answer,
            'timestamp': datetime.now().isoformat()
        }, room=target_sid)
        
        logger.info(f'Call answer from {request.sid} to {target_sid}')
        
    except Exception as e:
        logger.error(f'Error handling call answer: {e}')

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    try:
        candidate = data.get('candidate')
        room = data.get('room')
        
        if not candidate or not room:
            return
        
        user_data = ChatStore.get_user(request.sid)
        if not user_data:
            return
        
        # Send ICE candidate to all other users in room
        emit('ice_candidate', {
            'from': request.sid,
            'candidate': candidate
        }, room=room, include_self=False)
        
    except Exception as e:
        logger.error(f'Error handling ICE candidate: {e}')

@socketio.on('call_ended')
def handle_call_ended():
    try:
        if request.sid in active_calls:
            partner_sid = active_calls[request.sid]
            
            # Clean up call state
            active_calls.pop(request.sid, None)
            if partner_sid != 'pending':
                active_calls.pop(partner_sid, None)
                emit('call_ended', room=partner_sid)
        
        logger.info(f'Call ended by {request.sid}')
        
    except Exception as e:
        logger.error(f'Error handling call end: {e}')

@socketio.on('call_declined')
def handle_call_declined(data):
    try:
        target_sid = data.get('to')
        if target_sid:
            emit('call_declined', room=target_sid)
            active_calls.pop(target_sid, None)
        
    except Exception as e:
        logger.error(f'Error handling call decline: {e}')

# Status updates
@socketio.on('typing_start')
def handle_typing_start():
    user_data = ChatStore.get_user(request.sid)
    if user_data:
        emit('user_typing', {
            'user': user_data['username'],
            'typing': True
        }, room=user_data['room'], include_self=False)

@socketio.on('typing_stop')
def handle_typing_stop():
    user_data = ChatStore.get_user(request.sid)
    if user_data:
        emit('user_typing', {
            'user': user_data['username'],
            'typing': False
        }, room=user_data['room'], include_self=False)

@socketio.on_error_default
def default_error_handler(e):
    logger.error(f'SocketIO error: {str(e)}')
    emit('error', {'message': 'An error occurred'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f'Starting ChatApp server on port {port}')
    logger.info(f'Redis enabled: {USE_REDIS}')
    
    socketio.run(
        app, 
        debug=debug, 
        host='0.0.0.0', 
        port=port,
        allow_unsafe_werkzeug=True
    )
