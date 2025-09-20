from flask import Flask, request, jsonify
import psycopg2
import os
from datetime import datetime
import hashlib

app = Flask(__name__)

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://chat:password@postgres:5432/chatapp')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def generate_avatar_color(user_id):
    """Generate a consistent color based on user_id"""
    colors = [
        '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', '#2196f3',
        '#03a9f4', '#00bcd4', '#009688', '#4caf50', '#8bc34a',
        '#cddc39', '#ffeb3b', '#ffc107', '#ff9800', '#ff5722',
        '#795548', '#607d8b', '#f44336', '#e91e63', '#9c27b0'
    ]
    hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    return colors[hash_value % len(colors)]

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user_id = data['user_id']
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT user_id, avatar_color FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        
        if user:
            # Update status to online
            cur.execute(
                "UPDATE users SET status = 'online', last_seen = CURRENT_TIMESTAMP WHERE user_id = %s",
                (user_id,)
            )
            avatar_color = user[1]
        else:
            # Create new user with generated avatar color
            avatar_color = generate_avatar_color(user_id)
            cur.execute(
                "INSERT INTO users (user_id, status, avatar_color) VALUES (%s, 'online', %s)",
                (user_id, avatar_color)
            )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'avatar_color': avatar_color
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/users')
def get_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT user_id, status, avatar_color FROM users ORDER BY last_seen DESC")
        
        users = []
        for row in cur.fetchall():
            users.append({
                'user_id': row[0],
                'status': row[1],
                'avatar_color': row[2] or generate_avatar_color(row[0])
            })
        
        cur.close()
        conn.close()
        
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
