#!/usr/bin/env python3
# Quick HTTPS server for testing camera access

from flask import Flask
from flask_socketio import SocketIO
import ssl
import subprocess
import os

# Generate self-signed certificate
def generate_cert():
    if not os.path.exists('cert.pem'):
        print("Generating self-signed certificate...")
        subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:4096', 
            '-keyout', 'key.pem', '-out', 'cert.pem', 
            '-days', '365', '-nodes', '-subj', 
            '/C=US/ST=State/L=City/O=Org/CN=localhost'
        ])

if __name__ == '__main__':
    generate_cert()
    
    # Import your app
    from app import app, socketio
    
    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    print("🔒 HTTPS Server starting on https://YOUR_EC2_IP:5000")
    print("⚠️  Accept the security warning in browser for self-signed cert")
    
    socketio.run(app, host='0.0.0.0', port=5000, ssl_context=context, debug=True)
