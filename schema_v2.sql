-- YouTube Learning Orchestrator - Clean Schema v2
-- Eliminates foreign key conflicts by using auth.uid() directly (no custom users table)

-- 1. Videos (Source Content) - Public read
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    youtube_url TEXT UNIQUE NOT NULL,
    title TEXT,
    transcript TEXT,
    processed_status TEXT DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Modules (Learning Materials) - Public read
CREATE TABLE IF NOT EXISTS modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    summary TEXT,
    key_concepts JSONB,
    transfer_scenarios JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Roadmaps (Per-user learning paths) - User-owned
CREATE TABLE IF NOT EXISTS roadmaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,  -- auth.uid(), NO foreign key to avoid sync issues
    sequence JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- 4. Sessions (Learning sessions) - User-owned
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,  -- auth.uid(), NO foreign key
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

-- 5. Progress (Mastery tracking) - User-owned
CREATE TABLE IF NOT EXISTS progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,  -- auth.uid(), NO foreign key
    module_id UUID REFERENCES modules(id) ON DELETE CASCADE,
    mastery_score FLOAT DEFAULT 0.0,
    delayed_recall_status TEXT DEFAULT 'pending',
    next_recall_at TIMESTAMP WITH TIME ZONE,
    last_recall_accuracy FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, module_id)
);

-- Enable RLS on user-owned tables
ALTER TABLE roadmaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE progress ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only access their own data
CREATE POLICY "roadmaps_user_policy" ON roadmaps
    FOR ALL 
    USING (auth.uid() = user_id) 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "sessions_user_policy" ON sessions
    FOR ALL 
    USING (auth.uid() = user_id) 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "progress_user_policy" ON progress
    FOR ALL 
    USING (auth.uid() = user_id) 
    WITH CHECK (auth.uid() = user_id);

-- Public read access for videos and modules (all users can learn from any content)
CREATE POLICY "videos_public_read" ON videos
    FOR SELECT USING (true);

CREATE POLICY "modules_public_read" ON modules
    FOR SELECT USING (true);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_videos_url ON videos(youtube_url);
CREATE INDEX IF NOT EXISTS idx_modules_video ON modules(video_id);
CREATE INDEX IF NOT EXISTS idx_roadmaps_user ON roadmaps(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_module ON sessions(module_id);
CREATE INDEX IF NOT EXISTS idx_progress_user ON progress(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_module ON progress(module_id);
