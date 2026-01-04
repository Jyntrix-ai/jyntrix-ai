'use client';

import { memo } from 'react';
import { clsx } from 'clsx';

export interface Message {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt?: string;
  memories?: Array<{
    id: string;
    type: string;
    content: string;
  }>;
}

interface MessageItemProps {
  message: Message;
  isStreaming?: boolean;
}

export const MessageItem = memo(function MessageItem({
  message,
  isStreaming = false,
}: MessageItemProps) {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  if (message.role === 'system') {
    return null;
  }

  return (
    <div
      className={clsx(
        'flex w-full animate-fade-in',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div
        className={clsx(
          'flex gap-3 max-w-[85%] sm:max-w-[75%]',
          isUser ? 'flex-row-reverse' : 'flex-row'
        )}
      >
        {/* Avatar */}
        <div
          className={clsx(
            'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
            isUser
              ? 'bg-primary-500'
              : 'bg-gradient-to-br from-primary-500 to-accent-500'
          )}
        >
          {isUser ? (
            <svg
              className="w-4 h-4 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
              />
            </svg>
          ) : (
            <span className="text-white font-bold text-xs">J</span>
          )}
        </div>

        {/* Message content */}
        <div className="flex flex-col gap-1">
          <div
            className={clsx(
              'message-bubble',
              isUser ? 'message-bubble-user' : 'message-bubble-assistant'
            )}
          >
            {/* Render message content with basic formatting */}
            <div className="whitespace-pre-wrap break-words">
              {message.content}
              {isStreaming && isAssistant && (
                <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
              )}
            </div>
          </div>

          {/* Memory indicators */}
          {message.memories && message.memories.length > 0 && (
            <div className="flex items-center gap-1.5 mt-1 px-1">
              <svg
                className="w-3.5 h-3.5 text-primary-500"
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
              <span className="text-xs text-text-muted dark:text-text-muted-dark">
                {message.memories.length} memories used
              </span>
            </div>
          )}

          {/* Timestamp */}
          {message.createdAt && (
            <span className="text-2xs text-text-muted dark:text-text-muted-dark px-1">
              {new Date(message.createdAt).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          )}
        </div>
      </div>
    </div>
  );
});
