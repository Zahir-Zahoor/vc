from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import redis
import json
import logging
import requests
import os
from kafka import KafkaConsumer
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

MESSAGING_SERVICE_URL = os.getenv('MESSAGING_SERVICE_URL', 'http://messaging-service:5000')
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')

try:
    redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
    redis_client.ping()
    print("✅ Connected to Redis")
except:
    print("❌ Redis connection failed, using in-memory storage")
    redis_client = None

# In-memory storage as fallback
rooms = {}
user_sockets = {}

def process_redis_notifications():
    """Redis subscriber for user notifications"""
    if not redis_client:
        print("❌ Redis not available, notifications disabled")
        return
        
    max_retries = 10
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            pubsub = redis_client.pubsub()
            pubsub.psubscribe('user_notifications:*')
            print("✅ Redis notification subscriber connected")
            
            for message in pubsub.listen():
                try:
                    if message['type'] == 'pmessage':
                        channel = message['channel']
                        user_id = channel.split(':')[1]  # Extract user_id from channel
                        notification_data = json.loads(message['data'])
                        
                        print(f"📢 Sending notification to user {user_id}: {notification_data['message']}")
                        
                        # Send notification to specific user if they're connected
                        if user_id in user_sockets:
                            socketio.emit('notification', notification_data, room=user_sockets[user_id])
                        
                except Exception as e:
                    print(f"❌ Error processing notification: {e}")
                    
        except Exception as e:
            retry_count += 1
            print(f"❌ Redis notification subscriber connection attempt {retry_count}/{max_retries} failed: {e}")
            time.sleep(5)
    
    print("❌ Failed to connect Redis notification subscriber after all retries")

def process_websocket_delivery():
    """Kafka consumer for real-time message delivery"""
    max_retries = 10
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            consumer = KafkaConsumer(
                'websocket-delivery',
                bootstrap_servers=[KAFKA_BOOTSTRAP_SERVERS],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='websocket-service'
            )
            print("✅ WebSocket Kafka consumer connected")
            
            for message in consumer:
                try:
                    msg_data = message.value
                    room_id = str(msg_data['room_id'])
                    
                    print(f"📤 Delivering message to room {room_id}")
                    
                    # Emit to all users in room
                    socketio.emit('receive_message', {
                        'room_id': room_id,
                        'user_id': msg_data['user_id'],
                        'message': msg_data['message'],
                        'timestamp': msg_data['timestamp'],
                        'delivery_status': msg_data['delivery_status']
                    }, room=room_id)
                    
                except Exception as e:
                    print(f"❌ Error delivering message: {e}")
                    
        except Exception as e:
            retry_count += 1
            print(f"❌ WebSocket Kafka consumer connection attempt {retry_count}/{max_retries} failed: {e}")
            time.sleep(5)
    
    print("❌ Failed to connect WebSocket Kafka consumer after all retries")

# Start Kafka consumer in background thread
delivery_thread = threading.Thread(target=process_websocket_delivery, daemon=True)
delivery_thread.start()

# Start Redis notification subscriber in background thread
notification_thread = threading.Thread(target=process_redis_notifications, daemon=True)
notification_thread.start()

@app.route('/health')
def health():
    return {'status': 'healthy'}

@socketio.on('connect')
def on_connect():
    print(f'Client connected: {request.sid}')
    emit('connected', {'status': 'connected'})

@socketio.on('register_user')
def on_register_user(data):
    user_id = data['user_id']
    user_sockets[user_id] = request.sid
    print(f'User {user_id} registered for notifications with socket {request.sid}')
    
    if redis_client:
        try:
            redis_client.hset(f'user:{user_id}', 'socket_id', request.sid)
        except:
            pass

@socketio.on('disconnect')
def on_disconnect():
    print(f'Client disconnected: {request.sid}')
    # Remove user from socket mapping
    for user_id, socket_id in list(user_sockets.items()):
        if socket_id == request.sid:
            del user_sockets[user_id]
            break

@socketio.on('join_room')
def on_join_room(data):
    room_id = str(data['room_id'])
    user_id = data['user_id']
    
    join_room(room_id)
    user_sockets[user_id] = request.sid
    
    if redis_client:
        try:
            redis_client.sadd(f'room:{room_id}:users', user_id)
            redis_client.hset(f'user:{user_id}', 'socket_id', request.sid)
            redis_client.hset(f'user:{user_id}', 'room_id', room_id)
        except:
            pass
    else:
        if room_id not in rooms:
            rooms[room_id] = set()
        rooms[room_id].add(user_id)
    
    print(f'{user_id} joined room {room_id}')
    emit('room_joined', {'room_id': room_id, 'user_id': user_id})
    
    # When user joins room, mark all their unread messages in this room as read
    # and notify senders about read receipts
    try:
        # Get all messages in this room that were sent by others
        response = requests.get(f'{MESSAGING_SERVICE_URL}/get_messages/{room_id}')
        if response.status_code == 200:
            messages = response.json()
            for msg in messages:
                if msg['user_id'] != user_id and msg.get('delivery_status') != 'read':
                    # Update message status to read
                    requests.post(f'{MESSAGING_SERVICE_URL}/update_message_status', 
                                json={'timestamp': msg['timestamp'], 'status': 'read'})
                    
                    # Notify sender about read receipt
                    emit('message_status_update', {
                        'timestamp': msg['timestamp'],
                        'status': 'read',
                        'read_by': user_id
                    }, room=room_id)
                    
                    print(f'📖 Marked message {msg["timestamp"]} as read by {user_id}')
    except Exception as e:
        print(f'Error updating read receipts on join: {e}')

@socketio.on('send_message')
def on_send_message(data):
    room_id = str(data['room_id'])
    user_id = data['user_id']
    message = data['message']
    timestamp = data['timestamp']
    reply_to = data.get('reply_to')  # Optional reply data
    
    print(f'📨 Received message from {user_id} for room {room_id}')
    
    # Store message in database first
    try:
        response = requests.post(f'{MESSAGING_SERVICE_URL}/send_message', json={
            'room_id': room_id,
            'user_id': user_id,
            'message': message,
            'timestamp': timestamp,
            'reply_to': reply_to
        })
        
        if response.status_code == 200:
            print(f'✅ Message stored in database')
            
            # Emit directly to room instead of using Kafka
            socketio.emit('receive_message', {
                'room_id': room_id,
                'user_id': user_id,
                'message': message,
                'timestamp': timestamp,
                'delivery_status': 'delivered',
                'reply_to': reply_to
            }, room=room_id)
            
            print(f'📤 Message delivered to room {room_id}')
            
        else:
            print(f'❌ Failed to store message: {response.status_code}')
            
    except Exception as e:
        print(f'❌ Error sending message: {e}')

@socketio.on('message_read')
def on_message_read(data):
    room_id = str(data['room_id'])
    timestamp = data['timestamp']
    user_id = data['user_id']
    
    print(f'📖 Message read by {user_id} in room {room_id}, timestamp: {timestamp}')
    
    # Update message status in database
    try:
        response = requests.post(f'{MESSAGING_SERVICE_URL}/update_message_status', 
                               json={'timestamp': timestamp, 'status': 'read'})
        if response.status_code == 200:
            print(f'✅ Message status updated to read in database')
        else:
            print(f'❌ Failed to update message status: {response.status_code}')
    except Exception as e:
        print(f'❌ Error updating message status: {e}')
    
    # Notify all users in room about read status (including sender)
    emit('message_status_update', {
        'timestamp': timestamp,
        'status': 'read',
        'read_by': user_id
    }, room=room_id)
    
    print(f'📤 Read receipt sent to room {room_id}')

@socketio.on('typing_start')
def on_typing_start(data):
    room_id = str(data['room_id'])
    user_id = data['user_id']
    
    emit('user_typing', {
        'user_id': user_id,
        'room_id': room_id,
        'typing': True
    }, room=room_id)

@socketio.on('typing_stop')
def on_typing_stop(data):
    room_id = str(data['room_id'])
    user_id = data['user_id']
    
    emit('user_typing', {
        'user_id': user_id,
        'room_id': room_id,
        'typing': False
    }, room=room_id)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
