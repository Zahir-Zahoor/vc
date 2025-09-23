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
    name = data.get('name')
    description = data.get('description', '')
    creator_id = data.get('creator_id')
    require_approval = data.get('require_approval', True)
    
    if not name or not creator_id:
        return jsonify({'error': 'Name and creator_id are required'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Generate unique invite link
        invite_link = str(uuid.uuid4())
        
        # Create group
        cur.execute("""
            INSERT INTO groups (name, description, creator_id, invite_link, require_approval, created_at)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (name, description, creator_id, invite_link, require_approval, datetime.now()))
        
        group_id = cur.fetchone()[0]
        
        # Add creator as owner
        cur.execute("""
            INSERT INTO group_members (group_id, user_id, role, joined_at)
            VALUES (%s, %s, 'owner', %s)
        """, (group_id, creator_id, datetime.now()))
        
        conn.commit()
        
        return jsonify({
            'id': group_id,
            'name': name,
            'description': description,
            'invite_link': invite_link,
            'require_approval': require_approval
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/join_group', methods=['POST'])
def join_group():
    data = request.json
    group_id = data.get('group_id')
    user_id = data.get('user_id')
    
    if not group_id or not user_id:
        return jsonify({'error': 'Group ID and user ID are required'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user is already a member
        cur.execute("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
        if cur.fetchone():
            return jsonify({'error': 'User is already a member'}), 400
        
        # Add user as member
        cur.execute("""
            INSERT INTO group_members (group_id, user_id, role, joined_at)
            VALUES (%s, %s, 'member', %s)
        """, (group_id, user_id, datetime.now()))
        
        conn.commit()
        return jsonify({'message': 'Successfully joined group'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/user_groups/<user_id>')
def get_user_groups(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT g.id, g.name, g.description, gm.role, g.created_at
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
                'description': row[2],
                'role': row[3],
                'created_at': row[4].isoformat() if row[4] else None
            })
        
        return jsonify(groups)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/group_members/<group_id>')
def get_group_members(group_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT gm.user_id, gm.role, gm.joined_at, u.avatar_color
            FROM group_members gm
            LEFT JOIN users u ON gm.user_id = u.user_id
            WHERE gm.group_id = %s
            ORDER BY 
                CASE gm.role 
                    WHEN 'owner' THEN 1 
                    WHEN 'admin' THEN 2 
                    ELSE 3 
                END,
                gm.joined_at
        """, (group_id,))
        
        members = []
        for row in cur.fetchall():
            members.append({
                'user_id': row[0],
                'role': row[1],
                'joined_at': row[2].isoformat() if row[2] else None,
                'avatar_color': row[3] or '#00a884'
            })
        
        return jsonify(members)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/direct_chat', methods=['POST'])
def create_direct_chat():
    data = request.json
    user1 = data.get('user1')
    user2 = data.get('user2')
    
    # Create a consistent room ID for direct chats
    users = sorted([user1, user2])
    room_id = f"dm_{users[0]}_{users[1]}"
    
    return jsonify({'room_id': room_id})

@app.route('/join_by_link', methods=['POST'])
def join_by_link():
    data = request.json
    invite_link = data.get('invite_link')
    user_id = data.get('user_id')
    
    if not invite_link or not user_id:
        return jsonify({'error': 'Invite link and user ID are required'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Find group by invite link
        cur.execute("SELECT id, name, require_approval FROM groups WHERE invite_link = %s", (invite_link,))
        group = cur.fetchone()
        
        if not group:
            return jsonify({'error': 'Invalid invite link'}), 404
        
        group_id, group_name, require_approval = group
        
        # Check if user is already a member
        cur.execute("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
        if cur.fetchone():
            return jsonify({'error': 'User is already a member'}), 400
        
        if require_approval:
            # Add as pending member (you might want to implement a pending_members table)
            return jsonify({'message': 'Join request sent for approval', 'group_name': group_name})
        else:
            # Add directly as member
            cur.execute("""
                INSERT INTO group_members (group_id, user_id, role, joined_at)
                VALUES (%s, %s, 'member', %s)
            """, (group_id, user_id, datetime.now()))
            
            conn.commit()
            return jsonify({'message': f'Successfully joined {group_name}', 'group_id': group_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/invite_users', methods=['POST'])
def invite_users():
    data = request.json
    group_id = data.get('group_id')
    user_ids = data.get('user_ids', [])
    inviter_id = data.get('inviter_id')
    
    if not group_id or not user_ids or not inviter_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if inviter has permission (owner or admin)
        cur.execute("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, inviter_id))
        inviter_role = cur.fetchone()
        
        if not inviter_role or inviter_role[0] not in ['owner', 'admin']:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        successful_invites = []
        failed_invites = []
        
        for user_id in user_ids:
            try:
                # Check if user is already a member
                cur.execute("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
                if cur.fetchone():
                    failed_invites.append(f"{user_id} is already a member")
                    continue
                
                # Add user as member
                cur.execute("""
                    INSERT INTO group_members (group_id, user_id, role, joined_at)
                    VALUES (%s, %s, 'member', %s)
                """, (group_id, user_id, datetime.now()))
                
                successful_invites.append(user_id)
                
            except Exception as e:
                failed_invites.append(f"{user_id}: {str(e)}")
        
        conn.commit()
        
        message = f"Successfully invited {len(successful_invites)} users"
        if failed_invites:
            message += f". {len(failed_invites)} failed"
        
        return jsonify({
            'message': message,
            'successful': successful_invites,
            'failed': failed_invites
        })
        
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

@app.route('/remove_member', methods=['POST'])
def remove_member():
    data = request.json
    group_id = data.get('group_id')
    user_id = data.get('user_id')
    remover_id = data.get('remover_id')
    
    if not all([group_id, user_id, remover_id]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if remover is owner or admin
        cur.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, remover_id))
        
        remover_role = cur.fetchone()
        if not remover_role or remover_role[0] not in ['owner', 'admin']:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        # Cannot remove owner
        cur.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        target_role = cur.fetchone()
        if not target_role:
            return jsonify({'error': 'User not in group'}), 404
        
        if target_role[0] == 'owner':
            return jsonify({'error': 'Cannot remove group owner'}), 403
        
        # Remove the member
        cur.execute("""
            DELETE FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        conn.commit()
        return jsonify({'message': 'Member removed successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
