'use client';

import { MemoryCard, type Memory } from './memory-card';

interface MemoryListProps {
  memories: Memory[];
  isLoading?: boolean;
  onDelete?: (memoryId: string) => void;
}

export function MemoryList({
  memories,
  isLoading = false,
  onDelete,
}: MemoryListProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="h-40 rounded-xl bg-surface dark:bg-surface-dark border border-border dark:border-border-dark animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (memories.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-surface-elevated dark:bg-surface-elevated-dark flex items-center justify-center">
          <svg
            className="w-8 h-8 text-text-muted dark:text-text-muted-dark"
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
        </div>
        <h3 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark mb-2">
          No memories yet
        </h3>
        <p className="text-text-secondary dark:text-text-secondary-dark max-w-sm mx-auto">
          Start chatting with the AI to build up memories. Important information
          will be saved automatically.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {memories.map((memory) => (
        <MemoryCard key={memory.id} memory={memory} onDelete={onDelete} />
      ))}
    </div>
  );
}
