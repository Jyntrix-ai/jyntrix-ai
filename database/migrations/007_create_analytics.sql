-- Migration: 007_create_analytics
-- Description: Create analytics tables for request tracking and performance metrics
-- Created: 2026-01-04

-- ============================================================================
-- Table: request_analytics
-- Purpose: Store per-request detailed timing and quality metrics
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.request_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE SET NULL,
    message_id UUID REFERENCES public.messages(id) ON DELETE SET NULL,

    -- Request identification
    request_id TEXT NOT NULL,  -- Correlates with X-Request-ID header
    request_type TEXT NOT NULL CHECK (request_type IN ('chat_stream', 'chat_complete', 'memory_search', 'context_build')),

    -- Latency metrics (all in milliseconds)
    total_time_ms FLOAT NOT NULL,
    ttfb_ms FLOAT,  -- Time to first byte (for streaming)

    -- Per-step timing breakdown (JSONB for flexibility)
    step_timings JSONB DEFAULT '{}'::jsonb,
    /*
    Expected structure:
    {
        "setup_time": 12.5,
        "query_analysis_time": 45.3,
        "vector_search_time": 23.1,
        "keyword_search_time": 18.7,
        "graph_search_time": 31.2,
        "profile_retrieval_time": 8.4,
        "recent_context_time": 15.6,
        "total_retrieval_time": 35.2,
        "ranking_time": 5.8,
        "context_building_time": 12.1,
        "llm_ttfb": 156.3,
        "llm_total_time": 2340.5,
        "save_response_time": 23.4
    }
    */

    -- Retrieval quality metrics
    retrieval_metrics JSONB DEFAULT '{}'::jsonb,
    /*
    Expected structure:
    {
        "vector_results_count": 8,
        "keyword_results_count": 5,
        "graph_results_count": 3,
        "profile_results_count": 12,
        "recent_results_count": 6,
        "total_raw_results": 34,
        "post_dedup_count": 22,
        "deduplication_removed": 12,
        "score_distribution": {
            "vector": {"min": 0.45, "max": 0.92, "avg": 0.71},
            "keyword": {"min": 0.32, "max": 0.88, "avg": 0.56},
            "combined": {"min": 0.38, "max": 0.89, "avg": 0.64}
        },
        "memories_by_type": {
            "profile": 5,
            "semantic": 8,
            "episodic": 6,
            "procedural": 3
        }
    }
    */

    -- Context building metrics
    context_metrics JSONB DEFAULT '{}'::jsonb,
    /*
    Expected structure:
    {
        "profile_tokens_used": 180,
        "semantic_tokens_used": 650,
        "episodic_tokens_used": 420,
        "procedural_tokens_used": 0,
        "entity_tokens_used": 85,
        "total_context_tokens": 1335,
        "token_budget_max": 2000,
        "truncation_occurred": false,
        "memories_included": 15,
        "memories_truncated": 2
    }
    */

    -- Query analysis results
    query_analysis JSONB DEFAULT '{}'::jsonb,
    /*
    Expected structure:
    {
        "intent": "recall",
        "requires_memory": true,
        "keywords_count": 5,
        "entities_count": 2,
        "memory_types_needed": ["semantic", "profile"]
    }
    */

    -- Status and error tracking
    status TEXT DEFAULT 'success' CHECK (status IN ('success', 'partial', 'error', 'timeout')),
    error_message TEXT,
    error_type TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Indexes for request_analytics
-- ============================================================================

-- Primary query patterns
CREATE INDEX IF NOT EXISTS idx_analytics_user
    ON public.request_analytics(user_id);

CREATE INDEX IF NOT EXISTS idx_analytics_user_created
    ON public.request_analytics(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analytics_created
    ON public.request_analytics(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analytics_request_type
    ON public.request_analytics(request_type, created_at DESC);

-- Filter by status (partial index for non-success)
CREATE INDEX IF NOT EXISTS idx_analytics_status
    ON public.request_analytics(status)
    WHERE status != 'success';

-- Filter by conversation
CREATE INDEX IF NOT EXISTS idx_analytics_conversation
    ON public.request_analytics(conversation_id)
    WHERE conversation_id IS NOT NULL;

-- Note: Partial index for "recent data" removed because NOW() is not immutable.
-- The idx_analytics_user_created index already covers this use case efficiently.

-- GIN indexes for JSONB queries
CREATE INDEX IF NOT EXISTS idx_analytics_step_timings
    ON public.request_analytics USING gin(step_timings);

CREATE INDEX IF NOT EXISTS idx_analytics_retrieval_metrics
    ON public.request_analytics USING gin(retrieval_metrics);

-- ============================================================================
-- Table: analytics_daily_aggregates
-- Purpose: Pre-computed daily statistics for dashboard performance
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.analytics_daily_aggregates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    date DATE NOT NULL,

    -- Request counts
    total_requests INTEGER DEFAULT 0,
    chat_stream_requests INTEGER DEFAULT 0,
    chat_complete_requests INTEGER DEFAULT 0,
    memory_search_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    error_requests INTEGER DEFAULT 0,

    -- Latency aggregates
    latency_stats JSONB DEFAULT '{}'::jsonb,
    /*
    Expected structure:
    {
        "total_time": {"p50": 234, "p95": 567, "p99": 890, "avg": 312, "min": 89, "max": 1234},
        "ttfb": {"p50": 145, "p95": 320, "p99": 456, "avg": 178, "min": 45, "max": 678},
        "retrieval": {"p50": 45, "p95": 120, "p99": 180, "avg": 67, "min": 12, "max": 245},
        "llm": {"p50": 180, "p95": 450, "p99": 780, "avg": 234, "min": 89, "max": 1100}
    }
    */

    -- Retrieval quality aggregates
    retrieval_stats JSONB DEFAULT '{}'::jsonb,
    /*
    Expected structure:
    {
        "avg_vector_results": 7.2,
        "avg_keyword_results": 4.8,
        "avg_total_results": 18.5,
        "avg_dedup_rate": 0.35,
        "avg_score": 0.67,
        "memories_by_type": {"profile": 234, "semantic": 567, "episodic": 345, "procedural": 89}
    }
    */

    -- Context usage aggregates
    context_stats JSONB DEFAULT '{}'::jsonb,
    /*
    Expected structure:
    {
        "avg_tokens_used": 1456,
        "avg_memories_included": 12,
        "truncation_rate": 0.08
    }
    */

    -- Intent distribution
    intent_distribution JSONB DEFAULT '{}'::jsonb,
    /* {"recall": 45, "question": 123, "conversation": 234, "command": 12} */

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint for upsert
    UNIQUE(user_id, date)
);

-- ============================================================================
-- Indexes for analytics_daily_aggregates
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_daily_agg_user
    ON public.analytics_daily_aggregates(user_id);

CREATE INDEX IF NOT EXISTS idx_daily_agg_user_date
    ON public.analytics_daily_aggregates(user_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_daily_agg_date
    ON public.analytics_daily_aggregates(date DESC);

-- ============================================================================
-- Row Level Security
-- ============================================================================

-- Enable RLS on request_analytics
ALTER TABLE public.request_analytics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own analytics"
    ON public.request_analytics FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own analytics"
    ON public.request_analytics FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role has full access to request_analytics"
    ON public.request_analytics FOR ALL
    USING (auth.role() = 'service_role');

-- Enable RLS on analytics_daily_aggregates
ALTER TABLE public.analytics_daily_aggregates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own daily aggregates"
    ON public.analytics_daily_aggregates FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role has full access to daily aggregates"
    ON public.analytics_daily_aggregates FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- Trigger for updated_at on daily aggregates
-- ============================================================================

DROP TRIGGER IF EXISTS update_analytics_daily_aggregates_updated_at
    ON public.analytics_daily_aggregates;

CREATE TRIGGER update_analytics_daily_aggregates_updated_at
    BEFORE UPDATE ON public.analytics_daily_aggregates
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================================================
-- Views for common queries
-- ============================================================================

-- View: Recent analytics summary (last 7 days)
CREATE OR REPLACE VIEW public.user_analytics_summary AS
SELECT
    user_id,
    COUNT(*) AS total_requests_7d,
    COUNT(*) FILTER (WHERE status = 'success') AS successful_requests_7d,
    COUNT(*) FILTER (WHERE status = 'error') AS error_requests_7d,
    AVG(total_time_ms) AS avg_total_time_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_time_ms) AS p50_total_time_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_time_ms) AS p95_total_time_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_time_ms) AS p99_total_time_ms,
    AVG(ttfb_ms) FILTER (WHERE ttfb_ms IS NOT NULL) AS avg_ttfb_ms,
    AVG((retrieval_metrics->>'total_raw_results')::float) AS avg_retrieval_results,
    AVG((context_metrics->>'total_context_tokens')::float) AS avg_context_tokens
FROM public.request_analytics
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY user_id;

-- Grant access to view
GRANT SELECT ON public.user_analytics_summary TO authenticated;

-- View: Hourly request counts (last 24 hours) for time-series charts
CREATE OR REPLACE VIEW public.user_analytics_hourly AS
SELECT
    user_id,
    DATE_TRUNC('hour', created_at) AS hour,
    COUNT(*) AS request_count,
    AVG(total_time_ms) AS avg_latency_ms,
    COUNT(*) FILTER (WHERE status = 'error') AS error_count
FROM public.request_analytics
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY user_id, DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;

-- Grant access to view
GRANT SELECT ON public.user_analytics_hourly TO authenticated;

-- ============================================================================
-- Functions for analytics operations
-- ============================================================================

-- Function: Calculate latency percentiles for a user over a time window
CREATE OR REPLACE FUNCTION public.get_latency_percentiles(
    p_user_id UUID,
    p_days INTEGER DEFAULT 7,
    p_request_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    metric_name TEXT,
    p50 FLOAT,
    p95 FLOAT,
    p99 FLOAT,
    avg_value FLOAT,
    min_value FLOAT,
    max_value FLOAT,
    sample_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH filtered_data AS (
        SELECT
            total_time_ms,
            ttfb_ms,
            (step_timings->>'total_retrieval_time')::float AS retrieval_time,
            (step_timings->>'llm_total_time')::float AS llm_time,
            (step_timings->>'ranking_time')::float AS ranking_time,
            (step_timings->>'context_building_time')::float AS context_time
        FROM public.request_analytics
        WHERE user_id = p_user_id
            AND created_at > NOW() - (p_days || ' days')::INTERVAL
            AND status = 'success'
            AND (p_request_type IS NULL OR request_type = p_request_type)
    )
    SELECT 'total_time'::TEXT,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_time_ms),
           PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_time_ms),
           PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_time_ms),
           AVG(total_time_ms),
           MIN(total_time_ms),
           MAX(total_time_ms),
           COUNT(*)
    FROM filtered_data
    UNION ALL
    SELECT 'ttfb'::TEXT,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ttfb_ms),
           PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ttfb_ms),
           PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY ttfb_ms),
           AVG(ttfb_ms),
           MIN(ttfb_ms),
           MAX(ttfb_ms),
           COUNT(*) FILTER (WHERE ttfb_ms IS NOT NULL)
    FROM filtered_data
    UNION ALL
    SELECT 'retrieval'::TEXT,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY retrieval_time),
           PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY retrieval_time),
           PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY retrieval_time),
           AVG(retrieval_time),
           MIN(retrieval_time),
           MAX(retrieval_time),
           COUNT(*) FILTER (WHERE retrieval_time IS NOT NULL)
    FROM filtered_data
    UNION ALL
    SELECT 'llm'::TEXT,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY llm_time),
           PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY llm_time),
           PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY llm_time),
           AVG(llm_time),
           MIN(llm_time),
           MAX(llm_time),
           COUNT(*) FILTER (WHERE llm_time IS NOT NULL)
    FROM filtered_data
    UNION ALL
    SELECT 'ranking'::TEXT,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ranking_time),
           PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ranking_time),
           PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY ranking_time),
           AVG(ranking_time),
           MIN(ranking_time),
           MAX(ranking_time),
           COUNT(*) FILTER (WHERE ranking_time IS NOT NULL)
    FROM filtered_data
    UNION ALL
    SELECT 'context_building'::TEXT,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY context_time),
           PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY context_time),
           PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY context_time),
           AVG(context_time),
           MIN(context_time),
           MAX(context_time),
           COUNT(*) FILTER (WHERE context_time IS NOT NULL)
    FROM filtered_data;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Aggregate daily analytics (run by cron job or worker)
CREATE OR REPLACE FUNCTION public.aggregate_daily_analytics(p_date DATE DEFAULT CURRENT_DATE - 1)
RETURNS INTEGER AS $$
DECLARE
    rows_affected INTEGER;
BEGIN
    INSERT INTO public.analytics_daily_aggregates (
        user_id,
        date,
        total_requests,
        chat_stream_requests,
        chat_complete_requests,
        memory_search_requests,
        successful_requests,
        error_requests,
        latency_stats,
        retrieval_stats,
        context_stats,
        intent_distribution
    )
    SELECT
        user_id,
        p_date,
        COUNT(*),
        COUNT(*) FILTER (WHERE request_type = 'chat_stream'),
        COUNT(*) FILTER (WHERE request_type = 'chat_complete'),
        COUNT(*) FILTER (WHERE request_type = 'memory_search'),
        COUNT(*) FILTER (WHERE status = 'success'),
        COUNT(*) FILTER (WHERE status = 'error'),
        jsonb_build_object(
            'total_time', jsonb_build_object(
                'p50', PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_time_ms),
                'p95', PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_time_ms),
                'p99', PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_time_ms),
                'avg', AVG(total_time_ms),
                'min', MIN(total_time_ms),
                'max', MAX(total_time_ms)
            ),
            'ttfb', jsonb_build_object(
                'p50', PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ttfb_ms),
                'p95', PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ttfb_ms),
                'p99', PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY ttfb_ms),
                'avg', AVG(ttfb_ms)
            ),
            'retrieval', jsonb_build_object(
                'avg', AVG((step_timings->>'total_retrieval_time')::float)
            ),
            'llm', jsonb_build_object(
                'avg', AVG((step_timings->>'llm_total_time')::float)
            )
        ),
        jsonb_build_object(
            'avg_vector_results', AVG((retrieval_metrics->>'vector_results_count')::float),
            'avg_keyword_results', AVG((retrieval_metrics->>'keyword_results_count')::float),
            'avg_total_results', AVG((retrieval_metrics->>'total_raw_results')::float),
            'avg_score', AVG((retrieval_metrics->'score_distribution'->'combined'->>'avg')::float)
        ),
        jsonb_build_object(
            'avg_tokens_used', AVG((context_metrics->>'total_context_tokens')::float),
            'avg_memories_included', AVG((context_metrics->>'memories_included')::float),
            'truncation_rate', AVG(CASE WHEN (context_metrics->>'truncation_occurred')::boolean THEN 1 ELSE 0 END)
        ),
        (
            SELECT jsonb_object_agg(intent, cnt)
            FROM (
                SELECT
                    COALESCE(query_analysis->>'intent', 'unknown') AS intent,
                    COUNT(*) AS cnt
                FROM public.request_analytics ra2
                WHERE ra2.user_id = request_analytics.user_id
                    AND DATE(ra2.created_at) = p_date
                GROUP BY COALESCE(query_analysis->>'intent', 'unknown')
            ) sub
        )
    FROM public.request_analytics
    WHERE DATE(created_at) = p_date
    GROUP BY user_id
    ON CONFLICT (user_id, date) DO UPDATE SET
        total_requests = EXCLUDED.total_requests,
        chat_stream_requests = EXCLUDED.chat_stream_requests,
        chat_complete_requests = EXCLUDED.chat_complete_requests,
        memory_search_requests = EXCLUDED.memory_search_requests,
        successful_requests = EXCLUDED.successful_requests,
        error_requests = EXCLUDED.error_requests,
        latency_stats = EXCLUDED.latency_stats,
        retrieval_stats = EXCLUDED.retrieval_stats,
        context_stats = EXCLUDED.context_stats,
        intent_distribution = EXCLUDED.intent_distribution,
        updated_at = NOW();

    GET DIAGNOSTICS rows_affected = ROW_COUNT;
    RETURN rows_affected;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Clean up old analytics data (retention policy)
CREATE OR REPLACE FUNCTION public.cleanup_old_analytics(
    p_retention_days INTEGER DEFAULT 90
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.request_analytics
    WHERE created_at < NOW() - (p_retention_days || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Get retrieval strategy effectiveness
CREATE OR REPLACE FUNCTION public.get_retrieval_stats(
    p_user_id UUID,
    p_days INTEGER DEFAULT 7
)
RETURNS TABLE (
    strategy TEXT,
    avg_results FLOAT,
    avg_score FLOAT,
    usage_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'vector'::TEXT,
           AVG((retrieval_metrics->>'vector_results_count')::float),
           AVG((retrieval_metrics->'score_distribution'->'vector'->>'avg')::float),
           COUNT(*) FILTER (WHERE (retrieval_metrics->>'vector_results_count')::int > 0)
    FROM public.request_analytics
    WHERE user_id = p_user_id
        AND created_at > NOW() - (p_days || ' days')::INTERVAL
    UNION ALL
    SELECT 'keyword'::TEXT,
           AVG((retrieval_metrics->>'keyword_results_count')::float),
           AVG((retrieval_metrics->'score_distribution'->'keyword'->>'avg')::float),
           COUNT(*) FILTER (WHERE (retrieval_metrics->>'keyword_results_count')::int > 0)
    FROM public.request_analytics
    WHERE user_id = p_user_id
        AND created_at > NOW() - (p_days || ' days')::INTERVAL
    UNION ALL
    SELECT 'graph'::TEXT,
           AVG((retrieval_metrics->>'graph_results_count')::float),
           NULL,
           COUNT(*) FILTER (WHERE (retrieval_metrics->>'graph_results_count')::int > 0)
    FROM public.request_analytics
    WHERE user_id = p_user_id
        AND created_at > NOW() - (p_days || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
