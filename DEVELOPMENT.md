# Video Chat App - Development Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Flutter SDK 3.24.5+
- Android SDK (API 21+)
- Java JDK 17

### Backend Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python run.py

# Run with auto-reload
python app.py
```

### Flutter Development
```bash
cd videochat_new

# Get dependencies
flutter pub get

# Run on device/emulator
flutter run

# Build APK
flutter build apk --release
```

## 📁 Project Structure

```
videoapp/
├── app.py              # Flask server
├── run.py              # Production runner
├── templates/          # Web interface
├── videochat_new/      # Flutter app
│   ├── lib/
│   │   ├── main.dart
│   │   ├── screens/
│   │   └── services/
│   └── android/
└── videochat-app.apk   # Built APK
```

## 🔧 Development Setup

### Environment Variables
```bash
# .env
FLASK_ENV=development
PORT=5000
```

### Flutter Dependencies
```yaml
dependencies:
  flutter_webrtc: ^0.9.48
  socket_io_client: ^2.0.3+1
  permission_handler: ^11.0.1
  shared_preferences: ^2.2.2
```

## 🛠 Common Tasks

### Add New Features
1. Backend: Add routes in `app.py`
2. Frontend: Add screens in `lib/screens/`
3. Update Socket.IO events in both

### Update Server URL
Edit `lib/services/socket_service.dart`:
```dart
await _socketService.connect('http://YOUR_SERVER_IP:5000');
```

### Debug Issues
```bash
# Flutter logs
flutter logs

# Python logs
python app.py --debug
```

## 📱 Testing

### Web Testing
- Open `http://localhost:5000`
- Use `browser_test.html` for WebRTC testing

### Mobile Testing
- Install APK on Android device
- Ensure server is accessible from device network

## 🚢 Deployment

### Production Build
```bash
# Backend
gunicorn -c gunicorn.conf.py app:app

# Flutter
flutter build apk --release
```

### Docker
```bash
docker-compose up -d
```

## 🔍 Troubleshooting

### Common Issues
- **WebRTC not working**: Check HTTPS/localhost requirements
- **Socket connection failed**: Verify server URL and network
- **APK build fails**: Ensure Android SDK properly configured
- **Permissions denied**: Check AndroidManifest.xml permissions

### Environment Setup
```bash
# Flutter path
export PATH="$PATH:/home/developer/flutter/bin"

# Android SDK
export ANDROID_HOME=/home/developer/android-sdk
export PATH="$PATH:$ANDROID_HOME/cmdline-tools/latest/bin"
```

## 📚 API Reference

### Socket.IO Events
- `join_room` - Join video room
- `leave_room` - Leave room
- `message` - Send chat message
- `offer`, `answer`, `ice_candidate` - WebRTC signaling

### REST Endpoints
- `GET /` - Web interface
- WebSocket on `/socket.io/`

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Test changes
4. Submit pull request

## 📄 License

MIT License - see LICENSE file
