'use client';

import { useEffect, useState, type ReactNode } from 'react';

interface HydrationWrapperProps {
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Wrapper component that safely handles hydration mismatches caused by
 * browser extensions (like Bitdefender) that inject attributes into the DOM.
 *
 * This component renders children only after hydration is complete,
 * preventing mismatches between server and client-rendered HTML.
 */
export function HydrationWrapper({ children, fallback = null }: HydrationWrapperProps) {
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  // During SSR and initial hydration, render fallback or null
  if (!isHydrated) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

/**
 * Hook to check if the component has been hydrated.
 * Useful for conditionally rendering client-only content.
 */
export function useHydrated() {
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  return isHydrated;
}
