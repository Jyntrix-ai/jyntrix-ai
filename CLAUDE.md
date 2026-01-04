# Jyntrix AI - AI Memory Architecture

## Project Overview

Jyntrix AI is a production-ready AI Memory System with RAG (Retrieval-Augmented Generation) pipelines, vector databases, user isolation, and query optimization. It enables LLMs to "remember" past interactions, transforming stateless chatbots into context-aware assistants.

## Tech Stack

| Component | Service | Purpose |
|-----------|---------|---------|
| Primary DB | Supabase PostgreSQL | Source of truth |
| Vector DB | Qdrant Cloud | Semantic search |
| Cache/Queue | Redis (Upstash in prod) | Caching + ARQ task queue |
| LLM | Google Gemini 1.5 Flash | Response generation |
| Embeddings | sentence-transformers | Local vector generation |
| Keyword Search | rank-bm25 | BM25 scoring |
| Backend | FastAPI (Python) | API server |
| Worker | ARQ (Python) | Background tasks |
| Frontend | Next.js 14+ | User interface |

## Project Structure

```
jyntrix_ai/
├── services/
│   ├── api/                 # FastAPI Backend (Python)
│   │   ├── src/
│   │   │   ├── main.py      # App entry point
│   │   │   ├── config.py    # Settings
│   │   │   ├── routers/     # API routes
│   │   │   ├── services/    # Business logic
│   │   │   ├── core/        # AI/RAG modules
│   │   │   └── db/          # Database clients
│   │   └── Dockerfile
│   │
│   └── worker/              # ARQ Worker (Python)
│       ├── src/
│       │   ├── main.py      # Worker entry
│       │   └── tasks/       # Background tasks
│       └── Dockerfile
│
├── apps/
│   └── web/                 # Next.js Frontend
│       └── src/
│           ├── app/         # App Router pages
│           ├── components/  # React components
│           └── lib/         # Utils, API client
│
├── packages/
│   └── shared/              # TypeScript types
│
├── database/
│   └── migrations/          # SQL migrations
│
├── docker-compose.yml
└── CLAUDE.md
```

## Key Architectural Concepts

### 1. Dual-Path Processing

**SYNC Path (<100ms target):**
1. Validate JWT
2. Save message to PostgreSQL
3. Analyze query (intent, entities, keywords)
4. Multi-strategy retrieval (parallel)
5. Hybrid ranking
6. Context assembly
7. Stream LLM response
8. Enqueue async tasks

**ASYNC Path (ARQ Worker):**
- Generate embeddings (sentence-transformers)
- Extract entities/facts (Gemini)
- Generate session summaries
- Store in Qdrant/PostgreSQL

### 2. Multi-Strategy Retrieval

The system uses THREE search strategies, run in parallel:

1. **Vector Search** (Qdrant): Semantic similarity
2. **Keyword Search** (BM25): Exact term matching
3. **Graph Search**: Entity relationship traversal

Results are merged using **Hybrid Ranking**:
```python
score = (keyword_match * 0.35) +
        (vector_similarity * 0.25) +
        (reliability * 0.20) +
        (recency * 0.15) +
        (frequency * 0.05)
```

### 3. User Data Isolation

**CRITICAL**: Always use PRE-filtering (filter by user_id BEFORE search):
- Qdrant: `user_id` in payload filter
- PostgreSQL: RLS policies + explicit WHERE clauses
- All queries must include `user_id`

### 4. Memory Types

| Type | Purpose | Example |
|------|---------|---------|
| profile | User preferences | "Prefers concise responses" |
| semantic | Facts | "Wife's name is Sarah" |
| episodic | Session summaries | "Discussed project timeline" |
| procedural | Style preferences | "Uses formal language" |

### 5. Token Budget (8K Context)

```
System prompt:     500 tokens
Profile memory:    200 tokens (always)
Working memory:   1000 tokens (recent messages)
Retrieved:        2000 tokens (from search)
Current message:   300 tokens
Response:         4000 tokens (reserved)
```

## Development Commands

### Local Development

```bash
# Start all services
docker-compose up -d

# Start only backend services
docker-compose up -d api worker redis qdrant

# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Run API locally (without Docker)
cd services/api
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

# Run worker locally
cd services/worker
pip install -r requirements.txt
arq src.main.WorkerSettings

# Run frontend locally
cd apps/web
npm install
npm run dev
```

### Database Migrations

Run migrations in Supabase SQL Editor in order:
1. `001_create_profiles.sql`
2. `002_create_conversations.sql`
3. `003_create_messages.sql`
4. `004_create_memories.sql`
5. `005_create_entities.sql`
6. `006_create_indexes_and_functions.sql`

## Environment Variables

```env
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# Qdrant
QDRANT_URL=https://xxx.cloud.qdrant.io
QDRANT_API_KEY=xxx

# Redis (local: redis://localhost:6379)
REDIS_URL=redis://...

# Google AI
GOOGLE_AI_API_KEY=xxx

# App
ENVIRONMENT=development
API_PORT=8000
FRONTEND_URL=http://localhost:3000
```

## Critical Files

1. **`services/api/src/core/hybrid_ranker.py`** - Weighted scoring logic
2. **`services/api/src/services/chat_service.py`** - SYNC path orchestrator
3. **`services/api/src/core/context_builder.py`** - Token budget management
4. **`services/worker/src/tasks/embedding_task.py`** - Embedding generation
5. **`database/migrations/`** - SQL schemas

## API Endpoints

### Authentication
- `POST /api/v1/auth/signup` - Register
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Current user

### Chat
- `POST /api/v1/chat/message` - Send message (SSE streaming)
- `GET /api/v1/chat/conversations` - List conversations
- `POST /api/v1/chat/conversations` - Create conversation

### Memory
- `GET /api/v1/memories` - List memories
- `POST /api/v1/memories` - Create memory
- `GET /api/v1/memories/search` - Search memories

## Common Tasks

### Adding a New Memory Type

1. Update `memories` table CHECK constraint
2. Update `MemoryType` enum in `services/api/src/models/memory.py`
3. Update `packages/shared/src/types/memory.types.ts`
4. Update context builder allocation

### Modifying Hybrid Ranking Weights

Edit `services/api/src/core/hybrid_ranker.py`:
```python
RANKING_WEIGHTS = {
    "keyword_match": 0.35,
    "vector_similarity": 0.25,
    "reliability": 0.20,
    "recency": 0.15,
    "frequency": 0.05
}
```

### Adding a New Entity Type

1. Update `entities` table CHECK constraint
2. Update extraction prompts in `services/worker/src/tasks/extraction_task.py`
3. Update frontend entity display

## Troubleshooting

### Embeddings Not Generated
- Check worker logs: `docker-compose logs worker`
- Verify Redis connection
- Check `embedding_status` in memories table

### Slow Vector Search
- Ensure Qdrant collection has `user_id` index
- Check if PRE-filtering is used (not POST)
- Consider reducing `top_k`

### SSE Streaming Issues
- Ensure `Content-Type: text/event-stream`
- Check CORS allows the frontend origin
- Verify no buffering middleware

## Performance Targets

| Scenario | Target |
|----------|--------|
| Chat response (TTFB) | <500ms |
| Vector search | <50ms |
| Full retrieval pipeline | <200ms |
| Embedding generation | <2s |

## Security Checklist

- [ ] All routes protected by auth middleware
- [ ] User isolation in all queries (PRE-filtering)
- [ ] RLS enabled on all tables
- [ ] Service role key only in backend
- [ ] Rate limiting enabled
- [ ] CORS restricted to frontend domain
