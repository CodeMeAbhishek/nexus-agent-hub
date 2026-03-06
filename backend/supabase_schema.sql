-- Nexus Agent Hub — Supabase Schema
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard → SQL Editor

-- ============================================================================
-- User Settings Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  theme VARCHAR(20) DEFAULT 'dark',
  default_model VARCHAR(50) DEFAULT 'gemini-2.0-flash',
  notifications_enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id)
);

-- ============================================================================
-- User Connections (Limb Credentials)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  limb_id VARCHAR(50) NOT NULL,           -- 'notion', 'slack', 'gmail', etc.
  is_enabled BOOLEAN DEFAULT true,
  encrypted_credentials TEXT,              -- Fernet-encrypted JSON
  last_verified_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, limb_id)
);

-- ============================================================================
-- Conversations History (Optional)
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  title VARCHAR(255),
  messages JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Row Level Security (RLS)
-- Users can only access their own data
-- ============================================================================
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Policies for user_settings
CREATE POLICY "Users can view own settings" ON user_settings
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own settings" ON user_settings
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own settings" ON user_settings
  FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own settings" ON user_settings
  FOR DELETE USING (auth.uid() = user_id);

-- Policies for user_connections
CREATE POLICY "Users can view own connections" ON user_connections
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own connections" ON user_connections
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own connections" ON user_connections
  FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own connections" ON user_connections
  FOR DELETE USING (auth.uid() = user_id);

-- Policies for conversations
CREATE POLICY "Users can view own conversations" ON conversations
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own conversations" ON conversations
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own conversations" ON conversations
  FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own conversations" ON conversations
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================================================
-- Indexes for performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_user_connections_user_id ON user_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_user_connections_limb ON user_connections(user_id, limb_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
