'use client';

import { useEffect, useRef, useCallback, useMemo } from 'react';
import { MessageItem } from './message-item';
import { ChatInput } from './chat-input';
import { StreamingMessage } from './streaming-message';
import { useChatStore } from '@/stores/chat.store';
import { useChat } from '@/hooks/use-chat';

interface ChatInterfaceProps {
  conversationId: string | null;
  onFirstMessage?: (message: string) => Promise<string>;
  isNewChat?: boolean;
}

export function ChatInterface({
  conversationId,
  onFirstMessage,
  isNewChat = false,
}: ChatInterfaceProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const lastMessageCountRef = useRef(0);
  const scrollToBottomRef = useRef<(instant?: boolean) => void>(() => {});

  const messages = useChatStore((state) => state.messages);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const streamingMessageId = useChatStore((state) => state.streamingMessageId);

  // Track if user is near bottom of scroll
  const checkIfNearBottom = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return true;

    const threshold = 100;
    const position = container.scrollHeight - container.scrollTop - container.clientHeight;
    return position < threshold;
  }, []);

  // Scroll to bottom with appropriate behavior
  const scrollToBottom = useCallback((instant = false) => {
    if (!messagesEndRef.current) return;

    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({
        behavior: instant ? 'instant' : 'smooth',
        block: 'end',
      });
    });
  }, []);

  // Keep ref updated for use in callbacks
  scrollToBottomRef.current = scrollToBottom;

  const { sendMessage, isLoading } = useChat(conversationId, {
    onStreamChunk: () => {
      // Scroll to bottom during streaming if user was near bottom
      if (isNearBottomRef.current) {
        scrollToBottomRef.current(true);
      }
    },
  });

  // Memoize static messages - exclude the streaming message
  const staticMessages = useMemo(() => {
    if (!isStreaming || !streamingMessageId) {
      return messages;
    }
    // Exclude the placeholder message being streamed
    return messages.filter((m) => m.id !== streamingMessageId);
  }, [messages, isStreaming, streamingMessageId]);

  // Track scroll position
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      isNearBottomRef.current = checkIfNearBottom();
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [checkIfNearBottom]);

  // Scroll on new messages (not during streaming content updates)
  useEffect(() => {
    // Only scroll when message count changes
    if (messages.length !== lastMessageCountRef.current) {
      lastMessageCountRef.current = messages.length;

      // Use smooth scroll for new messages, but only if user is near bottom
      if (isNearBottomRef.current) {
        // Use instant scroll during streaming for better performance
        scrollToBottom(isStreaming);
      }
    }
  }, [messages.length, isStreaming, scrollToBottom]);

  // Keep scrolled to bottom during streaming if user was at bottom
  useEffect(() => {
    if (isStreaming && isNearBottomRef.current) {
      // Use instant scroll during active streaming
      scrollToBottom(true);
    }
  }, [isStreaming, scrollToBottom]);

  const handleSendMessage = async (content: string) => {
    if (isNewChat && onFirstMessage) {
      // For new chats, create the conversation first
      try {
        const newConversationId = await onFirstMessage(content);
        // Store the pending message to be sent after navigation
        sessionStorage.setItem('pendingMessage', content);
        sessionStorage.setItem('pendingConversationId', newConversationId);
      } catch {
        console.error('Failed to create conversation');
      }
    } else {
      await sendMessage(content);
    }
  };

  // Check for pending message after navigation
  useEffect(() => {
    const pendingMessage = sessionStorage.getItem('pendingMessage');
    const pendingConversationId = sessionStorage.getItem('pendingConversationId');

    if (pendingMessage && pendingConversationId === conversationId) {
      sessionStorage.removeItem('pendingMessage');
      sessionStorage.removeItem('pendingConversationId');
      sendMessage(pendingMessage);
    }
  }, [conversationId, sendMessage]);

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
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
              {isNewChat ? 'Start a new conversation' : 'Welcome back!'}
            </h2>
            <p className="text-text-secondary dark:text-text-secondary-dark max-w-md">
              {isNewChat
                ? "I'm here to help with anything you need. Ask me questions, explore ideas, or just chat."
                : 'Continue your conversation or start something new.'}
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
                  className="p-3 text-left text-sm rounded-xl border border-border dark:border-border-dark hover:bg-surface-elevated dark:hover:bg-surface-elevated-dark transition-colors text-text-secondary dark:text-text-secondary-dark"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {/* Render static (non-streaming) messages - these won't re-render during streaming */}
            {staticMessages.map((message) => (
              <MessageItem key={message.id} message={message} />
            ))}

            {/* Render streaming message separately - only this re-renders during streaming */}
            {isStreaming && <StreamingMessage />}
          </>
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
