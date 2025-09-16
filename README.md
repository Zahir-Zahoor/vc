# Video Call & Chat Application

A minimal Python-based video calling and chat application using Flask, WebSockets, and WebRTC.

## Features

- Real-time video calling using WebRTC
- Text chat functionality
- Room-based communication
- Multiple users per room

## Quick Start

1. Run the application:
   ```bash
   python3 run.py
   ```

2. Open http://localhost:5000 in your browser

3. Enter a username and room name to join

4. Click "Start Video" to begin video calling

## Manual Setup

If you prefer to install dependencies manually:

```bash
pip3 install -r requirements.txt
python3 app.py
```

## Usage

- Multiple users can join the same room by using the same room name
- Video calls work peer-to-peer using WebRTC
- Chat messages are broadcast to all users in the room
- Camera access permission is required for video functionality

## Requirements

- Python 3.7+
- Modern web browser with WebRTC support
- Camera and microphone access
