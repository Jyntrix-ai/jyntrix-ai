-- Migration: 004_create_memories
-- Description: Create memories table with all memory types
-- Created: 2026-01-04

-- Memory type enum (for documentation, using CHECK constraint instead)
-- Types: profile, semantic, episodic, procedural

CREATE TABLE IF NOT EXISTS public.memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('profile', 'semantic', 'episodic', 'procedural')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Source tracking
    source_message_id UUID REFERENCES public.messages(id) ON DELETE SET NULL,
    source_conversation_id UUID REFERENCES public.conversations(id) ON DELETE SET NULL,

    -- Relevance scoring
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    importance FLOAT DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),

    -- Access tracking (for frequency scoring)
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,

    -- Embedding status
    embedding_status TEXT DEFAULT 'pending' CHECK (embedding_status IN ('pending', 'processing', 'completed', 'failed')),
    embedding_error TEXT,

    -- Keywords for BM25 search
    keywords TEXT[] DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_memories_user ON public.memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_user_type ON public.memories(user_id, type);
CREATE INDEX IF NOT EXISTS idx_memories_user_created ON public.memories(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_embedding_status ON public.memories(embedding_status)
    WHERE embedding_status = 'pending';
CREATE INDEX IF NOT EXISTS idx_memories_importance ON public.memories(user_id, importance DESC);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_memories_content_search
    ON public.memories USING gin(to_tsvector('english', content));

-- Keywords array index
CREATE INDEX IF NOT EXISTS idx_memories_keywords ON public.memories USING gin(keywords);

-- Enable Row Level Security
ALTER TABLE public.memories ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own memories"
    ON public.memories FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own memories"
    ON public.memories FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own memories"
    ON public.memories FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own memories"
    ON public.memories FOR DELETE
    USING (auth.uid() = user_id);

-- Service role policy for workers (bypasses RLS)
CREATE POLICY "Service role has full access"
    ON public.memories FOR ALL
    USING (auth.role() = 'service_role');

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_memories_updated_at ON public.memories;
CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON public.memories
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Function to increment access count
CREATE OR REPLACE FUNCTION public.increment_memory_access(memory_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE public.memories
    SET
        access_count = access_count + 1,
        last_accessed_at = NOW()
    WHERE id = memory_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
