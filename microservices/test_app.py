#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_microservices():
    print("🚀 Testing Microservices Chat Application")
    print("=" * 50)
    
    # Test 1: User Login
    print("\n1. Testing User Login...")
    response = requests.post(f"{BASE_URL}/login", json={"user_id": "alice"})
    print(f"   Login Alice: {response.json()}")
    
    response = requests.post(f"{BASE_URL}/login", json={"user_id": "bob"})
    print(f"   Login Bob: {response.json()}")
    
    # Test 2: Check User Status
    print("\n2. Testing User Status...")
    response = requests.get(f"{BASE_URL}/status/alice")
    print(f"   Alice Status: {response.json()}")
    
    # Test 3: Create Group
    print("\n3. Testing Group Creation...")
    response = requests.post(f"{BASE_URL}/create_group", json={
        "name": "Python Developers",
        "creator_id": "alice"
    })
    group_data = response.json()
    group_id = group_data["group_id"]
    print(f"   Created Group: {group_data}")
    
    # Test 4: Join Group
    print("\n4. Testing Group Join...")
    response = requests.post(f"{BASE_URL}/join_group", json={
        "group_id": group_id,
        "user_id": "bob"
    })
    print(f"   Bob Joined: {response.json()}")
    
    # Test 5: Get User Groups
    print("\n5. Testing Get Groups...")
    response = requests.get(f"{BASE_URL}/groups/alice")
    print(f"   Alice's Groups: {response.json()}")
    
    response = requests.get(f"{BASE_URL}/groups/bob")
    print(f"   Bob's Groups: {response.json()}")
    
    # Test 6: Health Check
    print("\n6. Testing Health Check...")
    response = requests.get("http://localhost:5000/health")
    print(f"   System Health: {response.json()}")
    
    print("\n✅ Microservices Testing Complete!")
    print("\n📱 Access the chat interface at: http://localhost:5000")
    print("🔧 Individual service ports:")
    print("   - API Gateway: 5000")
    print("   - WebSocket: 5001 (needs Kafka)")
    print("   - Messaging: 5002 (needs Kafka)")
    print("   - Groups: 5003 ✅")
    print("   - Sessions: 5004 ✅")

if __name__ == "__main__":
    test_microservices()
