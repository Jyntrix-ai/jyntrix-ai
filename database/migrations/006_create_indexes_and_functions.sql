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
