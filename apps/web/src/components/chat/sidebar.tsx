'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import { createClient } from '@/lib/supabase/client';

interface SidebarProps {
  userId: string;
  userName: string;
}

export function Sidebar({ userId, userName }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  // Fetch conversations
  const { data: conversations, isLoading } = useQuery({
    queryKey: ['conversations', userId],
    queryFn: () => api.conversations.list(),
  });

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push('/login');
    router.refresh();
  };

  const handleNewChat = () => {
    router.push('/chat');
    setIsMobileOpen(false);
  };

  const sidebarContent = (
    <>
      {/* Header */}
      <div className="p-4 border-b border-border dark:border-border-dark">
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
              <span className="text-white font-bold text-sm">J</span>
            </div>
            {!isCollapsed && (
              <span className="font-semibold text-text-primary dark:text-text-primary-dark">
                Jyntrix AI
              </span>
            )}
          </Link>
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="hidden lg:flex p-1.5 rounded-lg hover:bg-surface-elevated dark:hover:bg-surface-elevated-dark transition-colors"
          >
            <svg
              className={clsx(
                'w-5 h-5 text-text-secondary dark:text-text-secondary-dark transition-transform',
                isCollapsed && 'rotate-180'
              )}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
              />
            </svg>
          </button>
        </div>

        {/* New chat button */}
        <Button
          onClick={handleNewChat}
          variant="primary"
          className={clsx('mt-4', isCollapsed ? 'w-10 p-0' : 'w-full')}
        >
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
              d="M12 4v16m8-8H4"
            />
          </svg>
          {!isCollapsed && <span className="ml-2">New Chat</span>}
        </Button>
      </div>

      {/* Conversations list */}
      <div className="flex-1 overflow-y-auto py-2">
        {isLoading ? (
          <div className="px-4 space-y-2">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="h-10 rounded-lg bg-surface-elevated dark:bg-surface-elevated-dark animate-pulse"
              />
            ))}
          </div>
        ) : conversations && conversations.length > 0 ? (
          <nav className="px-2 space-y-1">
            {conversations.map((conversation) => {
              const isActive = pathname === `/chat/${conversation.id}`;
              return (
                <Link
                  key={conversation.id}
                  href={`/chat/${conversation.id}`}
                  onClick={() => setIsMobileOpen(false)}
                  className={clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                    isActive
                      ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                      : 'hover:bg-surface-elevated dark:hover:bg-surface-elevated-dark text-text-secondary dark:text-text-secondary-dark'
                  )}
                >
                  <svg
                    className="w-4 h-4 flex-shrink-0"
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
                  {!isCollapsed && (
                    <span className="truncate text-sm">
                      {conversation.title || 'New Conversation'}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        ) : (
          !isCollapsed && (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-text-muted dark:text-text-muted-dark">
                No conversations yet
              </p>
            </div>
          )
        )}
      </div>

      {/* Navigation links */}
      <div className="border-t border-border dark:border-border-dark p-2">
        <Link
          href="/memories"
          className={clsx(
            'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
            pathname === '/memories'
              ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
              : 'hover:bg-surface-elevated dark:hover:bg-surface-elevated-dark text-text-secondary dark:text-text-secondary-dark'
          )}
        >
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
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          {!isCollapsed && <span className="text-sm">Memories</span>}
        </Link>
      </div>

      {/* User section */}
      <div className="border-t border-border dark:border-border-dark p-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
            <span className="text-sm font-medium text-primary-600 dark:text-primary-400">
              {userName.charAt(0).toUpperCase()}
            </span>
          </div>
          {!isCollapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary dark:text-text-primary-dark truncate">
                {userName}
              </p>
            </div>
          )}
          <button
            onClick={handleSignOut}
            className="p-1.5 rounded-lg hover:bg-surface-elevated dark:hover:bg-surface-elevated-dark transition-colors"
            title="Sign out"
          >
            <svg
              className="w-5 h-5 text-text-secondary dark:text-text-secondary-dark"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
              />
            </svg>
          </button>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={() => setIsMobileOpen(true)}
        className="fixed top-4 left-4 z-40 lg:hidden p-2 rounded-lg bg-surface dark:bg-surface-dark border border-border dark:border-border-dark shadow-sm"
      >
        <svg
          className="w-6 h-6 text-text-primary dark:text-text-primary-dark"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 6h16M4 12h16M4 18h16"
          />
        </svg>
      </button>

      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 w-72 transform transition-transform duration-300 lg:hidden',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="sidebar h-full">
          {/* Close button */}
          <button
            onClick={() => setIsMobileOpen(false)}
            className="absolute top-4 right-4 p-1.5 rounded-lg hover:bg-surface-elevated dark:hover:bg-surface-elevated-dark transition-colors"
          >
            <svg
              className="w-5 h-5 text-text-secondary dark:text-text-secondary-dark"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
          {sidebarContent}
        </div>
      </aside>

      {/* Desktop sidebar */}
      <aside
        className={clsx(
          'hidden lg:flex flex-col transition-all duration-300 sidebar',
          isCollapsed ? 'w-16' : 'w-72'
        )}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
