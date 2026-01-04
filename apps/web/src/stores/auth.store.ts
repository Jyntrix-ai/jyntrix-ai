import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { User } from '@supabase/supabase-js';

interface AuthState {
  user: User | null;
  isLoading: boolean;

  // Actions
  setUser: (user: User | null) => void;
  setLoading: (isLoading: boolean) => void;

  // Computed
  isAuthenticated: () => boolean;

  // Reset
  reset: () => void;
}

const initialState = {
  user: null,
  isLoading: true,
};

export const useAuthStore = create<AuthState>()(
  devtools(
    (set, get) => ({
      ...initialState,

      setUser: (user) => set({ user, isLoading: false }, false, 'setUser'),

      setLoading: (isLoading) => set({ isLoading }, false, 'setLoading'),

      isAuthenticated: () => !!get().user,

      reset: () => set(initialState, false, 'reset'),
    }),
    { name: 'AuthStore' }
  )
);
