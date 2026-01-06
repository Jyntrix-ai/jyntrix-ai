import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

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

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  memoryCount?: number;
}

interface ChatState {
  // Current conversation
  currentConversationId: string | null;
  conversations: Conversation[];
  messages: Message[];
  isStreaming: boolean;

  // Streaming optimization - separate state for streaming content
  streamingContent: string;
  streamingMessageId: string | null;

  // Actions
  setCurrentConversationId: (id: string | null) => void;
  setConversations: (conversations: Conversation[]) => void;
  addConversation: (conversation: Conversation) => void;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  removeConversation: (id: string) => void;

  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  updateLastMessage: (updater: (content: string) => string) => void;
  clearMessages: () => void;

  setIsStreaming: (isStreaming: boolean) => void;

  // Streaming optimization actions
  startStreaming: (messageId: string) => void;
  appendStreamingContent: (chunk: string) => void;
  finalizeStreamingMessage: () => void;

  // Reset
  reset: () => void;
}

const initialState = {
  currentConversationId: null,
  conversations: [],
  messages: [],
  isStreaming: false,
  streamingContent: '',
  streamingMessageId: null as string | null,
};

export const useChatStore = create<ChatState>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        // Conversation ID
        setCurrentConversationId: (id) =>
          set({ currentConversationId: id }, false, 'setCurrentConversationId'),

        // Conversations
        setConversations: (conversations) =>
          set({ conversations }, false, 'setConversations'),

        addConversation: (conversation) =>
          set(
            (state) => ({
              conversations: [conversation, ...state.conversations],
            }),
            false,
            'addConversation'
          ),

        updateConversation: (id, updates) =>
          set(
            (state) => ({
              conversations: state.conversations.map((c) =>
                c.id === id ? { ...c, ...updates } : c
              ),
            }),
            false,
            'updateConversation'
          ),

        removeConversation: (id) =>
          set(
            (state) => ({
              conversations: state.conversations.filter((c) => c.id !== id),
              // Clear messages if removing current conversation
              ...(state.currentConversationId === id
                ? { currentConversationId: null, messages: [] }
                : {}),
            }),
            false,
            'removeConversation'
          ),

        // Messages
        setMessages: (messages) => set({ messages }, false, 'setMessages'),

        addMessage: (message) =>
          set(
            (state) => ({
              messages: [...state.messages, message],
            }),
            false,
            'addMessage'
          ),

        updateLastMessage: (updater) =>
          set(
            (state) => {
              const messages = [...state.messages];
              const lastMessage = messages[messages.length - 1];
              if (lastMessage && lastMessage.role === 'assistant') {
                messages[messages.length - 1] = {
                  ...lastMessage,
                  content: updater(lastMessage.content),
                };
              }
              return { messages };
            },
            false,
            'updateLastMessage'
          ),

        clearMessages: () => set({ messages: [] }, false, 'clearMessages'),

        // Streaming
        setIsStreaming: (isStreaming) =>
          set({ isStreaming }, false, 'setIsStreaming'),

        // Streaming optimization - only update streamingContent, not messages array
        startStreaming: (messageId) =>
          set(
            { streamingMessageId: messageId, streamingContent: '', isStreaming: true },
            false,
            'startStreaming'
          ),

        appendStreamingContent: (chunk) =>
          set(
            (state) => ({ streamingContent: state.streamingContent + chunk }),
            false,
            'appendStreamingContent'
          ),

        finalizeStreamingMessage: () =>
          set(
            (state) => {
              if (!state.streamingMessageId) return state;

              // Update the message content with the accumulated streaming content
              const messages = state.messages.map((msg) =>
                msg.id === state.streamingMessageId
                  ? { ...msg, content: state.streamingContent }
                  : msg
              );

              return {
                messages,
                streamingContent: '',
                streamingMessageId: null,
                isStreaming: false,
              };
            },
            false,
            'finalizeStreamingMessage'
          ),

        // Reset
        reset: () => set(initialState, false, 'reset'),
      }),
      {
        name: 'jyntrix-chat-store',
        partialize: (state) => ({
          // Only persist conversations list, not messages or current state
          conversations: state.conversations.slice(0, 20), // Keep last 20
        }),
      }
    ),
    { name: 'ChatStore' }
  )
);
