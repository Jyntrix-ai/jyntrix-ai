'use client';

/**
 * Animated thinking indicator shown while waiting for AI response.
 * Displays bouncing dots with "Thinking..." text.
 */
export function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 text-text-secondary dark:text-text-secondary-dark whitespace-nowrap">
      <div className="flex gap-1">
        <span
          className="w-2 h-2 rounded-full bg-primary-500 animate-bounce"
          style={{ animationDelay: '0ms', animationDuration: '0.6s' }}
        />
        <span
          className="w-2 h-2 rounded-full bg-primary-500 animate-bounce"
          style={{ animationDelay: '150ms', animationDuration: '0.6s' }}
        />
        <span
          className="w-2 h-2 rounded-full bg-primary-500 animate-bounce"
          style={{ animationDelay: '300ms', animationDuration: '0.6s' }}
        />
      </div>
      <span className="text-sm">Thinking...</span>
    </div>
  );
}

/**
 * Blinking cursor shown at the end of streaming text.
 */
export function StreamingCursor() {
  return (
    <span
      className="inline-block w-0.5 h-[1.1em] ml-0.5 bg-current animate-blink align-middle"
      aria-hidden="true"
    />
  );
}
