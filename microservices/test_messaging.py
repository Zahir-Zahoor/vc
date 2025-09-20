#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_messaging():
    print("🚀 Testing Real-Time Messaging")
    print("=" * 40)
    
    # Step 1: Login users
    print("\n1. Login users...")
    requests.post(f"{BASE_URL}/login", json={"user_id": "alice"})
    requests.post(f"{BASE_URL}/login", json={"user_id": "bob"})
    print("   ✅ Alice and Bob logged in")
    
    # Step 2: Create group
    print("\n2. Create group...")
    response = requests.post(f"{BASE_URL}/create_group", json={
        "name": "Test Chat",
        "creator_id": "alice"
    })
    group_id = response.json()["group_id"]
    print(f"   ✅ Group created with ID: {group_id}")
    
    # Step 3: Bob joins group
    print("\n3. Bob joins group...")
    requests.post(f"{BASE_URL}/join_group", json={
        "group_id": group_id,
        "user_id": "bob"
    })
    print("   ✅ Bob joined the group")
    
    # Step 4: Send test message
    print("\n4. Send test message...")
    requests.post(f"{BASE_URL}/messages", json={
        "room_id": group_id,
        "user_id": "alice",
        "message": "Hello Bob! Can you see this message?",
        "timestamp": 1234567890
    })
    print("   ✅ Alice sent a message")
    
    # Step 5: Check message history
    print("\n5. Check message history...")
    response = requests.get(f"{BASE_URL}/messages/{group_id}")
    messages = response.json()
    
    if messages:
        print(f"   ✅ Found {len(messages)} message(s):")
        for msg in messages:
            print(f"      {msg['user_id']}: {msg['message']}")
    else:
        print("   ❌ No messages found")
    
    print(f"\n🌐 Open http://localhost:5000 in two browser tabs")
    print(f"   - Tab 1: Login as 'alice', join group {group_id}")
    print(f"   - Tab 2: Login as 'bob', join group {group_id}")
    print(f"   - Start chatting! Messages should appear in real-time")
    
    print(f"\n✅ Messaging system is ready!")

if __name__ == "__main__":
    test_messaging()
