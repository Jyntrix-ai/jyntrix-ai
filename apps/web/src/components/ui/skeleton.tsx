'use client';

import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
}

/**
 * Base skeleton component for loading states.
 */
export function Skeleton({ className, variant = 'text' }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse bg-surface-secondary dark:bg-surface-secondary-dark',
        variant === 'circular' && 'rounded-full',
        variant === 'rectangular' && 'rounded-lg',
        variant === 'text' && 'rounded',
        className
      )}
    />
  );
}

interface MessageSkeletonProps {
  isUser?: boolean;
}

/**
 * Skeleton for a single message bubble.
 */
export function MessageSkeleton({ isUser = false }: MessageSkeletonProps) {
  return (
    <div
      className={cn(
        'flex w-full animate-fade-in',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div
        className={cn(
          'flex gap-3 max-w-[85%] sm:max-w-[75%]',
          isUser ? 'flex-row-reverse' : 'flex-row'
        )}
      >
        {/* Avatar skeleton */}
        <Skeleton variant="circular" className="flex-shrink-0 w-8 h-8" />

        {/* Message content skeleton */}
        <div className="flex flex-col gap-2">
          <div
            className={cn(
              'rounded-2xl p-4 min-w-[120px]',
              isUser
                ? 'bg-primary-500/20 dark:bg-primary-500/20'
                : 'bg-surface-secondary dark:bg-surface-secondary-dark'
            )}
          >
            <div className="space-y-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-24" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Full chat interface skeleton for initial loading.
 */
export function ChatSkeleton() {
  return (
    <div className="flex flex-col h-full">
      {/* Messages area skeleton */}
      <div className="flex-1 overflow-hidden p-4 space-y-4">
        <MessageSkeleton isUser={false} />
        <MessageSkeleton isUser={true} />
        <MessageSkeleton isUser={false} />
        <MessageSkeleton isUser={true} />
      </div>

      {/* Input area skeleton */}
      <div className="border-t border-border dark:border-border-dark p-4">
        <div className="flex gap-3 items-end">
          <Skeleton className="flex-1 h-12 rounded-xl" />
          <Skeleton variant="circular" className="w-10 h-10" />
        </div>
      </div>
    </div>
  );
}

/**
 * Sidebar conversation list skeleton.
 */
export function ConversationListSkeleton() {
  return (
    <div className="space-y-2 p-2">
      {[...Array(5)].map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 p-3 rounded-lg"
          style={{ animationDelay: `${i * 50}ms` }}
        >
          <Skeleton variant="circular" className="w-8 h-8 flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}
