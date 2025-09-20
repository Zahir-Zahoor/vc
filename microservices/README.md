# Microservices Chat Application

A scalable real-time chat application built with Python Flask microservices architecture.

## Architecture

- **API Gateway** (Port 5000): Routes requests to appropriate services
- **WebSocket Service** (Port 5001): Handles real-time connections
- **Messaging Service** (Port 5002): Processes and delivers messages
- **Group Service** (Port 5003): Manages groups and memberships
- **Session Service** (Port 5004): Handles user sessions and presence

## Infrastructure

- **Redis**: Caching and real-time data
- **Kafka**: Message queue for reliable delivery
- **PostgreSQL**: Persistent data storage
- **Zookeeper**: Kafka coordination

## Quick Start

```bash
cd microservices
./start.sh
```

## Manual Start

```bash
# Start infrastructure
docker-compose up -d redis kafka zookeeper postgres

# Initialize database
docker-compose exec -T postgres psql -U chat -d chatapp < init.sql

# Start services
docker-compose up -d --build
```

## Usage

1. Open http://localhost:5000
2. Enter a User ID and click Login
3. Create or join a group
4. Start chatting!

## Health Check

```bash
curl http://localhost:5000/health
```

## API Endpoints

- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `POST /api/create_group` - Create new group
- `POST /api/join_group` - Join existing group
- `GET /api/groups/<user_id>` - Get user's groups
- `GET /api/messages/<user_id>` - Get pending messages
- `GET /api/status/<user_id>` - Get user status

## WebSocket Events

- `connect` - Client connection
- `join_room` - Join chat room
- `send_message` - Send message
- `receive_message` - Receive message
