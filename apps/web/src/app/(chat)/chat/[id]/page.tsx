'use client';

import { useEffect } from 'react';
import { useParams } from 'next/navigation';
import { ChatInterface } from '@/components/chat/chat-interface';
import { useChatStore } from '@/stores/chat.store';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export default function ConversationPage() {
  const params = useParams();
  const conversationId = params.id as string;
  const { setCurrentConversationId, setMessages } = useChatStore();

  // Fetch conversation details
  const { data: conversation, isLoading: conversationLoading } = useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => api.conversations.get(conversationId),
    enabled: !!conversationId,
  });

  // Fetch messages for this conversation
  const { data: messages, isLoading: messagesLoading } = useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () => api.messages.list(conversationId),
    enabled: !!conversationId,
  });

  // Set current conversation and messages in store
  useEffect(() => {
    if (conversationId) {
      setCurrentConversationId(conversationId);
    }
  }, [conversationId, setCurrentConversationId]);

  useEffect(() => {
    if (messages) {
      setMessages(messages);
    }
  }, [messages, setMessages]);

  const isLoading = conversationLoading || messagesLoading;

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        {/* Header skeleton */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-border dark:border-border-dark">
          <div className="flex items-center gap-3">
            <div className="h-6 w-48 bg-surface-elevated dark:bg-surface-elevated-dark rounded animate-pulse" />
          </div>
        </header>

        {/* Loading state */}
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="typing-indicator text-text-muted dark:text-text-muted-dark">
              <span />
              <span />
              <span />
            </div>
            <p className="text-sm text-text-secondary dark:text-text-secondary-dark">
              Loading conversation...
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-border dark:border-border-dark">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark truncate max-w-md">
            {conversation?.title || 'Conversation'}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {/* Memory indicator */}
          {conversation?.memoryCount && conversation.memoryCount > 0 && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400">
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
              <span className="text-xs font-medium">
                {conversation.memoryCount} memories
              </span>
            </div>
          )}
        </div>
      </header>

      {/* Chat Interface */}
      <ChatInterface conversationId={conversationId} isNewChat={false} />
    </div>
  );
}
