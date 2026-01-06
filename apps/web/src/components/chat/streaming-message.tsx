'use client';

import { useChatStore } from '@/stores/chat.store';
import { ThinkingIndicator, StreamingCursor } from './thinking-indicator';

/**
 * Dedicated component for the streaming message.
 * Reads streamingContent directly from store - only THIS component
 * re-renders during streaming, not the entire message list.
 */
export function StreamingMessage() {
  const streamingContent = useChatStore((state) => state.streamingContent);

  return (
    <div className="flex w-full justify-start animate-fade-in">
      <div className="flex gap-3 max-w-[85%] sm:max-w-[75%] flex-row">
        {/* Avatar */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-br from-primary-500 to-accent-500">
          <span className="text-white font-bold text-xs">J</span>
        </div>

        {/* Message content */}
        <div className="flex flex-col gap-1">
          <div className="message-bubble message-bubble-assistant">
            {streamingContent ? (
              <div className="whitespace-pre-wrap break-words">
                {streamingContent}
                <StreamingCursor />
              </div>
            ) : (
              <ThinkingIndicator />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
