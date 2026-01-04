import { createClient } from '@/lib/supabase/client';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';

interface ApiOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

async function getAuthToken(): Promise<string | null> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token || null;
}

async function request<T>(
  endpoint: string,
  options: ApiOptions = {}
): Promise<T> {
  const { params, ...fetchOptions } = options;

  // Build URL with query params
  let url = `${API_URL}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  // Get auth token
  const token = await getAuthToken();

  // Make request
  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...fetchOptions.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || `API error: ${response.status}`);
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) {
    return {} as T;
  }

  return JSON.parse(text);
}

// Streaming request for SSE
async function streamRequest(
  endpoint: string,
  body: Record<string, unknown>,
  onChunk: (chunk: string) => void,
  onDone?: () => void
): Promise<void> {
  const token = await getAuthToken();

  const response = await fetch(`${API_URL}${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || `API error: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process SSE events
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            onDone?.();
            return;
          }
          try {
            const parsed = JSON.parse(data);
            if (parsed.content) {
              onChunk(parsed.content);
            }
          } catch {
            // Not JSON, treat as raw text
            onChunk(data);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  onDone?.();
}

// API interface types
export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  memoryCount?: number;
}

export interface Message {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: string;
  memories?: Array<{
    id: string;
    type: string;
    content: string;
  }>;
}

export interface Memory {
  id: string;
  type: 'core' | 'episodic' | 'semantic' | 'procedural';
  content: string;
  importance: number;
  createdAt: string;
  lastAccessedAt?: string;
  accessCount?: number;
  sourceConversationId?: string;
  metadata?: Record<string, unknown>;
}

// Conversation list response type
interface ConversationListResponse {
  conversations: Conversation[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// API endpoints
export const api = {
  // Conversations
  conversations: {
    list: async () => {
      const response = await request<ConversationListResponse>('/api/chat/conversations');
      return response.conversations || [];
    },

    get: (id: string) => request<Conversation>(`/api/chat/conversations/${id}`),

    create: (data: { title?: string }) =>
      request<Conversation>('/api/chat/conversations', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    update: (id: string, data: { title?: string }) =>
      request<Conversation>(`/api/chat/conversations/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),

    delete: (id: string) =>
      request<void>(`/api/chat/conversations/${id}`, {
        method: 'DELETE',
      }),
  },

  // Messages
  messages: {
    list: (conversationId: string) =>
      request<Message[]>(`/api/chat/conversations/${conversationId}/messages`),

    send: (conversationId: string, content: string) =>
      request<Message>(`/api/chat/conversations/${conversationId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content }),
      }),

    stream: (
      conversationId: string,
      content: string,
      onChunk: (chunk: string) => void,
      onDone?: () => void
    ) =>
      streamRequest(
        `/api/chat/send`,
        { content, conversation_id: conversationId },
        onChunk,
        onDone
      ),
  },

  // Memories
  memories: {
    list: (params?: { type?: string; search?: string; limit?: number }) =>
      request<Memory[]>('/api/memories', { params }),

    get: (id: string) => request<Memory>(`/api/memories/${id}`),

    delete: (id: string) =>
      request<void>(`/api/memories/${id}`, {
        method: 'DELETE',
      }),

    search: (query: string, limit?: number) =>
      request<Memory[]>('/api/memories/search', {
        method: 'POST',
        body: JSON.stringify({ query, limit }),
      }),
  },

  // Health check
  health: () => request<{ status: string }>('/health'),
};
