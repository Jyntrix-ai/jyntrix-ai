'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MemoryList } from '@/components/memory/memory-list';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { api } from '@/lib/api';

type MemoryFilter = 'all' | 'core' | 'episodic' | 'semantic' | 'procedural';

export default function MemoriesPage() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<MemoryFilter>('all');

  // Fetch memories
  const { data: memories, isLoading } = useQuery({
    queryKey: ['memories', filter, searchQuery],
    queryFn: () =>
      api.memories.list({
        type: filter === 'all' ? undefined : filter,
        search: searchQuery || undefined,
      }),
  });

  // Delete memory mutation
  const deleteMutation = useMutation({
    mutationFn: (memoryId: string) => api.memories.delete(memoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
    },
  });

  const handleDelete = async (memoryId: string) => {
    if (confirm('Are you sure you want to delete this memory?')) {
      deleteMutation.mutate(memoryId);
    }
  };

  const filterOptions: { value: MemoryFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'core', label: 'Core' },
    { value: 'episodic', label: 'Episodic' },
    { value: 'semantic', label: 'Semantic' },
    { value: 'procedural', label: 'Procedural' },
  ];

  return (
    <div className="min-h-screen bg-background dark:bg-background-dark">
      {/* Header */}
      <header className="sticky top-0 z-10 glass border-b border-border dark:border-border-dark">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-text-primary dark:text-text-primary-dark">
                Memory Dashboard
              </h1>
              <p className="mt-1 text-sm text-text-secondary dark:text-text-secondary-dark">
                View and manage your AI&apos;s memories
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                onClick={() =>
                  queryClient.invalidateQueries({ queryKey: ['memories'] })
                }
              >
                <svg
                  className="w-4 h-4 mr-2"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search and filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <div className="flex-1">
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted dark:text-text-muted-dark"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <Input
                type="search"
                placeholder="Search memories..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-2 sm:pb-0">
            {filterOptions.map((option) => (
              <Button
                key={option.value}
                variant={filter === option.value ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setFilter(option.value)}
                className="whitespace-nowrap"
              >
                {option.label}
              </Button>
            ))}
          </div>
        </div>

        {/* Memory stats */}
        {memories && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            <div className="p-4 rounded-xl bg-surface dark:bg-surface-dark border border-border dark:border-border-dark">
              <p className="text-2xl font-bold text-text-primary dark:text-text-primary-dark">
                {memories.length}
              </p>
              <p className="text-sm text-text-secondary dark:text-text-secondary-dark">
                Total Memories
              </p>
            </div>
            <div className="p-4 rounded-xl bg-surface dark:bg-surface-dark border border-border dark:border-border-dark">
              <p className="text-2xl font-bold text-primary-500">
                {memories.filter((m) => m.type === 'core').length}
              </p>
              <p className="text-sm text-text-secondary dark:text-text-secondary-dark">
                Core Memories
              </p>
            </div>
            <div className="p-4 rounded-xl bg-surface dark:bg-surface-dark border border-border dark:border-border-dark">
              <p className="text-2xl font-bold text-accent-500">
                {memories.filter((m) => m.type === 'episodic').length}
              </p>
              <p className="text-sm text-text-secondary dark:text-text-secondary-dark">
                Episodic
              </p>
            </div>
            <div className="p-4 rounded-xl bg-surface dark:bg-surface-dark border border-border dark:border-border-dark">
              <p className="text-2xl font-bold text-green-500">
                {memories.filter((m) => m.type === 'semantic').length}
              </p>
              <p className="text-sm text-text-secondary dark:text-text-secondary-dark">
                Semantic
              </p>
            </div>
          </div>
        )}

        {/* Memory list */}
        <MemoryList
          memories={memories || []}
          isLoading={isLoading}
          onDelete={handleDelete}
        />
      </main>
    </div>
  );
}
