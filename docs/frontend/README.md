# Frontend Architecture Documentation

> Next.js 15 application powering the Jyntrix AI user interface.

---

## Overview

The frontend is a modern React application built with Next.js 15, featuring:
- Server-side rendering with App Router
- Real-time chat with SSE streaming
- Zustand state management
- Supabase authentication
- Responsive design with Tailwind CSS

### Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | Next.js 15 | React meta-framework |
| Runtime | React 19 | UI library |
| Auth | Supabase Auth | Authentication |
| State | Zustand | Client state management |
| Styling | Tailwind CSS | Utility-first CSS |
| UI | Custom components | Chat interface |
| Font | Inter | Typography |

---

## Project Structure

```
apps/web/src/
├── app/                        # Next.js App Router
│   ├── layout.tsx              # Root layout, providers, metadata
│   ├── page.tsx                # Landing page (redirects)
│   ├── globals.css             # Global styles
│   ├── providers.tsx           # React context providers
│   │
│   ├── (auth)/                 # Auth route group
│   │   ├── layout.tsx          # Auth layout
│   │   ├── login/page.tsx      # Login page
│   │   └── signup/page.tsx     # Signup page
│   │
│   ├── (chat)/                 # Chat route group
│   │   ├── layout.tsx          # Chat layout with sidebar
│   │   ├── chat/page.tsx       # New chat page
│   │   └── chat/[id]/page.tsx  # Existing conversation
│   │
│   ├── (dashboard)/            # Dashboard route group
│   │   └── memories/page.tsx   # Memory management
│   │
│   └── auth/
│       └── callback/route.ts   # OAuth callback handler
│
├── components/                  # React components
│   ├── ui/                      # Base UI components
│   │   ├── button.tsx          # Button component
│   │   ├── input.tsx           # Input component
│   │   ├── card.tsx            # Card component
│   │   ├── skeleton.tsx        # Loading skeleton
│   │   └── hydration-wrapper.tsx # SSR hydration helper
│   │
│   ├── chat/                    # Chat-specific components
│   │   ├── chat-interface.tsx  # Main chat container
│   │   ├── chat-input.tsx      # Message input
│   │   ├── message-item.tsx    # Single message display
│   │   ├── streaming-message.tsx # Live streaming message
│   │   ├── thinking-indicator.tsx # "Thinking..." indicator
│   │   └── sidebar.tsx         # Conversation sidebar
│   │
│   └── memory/                  # Memory components
│       ├── memory-list.tsx     # Memory list view
│       └── memory-card.tsx     # Single memory card
│
├── hooks/                       # Custom React hooks
│   ├── use-chat.ts             # Chat functionality hook
│   └── use-auth.ts             # Authentication hook
│
├── stores/                      # Zustand stores
│   ├── chat.store.ts           # Chat state management
│   └── auth.store.ts           # Auth state management
│
├── lib/                         # Utilities and services
│   ├── api.ts                  # API client with SSE
│   ├── utils.ts                # Utility functions
│   ├── id.ts                   # ID generation
│   └── supabase/               # Supabase clients
│       ├── client.ts           # Browser client
│       ├── server.ts           # Server client
│       └── middleware.ts       # Auth middleware
│
└── middleware.ts               # Next.js middleware (auth)
```

---

## Core Components

### 1. ChatInterface (`components/chat/chat-interface.tsx`)

Main container for the chat experience. Handles:
- Message display (static and streaming)
- Auto-scroll behavior
- New conversation creation
- Quick prompts for empty state

**Key Features:**

```typescript
export function ChatInterface({
  conversationId,
  onFirstMessage,
  isNewChat = false,
}: ChatInterfaceProps) {
  // Optimized rendering: Static messages and streaming message are separate
  const staticMessages = useMemo(() => {
    if (!isStreaming || !streamingMessageId) return messages;
    return messages.filter((m) => m.id !== streamingMessageId);
  }, [messages, isStreaming, streamingMessageId]);

  // Auto-scroll during streaming with performance optimization
  const { sendMessage } = useChat(conversationId, {
    onStreamChunk: () => {
      if (isNearBottomRef.current) {
        scrollToBottomRef.current(true); // Instant scroll during streaming
      }
    },
  });
}
```

**Performance Optimizations:**
- Separate rendering for static vs streaming messages
- `useMemo` for message filtering
- Instant scroll during streaming (not smooth)
- `requestAnimationFrame` for scroll actions

---

### 2. StreamingMessage (`components/chat/streaming-message.tsx`)

Dedicated component for live streaming responses.

**Purpose:**
- Only re-renders during streaming (not entire message list)
- Reads from `streamingContent` store (not messages array)
- Reduces React reconciliation overhead

---

### 3. ThinkingIndicator (`components/chat/thinking-indicator.tsx`)

Shows "Thinking..." animation during LLM processing.

**Fix Applied:**
- Added `whitespace-nowrap` to prevent awkward line breaks on small screens

---

## Custom Hooks

### useChat (`hooks/use-chat.ts`)

Primary hook for chat functionality.

```typescript
export function useChat(
  conversationId: string | null,
  options?: UseChatOptions
) {
  // Returns:
  return {
    sendMessage,      // Stream a message
    sendMessageSync,  // Non-streaming fallback
    cancelStream,     // Abort current stream
    isLoading,        // Loading state
    error,            // Error message
    clearError,       // Clear error
  };
}
```

**Key Features:**
- AbortController for stream cancellation
- Optimistic UI updates (user message appears immediately)
- Error recovery with fallback message
- Callback for scroll on stream chunks

**Flow:**

1. Cancel any existing stream
2. Create AbortController for new stream
3. Add user message optimistically
4. Add placeholder assistant message
5. Start streaming state
6. Process SSE chunks
7. Finalize message on completion

---

### useAuth (`hooks/use-auth.ts`)

Authentication state and actions.

```typescript
export function useAuth() {
  return {
    user,         // Current user
    session,      // Supabase session
    isLoading,    // Auth loading state
    signIn,       // Sign in function
    signUp,       // Sign up function
    signOut,      // Sign out function
  };
}
```

---

## State Management

### ChatStore (`stores/chat.store.ts`)

Zustand store for chat state with devtools and persistence.

**State Shape:**

```typescript
interface ChatState {
  // Current state
  currentConversationId: string | null;
  conversations: Conversation[];
  messages: Message[];
  isStreaming: boolean;

  // Streaming optimization
  streamingContent: string;      // Accumulated content during stream
  streamingMessageId: string | null;

  // Actions
  addMessage: (message: Message) => void;
  startStreaming: (messageId: string) => void;
  appendStreamingContent: (chunk: string) => void;
  finalizeStreamingMessage: () => void;
  // ... more actions
}
```

**Streaming Optimization:**

Instead of updating the messages array on every chunk (causing full re-renders), we:

1. Store streaming content separately (`streamingContent`)
2. Only render `StreamingMessage` component during streaming
3. Finalize by updating the message content once at the end

```typescript
// Start streaming - don't touch messages array
startStreaming: (messageId) => set({
  streamingMessageId: messageId,
  streamingContent: '',
  isStreaming: true,
});

// Append chunks - only update streamingContent
appendStreamingContent: (chunk) => set((state) => ({
  streamingContent: state.streamingContent + chunk,
}));

// Finalize - update message once
finalizeStreamingMessage: () => set((state) => ({
  messages: state.messages.map((msg) =>
    msg.id === state.streamingMessageId
      ? { ...msg, content: state.streamingContent }
      : msg
  ),
  streamingContent: '',
  streamingMessageId: null,
  isStreaming: false,
}));
```

**Persistence:**
- Only persists last 20 conversations (not messages or streaming state)
- Uses `partialize` option to select what to persist

---

## API Client (`lib/api.ts`)

Handles all backend communication.

### Standard Requests

```typescript
async function request<T>(
  endpoint: string,
  options: ApiOptions = {}
): Promise<T> {
  // 1. Get auth token from Supabase
  const token = await getAuthToken();

  // 2. Make request with Authorization header
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    ...options,
  });

  return response.json();
}
```

### SSE Streaming

```typescript
async function streamRequest(
  endpoint: string,
  body: Record<string, unknown>,
  onChunk: (chunk: string) => void,
  onDone?: () => void,
  onError?: (error: Error) => void,
  signal?: AbortSignal
): Promise<void> {
  // 1. Make request with Accept: text/event-stream
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
    signal,  // For cancellation
  });

  // 2. Read stream
  const reader = response.body.getReader();

  // 3. Process SSE events
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    // Parse "data: {...}" lines
    if (line.startsWith('data: ')) {
      const parsed = JSON.parse(line.slice(6));
      if (parsed.content) {
        onChunk(parsed.content);
      }
    }
  }
}
```

### API Endpoints

```typescript
export const api = {
  conversations: {
    list: () => request('/api/chat/conversations'),
    get: (id) => request(`/api/chat/conversations/${id}`),
    create: (data) => request('/api/chat/conversations', { method: 'POST', body }),
    update: (id, data) => request(`/api/chat/conversations/${id}`, { method: 'PATCH', body }),
    delete: (id) => request(`/api/chat/conversations/${id}`, { method: 'DELETE' }),
  },

  messages: {
    list: (conversationId) => request(`/api/chat/conversations/${conversationId}/messages`),
    send: (conversationId, content) => request(...),
    stream: (conversationId, content, onChunk, onDone, onError, signal) => streamRequest(...),
  },

  memories: {
    list: (params) => request('/api/memories', { params }),
    get: (id) => request(`/api/memories/${id}`),
    delete: (id) => request(`/api/memories/${id}`, { method: 'DELETE' }),
    search: (query, limit) => request('/api/memories/search', { method: 'POST', body }),
  },

  health: () => request('/health'),
};
```

---

## Authentication Flow

### Supabase Integration

**Browser Client (`lib/supabase/client.ts`):**
```typescript
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

**Server Client (`lib/supabase/server.ts`):**
```typescript
export async function createClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: cookieStore }
  );
}
```

### Middleware (`middleware.ts`)

Protects routes and refreshes sessions:

```typescript
export async function middleware(request: NextRequest) {
  // Skip public routes
  if (isPublicRoute(request.nextUrl.pathname)) {
    return NextResponse.next();
  }

  // Refresh session via Supabase
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();

  // Redirect to login if no session
  if (!session) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
}
```

---

## Browser Extension Fix

### Hydration Mismatch Issue

Browser extensions like Bitdefender inject attributes (`bis_skin_checked`) into the DOM, causing React hydration mismatches.

**Solution (`app/layout.tsx`):**

```javascript
const extensionCleanupScript = `
(function() {
  var EXTENSION_ATTRS = ['bis_skin_checked', 'bis_register'];

  // 1. Suppress hydration warnings in console
  var originalError = console.error;
  console.error = function() {
    if (message.includes('Hydration') && message.includes('bis_skin_checked')) {
      return; // Suppress
    }
    return originalError.apply(console, args);
  };

  // 2. Clean existing attributes
  function cleanAll() {
    EXTENSION_ATTRS.forEach(function(attr) {
      document.querySelectorAll('[' + attr + ']').forEach(el => {
        el.removeAttribute(attr);
      });
    });
  }

  // 3. MutationObserver for future injections
  var observer = new MutationObserver(function(mutations) {
    requestAnimationFrame(cleanAll);
  });
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: EXTENSION_ATTRS,
    childList: true,
    subtree: true
  });
})();
`;
```

---

## URL Management

### Silent URL Updates

When creating a new conversation, we update the URL without triggering navigation (which would abort the stream):

```typescript
// Instead of router.replace() which causes navigation:
window.history.replaceState(null, '', `/chat/${newConversationId}`);
```

This keeps the stream running while updating the URL for bookmarking.

---

## Styling

### Tailwind CSS Configuration

Custom design tokens defined in `globals.css`:

```css
:root {
  /* Colors */
  --color-primary-500: #6366f1;
  --color-accent-500: #8b5cf6;

  /* Surfaces */
  --color-surface: #ffffff;
  --color-surface-elevated: #f8fafc;
  --color-border: #e2e8f0;

  /* Text */
  --color-text-primary: #0f172a;
  --color-text-secondary: #64748b;
}

.dark {
  --color-surface: #0f172a;
  --color-surface-elevated: #1e293b;
  --color-border: #334155;
  --color-text-primary: #f8fafc;
  --color-text-secondary: #94a3b8;
}
```

### Message Bubble Fix

Prevents awkward text breaking on small screens:

```css
.message-bubble {
  min-width: fit-content;
}
```

---

## Environment Variables

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# App
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

---

## Development Commands

```bash
# Install dependencies
cd apps/web
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Type checking
npm run typecheck

# Linting
npm run lint
```

---

## Performance Considerations

### Optimizations Implemented

| Optimization | Description |
|--------------|-------------|
| Streaming separation | StreamingMessage renders independently |
| useMemo for messages | Prevent unnecessary re-renders |
| Instant scroll | Use `behavior: 'instant'` during streaming |
| Partial persistence | Only persist conversation list, not messages |
| requestAnimationFrame | Batch DOM updates for scrolling |

### Bundle Considerations

- Inter font loaded with `display: 'swap'`
- Components are client-side where needed (`'use client'`)
- Supabase client created lazily

---

## Related Documentation

- [Backend Architecture](../backend/README.md)
- [API Reference](../api/README.md)
- [Pipeline Flow](../architecture/pipeline-flow.md)
