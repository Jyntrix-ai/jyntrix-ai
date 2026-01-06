# Fixes & Optimizations History

## Performance Fixes (2026-01-06)

### Phase 1: Embedding Pre-warm

**Problem:** First chat request took 43+ seconds
**Root Cause:** `SentenceTransformer('all-MiniLM-L6-v2')` model (~80MB) was loaded on first `embed()` call
**Fix:** Pre-load in `main.py` lifespan function

```python
# services/api/src/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm embedding model
    from src.core.embeddings import get_embedding_service
    embedding_service = get_embedding_service()
    embedding_service._ensure_initialized()
```

**Result:** 43s → <1s first request

---

### Phase 2: Full Optimization

**Problem:** After Phase 1, still 13-15 seconds total

**Fix 1: Non-blocking Embedding**
```python
# services/api/src/core/vector_search.py
# Change from:
query_embedding = self.embedder.embed(query)
# To:
query_embedding = await asyncio.to_thread(self.embedder.embed, query)
```

**Fix 2: Embedding Cache**
```python
# services/api/src/core/vector_search.py
_embedding_cache: dict[str, list] = {}  # Class-level cache
_cache_max_size: int = 100

cache_key = f"{user_id}:{query}"
if cache_key in self._embedding_cache:
    query_embedding = self._embedding_cache[cache_key]
else:
    query_embedding = await asyncio.to_thread(...)
    self._embedding_cache[cache_key] = query_embedding
```

**Fix 3: Reduce Keyword Search Limit**
```python
# services/api/src/services/retrieval_service.py
response = query.limit(200).execute()  # was 1000
```

**Fix 4: Reduce Token Budgets**
```python
# services/api/src/config.py
max_context_tokens: int = 5000      # was 8000
profile_memory_tokens: int = 600    # was 1000
semantic_memory_tokens: int = 1500  # was 2500
episodic_memory_tokens: int = 1500  # was 2500
procedural_memory_tokens: int = 400 # was 1000
```

**Result:** 13-15s → 3-5s total

---

### Analytics Fix

**Problem:** Analytics data never persisted - always empty
**Root Cause:** `AnalyticsEmitter` buffered but never flushed

**Fix:**
```python
# services/api/src/analytics/emitter.py
async def start(self):
    """Start background flush task."""
    self._flush_task = asyncio.create_task(self._periodic_flush())

async def _periodic_flush(self):
    """Flush buffer every N seconds."""
    while True:
        await asyncio.sleep(self.flush_interval)
        await self.flush()
```

Also added:
- Auto-start in `get_emitter()`
- Shutdown handler in `main.py` lifespan
- `/api/v1/analytics/flush` debug endpoint

---

## Frontend Fixes (2026-01-06)

### Hydration Mismatch

**Problem:** React hydration errors from browser extensions (Bitdefender injects `bis_skin_checked`)

**Fix:** MutationObserver cleanup in `apps/web/src/app/layout.tsx`
```javascript
const extensionCleanupScript = `
  var EXTENSION_ATTRS = ['bis_skin_checked', 'bis_register'];

  // Suppress console warnings
  console.error = function() {
    if (message.includes('Hydration') && message.includes('bis_skin_checked'))
      return;
    return originalError.apply(console, args);
  };

  // MutationObserver to clean injected attributes
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: EXTENSION_ATTRS
  });
`;
```

---

### Text Breaking Fix

**Problem:** "Thinking..." indicator breaking awkwardly ("Thinki\nng...")

**Fix:**
```css
/* apps/web/src/components/chat/thinking-indicator.tsx */
whitespace-nowrap

/* apps/web/src/app/globals.css */
.message-bubble { min-width: fit-content; }
```

---

### Auto-Scroll During Streaming

**Problem:** Chat didn't scroll smoothly during message streaming

**Fix:** Added `onStreamChunk` callback in `use-chat.ts`
```typescript
const { sendMessage } = useChat(conversationId, {
  onStreamChunk: () => {
    if (isNearBottomRef.current) {
      scrollToBottomRef.current(true);  // instant scroll
    }
  },
});
```

---

### Stream Abort on Navigation

**Problem:** Navigating to new chat URL aborted ongoing stream

**Fix:** Use `history.replaceState` instead of `router.replace`
```typescript
// Instead of:
router.replace(`/chat/${newConversationId}`);

// Use:
window.history.replaceState(null, '', `/chat/${newConversationId}`);
```

---

## Known Issues (Unresolved)

1. **Google Generative AI SDK deprecation warning** - migrate to `google.genai` package
2. **FastAPI deprecation** - `regex` parameter should use `pattern` instead

---

## Performance Metrics Summary

| Metric | Before | After |
|--------|--------|-------|
| First request retrieval | 43s | <1s |
| Setup time | 5-13s | <500ms |
| Total response time | 16-62s | 3-5s |
| App startup time | Normal | +6s (embedding load) |
