'use client';

import { useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { useAuthStore } from '@/stores/auth.store';
import type { User } from '@supabase/supabase-js';

export function useAuth() {
  const router = useRouter();
  const { user, isLoading, setUser, setLoading } = useAuthStore();

  // Initialize auth state
  useEffect(() => {
    const supabase = createClient();

    // Get initial session
    const initAuth = async () => {
      setLoading(true);
      try {
        const {
          data: { user },
        } = await supabase.auth.getUser();
        setUser(user);
      } catch (error) {
        console.error('Auth init error:', error);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    initAuth();

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user || null);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [setUser, setLoading]);

  // Sign in with email/password
  const signIn = useCallback(
    async (email: string, password: string) => {
      const supabase = createClient();
      setLoading(true);

      try {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (error) {
          throw error;
        }

        setUser(data.user);
        router.push('/chat');
        router.refresh();

        return { user: data.user, error: null };
      } catch (error) {
        return {
          user: null,
          error: error instanceof Error ? error.message : 'Sign in failed',
        };
      } finally {
        setLoading(false);
      }
    },
    [router, setUser, setLoading]
  );

  // Sign up with email/password
  const signUp = useCallback(
    async (email: string, password: string, metadata?: { full_name?: string }) => {
      const supabase = createClient();
      setLoading(true);

      try {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: metadata,
            emailRedirectTo: `${window.location.origin}/auth/callback`,
          },
        });

        if (error) {
          throw error;
        }

        return { user: data.user, error: null };
      } catch (error) {
        return {
          user: null,
          error: error instanceof Error ? error.message : 'Sign up failed',
        };
      } finally {
        setLoading(false);
      }
    },
    [setLoading]
  );

  // Sign in with OAuth provider
  const signInWithProvider = useCallback(
    async (provider: 'google' | 'github') => {
      const supabase = createClient();

      try {
        const { error } = await supabase.auth.signInWithOAuth({
          provider,
          options: {
            redirectTo: `${window.location.origin}/auth/callback`,
          },
        });

        if (error) {
          throw error;
        }

        return { error: null };
      } catch (error) {
        return {
          error: error instanceof Error ? error.message : 'OAuth sign in failed',
        };
      }
    },
    []
  );

  // Sign out
  const signOut = useCallback(async () => {
    const supabase = createClient();
    setLoading(true);

    try {
      await supabase.auth.signOut();
      setUser(null);
      router.push('/login');
      router.refresh();
    } catch (error) {
      console.error('Sign out error:', error);
    } finally {
      setLoading(false);
    }
  }, [router, setUser, setLoading]);

  // Update user profile
  const updateProfile = useCallback(
    async (updates: { full_name?: string; avatar_url?: string }) => {
      const supabase = createClient();

      try {
        const { data, error } = await supabase.auth.updateUser({
          data: updates,
        });

        if (error) {
          throw error;
        }

        setUser(data.user);
        return { user: data.user, error: null };
      } catch (error) {
        return {
          user: null,
          error: error instanceof Error ? error.message : 'Update failed',
        };
      }
    },
    [setUser]
  );

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    signIn,
    signUp,
    signInWithProvider,
    signOut,
    updateProfile,
  };
}

// Helper type for user data
export type AuthUser = User;
