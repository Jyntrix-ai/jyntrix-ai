/**
 * User-related types for the AI Memory Architecture
 */

/**
 * User preferences stored as JSONB
 */
export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  timezone: string;
  notifications: {
    email: boolean;
    push: boolean;
    inApp: boolean;
  };
  privacy: {
    shareAnalytics: boolean;
    allowDataCollection: boolean;
  };
  memory: {
    autoSummarize: boolean;
    retentionDays: number;
    maxMemories: number;
  };
}

/**
 * User profile information
 */
export interface Profile {
  id: string;
  userId: string;
  displayName: string;
  avatarUrl: string | null;
  bio: string | null;
  preferences: UserPreferences;
  metadata: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Base user type
 */
export interface User {
  id: string;
  email: string;
  emailVerified: boolean;
  profile: Profile | null;
  status: UserStatus;
  role: UserRole;
  lastActiveAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * User status enum
 */
export type UserStatus = 'active' | 'inactive' | 'suspended' | 'deleted';

/**
 * User role enum
 */
export type UserRole = 'user' | 'admin' | 'moderator';

/**
 * User session information
 */
export interface UserSession {
  id: string;
  userId: string;
  token: string;
  expiresAt: Date;
  createdAt: Date;
  ipAddress: string | null;
  userAgent: string | null;
}

/**
 * User creation input
 */
export interface CreateUserInput {
  email: string;
  displayName?: string;
  preferences?: Partial<UserPreferences>;
}

/**
 * User update input
 */
export interface UpdateUserInput {
  email?: string;
  status?: UserStatus;
  role?: UserRole;
}

/**
 * Profile update input
 */
export interface UpdateProfileInput {
  displayName?: string;
  avatarUrl?: string | null;
  bio?: string | null;
  preferences?: Partial<UserPreferences>;
  metadata?: Record<string, unknown>;
}

/**
 * Default user preferences
 */
export const DEFAULT_USER_PREFERENCES: UserPreferences = {
  theme: 'system',
  language: 'en',
  timezone: 'UTC',
  notifications: {
    email: true,
    push: true,
    inApp: true,
  },
  privacy: {
    shareAnalytics: false,
    allowDataCollection: false,
  },
  memory: {
    autoSummarize: true,
    retentionDays: 365,
    maxMemories: 10000,
  },
};
