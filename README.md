# Video Chat Application

A real-time video calling and chat application built with Flask, WebRTC, and Socket.IO.

## 🚀 Features

- **Real-time Video Calling** - WebRTC peer-to-peer connections
- **Multi-user Support** - Multiple users per room
- **Text Chat** - Real-time messaging alongside video
- **Room-based** - Join specific rooms with room names
- **Responsive Design** - Works on desktop and mobile
- **HTTPS Support** - Camera access with SSL certificates

## 📋 Requirements

- Python 3.7+
- Modern web browser with WebRTC support
- Camera and microphone permissions
- HTTPS for remote access (HTTP works on localhost)

## 🛠 Installation

### Local Development
```bash
# Clone repository
git clone https://github.com/Zahir-Zahoor/vc.git
cd vc

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
```

### Production (EC2/Server)
```bash
# Install dependencies
pip install -r requirements.txt

# For HTTPS (required for camera access)
# Generate SSL certificate
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 30 -nodes -subj "/CN=YOUR_SERVER_IP"

# Setup nginx proxy (recommended)
sudo yum install -y nginx
# Configure nginx with SSL termination

# Run server
python run.py
```

## 🌐 Usage

### Local Testing
1. Start server: `python app.py`
2. Open: `http://localhost:5000`
3. Enter username and room name
4. Click "Join Room"
5. Click "Start Video" to begin video call

### Multi-user Testing
1. **User 1**: Join room "meeting123" as "Alice"
2. **User 2**: Join same room "meeting123" as "Bob"  
3. **Both**: Click "Start Video"
4. **Result**: Video call established with separate video panels

### Remote Access (HTTPS Required)
1. Deploy to server with public IP
2. Setup HTTPS (nginx + SSL certificate)
3. Access: `https://YOUR_SERVER_IP:5000`
4. Accept SSL certificate warning
5. Allow camera/microphone permissions

## 🏗 Architecture

### Backend (Flask + Socket.IO)
- **Flask**: Web server and API
- **Socket.IO**: Real-time communication
- **WebRTC Signaling**: Offer/Answer/ICE candidate exchange

### Frontend (HTML + JavaScript)
- **WebRTC**: Peer-to-peer video connections
- **Socket.IO Client**: Real-time messaging
- **Responsive UI**: CSS Grid layout for video panels

### Key Components
```
app.py              # Flask server with Socket.IO handlers
templates/index.html # Frontend UI and WebRTC logic
run.py              # Production server launcher
requirements.txt    # Python dependencies
```

## 🔧 Configuration

### Environment Variables
```bash
FLASK_ENV=development  # or production
PORT=5000             # Server port
```

### WebRTC Configuration
```javascript
const configuration = {
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
};
```

## 🐛 Troubleshooting

### Common Issues

**"Could not access camera/microphone"**
- **Cause**: HTTP on remote server
- **Fix**: Use HTTPS or test on localhost

**"Join Room not working"**
- **Cause**: JavaScript errors or network issues
- **Fix**: Check browser console (F12) for errors

**"Video not showing for other users"**
- **Cause**: WebRTC connection failed
- **Fix**: Check browser console for WebRTC errors, verify STUN server

**"SSL Certificate Error"**
- **Cause**: Self-signed certificate
- **Fix**: Accept certificate warning in browser

### Debug Steps
1. **Open browser console** (F12)
2. **Check for errors** in console
3. **Verify network connectivity**
4. **Test with localhost first**

### Server Logs
```bash
# Check application logs
tail -f /var/log/nginx/error.log

# Check if server is running
netstat -tlnp | grep :5000
```

## 📱 Mobile Support

### Android APK
- Flutter app available: `videochat-app.apk`
- Update server URL in `lib/services/socket_service.dart`
- Rebuild: `flutter build apk --release`

### Web Mobile
- Responsive design works on mobile browsers
- Requires HTTPS for camera access
- Touch-friendly interface

## 🚀 Deployment

### AWS EC2 Example
```bash
# Security Group: Allow ports 80, 443, 5000
# Install nginx for HTTPS termination
# Generate SSL certificate
# Configure nginx proxy to Flask app
```

### Docker (Optional)
```bash
# Build image
docker build -t videochat .

# Run container
docker run -p 5000:5000 videochat
```

## 🔒 Security

### HTTPS Setup
```bash
# Self-signed certificate (development)
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 30 -nodes

# Let's Encrypt (production)
sudo certbot --nginx -d yourdomain.com
```

### Best Practices
- Use HTTPS in production
- Validate user inputs
- Rate limit connections
- Monitor server resources

## 📊 Performance

### Optimization Tips
- Use nginx for static files
- Enable gzip compression
- Use CDN for assets
- Monitor WebRTC connection quality

### Scaling
- Use Redis for session storage
- Load balance multiple Flask instances
- Use TURN servers for NAT traversal

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Test changes locally
4. Submit pull request

## 📄 License

MIT License - see LICENSE file

## 🆘 Support

### Quick Test
```bash
# Local test
python app.py
# Open: http://localhost:5000

# Remote test  
# Open: https://YOUR_SERVER_IP:5000
```

### Contact
- GitHub Issues: Report bugs and feature requests
- Documentation: Check DEVELOPMENT.md for detailed setup

---

**Last Updated**: January 2025  
**Version**: 1.0.0  
**Status**: Production Ready ✅
