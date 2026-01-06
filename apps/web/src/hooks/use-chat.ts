'use client';

import { useCallback, useRef, useEffect, useState } from 'react';
import { useChatStore } from '@/stores/chat.store';
import { api } from '@/lib/api';
import { generateMessageId } from '@/lib/id';

interface UseChatOptions {
  onStreamChunk?: () => void;
}

export function useChat(conversationId: string | null, options?: UseChatOptions) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // AbortController ref for stream cleanup
  const abortControllerRef = useRef<AbortController | null>(null);

  const {
    addMessage,
    startStreaming,
    appendStreamingContent,
    finalizeStreamingMessage,
    setIsStreaming,
  } = useChatStore();

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Cancel any ongoing stream
  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
    }
  }, [setIsStreaming]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!conversationId || isLoading) return;

      // Cancel any previous stream
      cancelStream();

      // Create new abort controller
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      setIsLoading(true);
      setError(null);

      // Optimistically add user message with unique ID
      const userMessageId = generateMessageId();
      const userMessage = {
        id: userMessageId,
        conversationId,
        role: 'user' as const,
        content,
        createdAt: new Date().toISOString(),
      };
      addMessage(userMessage);

      // Add placeholder for assistant message with unique ID
      const assistantMessageId = generateMessageId();
      const assistantMessage = {
        id: assistantMessageId,
        conversationId,
        role: 'assistant' as const,
        content: '',
        createdAt: new Date().toISOString(),
      };
      addMessage(assistantMessage);

      // Start streaming with the assistant message ID
      startStreaming(assistantMessageId);

      try {
        // Stream the response
        await api.messages.stream(
          conversationId,
          content,
          // On each chunk, append to streaming content and trigger scroll callback
          (chunk) => {
            appendStreamingContent(chunk);
            options?.onStreamChunk?.();
          },
          // On done - finalize the streaming message
          () => {
            finalizeStreamingMessage();
            abortControllerRef.current = null;
          },
          // On error
          (err) => {
            console.error('Stream error:', err);
            setError(err.message);
          },
          // Pass abort signal
          abortController.signal
        );
      } catch (err) {
        // Don't report abort errors
        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }

        console.error('Failed to send message:', err);
        setError(err instanceof Error ? err.message : 'Failed to send message');

        // Finalize with error content
        appendStreamingContent('Sorry, I encountered an error. Please try again.');
        finalizeStreamingMessage();
      } finally {
        setIsLoading(false);
      }
    },
    [
      conversationId,
      isLoading,
      addMessage,
      startStreaming,
      appendStreamingContent,
      finalizeStreamingMessage,
      cancelStream,
    ]
  );

  // Fallback non-streaming send
  const sendMessageSync = useCallback(
    async (content: string) => {
      if (!conversationId || isLoading) return;

      setIsLoading(true);
      setError(null);

      // Optimistically add user message with unique ID
      const userMessage = {
        id: generateMessageId(),
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
          id: generateMessageId(),
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
    cancelStream,
    isLoading,
    error,
    clearError: () => setError(null),
  };
}
