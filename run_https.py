#!/usr/bin/env python3
import ssl
import subprocess
import os
from app import app, socketio

# Generate self-signed certificate
if not os.path.exists('cert.pem'):
    print("Generating certificate...")
    subprocess.run([
        'openssl', 'req', '-x509', '-newkey', 'rsa:2048', 
        '-keyout', 'key.pem', '-out', 'cert.pem', 
        '-days', '30', '-nodes', '-subj', 
        '/CN=3.89.180.39'
    ], check=True)

# SSL context
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('cert.pem', 'key.pem')

print("🔒 HTTPS Server running on: https://3.89.180.39:5000")
print("⚠️  Accept browser security warning to enable camera")

socketio.run(app, host='0.0.0.0', port=5000, ssl_context=context)
