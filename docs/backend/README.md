# Backend Architecture Documentation

> FastAPI-based backend service powering Jyntrix AI Memory System.

---

## Overview

The backend is a Python FastAPI application that handles:
- Authentication via Supabase JWT validation
- Chat processing with streaming responses (SSE)
- Multi-strategy memory retrieval (Vector, Keyword, Graph)
- Context assembly with token budget management
- Real-time analytics instrumentation

### Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | FastAPI | Async API server |
| Python | 3.11+ | Runtime |
| Database | Supabase PostgreSQL | Primary data store |
| Vector DB | Qdrant | Semantic similarity search |
| Cache | Redis | Caching, task queue |
| LLM | Google Gemini 2.5 Flash | Response generation |
| Embeddings | sentence-transformers | Local embedding model |

---

## Project Structure

```
services/api/src/
├── main.py                 # App entry point, lifespan, middleware
├── config.py               # Pydantic settings, environment config
├── dependencies.py         # FastAPI dependency injection
│
├── routers/                # API route handlers
│   ├── auth.py             # Authentication endpoints
│   ├── chat.py             # Chat/conversation endpoints
│   ├── memory.py           # Memory CRUD endpoints
│   ├── profile.py          # User profile endpoints
│   ├── analytics.py        # Analytics endpoints
│   └── health.py           # Health check endpoints
│
├── services/               # Business logic layer
│   ├── chat_service.py     # Main chat orchestrator
│   ├── retrieval_service.py # Multi-strategy retrieval
│   ├── memory_service.py   # Memory CRUD operations
│   ├── auth_service.py     # Authentication logic
│   └── analytics_service.py # Analytics queries
│
├── core/                   # AI/RAG core modules
│   ├── embeddings.py       # Embedding model service
│   ├── vector_search.py    # Qdrant vector search
│   ├── keyword_search.py   # BM25 keyword matching
│   ├── graph_search.py     # Entity graph traversal
│   ├── hybrid_ranker.py    # Weighted result ranking
│   ├── context_builder.py  # Token budget management
│   ├── query_analyzer.py   # Intent/entity extraction
│   └── llm_client.py       # Gemini API client
│
├── models/                 # Pydantic data models
│   ├── chat.py             # Conversation, Message models
│   ├── memory.py           # Memory type models
│   ├── entity.py           # Entity models
│   └── user.py             # User models
│
├── schemas/                # API request/response schemas
│   ├── chat.py             # Chat API schemas
│   ├── memory.py           # Memory API schemas
│   ├── auth.py             # Auth API schemas
│   └── analytics.py        # Analytics API schemas
│
├── analytics/              # Analytics instrumentation
│   ├── models.py           # Analytics data models
│   ├── context.py          # Request context tracking
│   ├── emitter.py          # Buffered analytics emitter
│   └── instrumentation.py  # Span tracking decorators
│
├── db/                     # Database clients
│   ├── supabase.py         # Supabase client
│   ├── qdrant.py           # Qdrant client
│   └── redis.py            # Redis client
│
└── utils/                  # Utilities
    └── token_counter.py    # Token counting for LLM context
```

---

## Application Lifecycle

### Startup (`main.py:lifespan`)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Pre-warm embedding model (CRITICAL for performance)
    embedding_service = get_embedding_service()
    embedding_service._ensure_initialized()

    # 2. Start analytics background flush task
    # Analytics buffer flushes every 10 seconds

    yield  # Application runs here

    # 3. Shutdown: Flush remaining analytics
    await _emitter.shutdown()
```

**Key Performance Note**: The embedding model (`all-MiniLM-L6-v2`, ~80MB) is pre-loaded during startup to prevent 30-40 second delays on the first request.

### Middleware Stack

| Middleware | Purpose |
|------------|---------|
| `CORSMiddleware` | Cross-origin resource sharing |
| `RequestLoggingMiddleware` | Request/response logging, X-Request-ID |
| `RateLimitMiddleware` | In-memory rate limiting (100 req/min) |

---

## Core Services

### 1. ChatService (`services/chat_service.py`)

The main orchestrator for the chat pipeline. Handles the complete flow from message receipt to LLM streaming.

**Key Method: `send_message_stream()`**

```python
async def send_message_stream(
    self,
    user_id: str,
    content: str,
    conversation_id: UUID | None = None,
    include_memory: bool = True,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Complete chat processing flow:
    1. SETUP: Get/create conversation, save user message
    2. QUERY_ANALYSIS: Extract intent, keywords, entities
    3. RETRIEVAL: Multi-strategy parallel retrieval
    4. CONTEXT_BUILDING: Assemble within token budget
    5. LLM_STREAMING: Stream response with TTFB tracking
    6. SAVE_RESPONSE: Persist assistant message
    7. ENQUEUE_TASKS: Queue memory extraction for worker
    """
```

**Analytics Instrumentation:**

Every phase is tracked using `track_span()` context manager:

```python
async with track_span("retrieval") as span:
    memory_context = await self._retrieve_memories(...)
    # Timing automatically recorded
```

---

### 2. RetrievalService (`services/retrieval_service.py`)

Implements multi-strategy retrieval using `asyncio.gather` for parallel execution.

**Retrieval Strategies:**

| Strategy | Source | Purpose |
|----------|--------|---------|
| `vector_search` | Qdrant | Semantic similarity (cosine) |
| `keyword_search` | Supabase + BM25 | Exact term matching |
| `graph_search` | Entity graph | Relationship traversal |
| `profile_retrieval` | Profile memories | User preferences |
| `recent_context` | Episodic memories | Recent interactions |

**Key Method: `multi_strategy_retrieve()`**

```python
async def multi_strategy_retrieve(...):
    # Run ALL strategies in parallel
    results = await asyncio.gather(
        tracker.track("vector_search", self._vector_retrieval(...)),
        tracker.track("keyword_search", self._keyword_retrieval(...)),
        tracker.track("graph_search", self._entity_retrieval(...)),
        tracker.track("profile_retrieval", self._profile_retrieval(...)),
        tracker.track("recent_context", self._recent_context_retrieval(...)),
        return_exceptions=True,
    )

    # Combine results from all strategies
    return combined_results
```

**Performance Optimization:**
- Keyword search limited to 200 documents (reduced from 1000)
- Each strategy runs independently and fails gracefully

---

## Core AI/RAG Modules

### 1. VectorSearch (`core/vector_search.py`)

Handles semantic similarity search using Qdrant.

**Key Features:**
- **User Isolation**: All queries PRE-filter by `user_id`
- **Non-blocking**: Uses `asyncio.to_thread()` for embedding generation
- **Caching**: LRU cache (100 entries) for repeated query embeddings

```python
class VectorSearch:
    _embedding_cache: dict[str, list] = {}  # Class-level cache
    _cache_max_size: int = 100

    async def search(self, user_id: str, query: str, ...):
        # Check cache first
        cache_key = f"{user_id}:{query}"
        if cache_key in self._embedding_cache:
            query_embedding = self._embedding_cache[cache_key]
        else:
            # Non-blocking embedding generation
            query_embedding = await asyncio.to_thread(
                self.embedder.embed, query
            )
            self._embedding_cache[cache_key] = query_embedding
```

---

### 2. HybridRanker (`core/hybrid_ranker.py`)

Combines results from multiple retrieval strategies using weighted scoring.

**Ranking Weights (from `config.py`):**

| Signal | Weight | Description |
|--------|--------|-------------|
| `keyword_match` | 0.35 | BM25 score (normalized) |
| `vector_similarity` | 0.25 | Cosine similarity (0-1) |
| `reliability` | 0.20 | Memory confidence score |
| `recency` | 0.15 | Exponential decay (30-day half-life) |
| `frequency` | 0.05 | Log-scaled access count |

**Combined Score Formula:**

```python
score = (keyword_match * 0.35) +
        (vector_similarity * 0.25) +
        (reliability * 0.20) +
        (recency * 0.15) +
        (frequency * 0.05)
```

**Features:**
- Deduplication by `memory_id` (keeps highest-scored version)
- Merges match types when same memory found by multiple strategies
- Adaptive variant adjusts weights based on query type

---

### 3. ContextBuilder (`core/context_builder.py`)

Assembles retrieved memories into LLM context within token budget.

**Token Budget Allocation:**

| Category | Tokens | Purpose |
|----------|--------|---------|
| `profile_memory` | 600 | User preferences |
| `semantic_memory` | 1,500 | Facts and knowledge |
| `episodic_memory` | 1,500 | Session summaries |
| `procedural_memory` | 400 | Learned patterns |
| `entity_context` | 300 | Related entities |
| `conversation_history` | 300 | Recent messages |
| **Total Context** | **5,000** | (reduced from 8,000) |

**Key Method: `build()`**

```python
async def build(self, memories: List[dict], ...):
    # 1. Categorize by memory type
    categorized = self._categorize_memories(memories)

    # 2. Build each section within budget
    profile_memories = await self._build_profile_section(...)
    semantic_memories = await self._build_semantic_section(...)
    episodic_memories = await self._build_episodic_section(...)

    # 3. Return structured context
    return MemoryContext(...)
```

---

### 4. QueryAnalyzer (`core/query_analyzer.py`)

Analyzes user queries to determine intent and extract entities.

**Extracted Information:**
- `intent`: conversation, question, recall, command
- `keywords`: Important terms for keyword search
- `entities_mentioned`: People, places, things
- `time_reference`: Temporal context
- `requires_memory`: Whether to retrieve memories
- `memory_types_needed`: Which memory types to search

---

### 5. LLMClient (`core/llm_client.py`)

Interfaces with Google Gemini for response generation.

**Configuration:**
- Model: `gemini-2.5-flash`
- Max tokens: 4,096
- Temperature: 0.7

**Methods:**
- `stream_chat()`: SSE streaming for real-time responses
- `complete()`: Non-streaming completion

---

## Memory Types

The system supports four memory types:

| Type | Purpose | Example |
|------|---------|---------|
| `profile` | User preferences | "Prefers concise responses" |
| `semantic` | Facts and knowledge | "Wife's name is Sarah" |
| `episodic` | Session summaries | "Discussed project timeline on Jan 5" |
| `procedural` | Learned patterns | "When user says 'done', summarize" |

---

## Analytics System

### AnalyticsEmitter (`analytics/emitter.py`)

Buffered analytics emission for performance.

**Configuration:**
- `analytics_buffer_size`: 10 records
- `analytics_flush_interval`: 10 seconds
- `analytics_retention_days`: 90 days

**Flush Triggers:**
1. Buffer reaches max size (10 records)
2. Periodic flush every 10 seconds
3. Application shutdown

**Key Fix Applied:**
Added background flush task that was missing, causing analytics to never persist.

---

## Database Layer

### Supabase (PostgreSQL)

Primary data store for:
- Users, Profiles
- Conversations, Messages
- Memories (with metadata)
- Entities and relationships
- Analytics records

**Security**: Row-Level Security (RLS) policies enforce user isolation.

### Qdrant (Vector Database)

Stores memory embeddings for semantic search.

**Collection Configuration:**
- Vector size: 384 (all-MiniLM-L6-v2)
- Distance metric: Cosine
- Indexes: `user_id`, `type`

**Critical**: All queries use `user_id` PRE-filter (not POST-filter).

### Redis

Used for:
- Response caching
- ARQ task queue for background jobs
- Rate limiting state

---

## Performance Optimizations

### Applied Optimizations

| Optimization | Before | After | Files |
|--------------|--------|-------|-------|
| Embedding pre-warm | 43s first request | <1s | `main.py` |
| Non-blocking embedding | Event loop blocked | Async | `vector_search.py` |
| Embedding cache | Regenerate every query | LRU cache | `vector_search.py` |
| Keyword search limit | 1000 docs | 200 docs | `retrieval_service.py` |
| Token budgets | 8000 tokens | 5000 tokens | `config.py` |

### Performance Metrics (After Optimizations)

| Metric | Value |
|--------|-------|
| Setup time | <500ms |
| Retrieval time | 1-2s |
| LLM TTFB | 1-2s |
| Total response time | 3-5s |

---

## Configuration Reference

### Environment Variables

```bash
# Application
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=xxx

# Redis
REDIS_URL=redis://localhost:6379

# Google AI
GOOGLE_AI_API_KEY=xxx
GEMINI_MODEL=gemini-2.5-flash

# Analytics
ANALYTICS_ENABLED=true
ANALYTICS_BUFFER_SIZE=10
ANALYTICS_FLUSH_INTERVAL=10
```

### Key Settings (`config.py`)

```python
class Settings(BaseSettings):
    # Token Budgets
    max_context_tokens: int = 5000
    profile_memory_tokens: int = 600
    semantic_memory_tokens: int = 1500
    episodic_memory_tokens: int = 1500
    procedural_memory_tokens: int = 400
    entity_memory_tokens: int = 300

    # Hybrid Ranking Weights
    keyword_match_weight: float = 0.35
    vector_similarity_weight: float = 0.25
    reliability_weight: float = 0.20
    recency_weight: float = 0.15
    frequency_weight: float = 0.05

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
```

---

## API Routers

| Router | Prefix | Description |
|--------|--------|-------------|
| `health` | `/`, `/health` | Health checks |
| `auth` | `/api/auth` | Authentication |
| `chat` | `/api/chat` | Conversations, messages |
| `memory` | `/api/memories` | Memory CRUD |
| `profile` | `/api/profile` | User profiles |
| `analytics` | `/api/v1/analytics` | Analytics queries |

See [API Reference](../api/README.md) for complete endpoint documentation.

---

## Error Handling

The application uses custom exception handlers for consistent error responses:

| Exception | Status Code | Response |
|-----------|-------------|----------|
| `RequestValidationError` | 422 | Detailed field errors |
| `ValueError` | 400 | Bad request message |
| `PermissionError` | 403 | Forbidden message |
| `FileNotFoundError` | 404 | Not found message |
| `Exception` | 500 | Internal error (sanitized in production) |

---

## Development Commands

```bash
# Install dependencies
cd services/api
pip install -r requirements.txt

# Run locally (development)
uvicorn src.main:app --reload --port 8000

# Run with Docker
docker-compose up -d api

# View logs
docker-compose logs -f api

# Run tests
pytest tests/

# Type checking
mypy src/
```

---

## Related Documentation

- [API Reference](../api/README.md)
- [Analytics API](../api/analytics.md)
- [Pipeline Flow](../architecture/pipeline-flow.md)
- [Frontend](../frontend/README.md)
