-- Migration: 001_create_profiles
-- Description: Create profiles table for user data
-- Created: 2026-01-04

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Profiles table (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    avatar_url TEXT,
    preferences JSONB DEFAULT '{
        "theme": "system",
        "language": "en",
        "notifications": true,
        "memory_enabled": true
    }'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON public.profiles(created_at DESC);

-- Enable Row Level Security
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON public.profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);

-- Function to auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, display_name)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'display_name', NEW.email)
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile on user signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_profiles_updated_at ON public.profiles;
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
-- Migration: 002_create_conversations
-- Description: Create conversations table for chat sessions
-- Created: 2026-01-04

CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT,
    summary TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON public.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_created ON public.conversations(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_last_message ON public.conversations(user_id, last_message_at DESC);

-- Enable Row Level Security
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own conversations"
    ON public.conversations FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own conversations"
    ON public.conversations FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own conversations"
    ON public.conversations FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own conversations"
    ON public.conversations FOR DELETE
    USING (auth.uid() = user_id);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_conversations_updated_at ON public.conversations;
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON public.conversations
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
-- Migration: 003_create_messages
-- Description: Create messages table (source of truth)
-- Created: 2026-01-04

CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON public.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_user ON public.messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created ON public.messages(conversation_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_messages_user_created ON public.messages(user_id, created_at DESC);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_messages_content_search
    ON public.messages USING gin(to_tsvector('english', content));

-- Enable Row Level Security
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own messages"
    ON public.messages FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own messages"
    ON public.messages FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Function to update conversation message count and last_message_at
CREATE OR REPLACE FUNCTION public.update_conversation_on_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.conversations
    SET
        message_count = message_count + 1,
        last_message_at = NEW.created_at,
        updated_at = NOW()
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger for message insert
DROP TRIGGER IF EXISTS on_message_created ON public.messages;
CREATE TRIGGER on_message_created
    AFTER INSERT ON public.messages
    FOR EACH ROW EXECUTE FUNCTION public.update_conversation_on_message();
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
-- Migration: 005_create_entities
-- Description: Create entities and entity_relations tables for knowledge graph
-- Created: 2026-01-04

-- Entities table (nodes in the knowledge graph)
CREATE TABLE IF NOT EXISTS public.entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('person', 'location', 'organization', 'date', 'event', 'concept', 'other')),
    normalized_name TEXT NOT NULL, -- Lowercase, trimmed for matching
    metadata JSONB DEFAULT '{}'::jsonb,
    mention_count INTEGER DEFAULT 1,
    last_mentioned_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint per user
    UNIQUE(user_id, normalized_name, type)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_entities_user ON public.entities(user_id);
CREATE INDEX IF NOT EXISTS idx_entities_user_type ON public.entities(user_id, type);
CREATE INDEX IF NOT EXISTS idx_entities_user_name ON public.entities(user_id, normalized_name);
CREATE INDEX IF NOT EXISTS idx_entities_mention_count ON public.entities(user_id, mention_count DESC);

-- Full-text search on entity names
CREATE INDEX IF NOT EXISTS idx_entities_name_search
    ON public.entities USING gin(to_tsvector('english', name));

-- Enable Row Level Security
ALTER TABLE public.entities ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own entities"
    ON public.entities FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own entities"
    ON public.entities FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own entities"
    ON public.entities FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own entities"
    ON public.entities FOR DELETE
    USING (auth.uid() = user_id);

CREATE POLICY "Service role has full access to entities"
    ON public.entities FOR ALL
    USING (auth.role() = 'service_role');

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_entities_updated_at ON public.entities;
CREATE TRIGGER update_entities_updated_at
    BEFORE UPDATE ON public.entities
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Entity Relations table (edges in the knowledge graph)
CREATE TABLE IF NOT EXISTS public.entity_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    source_entity_id UUID NOT NULL REFERENCES public.entities(id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES public.entities(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL, -- e.g., 'spouse', 'works_at', 'lives_in', 'friend_of'
    metadata JSONB DEFAULT '{}'::jsonb,
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    source_memory_id UUID REFERENCES public.memories(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate relations
    UNIQUE(user_id, source_entity_id, target_entity_id, relation_type)
);

-- Indexes for graph traversal
CREATE INDEX IF NOT EXISTS idx_relations_user ON public.entity_relations(user_id);
CREATE INDEX IF NOT EXISTS idx_relations_source ON public.entity_relations(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON public.entity_relations(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_user_source ON public.entity_relations(user_id, source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_user_type ON public.entity_relations(user_id, relation_type);

-- Enable Row Level Security
ALTER TABLE public.entity_relations ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own relations"
    ON public.entity_relations FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own relations"
    ON public.entity_relations FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own relations"
    ON public.entity_relations FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own relations"
    ON public.entity_relations FOR DELETE
    USING (auth.uid() = user_id);

CREATE POLICY "Service role has full access to relations"
    ON public.entity_relations FOR ALL
    USING (auth.role() = 'service_role');

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_relations_updated_at ON public.entity_relations;
CREATE TRIGGER update_relations_updated_at
    BEFORE UPDATE ON public.entity_relations
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Function to get related entities (graph traversal)
CREATE OR REPLACE FUNCTION public.get_related_entities(
    p_user_id UUID,
    p_entity_id UUID,
    p_max_depth INTEGER DEFAULT 2
)
RETURNS TABLE (
    entity_id UUID,
    entity_name TEXT,
    entity_type TEXT,
    relation_type TEXT,
    depth INTEGER
) AS $$
WITH RECURSIVE entity_graph AS (
    -- Base case: direct relations
    SELECT
        er.target_entity_id AS entity_id,
        e.name AS entity_name,
        e.type AS entity_type,
        er.relation_type,
        1 AS depth
    FROM public.entity_relations er
    JOIN public.entities e ON er.target_entity_id = e.id
    WHERE er.user_id = p_user_id AND er.source_entity_id = p_entity_id

    UNION

    -- Recursive case: follow relations
    SELECT
        er.target_entity_id,
        e.name,
        e.type,
        er.relation_type,
        eg.depth + 1
    FROM public.entity_relations er
    JOIN public.entities e ON er.target_entity_id = e.id
    JOIN entity_graph eg ON er.source_entity_id = eg.entity_id
    WHERE er.user_id = p_user_id AND eg.depth < p_max_depth
)
SELECT DISTINCT * FROM entity_graph;
$$ LANGUAGE sql SECURITY DEFINER;
-- Migration: 006_create_indexes_and_functions
-- Description: Additional indexes and utility functions
-- Created: 2026-01-04

-- ============================================
-- Additional Composite Indexes for Performance
-- ============================================

-- For hybrid search: memories by user with status
CREATE INDEX IF NOT EXISTS idx_memories_user_status_type
    ON public.memories(user_id, embedding_status, type);

-- For context retrieval: recent memories
CREATE INDEX IF NOT EXISTS idx_memories_user_accessed
    ON public.memories(user_id, last_accessed_at DESC NULLS LAST);

-- For conversation loading: messages in order
CREATE INDEX IF NOT EXISTS idx_messages_conv_role_created
    ON public.messages(conversation_id, role, created_at DESC);

-- ============================================
-- Utility Functions
-- ============================================

-- Function to search memories with full-text search
CREATE OR REPLACE FUNCTION public.search_memories(
    p_user_id UUID,
    p_query TEXT,
    p_memory_types TEXT[] DEFAULT NULL,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    type TEXT,
    content TEXT,
    confidence FLOAT,
    importance FLOAT,
    access_count INTEGER,
    created_at TIMESTAMPTZ,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.type,
        m.content,
        m.confidence,
        m.importance,
        m.access_count,
        m.created_at,
        ts_rank(to_tsvector('english', m.content), plainto_tsquery('english', p_query)) AS rank
    FROM public.memories m
    WHERE m.user_id = p_user_id
        AND m.embedding_status = 'completed'
        AND (p_memory_types IS NULL OR m.type = ANY(p_memory_types))
        AND to_tsvector('english', m.content) @@ plainto_tsquery('english', p_query)
    ORDER BY rank DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get recent working memory (last N messages)
CREATE OR REPLACE FUNCTION public.get_working_memory(
    p_user_id UUID,
    p_conversation_id UUID,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    role TEXT,
    content TEXT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.role,
        m.content,
        m.created_at
    FROM public.messages m
    WHERE m.user_id = p_user_id
        AND m.conversation_id = p_conversation_id
    ORDER BY m.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user profile memory
CREATE OR REPLACE FUNCTION public.get_profile_memory(p_user_id UUID)
RETURNS TABLE (
    id UUID,
    content TEXT,
    confidence FLOAT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.content,
        m.confidence,
        m.created_at
    FROM public.memories m
    WHERE m.user_id = p_user_id
        AND m.type = 'profile'
        AND m.embedding_status = 'completed'
    ORDER BY m.importance DESC, m.created_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to clean up old episodic memories (for maintenance)
CREATE OR REPLACE FUNCTION public.cleanup_old_memories(
    p_user_id UUID,
    p_days_old INTEGER DEFAULT 90,
    p_keep_important BOOLEAN DEFAULT true
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.memories
    WHERE user_id = p_user_id
        AND type = 'episodic'
        AND created_at < NOW() - (p_days_old || ' days')::INTERVAL
        AND (NOT p_keep_important OR importance < 0.7);

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get pending embedding jobs
CREATE OR REPLACE FUNCTION public.get_pending_embeddings(p_limit INTEGER DEFAULT 100)
RETURNS TABLE (
    id UUID,
    user_id UUID,
    content TEXT,
    type TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.user_id,
        m.content,
        m.type
    FROM public.memories m
    WHERE m.embedding_status = 'pending'
    ORDER BY m.created_at ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update embedding status
CREATE OR REPLACE FUNCTION public.update_embedding_status(
    p_memory_id UUID,
    p_status TEXT,
    p_error TEXT DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    UPDATE public.memories
    SET
        embedding_status = p_status,
        embedding_error = p_error,
        updated_at = NOW()
    WHERE id = p_memory_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- Statistics View
-- ============================================

CREATE OR REPLACE VIEW public.user_memory_stats AS
SELECT
    user_id,
    COUNT(*) FILTER (WHERE type = 'profile') AS profile_count,
    COUNT(*) FILTER (WHERE type = 'semantic') AS semantic_count,
    COUNT(*) FILTER (WHERE type = 'episodic') AS episodic_count,
    COUNT(*) FILTER (WHERE type = 'procedural') AS procedural_count,
    COUNT(*) AS total_memories,
    COUNT(*) FILTER (WHERE embedding_status = 'completed') AS embedded_count,
    COUNT(*) FILTER (WHERE embedding_status = 'pending') AS pending_count,
    AVG(confidence) AS avg_confidence,
    AVG(importance) AS avg_importance
FROM public.memories
GROUP BY user_id;

-- Grant access to the view
GRANT SELECT ON public.user_memory_stats TO authenticated;
