from flask import Flask, request, jsonify
import redis
import json
import os

app = Flask(__name__)
redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    room_id = str(data['room_id'])
    user_id = data['user_id']
    message = data['message']
    timestamp = data.get('timestamp')
    
    # Store message in Redis for history
    message_data = {
        'user_id': user_id,
        'message': message,
        'timestamp': timestamp,
        'room_id': room_id
    }
    
    redis_client.lpush(f'room_messages:{room_id}', json.dumps(message_data))
    redis_client.ltrim(f'room_messages:{room_id}', 0, 99)  # Keep last 100 messages
    
    return jsonify({'status': 'sent'})

@app.route('/get_messages/<room_id>')
def get_messages(room_id):
    messages = redis_client.lrange(f'room_messages:{room_id}', 0, -1)
    return jsonify([json.loads(msg) for msg in reversed(messages)])

@app.route('/health')
def health():
    return {'status': 'healthy'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
