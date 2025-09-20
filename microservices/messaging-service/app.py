from flask import Flask, request, jsonify
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://chat:password@postgres:5432/chatapp')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    room_id = data['room_id']
    user_id = data['user_id']
    message = data['message']
    timestamp = data['timestamp']
    delivery_status = data.get('delivery_status', 'sent')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO messages (room_id, user_id, message, timestamp, delivery_status) VALUES (%s, %s, %s, %s, %s)",
            (room_id, user_id, message, timestamp, delivery_status)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'status': 'sent', 'timestamp': timestamp})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_message_status', methods=['POST'])
def update_message_status():
    data = request.json
    timestamp = data['timestamp']
    status = data['status']
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "UPDATE messages SET delivery_status = %s WHERE timestamp = %s",
            (status, timestamp)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'status': 'updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_messages/<room_id>')
def get_messages(room_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "SELECT user_id, message, timestamp, delivery_status FROM messages WHERE room_id = %s ORDER BY timestamp ASC",
            (room_id,)
        )
        
        messages = []
        for row in cur.fetchall():
            messages.append({
                'user_id': row[0],
                'message': row[1],
                'timestamp': row[2],
                'delivery_status': row[3]
            })
        
        cur.close()
        conn.close()
        
        return jsonify(messages)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
