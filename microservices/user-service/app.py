from flask import Flask, request, jsonify
import psycopg2
import os
from datetime import datetime, timedelta
import redis
import json

app = Flask(__name__)

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://chat:password@postgres:5432/chatapp')
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
    redis_client.ping()
except:
    redis_client = None

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/user_status/<user_id>')
def get_user_status(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT status FROM users WHERE user_id = %s", (user_id,))
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if result:
            return jsonify({'status': result[0]})
        else:
            return jsonify({'status': 'offline'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search_users', methods=['GET'])
def search_users():
    query = request.args.get('q', '').strip()
    current_user = request.headers.get('X-User-ID')
    
    if not query or len(query) < 2:
        return jsonify({'error': 'Query too short'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Search users by user_id or email
        cur.execute(
            "SELECT user_id, email, avatar_color, status FROM users WHERE (user_id ILIKE %s OR email ILIKE %s) AND user_id != %s LIMIT 20",
            (f'%{query}%', f'%{query}%', current_user)
        )
        
        users = []
        for row in cur.fetchall():
            users.append({
                'user_id': row[0],
                'email': row[1],
                'avatar_color': row[2],
                'status': row[3]
            })
        
        cur.close()
        conn.close()
        
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/invite_user', methods=['POST'])
def invite_user():
    data = request.json
    from_user_id = request.headers.get('X-User-ID')
    to_user_id = data.get('to_user_id')
    message = data.get('message', '')
    
    if not all([from_user_id, to_user_id]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if invite already exists
        cur.execute(
            "SELECT id FROM invites WHERE from_user_id = %s AND to_user_id = %s AND invite_type = 'chat' AND status = 'pending'",
            (from_user_id, to_user_id)
        )
        if cur.fetchone():
            return jsonify({'error': 'Invite already sent'}), 409
        
        # Create invite
        cur.execute(
            "INSERT INTO invites (from_user_id, to_user_id, invite_type, message) VALUES (%s, %s, 'chat', %s) RETURNING id",
            (from_user_id, to_user_id, message)
        )
        invite_id = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Notify via Redis if user is online
        if redis_client:
            redis_client.publish(f"user_notifications:{to_user_id}", json.dumps({
                'type': 'chat_invite',
                'from_user_id': from_user_id,
                'invite_id': invite_id,
                'message': message
            }))
        
        return jsonify({
            'status': 'success',
            'invite_id': invite_id,
            'message': 'Invite sent successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/accept_invite', methods=['POST'])
def accept_invite():
    data = request.json
    user_id = request.headers.get('X-User-ID')
    invite_id = data.get('invite_id')
    action = data.get('action')  # 'accept' or 'reject'
    
    if not all([user_id, invite_id, action]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get invite details
        cur.execute(
            "SELECT from_user_id, to_user_id, invite_type, target_id FROM invites WHERE id = %s AND to_user_id = %s AND status = 'pending'",
            (invite_id, user_id)
        )
        invite = cur.fetchone()
        
        if not invite:
            return jsonify({'error': 'Invite not found'}), 404
        
        from_user_id, to_user_id, invite_type, target_id = invite
        
        # Update invite status
        cur.execute("UPDATE invites SET status = %s WHERE id = %s", (action + 'ed', invite_id))
        
        result = {'status': 'success', 'action': action}
        
        if action == 'accept':
            if invite_type == 'chat':
                # Add both users as contacts
                cur.execute(
                    "INSERT INTO contacts (user_id, contact_user_id) VALUES (%s, %s), (%s, %s) ON CONFLICT DO NOTHING",
                    (from_user_id, to_user_id, to_user_id, from_user_id)
                )
                
                # Create direct chat room ID
                users = sorted([from_user_id, to_user_id])
                room_id = f"direct_{users[0]}_{users[1]}"
                result['room_id'] = room_id
                
            elif invite_type == 'group' and target_id:
                # Add user to group
                cur.execute(
                    "INSERT INTO group_members (group_id, user_id, role) VALUES (%s, %s, 'member') ON CONFLICT DO NOTHING",
                    (target_id, to_user_id)
                )
                result['group_id'] = target_id
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/contacts')
def get_contacts():
    user_id = request.headers.get('X-User-ID')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get user's contacts with their info
        cur.execute("""
            SELECT u.user_id, u.email, u.avatar_color, u.status, c.added_at
            FROM contacts c
            JOIN users u ON c.contact_user_id = u.user_id
            WHERE c.user_id = %s AND c.status = 'active'
            ORDER BY u.status DESC, c.added_at DESC
        """, (user_id,))
        
        contacts = []
        for row in cur.fetchall():
            # Check Redis for real-time status
            status = row[3]
            if redis_client:
                redis_status = redis_client.get(f"user_status:{row[0]}")
                if redis_status:
                    status = redis_status
            
            contacts.append({
                'user_id': row[0],
                'email': row[1],
                'avatar_color': row[2],
                'status': status,
                'added_at': row[4].isoformat() if row[4] else None
            })
        
        cur.close()
        conn.close()
        
        return jsonify(contacts)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/invites')
def get_invites():
    user_id = request.headers.get('X-User-ID')
    invite_type = request.args.get('type', 'all')  # 'sent', 'received', 'all'
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if invite_type == 'sent':
            cur.execute("""
                SELECT i.id, i.to_user_id, u.email, i.invite_type, i.target_id, i.status, i.message, i.created_at
                FROM invites i
                JOIN users u ON i.to_user_id = u.user_id
                WHERE i.from_user_id = %s
                ORDER BY i.created_at DESC
            """, (user_id,))
        elif invite_type == 'received':
            cur.execute("""
                SELECT i.id, i.from_user_id, u.email, i.invite_type, i.target_id, i.status, i.message, i.created_at
                FROM invites i
                JOIN users u ON i.from_user_id = u.user_id
                WHERE i.to_user_id = %s
                ORDER BY i.created_at DESC
            """, (user_id,))
        else:
            cur.execute("""
                SELECT i.id, 
                       CASE WHEN i.from_user_id = %s THEN i.to_user_id ELSE i.from_user_id END as other_user_id,
                       u.email, i.invite_type, i.target_id, i.status, i.message, i.created_at,
                       CASE WHEN i.from_user_id = %s THEN 'sent' ELSE 'received' END as direction
                FROM invites i
                JOIN users u ON (CASE WHEN i.from_user_id = %s THEN i.to_user_id ELSE i.from_user_id END) = u.user_id
                WHERE i.from_user_id = %s OR i.to_user_id = %s
                ORDER BY i.created_at DESC
            """, (user_id, user_id, user_id, user_id, user_id))
        
        invites = []
        for row in cur.fetchall():
            invite_data = {
                'id': row[0],
                'other_user_id': row[1],
                'other_user_email': row[2],
                'invite_type': row[3],
                'target_id': row[4],
                'status': row[5],
                'message': row[6],
                'created_at': row[7].isoformat() if row[7] else None
            }
            
            if invite_type == 'all':
                invite_data['direction'] = row[8]
            
            invites.append(invite_data)
        
        cur.close()
        conn.close()
        
        return jsonify(invites)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
