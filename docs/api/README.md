# API Reference

> Complete REST API documentation for Jyntrix AI.

---

## Base URL

```
Development: http://localhost:8000
Production:  https://api.jyntrix.ai
```

---

## Authentication

All protected endpoints require JWT authentication via the `Authorization` header:

```http
Authorization: Bearer <jwt_token>
```

Tokens are obtained through Supabase Auth and validated on each request.

---

## API Endpoints Overview

### Authentication (`/api/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/signup` | Register new user |
| `POST` | `/api/auth/login` | Login and get token |
| `POST` | `/api/auth/logout` | Invalidate session |
| `GET` | `/api/auth/me` | Get current user |
| `POST` | `/api/auth/refresh` | Refresh access token |

[View Auth Documentation](./authentication.md)

---

### Chat (`/api/chat`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/chat/conversations` | List conversations |
| `POST` | `/api/chat/conversations` | Create conversation |
| `GET` | `/api/chat/conversations/{id}` | Get conversation |
| `DELETE` | `/api/chat/conversations/{id}` | Delete conversation |
| `GET` | `/api/chat/conversations/{id}/messages` | Get messages |
| `POST` | `/api/chat/send` | Send message (SSE streaming) |

[View Chat Documentation](./chat.md)

---

### Memory (`/api/memories`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/memories` | List memories |
| `POST` | `/api/memories` | Create memory |
| `GET` | `/api/memories/{id}` | Get memory |
| `PUT` | `/api/memories/{id}` | Update memory |
| `DELETE` | `/api/memories/{id}` | Delete memory |
| `GET` | `/api/memories/search` | Search memories |

[View Memory Documentation](./memory.md)

---

### Profile (`/api/profile`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/profile` | Get user profile |
| `PUT` | `/api/profile` | Update profile |
| `GET` | `/api/profile/preferences` | Get preferences |
| `PUT` | `/api/profile/preferences` | Update preferences |

[View Profile Documentation](./profile.md)

---

### Analytics (`/api/v1/analytics`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/analytics/requests` | List request analytics |
| `GET` | `/api/v1/analytics/requests/{id}` | Get single analytics |
| `GET` | `/api/v1/analytics/summary` | Get summary stats |
| `GET` | `/api/v1/analytics/latency` | Get latency percentiles |
| `GET` | `/api/v1/analytics/retrieval` | Get retrieval quality |
| `GET` | `/api/v1/analytics/timeseries` | Get time-series data |
| `POST` | `/api/v1/analytics/flush` | Force flush buffer |

[View Analytics Documentation](./analytics.md)

---

### Health (`/health`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API root info |
| `GET` | `/health` | Health check |

---

## Common Response Formats

### Success Response

```json
{
  "data": { ... },
  "message": "Success"
}
```

### Paginated Response

```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

### Error Response

```json
{
  "detail": "Error description",
  "error_code": "ERROR_CODE",
  "request_id": "uuid"
}
```

---

## HTTP Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `201` | Created |
| `400` | Bad Request - Invalid parameters |
| `401` | Unauthorized - Invalid/missing token |
| `403` | Forbidden - Insufficient permissions |
| `404` | Not Found - Resource doesn't exist |
| `422` | Validation Error - Invalid request body |
| `429` | Too Many Requests - Rate limited |
| `500` | Internal Server Error |

---

## Rate Limiting

| Limit | Value |
|-------|-------|
| Requests per minute | 100 |
| Requests per hour | 1000 |

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704556800
```

---

## Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes* | Bearer token for protected routes |
| `Content-Type` | Yes | `application/json` for POST/PUT |
| `X-Request-ID` | No | Custom request tracking ID |

---

## Streaming Responses (SSE)

The `/api/chat/send` endpoint uses Server-Sent Events for streaming:

```http
Content-Type: text/event-stream
```

Event format:
```
event: chunk
data: {"content": "Hello", "done": false}

event: done
data: {"message_id": "uuid", "done": true}
```

---

## SDK Examples

### cURL

```bash
# Get conversations
curl -X GET "http://localhost:8000/api/chat/conversations" \
  -H "Authorization: Bearer $TOKEN"

# Send message (streaming)
curl -X POST "http://localhost:8000/api/chat/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "uuid", "content": "Hello!"}'
```

### Python

```python
import requests

BASE_URL = "http://localhost:8000"
headers = {"Authorization": f"Bearer {token}"}

# Create conversation
response = requests.post(
    f"{BASE_URL}/api/chat/conversations",
    headers=headers,
    json={"title": "New Chat"}
)
conversation = response.json()
```

### TypeScript

```typescript
const api = {
  baseUrl: "http://localhost:8000",
  token: "your_token",

  async get(path: string) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      headers: { Authorization: `Bearer ${this.token}` },
    });
    return res.json();
  },

  async post(path: string, data: object) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    return res.json();
  },
};

// Usage
const conversations = await api.get("/api/chat/conversations");
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-06 | Initial release |
