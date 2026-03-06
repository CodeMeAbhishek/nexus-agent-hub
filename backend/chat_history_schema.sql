-- ============================================================================
-- Chat History & Contexts Schema
-- Run this in Supabase SQL Editor to enable history features.
-- ============================================================================

-- 2. Chat Sessions Table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Chat Messages Table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- RLS Policies

-- Chat Sessions
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own sessions"
    ON chat_sessions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own sessions"
    ON chat_sessions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own sessions"
    ON chat_sessions FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own sessions"
    ON chat_sessions FOR DELETE
    USING (auth.uid() = user_id);

-- Chat Messages
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view messages in their sessions"
    ON chat_messages FOR SELECT
    USING (
        session_id IN (
            SELECT id FROM chat_sessions WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create messages in their sessions"
    ON chat_messages FOR INSERT
    WITH CHECK (
        session_id IN (
            SELECT id FROM chat_sessions WHERE user_id = auth.uid()
        )
    );

-- ============================================================================
-- Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id);
