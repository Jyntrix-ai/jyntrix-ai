'use client';

import { useState, useRef, useCallback, useEffect, type KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  isLoading = false,
  disabled = false,
  placeholder = 'Type your message...',
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const previousHeightRef = useRef<number>(48);
  const rafIdRef = useRef<number>(0);

  // Auto-resize textarea with requestAnimationFrame for smooth reflow
  const adjustTextareaHeight = useCallback(() => {
    // Cancel any pending RAF
    if (rafIdRef.current) {
      cancelAnimationFrame(rafIdRef.current);
    }

    rafIdRef.current = requestAnimationFrame(() => {
      const textarea = textareaRef.current;
      if (!textarea) return;

      // Temporarily reset to auto to get scrollHeight
      textarea.style.height = 'auto';
      const newHeight = Math.min(textarea.scrollHeight, 200);

      // Only update if height actually changed
      if (newHeight !== previousHeightRef.current) {
        previousHeightRef.current = newHeight;
        textarea.style.height = `${newHeight}px`;
      } else {
        // Restore previous height if no change
        textarea.style.height = `${previousHeightRef.current}px`;
      }
    });
  }, []);

  useEffect(() => {
    adjustTextareaHeight();
    // Cleanup RAF on unmount
    return () => {
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, [message, adjustTextareaHeight]);

  const handleSubmit = useCallback(() => {
    const trimmedMessage = message.trim();
    if (trimmedMessage && !disabled && !isLoading) {
      onSend(trimmedMessage);
      setMessage('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = '48px';
        previousHeightRef.current = 48;
      }
    }
  }, [message, disabled, isLoading, onSend]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-border dark:border-border-dark bg-surface dark:bg-surface-dark p-4 safe-area-inset">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-3">
          {/* Text input */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled}
              rows={1}
              className="w-full resize-none rounded-xl border border-border dark:border-border-dark bg-background dark:bg-background-dark px-4 py-3 pr-12 text-sm text-text-primary dark:text-text-primary-dark placeholder:text-text-muted dark:placeholder:text-text-muted-dark focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ minHeight: '48px', maxHeight: '200px' }}
            />

            {/* Character count (optional, for long messages) */}
            {message.length > 500 && (
              <span className="absolute bottom-2 right-3 text-2xs text-text-muted dark:text-text-muted-dark">
                {message.length}/4000
              </span>
            )}
          </div>

          {/* Send button */}
          <Button
            onClick={handleSubmit}
            disabled={!message.trim() || disabled || isLoading}
            variant="primary"
            className="h-12 w-12 p-0 rounded-xl"
            aria-label="Send message"
          >
            {isLoading ? (
              <svg
                className="animate-spin h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : (
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            )}
          </Button>
        </div>

        {/* Helper text */}
        <p className="mt-2 text-center text-2xs text-text-muted dark:text-text-muted-dark">
          Press <kbd className="px-1.5 py-0.5 rounded bg-surface-elevated dark:bg-surface-elevated-dark text-text-secondary dark:text-text-secondary-dark">Enter</kbd> to send, <kbd className="px-1.5 py-0.5 rounded bg-surface-elevated dark:bg-surface-elevated-dark text-text-secondary dark:text-text-secondary-dark">Shift + Enter</kbd> for new line
        </p>
      </div>
    </div>
  );
}
