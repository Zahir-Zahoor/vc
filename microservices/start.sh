#!/bin/bash

echo "Starting microservices chat application..."

# Start infrastructure services
docker-compose up -d redis kafka zookeeper postgres

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Initialize database
docker-compose exec -T postgres psql -U chat -d chatapp < init.sql

# Start application services
docker-compose up -d --build

echo "Application started!"
echo "Access the chat at: http://localhost:5000"
echo "Health check: http://localhost:5000/health"
