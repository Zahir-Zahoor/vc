#!/usr/bin/env python3
import requests
import socketio
import time
import threading
import json

class VideoCallTester:
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
        self.results = []
    
    def log_result(self, test_name, success, message=""):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
    
    def test_health_endpoint(self):
        """Test server health check"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_result("Health Check", True, f"Status: {data['status']}")
            else:
                self.log_result("Health Check", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_result("Health Check", False, str(e))
    
    def test_main_page(self):
        """Test main page loads"""
        try:
            response = requests.get(self.base_url, timeout=5)
            if response.status_code == 200 and "VideoChat" in response.text:
                self.log_result("Main Page", True, "Page loads with title")
            else:
                self.log_result("Main Page", False, "Page not loading correctly")
        except Exception as e:
            self.log_result("Main Page", False, str(e))
    
    def test_socket_connection(self):
        """Test Socket.IO connection"""
        try:
            sio = socketio.Client()
            connected = False
            
            @sio.event
            def connect():
                nonlocal connected
                connected = True
            
            sio.connect(self.base_url)
            time.sleep(1)
            
            if connected:
                self.log_result("Socket Connection", True, "Connected successfully")
                sio.disconnect()
            else:
                self.log_result("Socket Connection", False, "Failed to connect")
        except Exception as e:
            self.log_result("Socket Connection", False, str(e))
    
    def test_room_functionality(self):
        """Test room join and messaging"""
        try:
            sio = socketio.Client()
            events_received = []
            
            @sio.event
            def user_joined(data):
                events_received.append(('user_joined', data))
            
            @sio.event
            def receive_message(data):
                events_received.append(('message', data))
            
            @sio.event
            def room_users(data):
                events_received.append(('room_users', data))
            
            sio.connect(self.base_url)
            sio.emit('join_room', {'username': 'TestUser', 'room': 'TestRoom'})
            time.sleep(0.5)
            
            sio.emit('send_message', {'message': 'Test message'})
            time.sleep(0.5)
            
            if len(events_received) >= 2:
                self.log_result("Room Functionality", True, f"Received {len(events_received)} events")
            else:
                self.log_result("Room Functionality", False, f"Only {len(events_received)} events received")
            
            sio.disconnect()
        except Exception as e:
            self.log_result("Room Functionality", False, str(e))
    
    def test_multiple_users(self):
        """Test multiple users in same room"""
        try:
            clients = []
            user_events = []
            
            def create_client(username):
                sio = socketio.Client()
                
                @sio.event
                def user_joined(data):
                    user_events.append(f"{username} saw {data['user']} join")
                
                @sio.event
                def receive_message(data):
                    user_events.append(f"{username} received: {data['message']}")
                
                sio.connect(self.base_url)
                sio.emit('join_room', {'username': username, 'room': 'MultiTest'})
                return sio
            
            # Create 2 clients
            client1 = create_client('User1')
            time.sleep(0.5)
            client2 = create_client('User2')
            time.sleep(0.5)
            
            # Send messages
            client1.emit('send_message', {'message': 'Hello from User1'})
            time.sleep(0.5)
            client2.emit('send_message', {'message': 'Hello from User2'})
            time.sleep(0.5)
            
            if len(user_events) >= 4:
                self.log_result("Multiple Users", True, f"Multi-user communication working")
            else:
                self.log_result("Multiple Users", False, f"Insufficient events: {len(user_events)}")
            
            client1.disconnect()
            client2.disconnect()
            
        except Exception as e:
            self.log_result("Multiple Users", False, str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting VideoChat Test Suite")
        print("=" * 50)
        
        self.test_health_endpoint()
        self.test_main_page()
        self.test_socket_connection()
        self.test_room_functionality()
        self.test_multiple_users()
        
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        
        passed = sum(1 for r in self.results if r['success'])
        total = len(self.results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("🎉 All tests passed! Application is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the logs above.")
        
        return passed == total

if __name__ == '__main__':
    tester = VideoCallTester()
    tester.run_all_tests()
