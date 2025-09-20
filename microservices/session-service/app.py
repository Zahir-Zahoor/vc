from flask import Flask, request, jsonify
import redis
import os
import time
import json

app = Flask(__name__)
redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user_id = data['user_id']
    
    session_data = {
        'user_id': user_id,
        'login_time': time.time(),
        'status': 'online'
    }
    
    redis_client.hset('sessions', user_id, json.dumps(session_data))
    redis_client.hset('user_status', user_id, 'online')
    redis_client.hset('last_seen', user_id, time.time())
    
    return jsonify({'status': 'logged_in'})

@app.route('/logout', methods=['POST'])
def logout():
    data = request.json
    user_id = data['user_id']
    
    redis_client.hdel('sessions', user_id)
    redis_client.hset('user_status', user_id, 'offline')
    redis_client.hset('last_seen', user_id, time.time())
    
    return jsonify({'status': 'logged_out'})

@app.route('/status/<user_id>')
def get_status(user_id):
    status = redis_client.hget('user_status', user_id)
    last_seen = redis_client.hget('last_seen', user_id)
    
    return jsonify({
        'user_id': user_id,
        'status': status.decode() if status else 'offline',
        'last_seen': float(last_seen) if last_seen else None
    })

@app.route('/users')
def get_users():
    users = []
    for user_id in redis_client.hkeys('user_status'):
        status = redis_client.hget('user_status', user_id.decode())
        users.append({
            'user_id': user_id.decode(),
            'status': status.decode() if status else 'offline'
        })
    return jsonify(users)

@app.route('/update_presence', methods=['POST'])
def update_presence():
    data = request.json
    user_id = data['user_id']
    
    redis_client.hset('last_seen', user_id, time.time())
    return jsonify({'status': 'updated'})

@app.route('/health')
def health():
    return {'status': 'healthy'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
