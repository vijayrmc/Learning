-- COMPLETE MIGRATION SCRIPT FOR SCHEMA V2
-- Run this entire script in your Supabase SQL Editor

-- ============================================
-- STEP 1: Drop ALL old tables and policies
-- ============================================

-- Drop policies first
DROP POLICY IF EXISTS "Users can view own data" ON users;
DROP POLICY IF EXISTS "Users can update own data" ON users;
DROP POLICY IF EXISTS "Users can view own roadmaps" ON roadmaps;
DROP POLICY IF EXISTS "Users can manage own roadmaps" ON roadmaps;
DROP POLICY IF EXISTS "Users can view own sessions" ON sessions;
DROP POLICY IF EXISTS "Users can manage own sessions" ON sessions;
DROP POLICY IF EXISTS "Users can view own progress" ON progress;
DROP POLICY IF EXISTS "Users can manage own progress" ON progress;
DROP POLICY IF EXISTS "videos_public_read" ON videos;
DROP POLICY IF EXISTS "modules_public_read" ON modules;

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS progress CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS roadmaps CASCADE;
DROP TABLE IF EXISTS modules CASCADE;
DROP TABLE IF EXISTS videos CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================
-- STEP 2: Create new schema v2
-- ============================================

-- 1. Videos (Source Content)
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    youtube_url TEXT UNIQUE NOT NULL,
    title TEXT,
    transcript TEXT,
    processed_status TEXT DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Modules (Learning Materials)
CREATE TABLE modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    summary TEXT,
    key_concepts JSONB,
    transfer_scenarios JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Roadmaps (Per-user, NO FK to users table)
CREATE TABLE roadmaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    sequence JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- 4. Sessions (Per-user, NO FK to users table)
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    module_id UUID REFERENCES modules(id) ON DELETE CASCADE,
    initial_explanation TEXT,
    attack_feedback JSONB,
    repaired_explanation TEXT,
    repair_delta_score FLOAT,
    teaching_provided TEXT,
    transfer_attempt TEXT,
    transfer_success BOOLEAN,
    reconstruction_attempts INTEGER DEFAULT 0,
    attack_attempts INTEGER DEFAULT 0,
    status TEXT DEFAULT 'in_progress',
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Progress (Per-user, NO FK to users table)
CREATE TABLE progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    module_id UUID REFERENCES modules(id) ON DELETE CASCADE,
    mastery_score FLOAT DEFAULT 0.0,
    delayed_recall_status TEXT DEFAULT 'pending',
    next_recall_at TIMESTAMP WITH TIME ZONE,
    last_recall_accuracy FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, module_id)
);

-- ============================================
-- STEP 3: Enable RLS
-- ============================================

ALTER TABLE roadmaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE progress ENABLE ROW LEVEL SECURITY;

-- ============================================
-- STEP 4: Create RLS Policies
-- ============================================

-- Roadmaps: Users own their data
CREATE POLICY "roadmaps_user_policy" ON roadmaps
    FOR ALL 
    USING (auth.uid() = user_id) 
    WITH CHECK (auth.uid() = user_id);

-- Sessions: Users own their data
CREATE POLICY "sessions_user_policy" ON sessions
    FOR ALL 
    USING (auth.uid() = user_id) 
    WITH CHECK (auth.uid() = user_id);

-- Progress: Users own their data
CREATE POLICY "progress_user_policy" ON progress
    FOR ALL 
    USING (auth.uid() = user_id) 
    WITH CHECK (auth.uid() = user_id);

-- Videos: Public read
CREATE POLICY "videos_public_read" ON videos
    FOR SELECT USING (true);

-- Modules: Public read
CREATE POLICY "modules_public_read" ON modules
    FOR SELECT USING (true);

-- ============================================
-- STEP 5: Create Indexes
-- ============================================

CREATE INDEX idx_videos_url ON videos(youtube_url);
CREATE INDEX idx_modules_video ON modules(video_id);
CREATE INDEX idx_roadmaps_user ON roadmaps(user_id);
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_module ON sessions(module_id);
CREATE INDEX idx_progress_user ON progress(user_id);
CREATE INDEX idx_progress_module ON progress(module_id);

-- ============================================
-- DONE! Schema v2 is now active.
-- ============================================
