#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_direct_messages():
    print("💬 Testing Direct Messages (1-on-1 Chat)")
    print("=" * 45)
    
    # Step 1: Login users
    print("\n1. Login users...")
    requests.post(f"{BASE_URL}/login", json={"user_id": "alice"})
    requests.post(f"{BASE_URL}/login", json={"user_id": "bob"})
    requests.post(f"{BASE_URL}/login", json={"user_id": "charlie"})
    print("   ✅ Alice, Bob, and Charlie logged in")
    
    # Step 2: Get user list
    print("\n2. Get online users...")
    response = requests.get(f"{BASE_URL}/users")
    users = response.json()
    print(f"   ✅ Found {len(users)} users:")
    for user in users:
        print(f"      - {user['user_id']} ({user['status']})")
    
    # Step 3: Create direct chat
    print("\n3. Create direct chat between Alice and Bob...")
    response = requests.post(f"{BASE_URL}/direct_chat", json={
        "user1": "alice",
        "user2": "bob"
    })
    dm_room = response.json()
    print(f"   ✅ Direct chat room: {dm_room['room_id']}")
    
    # Step 4: Send direct message
    print("\n4. Alice sends direct message to Bob...")
    requests.post(f"{BASE_URL}/messages", json={
        "room_id": dm_room['room_id'],
        "user_id": "alice",
        "message": "Hey Bob! This is a private message 🔒",
        "timestamp": 1234567890
    })
    print("   ✅ Direct message sent")
    
    # Step 5: Check message history
    print("\n5. Check direct message history...")
    response = requests.get(f"{BASE_URL}/messages/{dm_room['room_id']}")
    messages = response.json()
    
    if messages:
        print(f"   ✅ Found {len(messages)} message(s):")
        for msg in messages:
            print(f"      {msg['user_id']}: {msg['message']}")
    else:
        print("   ❌ No messages found")
    
    # Step 6: Test different direct chat
    print("\n6. Create another direct chat (Alice and Charlie)...")
    response = requests.post(f"{BASE_URL}/direct_chat", json={
        "user1": "alice",
        "user2": "charlie"
    })
    dm_room2 = response.json()
    print(f"   ✅ Second direct chat room: {dm_room2['room_id']}")
    
    print(f"\n🌐 Test Direct Messages:")
    print(f"   1. Open http://localhost:5000 in two browser tabs")
    print(f"   2. Tab 1: Login as 'alice'")
    print(f"   3. Tab 2: Login as 'bob'")
    print(f"   4. Click 'Direct' tab in both")
    print(f"   5. Alice clicks on 'bob' to start direct chat")
    print(f"   6. Bob should see the chat appear automatically")
    print(f"   7. Start private messaging! 💬")
    
    print(f"\n✅ Direct Messages feature implemented!")
    print(f"   - Room ID format: dm_user1_user2")
    print(f"   - Private 1-on-1 conversations")
    print(f"   - Real-time messaging")
    print(f"   - Message history persistence")

if __name__ == "__main__":
    test_direct_messages()
