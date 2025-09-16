# How to Connect Two Devices - Video Chat App

## 🔧 Setup Requirements

### 1. Server Setup
```bash
# Start the server
python run.py
# Server runs on: http://localhost:5000
```

### 2. Network Configuration
- **Same WiFi**: Both devices on same network
- **Public Server**: Deploy server with public IP
- **Local Network**: Use server machine's IP address

## 📱 Connection Methods

### Method 1: Web Browser (Any Device)
1. Open browser on both devices
2. Go to: `http://SERVER_IP:5000`
3. Enter same **Room Name** on both devices
4. Enter different **Username** on each device
5. Click **"Start Video"** on both devices

### Method 2: Android App + Web
1. **Device 1**: Install `videochat-app.apk`
2. **Device 2**: Open browser to `http://SERVER_IP:5000`
3. Both enter same **Room Name**
4. Both click **"Start Video"**

### Method 3: Two Android Devices
1. Install APK on both devices
2. Update server URL in app (if needed)
3. Both enter same **Room Name**
4. Both start video

## 🌐 Finding Server IP

### Local Network
```bash
# On server machine
ip addr show | grep inet
# Use the 192.168.x.x address
```

### Example Connection
- **Server IP**: `192.168.1.100`
- **URL**: `http://192.168.1.100:5000`
- **Room Name**: `meeting123`

## 📋 Step-by-Step Connection

### Device 1 (Host)
1. Start server: `python run.py`
2. Open app/browser
3. Enter Room: `meeting123`
4. Enter Username: `Alice`
5. Click "Start Video"
6. **Share room name with other user**

### Device 2 (Guest)
1. Open app/browser
2. Go to same server URL
3. Enter Room: `meeting123` (same as host)
4. Enter Username: `Bob`
5. Click "Start Video"
6. **Connection established!**

## 🔍 Troubleshooting

### Connection Issues
- **Same Room Name**: Both users must use identical room name
- **Network Access**: Ensure server IP is reachable from both devices
- **Firewall**: Check port 5000 is open
- **HTTPS**: Some browsers require HTTPS for camera access

### Testing Connection
```bash
# Test server accessibility
curl http://SERVER_IP:5000
# Should return HTML page
```

## 🚀 Quick Test

1. **Start Server**: `python run.py`
2. **Device 1**: Browser → `localhost:5000` → Room: `test` → Username: `user1`
3. **Device 2**: Browser → `SERVER_IP:5000` → Room: `test` → Username: `user2`
4. **Both Click**: "Start Video"
5. **Result**: Video call connected!

## 📱 Mobile App Configuration

If using Android APK, update server URL in:
`lib/services/socket_service.dart`
```dart
await _socketService.connect('http://YOUR_SERVER_IP:5000');
```

Then rebuild APK:
```bash
flutter build apk --release
```
