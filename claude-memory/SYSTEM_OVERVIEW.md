# Jyntrix AI - Claude Memory

> Quick reference for Claude to understand the Jyntrix AI system.

---

## What is Jyntrix AI?

A **production-ready AI Memory System** that enables LLMs to "remember" past interactions. It transforms stateless chatbots into context-aware, personalized assistants using RAG (Retrieval-Augmented Generation) pipelines.

---

## Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15 + React 19 + Zustand |
| Backend | FastAPI (Python 3.11+) |
| Database | Supabase PostgreSQL |
| Vector DB | Qdrant (semantic search) |
| Cache | Redis (caching + ARQ queue) |
| LLM | Google Gemini 2.5 Flash |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, 384 dims) |

---

## Project Structure

```
jyntrix_ai/
├── apps/web/                    # Next.js Frontend
│   └── src/
│       ├── app/                 # App Router pages
│       ├── components/chat/     # Chat UI components
│       ├── hooks/use-chat.ts    # Chat hook with SSE
│       ├── stores/chat.store.ts # Zustand state
│       └── lib/api.ts           # API client
│
├── services/api/                # FastAPI Backend
│   └── src/
│       ├── main.py              # App entry, lifespan
│       ├── config.py            # Settings
│       ├── routers/             # API routes
│       ├── services/            # Business logic
│       │   ├── chat_service.py  # Main orchestrator
│       │   └── retrieval_service.py # Multi-strategy retrieval
│       ├── core/                # AI/RAG modules
│       │   ├── vector_search.py # Qdrant search
│       │   ├── keyword_search.py # BM25 search
│       │   ├── hybrid_ranker.py # Weighted ranking
│       │   └── context_builder.py # Token budgets
│       └── analytics/           # Performance tracking
│
├── services/worker/             # ARQ Background Worker
│   └── src/tasks/               # Embedding, extraction tasks
│
├── docs/                        # Documentation
└── claude-memory/               # This folder
```

---

## Memory Types

| Type | Purpose | Example |
|------|---------|---------|
| `profile` | User preferences | "Prefers concise responses" |
| `semantic` | Facts/knowledge | "Wife's name is Sarah" |
| `episodic` | Session summaries | "Discussed project on Jan 5" |
| `procedural` | Learned patterns | "When user says 'done', summarize" |

---

## Chat Request Pipeline (7 phases)

```
1. SETUP (~500ms)
   - Validate JWT, get/create conversation, save user message

2. QUERY ANALYSIS (~50ms)
   - Extract intent, keywords, entities
   - Decide if memory retrieval needed

3. MULTI-STRATEGY RETRIEVAL (parallel, ~1-2s)
   - Vector search (Qdrant) - semantic similarity
   - Keyword search (BM25) - exact term matching
   - Graph search - entity relationships
   - Profile fetch - user preferences
   - Recent context - episodic memories

4. HYBRID RANKING (~20ms)
   - Deduplicate results
   - Apply weighted scoring:
     keyword=0.35, vector=0.25, reliability=0.20, recency=0.15, frequency=0.05

5. CONTEXT BUILDING (~30ms)
   - Categorize by memory type
   - Apply token budgets (5000 total)

6. LLM STREAMING (1-2s)
   - Build system prompt with memory context
   - Stream Gemini response via SSE

7. POST-PROCESSING
   - Save response, update conversation
   - Enqueue background tasks (entity extraction)
```

---

## Key Configuration (`services/api/src/config.py`)

```python
# Token Budgets (reduced ~40% for performance)
max_context_tokens: int = 5000      # was 8000
profile_memory_tokens: int = 600    # was 1000
semantic_memory_tokens: int = 1500  # was 2500
episodic_memory_tokens: int = 1500  # was 2500
procedural_memory_tokens: int = 400 # was 1000

# Hybrid Ranking Weights
keyword_match_weight: float = 0.35
vector_similarity_weight: float = 0.25
reliability_weight: float = 0.20
recency_weight: float = 0.15
frequency_weight: float = 0.05

# Analytics
analytics_buffer_size: int = 10
analytics_flush_interval: int = 10  # seconds
```

---

## Critical Files to Know

| File | Purpose |
|------|---------|
| `services/api/src/main.py` | App entry, embedding pre-warm, analytics shutdown |
| `services/api/src/services/chat_service.py` | Main chat orchestrator |
| `services/api/src/services/retrieval_service.py` | Multi-strategy retrieval |
| `services/api/src/core/vector_search.py` | Qdrant search + embedding cache |
| `services/api/src/core/hybrid_ranker.py` | Weighted scoring logic |
| `services/api/src/core/context_builder.py` | Token budget management |
| `services/api/src/analytics/emitter.py` | Buffered analytics emission |
| `apps/web/src/hooks/use-chat.ts` | Frontend SSE streaming |
| `apps/web/src/stores/chat.store.ts` | Zustand chat state |

---

## Performance Optimizations Applied

| Issue | Solution | Impact |
|-------|----------|--------|
| 43s first request | Pre-warm embedding model on startup | → <1s |
| Blocking event loop | `asyncio.to_thread()` for embeddings | Async-safe |
| Repeated query embeddings | LRU cache (100 entries) | -500ms |
| Slow keyword search | Reduced limit 1000 → 200 docs | -1-2s |
| Slow LLM response | Reduced token budgets 40% | -1s |
| Analytics not persisting | Added background flush task | Fixed |

### Current Performance Metrics

| Metric | Value |
|--------|-------|
| Setup time | <500ms |
| Retrieval time | 1-2s |
| LLM TTFB | 1-2s |
| Total response | 3-5s |

---

## User Data Isolation (CRITICAL)

**Always use PRE-filtering, never POST-filtering!**

```python
# CORRECT: Filter by user_id BEFORE search
search_filter = Filter(must=[
    FieldCondition(key="user_id", match=MatchValue(value=user_id))
])
results = qdrant.query_points(..., query_filter=search_filter)

# WRONG: Search all, then filter (exposes other users' vectors!)
```

- Supabase: Row Level Security (RLS) policies
- Qdrant: `user_id` in query filter (MUST condition)
- API: Explicit `user_id` in all queries

---

## API Endpoints

| Prefix | Purpose |
|--------|---------|
| `/api/auth` | Authentication (signup, login, logout) |
| `/api/chat` | Conversations, messages, SSE streaming |
| `/api/memories` | Memory CRUD, search |
| `/api/profile` | User profile, preferences |
| `/api/v1/analytics` | Request analytics, performance data |
| `/health` | Health check |

---

## Frontend Streaming Architecture

```typescript
// Optimized streaming: separate state for streaming content
// Prevents full message list re-render on every chunk

startStreaming(messageId)           // Set streaming mode
appendStreamingContent(chunk)        // Only update streamingContent
finalizeStreamingMessage()          // Merge into messages array

// StreamingMessage component reads from streamingContent
// Static messages read from messages array (memoized)
```

---

## Background Tasks (ARQ Worker)

| Task | Purpose |
|------|---------|
| `extract_entities` | Extract entities from messages using LLM |
| `generate_embeddings` | Create vectors for new memories |
| `generate_session_summary` | Summarize conversations into episodic memory |

---

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Hydration mismatch | Browser extensions (Bitdefender) inject attributes | MutationObserver cleanup in layout.tsx |
| Text breaking weirdly | CSS word-break on small screens | `whitespace-nowrap` on indicators |
| Stream aborts on navigation | `router.replace()` triggers re-render | Use `window.history.replaceState()` |
| 401 Unauthorized | Supabase auth timeout | Usually transient, check network |
| Analytics empty | Buffer never flushed | Added periodic flush task |

---

## Environment Variables

```bash
# Supabase
SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY

# Qdrant
QDRANT_URL, QDRANT_API_KEY

# Redis
REDIS_URL

# Google AI
GOOGLE_AI_API_KEY

# App
ENVIRONMENT, DEBUG, LOG_LEVEL
NEXT_PUBLIC_API_URL, NEXT_PUBLIC_SUPABASE_URL
```

---

## Development Commands

```bash
# Backend
cd services/api
uvicorn src.main:app --reload --port 8000

# Frontend
cd apps/web
npm run dev

# Worker
cd services/worker
arq src.main.WorkerSettings

# Docker
docker-compose up -d
docker-compose logs -f api
```

---

## Documentation Reference

| Path | Content |
|------|---------|
| `/docs/README.md` | Main index |
| `/docs/api/README.md` | Full API reference |
| `/docs/api/analytics.md` | Analytics API (7 endpoints) |
| `/docs/backend/README.md` | Backend architecture |
| `/docs/frontend/README.md` | Frontend architecture |
| `/docs/architecture/README.md` | System design |
| `/docs/architecture/pipeline-flow.md` | Detailed pipeline |
| `/CHANGELOG.md` | All fixes and features |
| `/CLAUDE.md` | Original project instructions |

---

## Quick Debugging

1. **Slow first request?** Check embedding model pre-warm in main.py
2. **Empty analytics?** Check analytics emitter flush task
3. **Vector search failing?** Check Qdrant connection and user_id filter
4. **Streaming issues?** Check SSE content-type and CORS
5. **Auth errors?** Check Supabase JWT and token expiration
