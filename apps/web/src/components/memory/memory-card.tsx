'use client';

import { useState } from 'react';
import { clsx } from 'clsx';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export interface Memory {
  id: string;
  type: 'core' | 'episodic' | 'semantic' | 'procedural';
  content: string;
  importance: number;
  createdAt: string;
  lastAccessedAt?: string;
  accessCount?: number;
  sourceConversationId?: string;
  metadata?: Record<string, unknown>;
}

interface MemoryCardProps {
  memory: Memory;
  onDelete?: (memoryId: string) => void;
}

const typeConfig = {
  core: {
    label: 'Core',
    color: 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
        />
      </svg>
    ),
  },
  episodic: {
    label: 'Episodic',
    color: 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
  },
  semantic: {
    label: 'Semantic',
    color: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
        />
      </svg>
    ),
  },
  procedural: {
    label: 'Procedural',
    color: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
        />
      </svg>
    ),
  },
};

export function MemoryCard({ memory, onDelete }: MemoryCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showActions, setShowActions] = useState(false);

  const config = typeConfig[memory.type];
  const importance = Math.round(memory.importance * 100);

  return (
    <Card
      className="group relative overflow-hidden"
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Importance indicator bar */}
      <div
        className="absolute top-0 left-0 h-1 bg-gradient-to-r from-primary-500 to-accent-500"
        style={{ width: `${importance}%` }}
      />

      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <div className={clsx('p-1.5 rounded-lg', config.color)}>
              {config.icon}
            </div>
            <span className={clsx('text-xs font-medium', config.color.split(' ')[2])}>
              {config.label}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-xs text-text-muted dark:text-text-muted-dark">
              {importance}%
            </span>
          </div>
        </div>

        {/* Content */}
        <div
          className={clsx(
            'text-sm text-text-primary dark:text-text-primary-dark',
            !isExpanded && 'line-clamp-3'
          )}
        >
          {memory.content}
        </div>

        {memory.content.length > 150 && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="mt-2 text-xs text-primary-500 hover:text-primary-600 transition-colors"
          >
            {isExpanded ? 'Show less' : 'Show more'}
          </button>
        )}

        {/* Metadata */}
        <div className="mt-4 pt-3 border-t border-border dark:border-border-dark flex items-center justify-between text-xs text-text-muted dark:text-text-muted-dark">
          <span>
            {new Date(memory.createdAt).toLocaleDateString(undefined, {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })}
          </span>
          {memory.accessCount !== undefined && (
            <span>Accessed {memory.accessCount} times</span>
          )}
        </div>

        {/* Actions (show on hover) */}
        {showActions && onDelete && (
          <div className="absolute top-3 right-3 flex items-center gap-1 animate-fade-in">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(memory.id)}
              className="h-8 w-8 p-0 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}
