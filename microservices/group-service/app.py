from flask import Flask, request, jsonify
import psycopg2
import os
import uuid
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
    description = data.get('description', '')
    require_approval = data.get('require_approval', True)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Generate invite link
        invite_link = str(uuid.uuid4())
        
        # Create group
        cur.execute(
            "INSERT INTO groups (name, description, creator_id, invite_link, require_approval) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (name, description, creator_id, invite_link, require_approval)
        )
        group_id = cur.fetchone()[0]
        
        # Add creator as owner
        cur.execute(
            "INSERT INTO group_members (group_id, user_id, role, permissions) VALUES (%s, %s, 'owner', %s)",
            (group_id, creator_id, '{"can_invite": true, "can_remove": true, "can_edit_group": true}')
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'group_id': group_id,
            'invite_link': invite_link,
            'require_approval': require_approval
        })
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
        
        cur.execute("""
            SELECT gm.user_id, gm.role, u.avatar_color, gm.joined_at 
            FROM group_members gm
            LEFT JOIN users u ON gm.user_id = u.user_id
            WHERE gm.group_id = %s 
            ORDER BY 
                CASE gm.role 
                    WHEN 'owner' THEN 1 
                    WHEN 'admin' THEN 2 
                    ELSE 3 
                END, gm.joined_at ASC
        """, (group_id,))
        
        members = []
        for row in cur.fetchall():
            members.append({
                'user_id': row[0],
                'role': row[1],
                'avatar_color': row[2] or '#00a884',
                'joined_at': row[3].isoformat() if row[3] else None
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

@app.route('/join_by_link', methods=['POST'])
def join_by_link():
    data = request.json
    invite_link = data['invite_link']
    user_id = data['user_id']
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Find group by invite link
        cur.execute("SELECT id, name, require_approval FROM groups WHERE invite_link = %s", (invite_link,))
        group_data = cur.fetchone()
        
        if not group_data:
            return jsonify({'error': 'Invalid invite link'}), 404
        
        group_id, group_name, require_approval = group_data
        
        # Check if user already in group
        cur.execute("SELECT id FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
        if cur.fetchone():
            return jsonify({'message': 'Already in group'})
        
        if require_approval:
            # Add to pending approvals
            cur.execute(
                "INSERT INTO group_join_requests (group_id, user_id, status) VALUES (%s, %s, 'pending') ON CONFLICT (group_id, user_id) DO UPDATE SET status = 'pending', created_at = CURRENT_TIMESTAMP",
                (group_id, user_id)
            )
            conn.commit()
            return jsonify({'message': 'Join request sent for approval', 'group_name': group_name})
        else:
            # Add directly to group
            cur.execute(
                "INSERT INTO group_members (group_id, user_id, role) VALUES (%s, %s, 'member')",
                (group_id, user_id)
            )
            conn.commit()
            return jsonify({'message': 'Joined group successfully', 'group_name': group_name})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/invite_users', methods=['POST'])
def invite_users():
    data = request.json
    group_id = data['group_id']
    user_ids = data['user_ids']
    inviter_id = data['inviter_id']
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if inviter has permission (owners and admins can invite)
        cur.execute(
            "SELECT role, permissions FROM group_members WHERE group_id = %s AND user_id = %s",
            (group_id, inviter_id)
        )
        result = cur.fetchone()
        if not result:
            return jsonify({'error': 'Not a member of this group'}), 403
        
        role, permissions = result
        # Allow owners and admins to invite, or check permissions
        can_invite = role in ['owner', 'admin'] or (permissions and permissions.get('can_invite', False))
        
        if not can_invite:
            return jsonify({'error': 'No permission to invite'}), 403
        
        invited_count = 0
        for user_id in user_ids:
            # Check if user already in group
            cur.execute("SELECT id FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
            if not cur.fetchone():
                # Send invite
                cur.execute(
                    "INSERT INTO invites (from_user_id, to_user_id, invite_type, target_id, message) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (inviter_id, user_id, 'group', group_id, f'Invited you to join the group')
                )
                invited_count += 1
        
        conn.commit()
        return jsonify({'message': f'Invited {invited_count} users'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/group_invite_link/<group_id>')
def get_group_invite_link(group_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT invite_link, require_approval FROM groups WHERE id = %s", (group_id,))
        result = cur.fetchone()
        
        if not result:
            return jsonify({'error': 'Group not found'}), 404
        
        return jsonify({
            'invite_link': result[0],
            'require_approval': result[1]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
