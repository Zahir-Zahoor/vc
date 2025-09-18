# Video Chat Application

A real-time video calling application built with Flask-SocketIO and WebRTC, featuring Google Meet-inspired UI and peer-to-peer video streaming.

## Features

- **Real-time Video Calls**: WebRTC-based P2P video streaming
- **Group Meetings**: Support for up to 50 participants per room
- **Screen Sharing**: Share your screen with other participants
- **Live Chat**: Real-time messaging with typing indicators
- **Modern UI**: Google Meet-inspired responsive design
- **Cross-platform**: Works on desktop and mobile browsers

## Tech Stack

**Backend:**
- Flask + Flask-SocketIO for real-time communication
- Redis for session management (with in-memory fallback)
- WebRTC signaling server
- Rate limiting and security features

**Frontend:**
- Vanilla JavaScript with WebRTC APIs
- Socket.IO client for real-time events
- Responsive CSS Grid layout
- Modern browser media APIs

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd videoapp

# Start with Docker Compose
docker-compose up -d

# Access the application
open http://localhost:5000
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SECRET_KEY=your_secret_key
export DEBUG=true

# Run the application
python app.py
```

## Environment Variables

```bash
SECRET_KEY=your_production_secret_key
DEBUG=false
PORT=5000
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Usage

1. **Join a Meeting**: Enter your name and room ID
2. **Start Video**: Click camera button to enable video
3. **Share Screen**: Use screen share button to present
4. **Chat**: Toggle chat sidebar for messaging
5. **Invite Others**: Copy meeting link to share

## API Endpoints

- `GET /` - Main application interface
- `GET /health` - Health check endpoint
- `GET /api/room/<room_id>/info` - Room information
- `WebSocket /socket.io/` - Real-time communication

## WebRTC Events

**Client to Server:**
- `join_room` - Join a meeting room
- `send_message` - Send chat message
- `offer/answer/ice_candidate` - WebRTC signaling
- `video_started/stopped` - Video state changes

**Server to Client:**
- `room_joined` - Successful room join
- `user_joined/left` - Participant updates
- `receive_message` - Chat messages
- `offer/answer/ice_candidate` - WebRTC signaling

## Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

*Requires HTTPS for camera/microphone access in production*

## Deployment

### Production Setup

```bash
# Build Docker image
docker build -t videoapp .

# Run with production settings
docker run -d \
  -p 5000:5000 \
  -e SECRET_KEY=production_key \
  -e REDIS_HOST=redis_server \
  videoapp
```

### HTTPS Configuration

For production deployment, ensure HTTPS is enabled as WebRTC requires secure contexts for camera/microphone access.

## Security Features

- Rate limiting (200 requests/day, 50/hour)
- Input validation and sanitization
- Session management with Redis
- Room capacity limits (50 users max)
- CORS protection

## Troubleshooting

**Camera/Microphone Issues:**
- Ensure HTTPS in production
- Check browser permissions
- Verify device availability

**Connection Problems:**
- Check firewall settings
- Verify STUN/TURN server access
- Monitor browser console for errors

**Performance Issues:**
- Limit participants per room
- Check network bandwidth
- Monitor server resources

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details
