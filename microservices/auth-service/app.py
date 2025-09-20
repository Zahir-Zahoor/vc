from flask import Flask, request, jsonify
import psycopg2
import os
import bcrypt
import jwt
import hashlib
from datetime import datetime, timedelta
import redis
import json

app = Flask(__name__)

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://chat:password@postgres:5432/chatapp')
JWT_SECRET = os.getenv('JWT_SECRET', 'your-super-secret-jwt-key')
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
    redis_client.ping()
except:
    redis_client = None

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def generate_avatar_color(user_id):
    colors = [
        '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', '#2196f3',
        '#03a9f4', '#00bcd4', '#009688', '#4caf50', '#8bc34a',
        '#cddc39', '#ffeb3b', '#ffc107', '#ff9800', '#ff5722',
        '#795548', '#607d8b', '#f44336', '#e91e63', '#9c27b0'
    ]
    hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    return colors[hash_value % len(colors)]

def create_jwt_token(user_id, email):
    payload = {
        'user_id': user_id,
        'email': email,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def create_refresh_token():
    return hashlib.sha256(os.urandom(32)).hexdigest()

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    user_id = data.get('user_id')
    email = data.get('email')
    password = data.get('password')
    
    if not all([user_id, email, password]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT user_id FROM users WHERE user_id = %s OR email = %s", (user_id, email))
        if cur.fetchone():
            return jsonify({'error': 'User already exists'}), 409
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        avatar_color = generate_avatar_color(user_id)
        
        # Create user
        cur.execute(
            "INSERT INTO users (user_id, email, password_hash, avatar_color, status) VALUES (%s, %s, %s, %s, 'offline')",
            (user_id, email, password_hash, avatar_color)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'User registered successfully',
            'user_id': user_id,
            'avatar_color': avatar_color
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    identifier = data.get('identifier')  # email or user_id
    password = data.get('password')
    device_info = data.get('device_info', 'Unknown Device')
    
    if not all([identifier, password]):
        return jsonify({'error': 'Missing credentials'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Find user by email or user_id
        cur.execute(
            "SELECT user_id, email, password_hash, avatar_color FROM users WHERE user_id = %s OR email = %s",
            (identifier, identifier)
        )
        user = cur.fetchone()
        
        if not user or not bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        user_id, email, _, avatar_color = user
        
        # Create JWT token
        token = create_jwt_token(user_id, email)
        refresh_token = create_refresh_token()
        
        # Store session
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        cur.execute(
            "INSERT INTO sessions (user_id, token_hash, refresh_token_hash, device_info, expires_at) VALUES (%s, %s, %s, %s, %s)",
            (user_id, token_hash, refresh_hash, device_info, expires_at)
        )
        
        # Update user status
        cur.execute("UPDATE users SET status = 'online', last_seen = CURRENT_TIMESTAMP WHERE user_id = %s", (user_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Cache in Redis
        if redis_client:
            redis_client.setex(f"session:{token_hash}", 86400, json.dumps({
                'user_id': user_id,
                'email': email,
                'avatar_color': avatar_color
            }))
            redis_client.setex(f"user_status:{user_id}", 3600, 'online')
        
        return jsonify({
            'status': 'success',
            'token': token,
            'refresh_token': refresh_token,
            'user': {
                'user_id': user_id,
                'email': email,
                'avatar_color': avatar_color
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'error': 'No token provided'}), 401
    
    try:
        # Decode token to get user_id
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload['user_id']
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Remove session
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        cur.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))
        
        # Update user status
        cur.execute("UPDATE users SET status = 'offline', last_seen = CURRENT_TIMESTAMP WHERE user_id = %s", (user_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Remove from Redis
        if redis_client:
            redis_client.delete(f"session:{token_hash}")
            redis_client.setex(f"user_status:{user_id}", 3600, 'offline')
        
        return jsonify({'status': 'success', 'message': 'Logged out successfully'})
        
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/verify_token', methods=['POST'])
def verify_token():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'error': 'No token provided'}), 401
    
    try:
        # Check Redis cache first
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if redis_client:
            cached_user = redis_client.get(f"session:{token_hash}")
            if cached_user:
                return jsonify({
                    'status': 'valid',
                    'user': json.loads(cached_user)
                })
        
        # Verify JWT
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
        # Check database session
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT u.user_id, u.email, u.avatar_color FROM users u JOIN sessions s ON u.user_id = s.user_id WHERE s.token_hash = %s AND s.expires_at > CURRENT_TIMESTAMP",
            (token_hash,)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if not user:
            return jsonify({'error': 'Invalid session'}), 401
        
        return jsonify({
            'status': 'valid',
            'user': {
                'user_id': user[0],
                'email': user[1],
                'avatar_color': user[2]
            }
        })
        
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/users')
def get_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT user_id, email, status, avatar_color, last_seen FROM users ORDER BY last_seen DESC")
        
        users = []
        for row in cur.fetchall():
            # Check Redis for real-time status
            status = row[2]
            if redis_client:
                redis_status = redis_client.get(f"user_status:{row[0]}")
                if redis_status:
                    status = redis_status
            
            users.append({
                'user_id': row[0],
                'email': row[1],
                'status': status,
                'avatar_color': row[3],
                'last_seen': row[4].isoformat() if row[4] else None
            })
        
        cur.close()
        conn.close()
        
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
