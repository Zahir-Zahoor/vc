#!/bin/bash
# HTTPS Setup for EC2 Video Chat App

echo "Setting up HTTPS for video chat app..."

# Install certbot
sudo apt update
sudo apt install -y certbot python3-certbot-nginx nginx

# Create nginx config
sudo tee /etc/nginx/sites-available/videochat << EOF
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/videochat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

echo "Setup complete! Now get SSL certificate:"
echo "sudo certbot --nginx -d YOUR_DOMAIN"
