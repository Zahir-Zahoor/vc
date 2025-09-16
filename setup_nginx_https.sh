#!/bin/bash
# Quick HTTPS setup with nginx

echo "Setting up nginx HTTPS proxy..."

# Install nginx
sudo yum install -y nginx

# Create nginx config
sudo tee /etc/nginx/nginx.conf << 'NGINX_EOF'
events { worker_connections 1024; }
http {
    server {
        listen 443 ssl;
        server_name 3.89.180.39;
        
        ssl_certificate /home/ec2-user/vc/cert.pem;
        ssl_certificate_key /home/ec2-user/vc/key.pem;
        
        location / {
            proxy_pass http://127.0.0.1:5000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
NGINX_EOF

# Start nginx
sudo systemctl enable nginx
sudo systemctl start nginx

echo "✅ Nginx HTTPS proxy setup complete!"
echo "🔒 Access: https://3.89.180.39:5000"
echo "🚀 Now run: python3 run.py"
