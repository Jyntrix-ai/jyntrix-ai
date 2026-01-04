'use client';

import { useCallback, useState } from 'react';
import { useChatStore } from '@/stores/chat.store';
import { api } from '@/lib/api';

export function useChat(conversationId: string | null) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { addMessage, updateLastMessage, setIsStreaming } = useChatStore();

  const sendMessage = useCallback(
    async (content: string) => {
      if (!conversationId || isLoading) return;

      setIsLoading(true);
      setError(null);

      // Optimistically add user message
      const userMessage = {
        id: `temp-${Date.now()}`,
        conversationId,
        role: 'user' as const,
        content,
        createdAt: new Date().toISOString(),
      };
      addMessage(userMessage);

      // Add placeholder for assistant message
      const assistantMessage = {
        id: `temp-${Date.now() + 1}`,
        conversationId,
        role: 'assistant' as const,
        content: '',
        createdAt: new Date().toISOString(),
      };
      addMessage(assistantMessage);
      setIsStreaming(true);

      try {
        // Stream the response
        await api.messages.stream(
          conversationId,
          content,
          // On each chunk, append to the assistant message
          (chunk) => {
            updateLastMessage((prev) => prev + chunk);
          },
          // On done
          () => {
            setIsStreaming(false);
          }
        );
      } catch (err) {
        console.error('Failed to send message:', err);
        setError(err instanceof Error ? err.message : 'Failed to send message');
        setIsStreaming(false);

        // Update the assistant message with error state
        updateLastMessage(() => 'Sorry, I encountered an error. Please try again.');
      } finally {
        setIsLoading(false);
      }
    },
    [conversationId, isLoading, addMessage, updateLastMessage, setIsStreaming]
  );

  // Fallback non-streaming send
  const sendMessageSync = useCallback(
    async (content: string) => {
      if (!conversationId || isLoading) return;

      setIsLoading(true);
      setError(null);

      // Optimistically add user message
      const userMessage = {
        id: `temp-${Date.now()}`,
        conversationId,
        role: 'user' as const,
        content,
        createdAt: new Date().toISOString(),
      };
      addMessage(userMessage);

      try {
        const response = await api.messages.send(conversationId, content);
        addMessage(response);
      } catch (err) {
        console.error('Failed to send message:', err);
        setError(err instanceof Error ? err.message : 'Failed to send message');

        // Add error message
        addMessage({
          id: `error-${Date.now()}`,
          conversationId,
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          createdAt: new Date().toISOString(),
        });
      } finally {
        setIsLoading(false);
      }
    },
    [conversationId, isLoading, addMessage]
  );

  return {
    sendMessage,
    sendMessageSync,
    isLoading,
    error,
    clearError: () => setError(null),
  };
}
