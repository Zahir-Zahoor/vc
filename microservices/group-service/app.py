from flask import Flask, request, jsonify
import psycopg2
import os
import uuid
from datetime import datetime, timedelta

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
            # Check if there's already a pending request
            cur.execute("SELECT status FROM group_join_requests WHERE group_id = %s AND user_id = %s", (group_id, user_id))
            existing_request = cur.fetchone()
            
            if existing_request:
                if existing_request[0] == 'pending':
                    return jsonify({'message': 'Join request already pending approval', 'group_name': group_name})
                elif existing_request[0] == 'rejected':
                    return jsonify({'error': 'Previous join request was rejected', 'group_name': group_name}), 403
            
            # Create new join request
            cur.execute("""
                INSERT INTO group_join_requests (group_id, user_id, status, created_at)
                VALUES (%s, %s, 'pending', %s)
                ON CONFLICT (group_id, user_id) 
                DO UPDATE SET status = 'pending', created_at = %s
            """, (group_id, user_id, datetime.now(), datetime.now()))
            
            conn.commit()
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
                # Check if user exists
                cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                if not cur.fetchone():
                    failed_invites.append(f"{user_id} does not exist")
                    continue
                
                # Check if user is already a member
                cur.execute("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
                if cur.fetchone():
                    failed_invites.append(f"{user_id} is already a member")
                    continue
                
                # Check if there's already a pending invite
                cur.execute("""
                    SELECT status FROM invites 
                    WHERE from_user_id = %s AND to_user_id = %s 
                    AND invite_type = 'group' AND target_id = %s 
                    AND status = 'pending'
                """, (inviter_id, user_id, str(group_id)))
                
                if cur.fetchone():
                    failed_invites.append(f"{user_id} already has a pending invite")
                    continue
                
                # Create invite instead of adding directly
                now = datetime.utcnow()
                expires = now + timedelta(days=7)
                cur.execute("""
                    INSERT INTO invites (from_user_id, to_user_id, invite_type, target_id, message, created_at, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (inviter_id, user_id, 'group', str(group_id), data.get('message', ''), now, expires))
                
                successful_invites.append(user_id)
                
            except Exception as e:
                failed_invites.append(f"{user_id}: {str(e)}")
        
        conn.commit()
        
        message = f"Successfully sent {len(successful_invites)} invites"
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

@app.route('/group_join_requests/<group_id>')
def get_join_requests(group_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT gjr.id, gjr.user_id, gjr.created_at, u.avatar_color
            FROM group_join_requests gjr
            JOIN users u ON gjr.user_id = u.user_id
            WHERE gjr.group_id = %s AND gjr.status = 'pending'
            ORDER BY gjr.created_at DESC
        """, (group_id,))
        
        requests = []
        for row in cur.fetchall():
            requests.append({
                'request_id': row[0],
                'user_id': row[1],
                'created_at': row[2].isoformat(),
                'avatar_color': row[3]
            })
        
        return jsonify(requests)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/approve_join_request', methods=['POST'])
def approve_join_request():
    data = request.json
    request_id = data.get('request_id')
    approver_id = data.get('approver_id')
    
    if not request_id or not approver_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get request details
        cur.execute("""
            SELECT gjr.group_id, gjr.user_id, g.name
            FROM group_join_requests gjr
            JOIN groups g ON gjr.group_id = g.id
            WHERE gjr.id = %s AND gjr.status = 'pending'
        """, (request_id,))
        
        request_info = cur.fetchone()
        if not request_info:
            return jsonify({'error': 'Request not found or already processed'}), 404
        
        group_id, user_id, group_name = request_info
        
        # Check if approver has permission
        cur.execute("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, approver_id))
        approver_role = cur.fetchone()
        
        if not approver_role or approver_role[0] not in ['owner', 'admin']:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        # Add user to group
        cur.execute("""
            INSERT INTO group_members (group_id, user_id, role, joined_at)
            VALUES (%s, %s, 'member', %s)
        """, (group_id, user_id, datetime.now()))
        
        # Update request status
        cur.execute("""
            UPDATE group_join_requests 
            SET status = 'approved', updated_at = %s
            WHERE id = %s
        """, (datetime.now(), request_id))
        
        conn.commit()
        return jsonify({'message': f'User {user_id} approved to join {group_name}'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/reject_join_request', methods=['POST'])
def reject_join_request():
    data = request.json
    request_id = data.get('request_id')
    rejector_id = data.get('rejector_id')
    
    if not request_id or not rejector_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get request details
        cur.execute("""
            SELECT gjr.group_id, gjr.user_id
            FROM group_join_requests gjr
            WHERE gjr.id = %s AND gjr.status = 'pending'
        """, (request_id,))
        
        request_info = cur.fetchone()
        if not request_info:
            return jsonify({'error': 'Request not found or already processed'}), 404
        
        group_id, user_id = request_info
        
        # Check if rejector has permission
        cur.execute("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, rejector_id))
        rejector_role = cur.fetchone()
        
        if not rejector_role or rejector_role[0] not in ['owner', 'admin']:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        # Update request status
        cur.execute("""
            UPDATE group_join_requests 
            SET status = 'rejected', updated_at = %s
            WHERE id = %s
        """, (datetime.now(), request_id))
        
        conn.commit()
        return jsonify({'message': f'Join request from {user_id} rejected'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/user_invites/<user_id>')
def get_user_invites(user_id):
    """Get pending invites for a user"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT i.id, i.from_user_id, i.target_id, i.message, i.created_at, i.expires_at, g.name as group_name, u.avatar_color
            FROM invites i
            JOIN groups g ON i.target_id = g.id::text
            JOIN users u ON i.from_user_id = u.user_id
            WHERE i.to_user_id = %s AND i.invite_type = 'group' AND i.status = 'pending'
            AND i.expires_at > %s
            ORDER BY i.created_at DESC
        """, (user_id, datetime.utcnow()))
        
        invites = []
        for row in cur.fetchall():
            invite_message = f"Invitation to join group {row[6]} from {row[1]}"
            if row[3]:  # If there's a custom message
                invite_message += f": {row[3]}"
            
            invites.append({
                'invite_id': row[0],
                'from_user_id': row[1],
                'group_id': int(row[2]),
                'group_name': row[6],
                'message': invite_message,
                'custom_message': row[3],
                'created_at': row[4].isoformat(),
                'expires_at': row[5].isoformat(),
                'inviter_avatar_color': row[7]
            })
        
        return jsonify(invites)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/accept_invite', methods=['POST'])
def accept_invite():
    """Accept a group invite"""
    data = request.json
    invite_id = data.get('invite_id')
    user_id = data.get('user_id')
    
    if not invite_id or not user_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get invite details including inviter
        cur.execute("""
            SELECT i.target_id, i.to_user_id, i.from_user_id, g.name
            FROM invites i
            JOIN groups g ON i.target_id = g.id::text
            WHERE i.id = %s AND i.status = 'pending' AND i.expires_at > %s
        """, (invite_id, datetime.now()))
        
        invite_info = cur.fetchone()
        if not invite_info:
            return jsonify({'error': 'Invite not found or expired'}), 404
        
        group_id, invited_user_id, from_user_id, group_name = invite_info
        
        # Verify user is the invited user
        if invited_user_id != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Check if user is already a member
        cur.execute("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
        if cur.fetchone():
            return jsonify({'error': 'Already a member of this group'}), 400
        
        # Add user to group
        cur.execute("""
            INSERT INTO group_members (group_id, user_id, role, joined_at)
            VALUES (%s, %s, 'member', %s)
        """, (group_id, user_id, datetime.now()))
        
        # Delete invite permanently instead of updating status
        cur.execute("DELETE FROM invites WHERE id = %s", (invite_id,))
        
        conn.commit()
        
        # Send notification to inviter (Redis notification)
        try:
            import redis
            import json
            redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
            notification_msg = f"{user_id} accepted your invite to join {group_name}"
            redis_client.publish(f"user_notifications:{from_user_id}", json.dumps({
                'type': 'group_invite_accepted',
                'from_user_id': user_id,
                'group_name': group_name,
                'group_id': int(group_id),
                'message': notification_msg
            }))
            
            # Send invite status update
            redis_client.publish(f"user_notifications:{from_user_id}", json.dumps({
                'type': 'invite_status_update',
                'invite_id': invite_id,
                'status': 'accepted',
                'invite_type': 'group'
            }))
        except Exception as e:
            print(f"Failed to send notification: {e}")
        
        return jsonify({'message': f'Successfully joined {group_name}', 'group_id': int(group_id)})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/decline_invite', methods=['POST'])
def decline_invite():
    """Decline a group invite"""
    data = request.json
    invite_id = data.get('invite_id')
    user_id = data.get('user_id')
    
    if not invite_id or not user_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get invite details including inviter
        cur.execute("""
            SELECT i.to_user_id, i.from_user_id, g.name
            FROM invites i
            JOIN groups g ON i.target_id = g.id::text
            WHERE i.id = %s AND i.status = 'pending'
        """, (invite_id,))
        
        invite_info = cur.fetchone()
        if not invite_info:
            return jsonify({'error': 'Invite not found'}), 404
        
        invited_user_id, from_user_id, group_name = invite_info
        
        # Verify user is the invited user
        if invited_user_id != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Delete invite permanently instead of updating status
        cur.execute("DELETE FROM invites WHERE id = %s", (invite_id,))
        
        conn.commit()
        
        # Send notification to inviter
        try:
            import redis
            import json
            redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
            notification_msg = f"{user_id} declined your invite to join {group_name}"
            redis_client.publish(f"user_notifications:{from_user_id}", json.dumps({
                'type': 'group_invite_declined',
                'from_user_id': user_id,
                'group_name': group_name,
                'message': notification_msg
            }))
            
            # Send invite status update
            redis_client.publish(f"user_notifications:{from_user_id}", json.dumps({
                'type': 'invite_status_update',
                'invite_id': invite_id,
                'status': 'declined',
                'invite_type': 'group'
            }))
        except Exception as e:
            print(f"Failed to send notification: {e}")
        
        return jsonify({'message': f'Declined invite to {group_name}'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
