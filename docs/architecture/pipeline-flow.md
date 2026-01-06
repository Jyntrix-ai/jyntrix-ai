# Pipeline Flow Documentation

> Detailed step-by-step flow of the Jyntrix AI request processing pipeline.

---

## Chat Request Pipeline

### Complete Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           CHAT REQUEST PIPELINE                               │
│                                                                               │
│  USER MESSAGE                                                                 │
│       │                                                                       │
│       ▼                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 1: SETUP                                              [~500ms]   │  │
│  │                                                                        │  │
│  │  1.1 Validate JWT token                                               │  │
│  │       - Extract user_id from token                                    │  │
│  │       - Verify token with Supabase                                    │  │
│  │                                                                        │  │
│  │  1.2 Get or Create Conversation                                       │  │
│  │       IF conversation_id provided:                                    │  │
│  │           - Fetch from Supabase with user_id check                   │  │
│  │       ELSE:                                                           │  │
│  │           - Create new conversation record                           │  │
│  │                                                                        │  │
│  │  1.3 Save User Message                                                │  │
│  │       - Generate message UUID                                         │  │
│  │       - Insert into messages table                                    │  │
│  │       - Return message_id for tracking                               │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│       │                                                                       │
│       ▼                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 2: QUERY ANALYSIS                                     [~50ms]    │  │
│  │                                                                        │  │
│  │  2.1 Intent Classification                                            │  │
│  │       - conversation: General chat                                    │  │
│  │       - question: Seeking information                                 │  │
│  │       - recall: Referencing past context                             │  │
│  │       - command: Actionable request                                  │  │
│  │                                                                        │  │
│  │  2.2 Keyword Extraction                                               │  │
│  │       - Remove stopwords                                              │  │
│  │       - Extract meaningful terms                                      │  │
│  │       - Limit to top 10 keywords                                     │  │
│  │                                                                        │  │
│  │  2.3 Entity Recognition                                               │  │
│  │       - People, places, organizations                                │  │
│  │       - Match against known entity graph                             │  │
│  │                                                                        │  │
│  │  2.4 Memory Requirement Decision                                      │  │
│  │       - requires_memory: true/false                                  │  │
│  │       - memory_types_needed: [semantic, episodic, ...]               │  │
│  │                                                                        │  │
│  │  OUTPUT: QueryAnalysis {                                              │  │
│  │    intent, keywords, entities_mentioned,                              │  │
│  │    requires_memory, memory_types_needed, confidence                  │  │
│  │  }                                                                    │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│       │                                                                       │
│       ▼                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 3: MULTI-STRATEGY RETRIEVAL (PARALLEL)               [~1-2s]    │  │
│  │                                                                        │  │
│  │  asyncio.gather() executes ALL strategies simultaneously:            │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 3.1 VECTOR SEARCH (Qdrant)                            [~500ms]   │ │  │
│  │  │                                                                   │ │  │
│  │  │  a) Check embedding cache                                        │ │  │
│  │  │     cache_key = f"{user_id}:{query}"                            │ │  │
│  │  │     IF hit: use cached embedding                                 │ │  │
│  │  │     ELSE: generate embedding (non-blocking via asyncio.to_thread)│ │  │
│  │  │                                                                   │ │  │
│  │  │  b) Build Qdrant filter (PRE-filter, not POST!)                 │ │  │
│  │  │     must = [                                                     │ │  │
│  │  │       FieldCondition(key="user_id", match=user_id),             │ │  │
│  │  │       FieldCondition(key="type", match=memory_types)            │ │  │
│  │  │     ]                                                            │ │  │
│  │  │                                                                   │ │  │
│  │  │  c) Execute query_points()                                       │ │  │
│  │  │     - Returns top 10 similar vectors                            │ │  │
│  │  │     - Each with score, payload, memory_id                       │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 3.2 KEYWORD SEARCH (BM25)                             [~300ms]   │ │  │
│  │  │                                                                   │ │  │
│  │  │  a) Fetch candidate documents from Supabase                      │ │  │
│  │  │     SELECT * FROM memories                                       │ │  │
│  │  │     WHERE user_id = :user_id                                     │ │  │
│  │  │       AND type IN (:memory_types)                                │ │  │
│  │  │     LIMIT 200  -- Reduced from 1000 for performance             │ │  │
│  │  │                                                                   │ │  │
│  │  │  b) Apply BM25 ranking                                           │ │  │
│  │  │     - Tokenize query and documents                              │ │  │
│  │  │     - Calculate IDF weights                                      │ │  │
│  │  │     - Score each document                                        │ │  │
│  │  │     - Return top 10                                              │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 3.3 GRAPH SEARCH (Entity Relationships)               [~100ms]   │ │  │
│  │  │                                                                   │ │  │
│  │  │  IF entities_mentioned is not empty:                             │ │  │
│  │  │    a) Look up entities by name                                   │ │  │
│  │  │    b) Traverse relationships in entity graph                    │ │  │
│  │  │    c) Find memories connected to those entities                 │ │  │
│  │  │    d) Return related memories                                    │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 3.4 PROFILE RETRIEVAL (Always)                        [~50ms]    │ │  │
│  │  │                                                                   │ │  │
│  │  │  SELECT * FROM memories                                          │ │  │
│  │  │  WHERE user_id = :user_id                                        │ │  │
│  │  │    AND type = 'profile'                                          │ │  │
│  │  │  ORDER BY confidence DESC                                        │ │  │
│  │  │  LIMIT 20                                                        │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 3.5 RECENT CONTEXT (Episodic)                         [~50ms]    │ │  │
│  │  │                                                                   │ │  │
│  │  │  SELECT * FROM memories                                          │ │  │
│  │  │  WHERE user_id = :user_id                                        │ │  │
│  │  │    AND type = 'episodic'                                         │ │  │
│  │  │  ORDER BY created_at DESC                                        │ │  │
│  │  │  LIMIT 10                                                        │ │  │
│  │  │                                                                   │ │  │
│  │  │  Calculate recency_score = max(0, 1 - age_days/30)              │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                        │  │
│  │  COMBINE RESULTS: All strategies merge into single list              │  │
│  │  Handle exceptions: Log failures, continue with other results        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│       │                                                                       │
│       ▼                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 4: HYBRID RANKING                                     [~20ms]   │  │
│  │                                                                        │  │
│  │  4.1 Deduplication                                                    │  │
│  │       - Group by memory_id                                            │  │
│  │       - Keep highest-scored version                                   │  │
│  │       - Merge match_types (e.g., "vector,keyword")                   │  │
│  │                                                                        │  │
│  │  4.2 Score Calculation (for each memory)                              │  │
│  │                                                                        │  │
│  │       keyword_score = normalize_bm25(raw_score)     # tanh(score*0.2)│  │
│  │       vector_score  = (cosine_sim + 1) / 2          # [-1,1] → [0,1] │  │
│  │       reliability   = memory.confidence             # Already [0,1]  │  │
│  │       recency_score = exp(-decay_rate * age_days)   # 30-day half-life│  │
│  │       frequency     = log(1+access_count) / log(1001) # Log scale    │  │
│  │                                                                        │  │
│  │  4.3 Weighted Combination                                             │  │
│  │                                                                        │  │
│  │       combined_score = (keyword_score  * 0.35) +                      │  │
│  │                        (vector_score   * 0.25) +                      │  │
│  │                        (reliability    * 0.20) +                      │  │
│  │                        (recency_score  * 0.15) +                      │  │
│  │                        (frequency      * 0.05)                        │  │
│  │                                                                        │  │
│  │  4.4 Sort by combined_score DESC                                      │  │
│  │                                                                        │  │
│  │  OUTPUT: Ranked list of memories with scores                          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│       │                                                                       │
│       ▼                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 5: CONTEXT BUILDING                                  [~30ms]    │  │
│  │                                                                        │  │
│  │  5.1 Categorize by Memory Type                                        │  │
│  │       profile:    []                                                  │  │
│  │       semantic:   []                                                  │  │
│  │       episodic:   []                                                  │  │
│  │       procedural: []                                                  │  │
│  │                                                                        │  │
│  │  5.2 Apply Token Budgets                                              │  │
│  │       FOR each category:                                              │  │
│  │         current_tokens = 0                                            │  │
│  │         FOR each memory in ranked order:                              │  │
│  │           tokens = count_tokens(memory.content)                       │  │
│  │           IF current_tokens + tokens > budget:                        │  │
│  │             BREAK                                                     │  │
│  │           ADD memory to result                                        │  │
│  │           current_tokens += tokens                                    │  │
│  │                                                                        │  │
│  │  5.3 Budget Allocation                                                │  │
│  │       Profile:    600 tokens                                          │  │
│  │       Semantic:   1500 tokens                                         │  │
│  │       Episodic:   1500 tokens                                         │  │
│  │       Procedural: 400 tokens                                          │  │
│  │       Entity:     300 tokens                                          │  │
│  │                                                                        │  │
│  │  OUTPUT: MemoryContext object                                         │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│       │                                                                       │
│       ▼                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 6: LLM STREAMING                                    [1-2s]      │  │
│  │                                                                        │  │
│  │  6.1 Build System Prompt                                              │  │
│  │       base_prompt = """                                               │  │
│  │         You are a helpful AI assistant with memory capabilities...   │  │
│  │       """                                                             │  │
│  │                                                                        │  │
│  │       IF memory_context:                                              │  │
│  │         prompt += "\n\n# User Context\n"                              │  │
│  │         prompt += format_memories_as_context()                        │  │
│  │                                                                        │  │
│  │  6.2 Build Messages Array                                             │  │
│  │       messages = [                                                    │  │
│  │         { role: "system", content: system_prompt },                   │  │
│  │         ...conversation_history[-10:],                                │  │
│  │         { role: "user", content: current_message }                    │  │
│  │       ]                                                               │  │
│  │                                                                        │  │
│  │  6.3 Call Gemini API (Streaming)                                      │  │
│  │       response = gemini.generate_content(                             │  │
│  │         contents=messages,                                            │  │
│  │         generation_config={max_tokens: 4096, temperature: 0.7},      │  │
│  │         stream=True                                                   │  │
│  │       )                                                               │  │
│  │                                                                        │  │
│  │  6.4 Stream Response                                                  │  │
│  │       first_chunk_time = None                                         │  │
│  │       full_response = ""                                              │  │
│  │                                                                        │  │
│  │       FOR chunk in response:                                          │  │
│  │         IF not first_chunk_time:                                      │  │
│  │           first_chunk_time = now()  # Track TTFB                     │  │
│  │         full_response += chunk.text                                   │  │
│  │         YIELD SSE event: { type: "text", content: chunk.text }       │  │
│  │                                                                        │  │
│  │  OUTPUT: Streamed text chunks via SSE                                 │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│       │                                                                       │
│       ▼                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 7: POST-PROCESSING                                   [~100ms]   │  │
│  │                                                                        │  │
│  │  7.1 Save Assistant Response                                          │  │
│  │       INSERT INTO messages (                                          │  │
│  │         id, conversation_id, user_id,                                │  │
│  │         role='assistant', content=full_response                      │  │
│  │       )                                                               │  │
│  │                                                                        │  │
│  │  7.2 Update Conversation Metadata                                     │  │
│  │       UPDATE conversations SET                                        │  │
│  │         message_count = message_count + 2,                           │  │
│  │         last_message_at = NOW(),                                      │  │
│  │         updated_at = NOW()                                            │  │
│  │       WHERE id = :conversation_id                                     │  │
│  │                                                                        │  │
│  │  7.3 Enqueue Background Tasks                                         │  │
│  │       arq.enqueue_job("extract_entities", user_message_id)           │  │
│  │       arq.enqueue_job("extract_entities", assistant_message_id)      │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│       │                                                                       │
│       ▼                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 8: ANALYTICS EMISSION                              [Non-blocking]│  │
│  │                                                                        │  │
│  │  8.1 Finalize Collector                                               │  │
│  │       analytics = collector.finalize()                                │  │
│  │       # Computes total_time, aggregates span timings                 │  │
│  │                                                                        │  │
│  │  8.2 Emit to Buffer                                                   │  │
│  │       asyncio.create_task(emit_analytics(analytics))                 │  │
│  │       # Non-blocking, runs in background                             │  │
│  │                                                                        │  │
│  │  8.3 Buffer Flush (periodic)                                          │  │
│  │       IF buffer.size >= 10 OR time_since_flush >= 10s:               │  │
│  │         INSERT BATCH INTO request_analytics                          │  │
│  │         buffer.clear()                                                │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  DONE: SSE stream closed, connection terminated                              │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Timing Breakdown

### Typical Request Timeline (After Optimizations)

```
0ms      100ms    200ms    500ms    1000ms   1500ms   2000ms   3000ms
|--------|--------|--------|--------|--------|--------|--------|
|                                                               |
|--SETUP--------------------------------|                       |
|  ~500ms: Auth + Save message          |                       |
|                                       |                       |
|        |--QUERY ANALYSIS--|           |                       |
|        |  ~50ms           |           |                       |
|        |                  |           |                       |
|                 |--RETRIEVAL (parallel)-----------------|     |
|                 |  ~1000-1500ms total                   |     |
|                 |  ├─ Vector: 500ms                     |     |
|                 |  ├─ Keyword: 300ms                    |     |
|                 |  ├─ Graph: 100ms                      |     |
|                 |  ├─ Profile: 50ms                     |     |
|                 |  └─ Recent: 50ms                      |     |
|                 |                                       |     |
|                                     |--RANKING-|              |
|                                     |  ~20ms   |              |
|                                               |--CONTEXT-|    |
|                                               |  ~30ms   |    |
|                                                          |    |
|                                                  |--LLM STREAMING--|
|                                                  |  1000-2000ms    |
|                                                  |  TTFB: ~1000ms  |
|                                                  |                 |
|-----------------------------------------------------------|------|
                                                             3000ms
                                                        (First chunk)
```

---

## Error Handling Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                         ERROR HANDLING FLOW                             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ TRY: Main pipeline execution                                     │   │
│  │                                                                   │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │ Phase 1-2: Setup & Query Analysis                         │  │   │
│  │  │   ON ERROR:                                               │  │   │
│  │  │     - Log error with request_id                           │  │   │
│  │  │     - Yield { type: "error", error: "Setup failed" }      │  │   │
│  │  │     - Return early                                         │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  │                                                                   │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │ Phase 3: Retrieval                                        │  │   │
│  │  │   Each strategy runs with return_exceptions=True          │  │   │
│  │  │                                                            │  │   │
│  │  │   FOR result in results:                                   │  │   │
│  │  │     IF isinstance(result, Exception):                      │  │   │
│  │  │       log.error(f"Strategy failed: {result}")             │  │   │
│  │  │       CONTINUE  # Don't fail entire pipeline              │  │   │
│  │  │     ELSE:                                                  │  │   │
│  │  │       combined_results.extend(result)                      │  │   │
│  │  │                                                            │  │   │
│  │  │   # Pipeline continues with partial results                │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  │                                                                   │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │ Phase 6: LLM Streaming                                    │  │   │
│  │  │   ON ERROR during stream:                                 │  │   │
│  │  │     - Record error in analytics                           │  │   │
│  │  │     - Yield { type: "error", error: message }             │  │   │
│  │  │     - Return early (no save, no async tasks)              │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  │                                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ CATCH: Any unhandled exception                                   │   │
│  │                                                                   │   │
│  │   1. Log full exception with traceback                           │   │
│  │   2. Record in analytics collector (if available)                │   │
│  │   3. Yield { type: "error", error: "Internal error" }           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ FINALLY: Cleanup                                                 │   │
│  │                                                                   │   │
│  │   1. Finalize analytics collector                                │   │
│  │   2. Emit analytics (async, non-blocking)                        │   │
│  │   3. Clear collector from context                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Memory Extraction Pipeline (Background)

```
┌────────────────────────────────────────────────────────────────────────┐
│                    MEMORY EXTRACTION PIPELINE                           │
│                    (Runs in ARQ Worker)                                 │
│                                                                         │
│  JOB RECEIVED: extract_entities(message_id)                            │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ STEP 1: Load Message                                             │   │
│  │                                                                   │   │
│  │   message = supabase.table("messages")                           │   │
│  │     .select("*")                                                 │   │
│  │     .eq("id", message_id)                                        │   │
│  │     .single()                                                    │   │
│  │     .execute()                                                   │   │
│  │                                                                   │   │
│  │   user_id = message.user_id                                      │   │
│  │   content = message.content                                      │   │
│  └────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ STEP 2: Extract Entities (LLM)                                   │   │
│  │                                                                   │   │
│  │   prompt = """                                                   │   │
│  │     Extract entities from this message:                         │   │
│  │     - People (names, relationships)                              │   │
│  │     - Places (locations, addresses)                              │   │
│  │     - Organizations (companies, schools)                         │   │
│  │     - Dates/Times (events, appointments)                         │   │
│  │     - Facts (preferences, statements)                            │   │
│  │                                                                   │   │
│  │     Return as JSON array.                                        │   │
│  │   """                                                            │   │
│  │                                                                   │   │
│  │   entities = gemini.generate(prompt + content)                   │   │
│  └────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ STEP 3: Store Entities                                           │   │
│  │                                                                   │   │
│  │   FOR entity in entities:                                        │   │
│  │     # Check if entity exists                                     │   │
│  │     existing = find_entity(user_id, entity.name, entity.type)   │   │
│  │                                                                   │   │
│  │     IF existing:                                                 │   │
│  │       # Update with new information                              │   │
│  │       merge_entity_attributes(existing, entity)                 │   │
│  │     ELSE:                                                        │   │
│  │       # Create new entity                                        │   │
│  │       insert_entity(user_id, entity)                            │   │
│  │                                                                   │   │
│  │     # Create relationship if mentioned with other entities      │   │
│  │     FOR related in entity.relationships:                        │   │
│  │       create_relationship(entity, related, type)                │   │
│  └────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ STEP 4: Create/Update Memories                                   │   │
│  │                                                                   │   │
│  │   FOR fact in extracted_facts:                                   │   │
│  │     memory = create_memory(                                      │   │
│  │       user_id=user_id,                                          │   │
│  │       type=determine_memory_type(fact),  # semantic, profile    │   │
│  │       content=fact.content,                                     │   │
│  │       source_message_id=message_id,                             │   │
│  │       confidence=fact.confidence,                               │   │
│  │     )                                                            │   │
│  │                                                                   │   │
│  │     # Enqueue embedding generation                               │   │
│  │     enqueue_job("generate_embedding", memory.id)                │   │
│  └────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  JOB COMPLETE                                                          │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Embedding Generation Pipeline

```
┌────────────────────────────────────────────────────────────────────────┐
│                   EMBEDDING GENERATION PIPELINE                         │
│                                                                         │
│  JOB RECEIVED: generate_embedding(memory_id)                           │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ STEP 1: Load Memory                                              │   │
│  │                                                                   │   │
│  │   memory = supabase.table("memories")                            │   │
│  │     .select("*")                                                 │   │
│  │     .eq("id", memory_id)                                         │   │
│  │     .single()                                                    │   │
│  │     .execute()                                                   │   │
│  │                                                                   │   │
│  │   # Skip if already embedded                                     │   │
│  │   IF memory.embedding_status == "completed":                     │   │
│  │     RETURN                                                       │   │
│  │                                                                   │   │
│  │   # Mark as processing                                           │   │
│  │   update_embedding_status(memory_id, "processing")               │   │
│  └────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ STEP 2: Generate Embedding                                       │   │
│  │                                                                   │   │
│  │   # Using sentence-transformers (all-MiniLM-L6-v2)              │   │
│  │   # Model is pre-loaded at worker startup                        │   │
│  │                                                                   │   │
│  │   embedding = model.encode(memory.content)                       │   │
│  │   # Returns: float[384] vector                                   │   │
│  └────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ STEP 3: Upsert to Qdrant                                        │   │
│  │                                                                   │   │
│  │   qdrant.upsert(                                                 │   │
│  │     collection_name="memories",                                  │   │
│  │     points=[                                                     │   │
│  │       PointStruct(                                               │   │
│  │         id=memory_id,                                            │   │
│  │         vector=embedding,                                        │   │
│  │         payload={                                                │   │
│  │           "user_id": memory.user_id,     # CRITICAL for PRE-filter│   │
│  │           "type": memory.type,                                   │   │
│  │           "content": memory.content,                             │   │
│  │           "keywords": memory.keywords,                           │   │
│  │           "confidence": memory.confidence,                       │   │
│  │           "created_at": memory.created_at,                       │   │
│  │         }                                                        │   │
│  │       )                                                          │   │
│  │     ]                                                            │   │
│  │   )                                                              │   │
│  └────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ STEP 4: Update Status                                            │   │
│  │                                                                   │   │
│  │   supabase.table("memories")                                     │   │
│  │     .update({ embedding_status: "completed" })                   │   │
│  │     .eq("id", memory_id)                                         │   │
│  │     .execute()                                                   │   │
│  └────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  JOB COMPLETE                                                          │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [Architecture Overview](./README.md)
- [Backend Architecture](../backend/README.md)
- [Frontend Architecture](../frontend/README.md)
- [API Reference](../api/README.md)
