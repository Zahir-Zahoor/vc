#!/usr/bin/env python3
import os
from app import app, socketio

# Generate certificate if needed
if not os.path.exists('cert.pem'):
    import subprocess
    print("Generating certificate...")
    subprocess.run([
        'openssl', 'req', '-x509', '-newkey', 'rsa:2048', 
        '-keyout', 'key.pem', '-out', 'cert.pem', 
        '-days', '30', '-nodes', '-subj', '/CN=3.89.180.39'
    ])

print("🔒 HTTPS Server running on: https://3.89.180.39:5000")
print("⚠️  Accept browser security warning to enable camera")

# Use gevent-websocket for better SSL support
socketio.run(app, 
    host='0.0.0.0', 
    port=5000, 
    keyfile='key.pem', 
    certfile='cert.pem',
    async_mode='gevent'
)
