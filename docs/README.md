# Jyntrix AI - Technical Documentation

> Comprehensive documentation for the Jyntrix AI Memory Architecture platform.

---

## Table of Contents

| Section | Description | Path |
|---------|-------------|------|
| [Architecture Overview](./architecture/README.md) | System design, data flow, and component interactions | `/docs/architecture/` |
| [Backend API](./backend/README.md) | FastAPI services, endpoints, and business logic | `/docs/backend/` |
| [Frontend](./frontend/README.md) | Next.js application, components, and state management | `/docs/frontend/` |
| [API Reference](./api/README.md) | Complete API endpoint documentation | `/docs/api/` |

---

## Quick Links

### For Developers
- [Getting Started](./backend/getting-started.md)
- [API Authentication](./api/authentication.md)
- [Analytics API](./api/analytics.md)

### For Contributors
- [Code Structure](./architecture/code-structure.md)
- [Pipeline Flow](./architecture/pipeline-flow.md)

---

## Project Overview

**Jyntrix AI** is a production-ready AI Memory System that enables Large Language Models (LLMs) to "remember" past interactions. It transforms stateless chatbots into context-aware, personalized assistants.

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Semantic Memory** | Long-term storage of facts and knowledge |
| **Episodic Memory** | Session summaries and conversation history |
| **Profile Memory** | User preferences and personalization |
| **Procedural Memory** | Learned patterns and behaviors |
| **Hybrid Retrieval** | Multi-strategy search combining vector, keyword, and graph |
| **Real-time Analytics** | Request performance tracking and insights |

### Tech Stack

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                    Next.js 15 + React                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Backend API                             │
│                  FastAPI (Python 3.11+)                      │
├─────────────────────────────────────────────────────────────┤
│  Services: Chat | Memory | Auth | Analytics | Profile        │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    Supabase     │  │     Qdrant      │  │      Redis      │
│   PostgreSQL    │  │  Vector Store   │  │   Cache/Queue   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Documentation Standards

This documentation follows these principles:

1. **Clarity** - Simple, professional language
2. **Completeness** - All features documented
3. **Examples** - Code samples for every endpoint
4. **Accuracy** - No invented features; assumptions marked clearly

---

## Version

| Component | Version |
|-----------|---------|
| Documentation | 1.0.0 |
| Backend API | 1.0.0 |
| Frontend | 1.0.0 |
| Last Updated | 2026-01-06 |
