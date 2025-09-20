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

@app.route('/create_group', methods=['POST'])
def create_group():
    data = request.json
    name = data['name']
    creator_id = data['creator_id']
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create group
        cur.execute(
            "INSERT INTO groups (name, creator_id) VALUES (%s, %s) RETURNING id",
            (name, creator_id)
        )
        group_id = cur.fetchone()[0]
        
        # Add creator as admin
        cur.execute(
            "INSERT INTO group_members (group_id, user_id, role) VALUES (%s, %s, 'admin')",
            (group_id, creator_id)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'group_id': group_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/join_group', methods=['POST'])
def join_group():
    data = request.json
    group_id = data['group_id']
    user_id = data['user_id']
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user already in group
        cur.execute(
            "SELECT id FROM group_members WHERE group_id = %s AND user_id = %s",
            (group_id, user_id)
        )
        if cur.fetchone():
            return jsonify({'message': 'Already in group'})
        
        # Add user to group
        cur.execute(
            "INSERT INTO group_members (group_id, user_id, role) VALUES (%s, %s, 'member')",
            (group_id, user_id)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Joined group successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/user_groups/<user_id>')
def get_user_groups(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT g.id, g.name, g.creator_id, gm.role 
            FROM groups g 
            JOIN group_members gm ON g.id = gm.group_id 
            WHERE gm.user_id = %s
            ORDER BY g.created_at DESC
        """, (user_id,))
        
        groups = []
        for row in cur.fetchall():
            groups.append({
                'id': row[0],
                'name': row[1],
                'creator_id': row[2],
                'role': row[3]
            })
        
        cur.close()
        conn.close()
        
        return jsonify(groups)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/group_members/<group_id>')
def get_group_members(group_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "SELECT user_id, role, joined_at FROM group_members WHERE group_id = %s ORDER BY joined_at ASC",
            (group_id,)
        )
        
        members = []
        for row in cur.fetchall():
            members.append({
                'user_id': row[0],
                'role': row[1],
                'joined_at': row[2].isoformat() if row[2] else None
            })
        
        cur.close()
        conn.close()
        
        return jsonify(members)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/direct_chat', methods=['POST'])
def create_direct_chat():
    data = request.json
    user1 = data['user1']
    user2 = data['user2']
    
    # Create a consistent room ID for direct chats
    users = sorted([user1, user2])
    room_id = f"direct_{users[0]}_{users[1]}"
    
    return jsonify({'room_id': room_id})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
