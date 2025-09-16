#!/bin/bash
echo "🔄 Restarting video chat server with WebRTC support..."

# Kill existing Python processes
pkill -f "python.*run.py"
pkill -f "python.*app.py"

# Wait a moment
sleep 2

# Start the server
echo "🚀 Starting server..."
python3 run.py &

echo "✅ Server restarted with WebRTC peer connections!"
echo "🌐 Access: https://3.89.180.39:5000"
echo "📱 Test with 2+ users in same room"
