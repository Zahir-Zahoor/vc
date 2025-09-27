from flask import Flask, request, jsonify
import psycopg2
import os
from datetime import datetime
import traceback
import json
from kafka import KafkaProducer, KafkaConsumer
import threading
import time

app = Flask(__name__)

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://chat:password@postgres:5432/chatapp')
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')

# Initialize Kafka producer with retry logic
producer = None
def init_kafka_producer():
    global producer
    max_retries = 10
    retry_count = 0
    
    while retry_count < max_retries and producer is None:
        try:
            producer = KafkaProducer(
                bootstrap_servers=[KAFKA_BOOTSTRAP_SERVERS],
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            print("✅ Connected to Kafka")
            break
        except Exception as e:
            retry_count += 1
            print(f"❌ Kafka connection attempt {retry_count}/{max_retries} failed: {e}")
            time.sleep(5)
    
    if producer is None:
        print("❌ Failed to connect to Kafka after all retries")

# Initialize Kafka in background thread
kafka_thread = threading.Thread(target=init_kafka_producer, daemon=True)
kafka_thread.start()

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def process_kafka_messages():
    """Kafka consumer to process incoming messages"""
    max_retries = 10
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            consumer = KafkaConsumer(
                'chat-messages',
                bootstrap_servers=[KAFKA_BOOTSTRAP_SERVERS],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='messaging-service'
            )
            print("✅ Kafka consumer connected")
            
            for message in consumer:
                try:
                    msg_data = message.value
                    print(f"Processing Kafka message: {msg_data}")
                    
                    room_id = msg_data['room_id']
                    user_id = msg_data['user_id']
                    message_text = msg_data['message']
                    timestamp = msg_data['timestamp']
                    
                    # Store message in database
                    conn = get_db_connection()
                    cur = conn.cursor()
                    
                    # Insert message
                    cur.execute(
                        "INSERT INTO messages (room_id, user_id, message, timestamp, delivery_status, reply_to) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                        (room_id, user_id, message_text, timestamp, 'delivered', json.dumps(msg_data.get('reply_to')) if msg_data.get('reply_to') else None)
                    )
                    message_id = cur.fetchone()[0]
                    
                    # Add unread entries for recipients
                    if str(room_id).startswith('dm_'):
                        # Direct message - extract other user
                        users_part = str(room_id)[3:]  # Remove 'dm_' prefix
                        users = users_part.split('_')
                        if len(users) >= 2:
                            other_user = users[1] if users[0] == user_id else users[0]
                            cur.execute(
                                "INSERT INTO unread_messages (user_id, room_id, message_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                                (other_user, room_id, message_id)
                            )
                    else:
                        # Group message - add unread for all members except sender
                        try:
                            group_id = int(room_id)
                            cur.execute(
                                "SELECT user_id FROM group_members WHERE group_id = %s AND user_id != %s",
                                (group_id, user_id)
                            )
                            members = cur.fetchall()
                            
                            for (member_user_id,) in members:
                                cur.execute(
                                    "INSERT INTO unread_messages (user_id, room_id, message_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                                    (member_user_id, room_id, message_id)
                                )
                        except ValueError:
                            pass
                    
                    conn.commit()
                    cur.close()
                    conn.close()
                    
                    # Publish to websocket topic for real-time delivery
                    if producer:
                        producer.send('websocket-delivery', {
                            'room_id': room_id,
                            'user_id': user_id,
                            'message': message_text,
                            'timestamp': timestamp,
                            'delivery_status': 'delivered'
                        })
                    
                    print(f"✅ Message stored and queued for delivery")
                    
                except Exception as e:
                    print(f"❌ Error processing message: {e}")
                    traceback.print_exc()
                    
        except Exception as e:
            retry_count += 1
            print(f"❌ Kafka consumer connection attempt {retry_count}/{max_retries} failed: {e}")
            time.sleep(5)
    
    print("❌ Failed to connect Kafka consumer after all retries")

# Start Kafka consumer in background thread
consumer_thread = threading.Thread(target=process_kafka_messages, daemon=True)
consumer_thread.start()

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/recent_chats/<user_id>')
def get_recent_chats(user_id):
    try:
        print(f"Getting recent chats for user: {user_id}")
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all recent conversations
        cur.execute("""
            SELECT DISTINCT room_id, MAX(timestamp) as last_time
            FROM messages 
            WHERE room_id IN (
                SELECT DISTINCT room_id FROM messages WHERE user_id = %s
            )
            GROUP BY room_id
            ORDER BY last_time DESC
        """, (user_id,))
        
        all_rooms = cur.fetchall()
        
        # Filter out completely deleted chats (no new messages after deletion)
        filtered_rooms = []
        for room_id, last_time in all_rooms:
            cur.execute("SELECT EXTRACT(EPOCH FROM deleted_at) FROM deleted_chats WHERE user_id = %s AND room_id = %s", (user_id, room_id))
            deleted_result = cur.fetchone()
            
            if deleted_result:
                # Check if there are ANY messages after deletion timestamp
                # Convert deletion timestamp from seconds to milliseconds for comparison
                deleted_timestamp_ms = int(deleted_result[0] * 1000)
                cur.execute("""
                    SELECT COUNT(*) FROM messages 
                    WHERE room_id = %s AND timestamp > %s
                """, (room_id, deleted_timestamp_ms))
                new_messages_count = cur.fetchone()[0]
                
                # Only show if there are new messages after deletion
                if new_messages_count > 0:
                    filtered_rooms.append((room_id, last_time))
            else:
                # Not deleted, show normally
                filtered_rooms.append((room_id, last_time))
        
        rows = filtered_rooms
        print(f"Found {len(rows)} rooms after filtering: {rows}")
        
        chats = []
        for row in rows:
            room_id = row[0]
            print(f"Processing room: {room_id}")
            
            # Handle different room_id formats
            if room_id.startswith('dm_'):
                # Direct message format: dm_user1_user2
                users_part = room_id[3:]  # Remove 'dm_' prefix
                users = users_part.split('_')
                if len(users) >= 2:
                    other_user = users[1] if users[0] == user_id else users[0]
                    chat_type = 'direct'
                else:
                    print(f"Invalid DM room format: {room_id}")
                    continue
            else:
                # Group chat (numeric room_id) - get actual group name
                cur.execute("SELECT name FROM groups WHERE id = %s", (room_id,))
                group_result = cur.fetchone()
                other_user = group_result[0] if group_result else f"Group {room_id}"
                chat_type = 'group'
            
            print(f"Other user/Group: {other_user}")
            
            # Get latest message
            cur.execute("SELECT user_id, message, timestamp FROM messages WHERE room_id = %s ORDER BY timestamp DESC LIMIT 1", (room_id,))
            msg_result = cur.fetchone()
            
            if msg_result:
                # Get user avatar color for direct chats
                avatar_color = '#00a884'  # Default
                if chat_type == 'direct':
                    cur.execute("SELECT avatar_color FROM users WHERE user_id = %s", (other_user,))
                    avatar_result = cur.fetchone()
                    avatar_color = avatar_result[0] if avatar_result else '#00a884'
                
                chats.append({
                    'other_user': other_user,
                    'room_id': room_id,
                    'chat_type': chat_type,
                    'last_message_time': msg_result[2],
                    'last_message': msg_result[1],
                    'last_message_user': msg_result[0],
                    'avatar_color': avatar_color
                })
        
        print(f"Final chats: {chats}")
        
        # Sort by last message time, newest first
        chats.sort(key=lambda x: x['last_message_time'] or 0, reverse=True)
        
        cur.close()
        conn.close()
        return jsonify(chats)
    except Exception as e:
        print(f"Error getting recent chats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])  # Return empty array on error

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        data = request.json
        room_id = data['room_id']
        user_id = data['user_id']
        message = data['message']
        timestamp = data['timestamp']
        reply_to = data.get('reply_to')  # Optional reply data
        
        print(f"Sending message to Kafka: {user_id} -> {room_id}")
        
        if producer is None:
            print("❌ Kafka producer not ready, falling back to direct storage")
            # Fallback to direct database storage
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO messages (room_id, user_id, message, timestamp, delivery_status, reply_to) VALUES (%s, %s, %s, %s, %s, %s)",
                (room_id, user_id, message, timestamp, 'delivered', json.dumps(reply_to) if reply_to else None)
            )
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'status': 'stored_direct', 'timestamp': timestamp})
        
        # Send to Kafka for reliable processing
        producer.send('chat-messages', {
            'room_id': room_id,
            'user_id': user_id,
            'message': message,
            'timestamp': timestamp,
            'reply_to': reply_to
        })
        
        return jsonify({'status': 'queued', 'timestamp': timestamp})
        
    except Exception as e:
        print(f"Error sending message: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/mark_read', methods=['POST'])
def mark_read():
    try:
        print(f"mark_read called with data: {request.json}")
        data = request.json
        
        if not data:
            print("No JSON data received")
            return jsonify({'error': 'No JSON data'}), 400
            
        user_id = data.get('user_id')
        room_id = data.get('room_id')
        
        print(f"user_id: {user_id}, room_id: {room_id}")
        
        if not user_id or not room_id:
            print("Missing user_id or room_id")
            return jsonify({'error': 'user_id and room_id are required'}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        print(f"Executing DELETE query for user_id={user_id}, room_id={room_id}")
        
        # Remove all unread messages for this user in this room
        cur.execute(
            "DELETE FROM unread_messages WHERE user_id = %s AND room_id = %s",
            (user_id, room_id)
        )
        
        deleted_count = cur.rowcount
        print(f"Deleted {deleted_count} unread messages")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("mark_read completed successfully")
        return jsonify({'status': 'marked_read', 'deleted': deleted_count})
        
    except Exception as e:
        print(f"Error in mark_read: {e}")
        print(traceback.format_exc())
        try:
            if 'conn' in locals():
                conn.rollback()
                conn.close()
        except:
            pass
        return jsonify({'error': str(e)}), 500

@app.route('/unread_counts/<user_id>')
def get_unread_counts(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get unread counts per room
        cur.execute(
            "SELECT room_id, COUNT(*) FROM unread_messages WHERE user_id = %s GROUP BY room_id",
            (user_id,)
        )
        
        unread_counts = {}
        for room_id, count in cur.fetchall():
            unread_counts[room_id] = count
        
        cur.close()
        conn.close()
        
        return jsonify(unread_counts)
    except Exception as e:
        print(f"Error in get_unread_counts: {e}")
        print(traceback.format_exc())
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
        print(f"Error in update_message_status: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/get_messages/<room_id>')
def get_messages(room_id):
    try:
        user_id = request.args.get('user_id')
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user has deleted this chat
        if user_id:
            cur.execute(
                "SELECT EXTRACT(EPOCH FROM deleted_at) FROM deleted_chats WHERE user_id = %s AND room_id = %s",
                (user_id, room_id)
            )
            deleted_result = cur.fetchone()
            deleted_timestamp = deleted_result[0] if deleted_result else None
        else:
            deleted_timestamp = None
        
        # Get messages, filtering by deletion timestamp if applicable
        if deleted_timestamp:
            # Convert deletion timestamp from seconds to milliseconds for comparison
            deleted_timestamp_ms = int(deleted_timestamp * 1000)
            cur.execute(
                "SELECT user_id, message, timestamp, delivery_status, reply_to FROM messages WHERE room_id = %s AND timestamp > %s ORDER BY timestamp ASC",
                (room_id, deleted_timestamp_ms)
            )
        else:
            cur.execute(
                "SELECT user_id, message, timestamp, delivery_status, reply_to FROM messages WHERE room_id = %s ORDER BY timestamp ASC",
                (room_id,)
            )
        
        messages = []
        for row in cur.fetchall():
            messages.append({
                'user_id': row[0],
                'message': row[1],
                'timestamp': row[2],
                'delivery_status': row[3],
                'reply_to': row[4] if row[4] else None  # PostgreSQL JSONB returns dict directly
            })
        
        cur.close()
        conn.close()
        
        return jsonify(messages)
    except Exception as e:
        print(f"Error in get_messages: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/delete_chat_history', methods=['POST'])
def delete_chat_history():
    try:
        data = request.json
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        
        if not room_id or not user_id:
            return jsonify({'error': 'Missing room_id or user_id'}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create deleted_chats table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deleted_chats (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                room_id VARCHAR(255) NOT NULL,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, room_id)
            )
        """)
        
        # Mark this chat as deleted for this user
        cur.execute(
            "INSERT INTO deleted_chats (user_id, room_id) VALUES (%s, %s) ON CONFLICT (user_id, room_id) DO UPDATE SET deleted_at = CURRENT_TIMESTAMP",
            (user_id, room_id)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in delete_chat_history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/export_chat/<room_id>')
def export_chat(room_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "SELECT user_id, message, timestamp FROM messages WHERE room_id = %s ORDER BY timestamp ASC",
            (room_id,)
        )
        
        messages = []
        for row in cur.fetchall():
            messages.append({
                'sender': row[0],
                'content': row[1],
                'timestamp': row[2].isoformat() if row[2] else None
            })
        
        cur.close()
        conn.close()
        
        return jsonify({'messages': messages})
    except Exception as e:
        print(f"Error in export_chat: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
