from flask import Flask, request, jsonify
import psycopg2
import os
from datetime import datetime
import traceback

app = Flask(__name__)

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://chat:password@postgres:5432/chatapp')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        data = request.json
        room_id = data['room_id']
        user_id = data['user_id']
        message = data['message']
        timestamp = data['timestamp']
        delivery_status = data.get('delivery_status', 'sent')
        
        print(f"send_message called: room_id={room_id}, user_id={user_id}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert message
        cur.execute(
            "INSERT INTO messages (room_id, user_id, message, timestamp, delivery_status) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (room_id, user_id, message, timestamp, delivery_status)
        )
        message_id = cur.fetchone()[0]
        print(f"Message inserted with ID: {message_id}")
        
        # Add unread entries for all room members except sender
        if str(room_id).startswith('direct_'):
            print("Processing direct message")
            # Direct message - add unread for the other user
            users = str(room_id).replace('direct_', '').split('_')
            other_user = users[1] if users[0] == user_id else users[0]
            cur.execute(
                "INSERT INTO unread_messages (user_id, room_id, message_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (other_user, room_id, message_id)
            )
            print(f"Added unread for direct user: {other_user}")
        else:
            print(f"Processing group message for group_id: {room_id}")
            # Group message - add unread for all group members except sender
            # Convert room_id to integer for group lookup
            try:
                group_id = int(room_id)
                print(f"Looking up members for group_id: {group_id}")
                cur.execute(
                    "SELECT user_id FROM group_members WHERE group_id = %s AND user_id != %s",
                    (group_id, user_id)
                )
                members = cur.fetchall()
                print(f"Found {len(members)} group members: {members}")
                
                for (member_user_id,) in members:
                    cur.execute(
                        "INSERT INTO unread_messages (user_id, room_id, message_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        (member_user_id, room_id, message_id)
                    )
                    print(f"Added unread for group member: {member_user_id}")
            except ValueError as e:
                print(f"Error converting room_id to int: {e}")
                # If room_id is not a valid integer, skip unread tracking
                pass
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("send_message completed successfully")
        return jsonify({'status': 'sent', 'timestamp': timestamp})
        
    except Exception as e:
        print(f"Error in send_message: {e}")
        print(traceback.format_exc())
        try:
            if 'conn' in locals():
                conn.rollback()
                conn.close()
        except:
            pass
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
        print(f"Error in get_messages: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
