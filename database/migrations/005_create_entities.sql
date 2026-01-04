-- Migration: 005_create_entities
-- Description: Create entities and entity_relations tables for knowledge graph
-- Created: 2026-01-04

-- Entities table (nodes in the knowledge graph)
CREATE TABLE IF NOT EXISTS public.entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('person', 'location', 'organization', 'date', 'event', 'concept', 'other')),
    description TEXT, -- Brief description of the entity
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
