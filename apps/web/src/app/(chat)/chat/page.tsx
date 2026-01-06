'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { ChatInput } from '@/components/chat/chat-input';
import { MessageItem } from '@/components/chat/message-item';
import { StreamingMessage } from '@/components/chat/streaming-message';
import { useChatStore } from '@/stores/chat.store';
import { api } from '@/lib/api';
import { generateMessageId } from '@/lib/id';

/**
 * New Chat Page - ChatGPT-style seamless flow.
 * Messages appear instantly, conversation created in background,
 * URL updates silently without page navigation.
 */
export default function NewChatPage() {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    messages,
    isStreaming,
    setCurrentConversationId,
    clearMessages,
    addMessage,
    addConversation,
    startStreaming,
    appendStreamingContent,
    finalizeStreamingMessage,
  } = useChatStore();

  // Clear current conversation on mount for new chat
  useEffect(() => {
    setCurrentConversationId(null);
    clearMessages();

    // Cleanup on unmount
    return () => {
      abortControllerRef.current?.abort();
    };
  }, [setCurrentConversationId, clearMessages]);

  // Scroll to bottom
  const scrollToBottom = useCallback((instant = false) => {
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({
        behavior: instant ? 'instant' : 'smooth',
        block: 'end',
      });
    });
  }, []);

  // Scroll on new messages
  useEffect(() => {
    if (messages.length > 0 || isStreaming) {
      scrollToBottom(isStreaming);
    }
  }, [messages.length, isStreaming, scrollToBottom]);

  /**
   * Handle first message in a new chat.
   * Implements ChatGPT-style seamless flow:
   * 1. Show user message immediately (optimistic UI)
   * 2. Create conversation in background
   * 3. Stream response while conversation is being created
   * 4. Update URL silently once conversation is ready
   */
  const handleSendMessage = async (content: string) => {
    if (isLoading || isStreaming) return;

    // Cancel any previous request
    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setIsLoading(true);
    setError(null);

    // 1. Add user message immediately (optimistic UI)
    const userMessageId = generateMessageId();
    addMessage({
      id: userMessageId,
      conversationId: 'pending',
      role: 'user',
      content,
      createdAt: new Date().toISOString(),
    });

    // 2. Add placeholder assistant message
    const assistantMessageId = generateMessageId();
    addMessage({
      id: assistantMessageId,
      conversationId: 'pending',
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString(),
    });

    // 3. Start streaming state
    startStreaming(assistantMessageId);

    try {
      // 4. Create conversation (this happens in parallel with showing messages)
      const conversation = await api.conversations.create({
        title: content.slice(0, 50) + (content.length > 50 ? '...' : ''),
      });

      // Check if aborted
      if (abortController.signal.aborted) return;

      // 5. Update store with real conversation ID
      setCurrentConversationId(conversation.id);
      addConversation(conversation);

      // 6. Silently update URL WITHOUT triggering navigation
      // Using window.history.replaceState to avoid unmounting this component
      // which would abort the stream via the cleanup effect
      if (typeof window !== 'undefined') {
        window.history.replaceState(
          { ...window.history.state, conversationId: conversation.id },
          '',
          `/chat/${conversation.id}`
        );
      }

      // 7. Stream the response
      await api.messages.stream(
        conversation.id,
        content,
        // On chunk - append to streaming content and scroll
        (chunk) => {
          appendStreamingContent(chunk);
          // Scroll to bottom during streaming
          scrollToBottom(true);
        },
        // On done - finalize message
        () => {
          finalizeStreamingMessage();
          abortControllerRef.current = null;
        },
        // On error
        (err) => {
          console.error('Stream error:', err);
          setError(err.message);
        },
        // Abort signal
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
  };

  // Filter out streaming message from static messages
  const staticMessages = messages.filter((m) => m.role !== 'assistant' || m.content !== '');

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-border dark:border-border-dark">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">
            New Chat
          </h1>
        </div>
      </header>

      {/* Messages area */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto px-4 py-6 space-y-6 scroll-smooth"
      >
        {messages.length === 0 && !isStreaming ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center mb-6">
              <svg
                className="w-8 h-8 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-text-primary dark:text-text-primary-dark mb-2">
              Start a new conversation
            </h2>
            <p className="text-text-secondary dark:text-text-secondary-dark max-w-md">
              I&apos;m here to help with anything you need. Ask me questions, explore ideas, or just chat.
            </p>

            {/* Quick prompts */}
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
              {[
                'What can you help me with?',
                'Tell me about your memory features',
                'Help me brainstorm an idea',
                'Explain a complex topic',
              ].map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => handleSendMessage(prompt)}
                  disabled={isLoading || isStreaming}
                  className="p-3 text-left text-sm rounded-xl border border-border dark:border-border-dark hover:bg-surface-elevated dark:hover:bg-surface-elevated-dark transition-colors text-text-secondary dark:text-text-secondary-dark disabled:opacity-50"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {/* Render static messages */}
            {staticMessages.map((message) => (
              <MessageItem key={message.id} message={message} />
            ))}

            {/* Render streaming message */}
            {isStreaming && <StreamingMessage />}
          </>
        )}

        {/* Error display */}
        {error && (
          <div className="flex justify-center">
            <div className="bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-400 px-4 py-2 rounded-lg text-sm">
              {error}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <ChatInput
        onSend={handleSendMessage}
        isLoading={isLoading}
        disabled={isLoading || isStreaming}
      />
    </div>
  );
}
