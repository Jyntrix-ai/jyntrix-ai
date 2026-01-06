# Analytics API Documentation

> Real-time request analytics and performance monitoring for Jyntrix AI.

---

## Overview

The Analytics API provides comprehensive insights into chat request performance, retrieval quality, and system health. All analytics are user-scoped and respect data isolation.

### Base URL
```
/api/v1/analytics
```

### Authentication
All endpoints require a valid JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

---

## Endpoints

### 1. List Request Analytics

Retrieve paginated list of request analytics with optional filtering.

```http
GET /api/v1/analytics/requests
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (min: 1) |
| `page_size` | integer | 20 | Records per page (1-100) |
| `request_type` | string | null | Filter by type: `chat_stream`, `chat_sync` |
| `status` | string | null | Filter by status: `success`, `error` |
| `date_from` | datetime | null | Start date (ISO 8601) |
| `date_to` | datetime | null | End date (ISO 8601) |
| `conversation_id` | UUID | null | Filter by conversation |
| `min_latency_ms` | float | null | Minimum total latency |
| `max_latency_ms` | float | null | Maximum total latency |

#### Example Request

```bash
curl -X GET \
  "http://localhost:8000/api/v1/analytics/requests?page=1&page_size=10&status=success" \
  -H "Authorization: Bearer <token>"
```

#### Example Response

```json
{
  "analytics": [
    {
      "id": "c743336a-64ba-4b79-8385-875e16896227",
      "user_id": "613e6399-ab12-4ccf-aac1-0219d8260f4e",
      "request_id": "f3074834-a5d4-44f1-ac64-965af2884b1c",
      "request_type": "chat_stream",
      "conversation_id": "59352015-1616-4e0f-a01c-0326d9b07575",
      "message_id": "ed5ae8ca-9237-4497-9021-5ecf2db0ad7c",
      "total_time_ms": 4523.45,
      "ttfb_ms": 1245.32,
      "step_timings": {
        "setup_time": 512.34,
        "query_analysis_time": 45.67,
        "total_retrieval_time": 1823.45,
        "context_building_time": 89.12,
        "llm_ttfb": 1245.32,
        "llm_total_time": 2052.87,
        "save_response_time": 234.56
      },
      "retrieval_metrics": {
        "total_raw_results": 17,
        "vector_results_count": 10,
        "keyword_results_count": 7,
        "graph_results_count": 0,
        "profile_results_count": 0,
        "memories_by_type": {
          "semantic": 10,
          "episodic": 7
        },
        "score_distribution": {
          "vector": { "avg": 0.75, "min": 0.52, "max": 0.89 },
          "keyword": { "avg": 0.65, "min": 0.45, "max": 0.82 }
        }
      },
      "query_analysis": {
        "intent": "conversation",
        "confidence": 0.85,
        "keywords_count": 5,
        "entities_count": 2,
        "requires_memory": true,
        "memory_types_needed": ["semantic", "episodic"]
      },
      "status": "success",
      "error_message": null,
      "created_at": "2026-01-06T13:55:48.775128Z"
    }
  ],
  "total": 156,
  "page": 1,
  "page_size": 10,
  "has_more": true
}
```

---

### 2. Get Single Analytics Record

Retrieve detailed analytics for a specific request.

```http
GET /api/v1/analytics/requests/{analytics_id}
```

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `analytics_id` | UUID | Analytics record ID |

#### Example Request

```bash
curl -X GET \
  "http://localhost:8000/api/v1/analytics/requests/c743336a-64ba-4b79-8385-875e16896227" \
  -H "Authorization: Bearer <token>"
```

#### Response

Returns a single analytics object (same structure as list items).

---

### 3. Analytics Summary

Get aggregated statistics over a time period.

```http
GET /api/v1/analytics/summary
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Number of days to aggregate (1-90) |
| `request_type` | string | null | Filter by request type |

#### Example Request

```bash
curl -X GET \
  "http://localhost:8000/api/v1/analytics/summary?days=7" \
  -H "Authorization: Bearer <token>"
```

#### Example Response

```json
{
  "period_days": 7,
  "total_requests": 1234,
  "successful_requests": 1189,
  "failed_requests": 45,
  "success_rate": 0.9635,
  "avg_total_time_ms": 4523.45,
  "avg_ttfb_ms": 1245.32,
  "avg_retrieval_time_ms": 1823.45,
  "total_tokens_used": 125000,
  "requests_by_type": {
    "chat_stream": 1100,
    "chat_sync": 134
  },
  "requests_by_status": {
    "success": 1189,
    "error": 45
  }
}
```

---

### 4. Latency Percentiles

Get P50/P95/P99 latency percentiles for performance analysis.

```http
GET /api/v1/analytics/latency
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Analysis period (1-90) |
| `request_type` | string | null | Filter by type |
| `granularity` | string | "day" | Time grouping: `hour`, `day`, `week` |

#### Example Request

```bash
curl -X GET \
  "http://localhost:8000/api/v1/analytics/latency?days=7&granularity=day" \
  -H "Authorization: Bearer <token>"
```

#### Example Response

```json
{
  "period_days": 7,
  "granularity": "day",
  "overall": {
    "p50_ms": 3245.67,
    "p95_ms": 8234.12,
    "p99_ms": 12456.78
  },
  "by_operation": {
    "setup": { "p50_ms": 450.23, "p95_ms": 890.45, "p99_ms": 1234.56 },
    "retrieval": { "p50_ms": 1234.56, "p95_ms": 2345.67, "p99_ms": 4567.89 },
    "llm": { "p50_ms": 1567.89, "p95_ms": 3456.78, "p99_ms": 6789.01 }
  },
  "timeseries": [
    {
      "date": "2026-01-01",
      "p50_ms": 3100.45,
      "p95_ms": 7800.23,
      "p99_ms": 11234.56
    }
  ]
}
```

---

### 5. Retrieval Quality Stats

Get metrics about memory retrieval quality and coverage.

```http
GET /api/v1/analytics/retrieval
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Analysis period (1-90) |

#### Example Request

```bash
curl -X GET \
  "http://localhost:8000/api/v1/analytics/retrieval?days=7" \
  -H "Authorization: Bearer <token>"
```

#### Example Response

```json
{
  "period_days": 7,
  "avg_results_per_request": 12.5,
  "avg_vector_results": 8.3,
  "avg_keyword_results": 4.2,
  "avg_graph_results": 0.5,
  "avg_score": {
    "vector": 0.72,
    "keyword": 0.65,
    "combined": 0.68
  },
  "memory_type_distribution": {
    "semantic": 0.45,
    "episodic": 0.30,
    "profile": 0.15,
    "procedural": 0.10
  },
  "deduplication_rate": 0.12,
  "zero_results_rate": 0.03
}
```

---

### 6. Time Series Data

Get time-series data for dashboard charts.

```http
GET /api/v1/analytics/timeseries
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `metric` | string | required | Metric: `requests`, `latency`, `errors` |
| `days` | integer | 7 | Period (1-90) |
| `granularity` | string | "hour" | Grouping: `hour`, `day` |

#### Example Request

```bash
curl -X GET \
  "http://localhost:8000/api/v1/analytics/timeseries?metric=requests&days=7&granularity=hour" \
  -H "Authorization: Bearer <token>"
```

#### Example Response

```json
{
  "metric": "requests",
  "granularity": "hour",
  "period_days": 7,
  "data": [
    { "timestamp": "2026-01-06T10:00:00Z", "value": 45 },
    { "timestamp": "2026-01-06T11:00:00Z", "value": 52 },
    { "timestamp": "2026-01-06T12:00:00Z", "value": 78 }
  ]
}
```

---

### 7. Force Flush Buffer (Debug)

Force flush any buffered analytics to database. Useful for testing.

```http
POST /api/v1/analytics/flush
```

#### Example Request

```bash
curl -X POST \
  "http://localhost:8000/api/v1/analytics/flush" \
  -H "Authorization: Bearer <token>"
```

#### Example Response

```json
{
  "status": "flushed",
  "records_flushed": 5,
  "message": "Flushed 5 buffered analytics records"
}
```

---

## Data Models

### RequestAnalytics

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique analytics record ID |
| `user_id` | UUID | User who made the request |
| `request_id` | UUID | Unique request identifier |
| `request_type` | string | Type: `chat_stream`, `chat_sync` |
| `conversation_id` | UUID | Associated conversation |
| `message_id` | UUID | Associated message |
| `total_time_ms` | float | Total request duration |
| `ttfb_ms` | float | Time to first byte |
| `step_timings` | object | Breakdown by operation |
| `retrieval_metrics` | object | Memory retrieval stats |
| `query_analysis` | object | Query understanding results |
| `context_metrics` | object | Context building stats |
| `status` | string | `success` or `error` |
| `error_message` | string | Error details (if failed) |
| `error_type` | string | Error classification |
| `created_at` | datetime | Record timestamp |

### StepTimings Object

| Field | Type | Description |
|-------|------|-------------|
| `setup_time` | float | Conversation/message setup |
| `query_analysis_time` | float | Intent and entity extraction |
| `total_retrieval_time` | float | All memory retrieval |
| `vector_search_time` | float | Qdrant vector search |
| `keyword_search_time` | float | BM25 keyword matching |
| `graph_search_time` | float | Entity graph traversal |
| `profile_retrieval_time` | float | User profile fetch |
| `recent_context_time` | float | Recent messages fetch |
| `ranking_time` | float | Hybrid ranking |
| `context_building_time` | float | Context assembly |
| `llm_ttfb` | float | LLM first token |
| `llm_total_time` | float | Full LLM generation |
| `save_response_time` | float | Database persistence |

---

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Could not validate credentials"
}
```

### 404 Not Found

```json
{
  "detail": "Analytics record not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error",
  "request_id": "abc123"
}
```

---

## Usage Examples

### Python

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your_jwt_token"

headers = {"Authorization": f"Bearer {TOKEN}"}

# Get recent analytics
response = requests.get(
    f"{BASE_URL}/api/v1/analytics/requests",
    headers=headers,
    params={"page_size": 10, "status": "success"}
)
analytics = response.json()

# Get summary stats
summary = requests.get(
    f"{BASE_URL}/api/v1/analytics/summary",
    headers=headers,
    params={"days": 7}
).json()

print(f"Total requests: {summary['total_requests']}")
print(f"Success rate: {summary['success_rate']*100:.1f}%")
print(f"Avg latency: {summary['avg_total_time_ms']:.0f}ms")
```

### JavaScript/TypeScript

```typescript
const BASE_URL = "http://localhost:8000";
const TOKEN = "your_jwt_token";

async function getAnalytics() {
  const response = await fetch(
    `${BASE_URL}/api/v1/analytics/requests?page_size=10`,
    {
      headers: {
        Authorization: `Bearer ${TOKEN}`,
      },
    }
  );

  const data = await response.json();
  return data.analytics;
}

async function getLatencyPercentiles() {
  const response = await fetch(
    `${BASE_URL}/api/v1/analytics/latency?days=7`,
    {
      headers: {
        Authorization: `Bearer ${TOKEN}`,
      },
    }
  );

  const data = await response.json();
  console.log(`P95 latency: ${data.overall.p95_ms}ms`);
}
```

---

## Performance Considerations

### Buffering

Analytics are buffered in memory and flushed to the database:
- Every **10 seconds** (configurable via `analytics_flush_interval`)
- When buffer reaches **100 records** (configurable via `analytics_buffer_size`)
- On application shutdown

### User Isolation

All analytics queries are pre-filtered by `user_id` to ensure data isolation. Users can only access their own analytics data.

### Pagination

Large result sets are paginated. Use `page` and `page_size` parameters to navigate:
- Maximum `page_size`: 100
- Response includes `has_more` flag for easy iteration

---

## Related Documentation

- [Authentication](./authentication.md)
- [Chat API](./chat.md)
- [Memory API](./memory.md)
- [Backend Architecture](../backend/README.md)
