# Quick Reference Card

## What This Is
AI Memory System - LLMs that remember past interactions via RAG pipelines.

## Stack
- Frontend: Next.js 15 + Zustand
- Backend: FastAPI + Python 3.11
- DB: Supabase PostgreSQL + Qdrant (vectors) + Redis (cache)
- LLM: Google Gemini 2.5 Flash
- Embeddings: all-MiniLM-L6-v2 (384 dims)

## Key Paths
```
services/api/src/main.py              # Backend entry
services/api/src/services/chat_service.py  # Chat orchestrator
services/api/src/core/hybrid_ranker.py     # Ranking logic
apps/web/src/hooks/use-chat.ts        # Frontend streaming
apps/web/src/stores/chat.store.ts     # Chat state
```

## Chat Pipeline (7 phases)
1. Setup (auth, save msg) → 2. Query Analysis → 3. Retrieval (parallel) →
4. Hybrid Ranking → 5. Context Build → 6. LLM Stream → 7. Post-process

## Retrieval Strategies (all parallel)
- Vector (Qdrant) - semantic similarity
- Keyword (BM25) - term matching
- Graph - entity relationships
- Profile - user preferences
- Recent - episodic context

## Ranking Weights
keyword=0.35, vector=0.25, reliability=0.20, recency=0.15, frequency=0.05

## Token Budgets (5000 total)
profile=600, semantic=1500, episodic=1500, procedural=400, entity=300

## Memory Types
profile | semantic | episodic | procedural

## Optimizations Done
- Embedding pre-warm on startup (fixes 43s delay)
- asyncio.to_thread() for non-blocking embedding
- LRU cache for repeated queries
- Reduced keyword limit (1000→200)
- Reduced token budgets 40%

## User Isolation (CRITICAL)
Always PRE-filter by user_id in Qdrant, never POST-filter!

## API Prefixes
/api/auth | /api/chat | /api/memories | /api/profile | /api/v1/analytics

## Run Commands
```bash
uvicorn src.main:app --reload --port 8000  # Backend
npm run dev                                  # Frontend (apps/web)
docker-compose up -d                         # All services
```

## Common Fixes
- Slow first request → Check embedding pre-warm in main.py
- Empty analytics → Check emitter flush task
- Hydration errors → Browser extension cleanup in layout.tsx
- Stream abort → Use history.replaceState not router.replace
