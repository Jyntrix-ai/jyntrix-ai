# Architecture Overview

> System design and component interactions for Jyntrix AI Memory System.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER BROWSER                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         Next.js Frontend                                 ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    ││
│  │  │    Auth     │  │    Chat     │  │   Memory    │  │   Profile   │    ││
│  │  │   Pages     │  │  Interface  │  │    View     │  │   Settings  │    ││
│  │  └─────────────┘  └──────┬──────┘  └─────────────┘  └─────────────┘    ││
│  │                          │                                               ││
│  │  ┌─────────────┐  ┌──────┴──────┐  ┌─────────────┐                      ││
│  │  │   Zustand   │◄─┤  API Client │──┤   Supabase  │                      ││
│  │  │    Store    │  │  (SSE/REST) │  │    Auth     │                      ││
│  │  └─────────────┘  └──────┬──────┘  └──────┬──────┘                      ││
│  └──────────────────────────┼────────────────┼──────────────────────────────┘│
└─────────────────────────────┼────────────────┼──────────────────────────────┘
                              │                │
                    HTTPS/SSE │                │ JWT
                              │                │
┌─────────────────────────────┼────────────────┼──────────────────────────────┐
│                             ▼                ▼          BACKEND             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         FastAPI Server                                │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐│   │
│  │  │                      Request Pipeline                             ││   │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐││   │
│  │  │  │  Auth   │──│ Query   │──│Retrieval│──│ Context │──│   LLM   │││   │
│  │  │  │Validate │  │Analysis │  │(Parallel│  │ Builder │  │Streaming│││   │
│  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘││   │
│  │  └──────────────────────────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│            │              │              │              │                    │
│            ▼              ▼              ▼              ▼                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │   Supabase   │ │    Qdrant    │ │    Redis     │ │ Google Gemini│        │
│  │  PostgreSQL  │ │ Vector Store │ │ Cache/Queue  │ │     LLM      │        │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                                              │
│                    ┌───────────────────────────────┐                         │
│                    │         ARQ Worker            │                         │
│                    │  ┌─────────────────────────┐  │                         │
│                    │  │  Background Tasks       │  │                         │
│                    │  │  - Embedding generation │  │                         │
│                    │  │  - Entity extraction    │  │                         │
│                    │  │  - Session summaries    │  │                         │
│                    │  └─────────────────────────┘  │                         │
│                    └───────────────────────────────┘                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Chat Request Flow

```
User Input
    │
    ▼
┌──────────────────┐
│  Frontend        │
│  1. Optimistic   │
│     UI update    │
│  2. Start SSE    │
│     connection   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  API Gateway     │
│  1. Rate limit   │
│  2. Request ID   │
│  3. Logging      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Auth Middleware │
│  1. Validate JWT │
│  2. Extract user │
│     context      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Chat Service    │────────────────────┐
│                  │                    │
│  1. Save user    │                    │
│     message      │                    │
│                  │                    │
│  2. Analyze      │                    │
│     query        │                    │
│                  │                    │
│  3. Retrieve     │◄───────────────────┤
│     memories     │   ┌────────────────┴────────────────┐
│     (parallel)   │   │       Multi-Strategy            │
│                  │   │        Retrieval                │
│  4. Build        │   │  ┌──────────────────────────┐  │
│     context      │   │  │ asyncio.gather()         │  │
│                  │   │  │                          │  │
│  5. Stream LLM   │   │  │ ┌─────────┐ ┌─────────┐  │  │
│     response     │   │  │ │ Vector  │ │ Keyword │  │  │
│                  │   │  │ │ Search  │ │ Search  │  │  │
│  6. Save         │   │  │ │(Qdrant) │ │ (BM25)  │  │  │
│     response     │   │  │ └─────────┘ └─────────┘  │  │
│                  │   │  │                          │  │
│  7. Enqueue      │   │  │ ┌─────────┐ ┌─────────┐  │  │
│     background   │   │  │ │ Graph   │ │ Profile │  │  │
│     tasks        │   │  │ │ Search  │ │  Fetch  │  │  │
└────────┬─────────┘   │  │ └─────────┘ └─────────┘  │  │
         │             │  │                          │  │
         │             │  │ ┌─────────┐              │  │
         │             │  │ │ Recent  │              │  │
         │             │  │ │ Context │              │  │
         │             │  │ └─────────┘              │  │
         │             │  └──────────────────────────┘  │
         │             └────────────────────────────────┘
         │
         ▼
┌──────────────────┐
│  Hybrid Ranker   │
│  1. Deduplicate  │
│  2. Score each   │
│     result       │
│  3. Apply        │
│     weights      │
│  4. Sort by      │
│     score        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Context Builder  │
│  1. Categorize   │
│     by type      │
│  2. Apply token  │
│     budgets      │
│  3. Truncate if  │
│     needed       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  LLM Client      │
│  1. Build prompt │
│  2. Stream       │
│     response     │
│  3. Track TTFB   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  SSE Stream      │
│  1. Send chunks  │
│  2. Send [DONE]  │
│  3. Close        │
│     connection   │
└──────────────────┘
```

---

## Component Relationships

### Service Dependencies

```
┌───────────────────────────────────────────────────────────────────┐
│                         ChatService                                │
│                                                                    │
│  Orchestrates the complete chat pipeline                          │
│                                                                    │
│  Dependencies:                                                     │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐     │
│  │ QueryAnalyzer   │ │RetrievalService │ │  HybridRanker   │     │
│  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘     │
│           │                   │                   │               │
│  ┌────────┴────────┐ ┌────────┴────────┐ ┌────────┴────────┐     │
│  │ ContextBuilder  │ │   LLMClient     │ │ Supabase Client │     │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘     │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                       RetrievalService                             │
│                                                                    │
│  Coordinates multi-strategy retrieval                              │
│                                                                    │
│  Dependencies:                                                     │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐     │
│  │  VectorSearch   │ │  KeywordSearch  │ │   GraphSearch   │     │
│  │    (Qdrant)     │ │    (BM25)       │ │  (Supabase)     │     │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘     │
│                                                                    │
│  ┌─────────────────┐                                              │
│  │EmbeddingService │                                              │
│  │(sentence-trans) │                                              │
│  └─────────────────┘                                              │
└───────────────────────────────────────────────────────────────────┘
```

---

## Memory Architecture

### Memory Types

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Memory Space                         │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │     PROFILE     │  │    SEMANTIC     │                       │
│  │                 │  │                 │                       │
│  │ User preferences│  │ Facts & knowledge│                      │
│  │ Communication   │  │ "Wife's name is │                       │
│  │ style           │  │  Sarah"         │                       │
│  │ "Prefers concise│  │ "Works at Tech  │                       │
│  │  responses"     │  │  Corp"          │                       │
│  └─────────────────┘  └─────────────────┘                       │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │    EPISODIC     │  │   PROCEDURAL    │                       │
│  │                 │  │                 │                       │
│  │ Session history │  │ Learned patterns│                       │
│  │ "Jan 5: Discussed│  │ "When user says │                       │
│  │  project deadline│  │  'summarize',   │                       │
│  │  is March 15"   │  │  provide bullets"│                       │
│  └─────────────────┘  └─────────────────┘                       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    ENTITY GRAPH                              ││
│  │                                                              ││
│  │  [Person: Sarah] ───marriage─── [Person: User]              ││
│  │        │                              │                      ││
│  │    works_at                      works_at                    ││
│  │        │                              │                      ││
│  │  [Company: Hospital]         [Company: Tech Corp]           ││
│  │                                       │                      ││
│  │                                  located_in                  ││
│  │                                       │                      ││
│  │                              [Location: Seattle]             ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Memory Storage

| Type | Storage | Search Method |
|------|---------|---------------|
| Profile | Supabase + Qdrant | Vector + Direct fetch |
| Semantic | Supabase + Qdrant | Vector + Keyword (BM25) |
| Episodic | Supabase + Qdrant | Vector + Recency sort |
| Procedural | Supabase + Qdrant | Vector + Keyword |
| Entity Graph | Supabase | Relationship traversal |

---

## Token Budget Management

### Context Window Allocation

```
┌─────────────────────────────────────────────────────────────────┐
│              LLM Context Window (5000 tokens)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ SYSTEM PROMPT (implicit)                           ~500     ││
│  │ Base instructions + personality                              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Profile Memory  │  │ Semantic Memory │  │ Episodic Memory │ │
│  │     600 tokens  │  │   1500 tokens   │  │   1500 tokens   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │Procedural Memory│  │ Entity Context  │                       │
│  │    400 tokens   │  │   300 tokens    │                       │
│  └─────────────────┘  └─────────────────┘                       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ CONVERSATION HISTORY                              300 tokens ││
│  │ Recent messages for context continuity                       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ CURRENT USER MESSAGE                              Variable   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ RESERVED FOR RESPONSE                            ~4000      ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Isolation

### User Isolation Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Tenant Architecture                     │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │    User A       │  │    User B       │  │    User C       │ │
│  │    Space        │  │    Space        │  │    Space        │ │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │ │
│  │  │ Memories  │  │  │  │ Memories  │  │  │  │ Memories  │  │ │
│  │  │ Entities  │  │  │  │ Entities  │  │  │  │ Entities  │  │ │
│  │  │ Convos    │  │  │  │ Convos    │  │  │  │ Convos    │  │ │
│  │  └───────────┘  │  │  └───────────┘  │  │  └───────────┘  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                  │
│  ISOLATION MECHANISMS:                                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 1. Supabase RLS    - Row Level Security policies           ││
│  │ 2. Qdrant PRE-filter - user_id in query filter (MUST)      ││
│  │ 3. API layer       - Explicit user_id in all queries        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  CRITICAL: Always use PRE-filtering, never POST-filtering!      │
│                                                                  │
│  ✓ CORRECT: Filter by user_id BEFORE vector search             │
│    Qdrant: query_filter = Filter(must=[user_id match])         │
│                                                                  │
│  ✗ WRONG: Search all, then filter results by user_id            │
│    This exposes other users' vectors to similarity matching!    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Async Processing

### ARQ Worker Tasks

```
┌─────────────────────────────────────────────────────────────────┐
│                    Background Task Pipeline                      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      Redis Queue                          │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │   │
│  │  │  Job 1  │  │  Job 2  │  │  Job 3  │  │  Job 4  │     │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘     │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      ARQ Worker                           │   │
│  │                                                           │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │ extract_entities                                    │  │   │
│  │  │  1. Load message from Supabase                      │  │   │
│  │  │  2. Extract entities using Gemini                   │  │   │
│  │  │  3. Store entities in Supabase                      │  │   │
│  │  │  4. Update entity graph relationships               │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │                                                           │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │ generate_embeddings                                 │  │   │
│  │  │  1. Load memory content                             │  │   │
│  │  │  2. Generate embedding via sentence-transformers   │  │   │
│  │  │  3. Upsert vector to Qdrant                        │  │   │
│  │  │  4. Update embedding_status in Supabase            │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │                                                           │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │ generate_session_summary                            │  │   │
│  │  │  1. Load conversation messages                      │  │   │
│  │  │  2. Summarize using Gemini                         │  │   │
│  │  │  3. Create episodic memory                         │  │   │
│  │  │  4. Trigger embedding generation                   │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │                                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Analytics Flow

### Request Analytics Collection

```
┌─────────────────────────────────────────────────────────────────┐
│                    Analytics Pipeline                            │
│                                                                  │
│  REQUEST START                                                   │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────┐                                            │
│  │AnalyticsCollector│ ◄── Created per request                   │
│  │  - request_id    │                                            │
│  │  - user_id       │                                            │
│  │  - request_type  │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                 track_span() calls                           ││
│  │                                                              ││
│  │  async with track_span("setup"):                            ││
│  │      # ... setup code ...                                    ││
│  │      # Timing recorded automatically                         ││
│  │                                                              ││
│  │  async with track_span("retrieval"):                        ││
│  │      # ... retrieval code ...                                ││
│  │                                                              ││
│  │  async with track_span("llm_streaming") as span:            ││
│  │      # ... LLM code ...                                      ││
│  │      span.metadata["ttfb_ms"] = ttfb                        ││
│  └─────────────────────────────────────────────────────────────┘│
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │collector.finalize│ ◄── Computes final metrics                │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  emit_analytics │ ◄── Non-blocking async task                │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │AnalyticsEmitter │ ◄── Buffers records                        │
│  │  - buffer[]     │                                            │
│  │  - flush timer  │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           │  (Every 10s or 10 records)                          │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │    Supabase     │                                            │
│  │ request_analytics│                                            │
│  │     table       │                                            │
│  └─────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Performance Targets

| Metric | Target | Actual (After Optimization) |
|--------|--------|----------------------------|
| TTFB (Time to First Byte) | <500ms | 1-2s |
| Total Response Time | <5s | 3-5s |
| Vector Search | <50ms | ~50ms |
| Retrieval Pipeline | <200ms | 1-2s |
| Embedding Generation | <2s | ~500ms (cached) |

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Security Layers                               │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ LAYER 1: Edge (Cloudflare / Vercel)                        ││
│  │  - DDoS protection                                          ││
│  │  - TLS termination                                          ││
│  │  - Geographic restrictions (if needed)                      ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ LAYER 2: API Gateway                                        ││
│  │  - Rate limiting (100 req/min per IP)                       ││
│  │  - Request validation                                       ││
│  │  - CORS enforcement                                         ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ LAYER 3: Authentication                                     ││
│  │  - Supabase JWT validation                                  ││
│  │  - Token expiration checks                                  ││
│  │  - Session management                                       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ LAYER 4: Data Access                                        ││
│  │  - Row Level Security (RLS) in Supabase                    ││
│  │  - user_id PRE-filtering in all queries                    ││
│  │  - Explicit ownership checks in code                       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ LAYER 5: Secrets Management                                 ││
│  │  - Environment variables for credentials                   ││
│  │  - Service role key only in backend                        ││
│  │  - Anon key for frontend (restricted permissions)          ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [Backend Architecture](../backend/README.md)
- [Frontend Architecture](../frontend/README.md)
- [Pipeline Flow Details](./pipeline-flow.md)
- [API Reference](../api/README.md)
