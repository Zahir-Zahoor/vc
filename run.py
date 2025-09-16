#!/usr/bin/env python3
import subprocess
import sys
import os
from dotenv import load_dotenv

def install_requirements():
    """Install required packages"""
    print("Installing requirements...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])

def run_development():
    """Run in development mode"""
    load_dotenv()
    from app import app, socketio
    print("Starting VideoChat in development mode...")
    print("Open http://localhost:5000 in your browser")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

def run_production():
    """Run in production mode with Gunicorn"""
    print("Starting VideoChat in production mode...")
    print("Open http://localhost:5000 in your browser")
    subprocess.run([
        'gunicorn',
        '--config', 'gunicorn.conf.py',
        'app:app'
    ])

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'dev'
    
    install_requirements()
    
    if mode == 'prod' or mode == 'production':
        run_production()
    else:
        run_development()
