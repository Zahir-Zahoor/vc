-- ChatApp Database Schema
-- Initialize all required tables for microservices

-- Groups table for group chats
CREATE TABLE IF NOT EXISTS groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    creator_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Group membership table
CREATE TABLE IF NOT EXISTS group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, user_id)
);

-- Messages table with delivery status
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    room_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    timestamp BIGINT NOT NULL,
    delivery_status VARCHAR(20) DEFAULT 'sent',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table for session management
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(255) PRIMARY KEY,
    status VARCHAR(50) DEFAULT 'offline',
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Unread messages table for unread count feature
CREATE TABLE IF NOT EXISTS unread_messages (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    room_id VARCHAR(255) NOT NULL,
    message_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, room_id, message_id)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_messages_room_id ON messages(room_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_delivery_status ON messages(delivery_status);
CREATE INDEX IF NOT EXISTS idx_group_members_group_id ON group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_group_members_user_id ON group_members(user_id);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_unread_messages_user_room ON unread_messages(user_id, room_id);
CREATE INDEX IF NOT EXISTS idx_unread_messages_message_id ON unread_messages(message_id);

-- Insert sample data for testing (optional)
INSERT INTO users (user_id, status) VALUES 
    ('alice', 'online'),
    ('bob', 'offline'),
    ('charlie', 'online')
ON CONFLICT (user_id) DO NOTHING;

-- Sample group for testing
INSERT INTO groups (name, creator_id) VALUES 
    ('General Chat', 'alice'),
    ('Development Team', 'bob')
ON CONFLICT DO NOTHING;

-- Add members to sample groups
INSERT INTO group_members (group_id, user_id, role) VALUES 
    (1, 'alice', 'admin'),
    (1, 'bob', 'member'),
    (1, 'charlie', 'member'),
    (2, 'bob', 'admin'),
    (2, 'alice', 'member')
ON CONFLICT (group_id, user_id) DO NOTHING;
