-- YouTube Learning Orchestrator v2 Schema
-- Optimizing for Durable Understanding

-- 1. Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- 2. Videos table (Source Truth)
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    youtube_url TEXT UNIQUE NOT NULL,
    title TEXT,
    transcript TEXT,
    processed_status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Modules (Teaching material)
CREATE TABLE IF NOT EXISTS modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    summary TEXT,
    key_concepts JSONB, -- List of concept objects
    transfer_scenarios JSONB, -- Novel cases for testing application
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Roadmap (Learning Sequence)
CREATE TABLE IF NOT EXISTS roadmaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    sequence JSONB, -- [{module_id, order, week}]
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Sessions (The multi-stage loop)
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    module_id UUID REFERENCES modules(id),
    
    -- Stage B: Reconstruction
    initial_explanation TEXT,
    
    -- Stage C: Attack & Repair
    attack_feedback JSONB, -- [{gap_identified, ai_question}]
    repaired_explanation TEXT,
    repair_delta_score FLOAT, -- Measured by AI (0-1)
    
    -- Stage D: Teaching
    teaching_provided TEXT,
    
    -- Stage E: Transfer
    transfer_attempt TEXT,
    transfer_success BOOLEAN,
    
    status TEXT DEFAULT 'in_progress', -- in_progress, completed, needs_recall
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Progress & Recall
CREATE TABLE IF NOT EXISTS progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    module_id UUID REFERENCES modules(id),
    mastery_score FLOAT DEFAULT 0.0,
    delayed_recall_status TEXT DEFAULT 'pending', 
    next_recall_at TIMESTAMP WITH TIME ZONE,
    last_recall_accuracy FLOAT,
    UNIQUE(user_id, module_id)
);

-- --- 7. Security (RLS) & Performance ---
-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE roadmaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE progress ENABLE ROW LEVEL SECURITY;

-- RLS Policies (users can only access their own data)
CREATE POLICY "Users can view own data" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own data" ON users
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can view own roadmaps" ON roadmaps
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own sessions" ON sessions
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own progress" ON progress
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_videos_url ON videos(youtube_url);
CREATE INDEX IF NOT EXISTS idx_roadmaps_user ON roadmaps(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_user ON progress(user_id);
