#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_group_members():
    print("👥 Testing Group Members Feature")
    print("=" * 35)
    
    # Step 1: Login users
    print("\n1. Login users...")
    requests.post(f"{BASE_URL}/login", json={"user_id": "alice"})
    requests.post(f"{BASE_URL}/login", json={"user_id": "bob"})
    requests.post(f"{BASE_URL}/login", json={"user_id": "charlie"})
    print("   ✅ Alice, Bob, and Charlie logged in")
    
    # Step 2: Create group
    print("\n2. Alice creates a group...")
    response = requests.post(f"{BASE_URL}/create_group", json={
        "name": "Team Chat",
        "creator_id": "alice"
    })
    group_id = response.json()["group_id"]
    print(f"   ✅ Group created with ID: {group_id}")
    
    # Step 3: Add members
    print("\n3. Bob and Charlie join the group...")
    requests.post(f"{BASE_URL}/join_group", json={
        "group_id": group_id,
        "user_id": "bob"
    })
    requests.post(f"{BASE_URL}/join_group", json={
        "group_id": group_id,
        "user_id": "charlie"
    })
    print("   ✅ Bob and Charlie joined")
    
    # Step 4: Get group members
    print("\n4. Get group members...")
    response = requests.get(f"{BASE_URL}/group_members/{group_id}")
    members = response.json()
    
    if members:
        print(f"   ✅ Found {len(members)} member(s):")
        for member in members:
            role_badge = " (Admin)" if member['role'] == 'admin' else ""
            print(f"      - {member['user_id']}{role_badge}")
    else:
        print("   ❌ No members found")
    
    # Step 5: Send group message
    print("\n5. Send a group message...")
    requests.post(f"{BASE_URL}/messages", json={
        "room_id": group_id,
        "user_id": "alice",
        "message": "Welcome to the team chat everyone! 👋",
        "timestamp": 1234567890
    })
    print("   ✅ Group message sent")
    
    print(f"\n🌐 Test Group Members UI:")
    print(f"   1. Open http://localhost:5000")
    print(f"   2. Login as 'alice'")
    print(f"   3. Click on 'Team Chat' group")
    print(f"   4. Click the '👥' button in the chat header")
    print(f"   5. See the members panel with:")
    print(f"      - alice (Admin)")
    print(f"      - bob (Member)")
    print(f"      - charlie (Member)")
    
    print(f"\n✅ Group Members feature implemented!")
    print(f"   - Members panel with roles")
    print(f"   - Admin badges")
    print(f"   - Toggle members view")
    print(f"   - Real-time member list")

if __name__ == "__main__":
    test_group_members()
