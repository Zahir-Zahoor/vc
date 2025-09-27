-- ChatApp Database Schema - Enhanced with Authentication & User Management
-- Initialize all required tables for microservices

-- Users table with authentication credentials
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'offline',
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    avatar_color VARCHAR(7) DEFAULT '#00a884',
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Active sessions table for JWT/token management
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255),
    device_info TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(token_hash)
);

-- User contacts/relationships table
CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
    contact_user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'active', -- active, blocked
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, contact_user_id)
);

-- Invitations table for chat/group invites
CREATE TABLE IF NOT EXISTS invites (
    id SERIAL PRIMARY KEY,
    from_user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
    to_user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
    invite_type VARCHAR(20) NOT NULL, -- 'chat', 'group'
    target_id VARCHAR(255), -- group_id for group invites, null for chat
    status VARCHAR(20) DEFAULT 'pending', -- pending, accepted, rejected, expired
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '7 days')
);

-- Groups table for group chats with enhanced permissions
CREATE TABLE IF NOT EXISTS groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    creator_id VARCHAR(255) REFERENCES users(user_id),
    avatar_color VARCHAR(7) DEFAULT '#00a884',
    is_private BOOLEAN DEFAULT FALSE,
    max_members INTEGER DEFAULT 100,
    invite_link VARCHAR(255) UNIQUE,
    require_approval BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Group membership table with enhanced roles
CREATE TABLE IF NOT EXISTS group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member', -- owner, admin, member
    permissions JSONB DEFAULT '{"can_invite": false, "can_remove": false, "can_edit_group": false}',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, user_id)
);

-- Group join requests table for approval-based groups
CREATE TABLE IF NOT EXISTS group_join_requests (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, user_id)
);

-- Messages table with delivery status
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    room_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) REFERENCES users(user_id),
    message TEXT NOT NULL,
    timestamp BIGINT NOT NULL,
    delivery_status VARCHAR(20) DEFAULT 'sent',
    message_type VARCHAR(20) DEFAULT 'text', -- text, image, file, system
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Unread messages table for unread count feature
CREATE TABLE IF NOT EXISTS unread_messages (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
    room_id VARCHAR(255) NOT NULL,
    message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, room_id, message_id)
);

-- Deleted chats table for tracking when users delete chat history
CREATE TABLE IF NOT EXISTS deleted_chats (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    room_id VARCHAR(255) NOT NULL,
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, room_id)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_contacts_user_id ON contacts(user_id);
CREATE INDEX IF NOT EXISTS idx_contacts_contact_user_id ON contacts(contact_user_id);
CREATE INDEX IF NOT EXISTS idx_invites_to_user_id ON invites(to_user_id);
CREATE INDEX IF NOT EXISTS idx_invites_from_user_id ON invites(from_user_id);
CREATE INDEX IF NOT EXISTS idx_invites_status ON invites(status);
CREATE INDEX IF NOT EXISTS idx_messages_room_id ON messages(room_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_group_members_group_id ON group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_group_members_user_id ON group_members(user_id);
CREATE INDEX IF NOT EXISTS idx_unread_messages_user_room ON unread_messages(user_id, room_id);
CREATE INDEX IF NOT EXISTS idx_deleted_chats_user_room ON deleted_chats(user_id, room_id);

-- Insert sample data for testing
-- Note: Passwords are hashed with bcrypt for 'password123'
INSERT INTO users (user_id, email, password_hash, status, avatar_color, is_verified) VALUES 
    ('alice', 'alice@example.com', '$2b$12$9k31syqeqHUn4Io.U9cOTuMAcLYSN.6strbcFsWqCSbUfqo2AgXP6', 'online', '#e91e63', TRUE),
    ('bob', 'bob@example.com', '$2b$12$9k31syqeqHUn4Io.U9cOTuMAcLYSN.6strbcFsWqCSbUfqo2AgXP6', 'offline', '#2196f3', TRUE),
    ('charlie', 'charlie@example.com', '$2b$12$9k31syqeqHUn4Io.U9cOTuMAcLYSN.6strbcFsWqCSbUfqo2AgXP6', 'online', '#ff9800', TRUE)
ON CONFLICT (user_id) DO UPDATE SET
    email = EXCLUDED.email,
    avatar_color = EXCLUDED.avatar_color,
    is_verified = EXCLUDED.is_verified;

-- Sample contacts
INSERT INTO contacts (user_id, contact_user_id) VALUES 
    ('alice', 'bob'),
    ('bob', 'alice'),
    ('alice', 'charlie'),
    ('charlie', 'alice')
ON CONFLICT (user_id, contact_user_id) DO NOTHING;

-- Sample groups with enhanced structure
INSERT INTO groups (name, description, creator_id, avatar_color) VALUES 
    ('General Chat', 'Main discussion group', 'alice', '#00a884'),
    ('Development Team', 'Dev team coordination', 'bob', '#9c27b0')
ON CONFLICT DO NOTHING;

-- Add members to sample groups with roles
INSERT INTO group_members (group_id, user_id, role, permissions) VALUES 
    (1, 'alice', 'owner', '{"can_invite": true, "can_remove": true, "can_edit_group": true}'),
    (1, 'bob', 'admin', '{"can_invite": true, "can_remove": true, "can_edit_group": false}'),
    (1, 'charlie', 'member', '{"can_invite": false, "can_remove": false, "can_edit_group": false}'),
    (2, 'bob', 'owner', '{"can_invite": true, "can_remove": true, "can_edit_group": true}'),
    (2, 'alice', 'member', '{"can_invite": false, "can_remove": false, "can_edit_group": false}')
ON CONFLICT (group_id, user_id) DO NOTHING;
