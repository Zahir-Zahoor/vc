from flask import Flask, request, jsonify
import psycopg2
import redis
import os
import json

app = Flask(__name__)
redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

def get_db():
    return psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://chat:password@localhost:5432/chatapp'))

@app.route('/create_group', methods=['POST'])
def create_group():
    data = request.json
    group_name = data['name']
    creator_id = data['creator_id']
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO groups (name, creator_id) VALUES (%s, %s) RETURNING id",
        (group_name, creator_id)
    )
    group_id = cur.fetchone()[0]
    
    cur.execute(
        "INSERT INTO group_members (group_id, user_id, role) VALUES (%s, %s, 'admin')",
        (group_id, creator_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    redis_client.sadd(f'group:{group_id}:members', creator_id)
    return jsonify({'group_id': group_id})

@app.route('/join_group', methods=['POST'])
def join_group():
    data = request.json
    group_id = data['group_id']
    user_id = data['user_id']
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO group_members (group_id, user_id, role) VALUES (%s, %s, 'member')",
        (group_id, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    redis_client.sadd(f'group:{group_id}:members', user_id)
    return jsonify({'status': 'joined'})

@app.route('/get_groups/<user_id>')
def get_groups(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT g.id, g.name FROM groups g JOIN group_members gm ON g.id = gm.group_id WHERE gm.user_id = %s",
        (user_id,)
    )
    groups = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(groups)

@app.route('/health')
def health():
    return {'status': 'healthy'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
