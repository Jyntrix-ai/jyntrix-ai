/**
 * User validation schemas using Zod
 */

import { z } from 'zod';

/**
 * User preferences schema
 */
export const userPreferencesSchema = z.object({
  theme: z.enum(['light', 'dark', 'system']).default('system'),
  language: z.string().min(2).max(10).default('en'),
  timezone: z.string().default('UTC'),
  notifications: z.object({
    email: z.boolean().default(true),
    push: z.boolean().default(true),
    inApp: z.boolean().default(true),
  }).default({}),
  privacy: z.object({
    shareAnalytics: z.boolean().default(false),
    allowDataCollection: z.boolean().default(false),
  }).default({}),
  memory: z.object({
    autoSummarize: z.boolean().default(true),
    retentionDays: z.number().int().min(1).max(3650).default(365),
    maxMemories: z.number().int().min(100).max(1000000).default(10000),
  }).default({}),
});

/**
 * Profile schema
 */
export const profileSchema = z.object({
  id: z.string().uuid(),
  userId: z.string().uuid(),
  displayName: z.string().min(1).max(100),
  avatarUrl: z.string().url().nullable(),
  bio: z.string().max(500).nullable(),
  preferences: userPreferencesSchema,
  metadata: z.record(z.unknown()).default({}),
  createdAt: z.coerce.date(),
  updatedAt: z.coerce.date(),
});

/**
 * User status schema
 */
export const userStatusSchema = z.enum(['active', 'inactive', 'suspended', 'deleted']);

/**
 * User role schema
 */
export const userRoleSchema = z.enum(['user', 'admin', 'moderator']);

/**
 * User schema
 */
export const userSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  emailVerified: z.boolean().default(false),
  profile: profileSchema.nullable(),
  status: userStatusSchema.default('active'),
  role: userRoleSchema.default('user'),
  lastActiveAt: z.coerce.date().nullable(),
  createdAt: z.coerce.date(),
  updatedAt: z.coerce.date(),
});

/**
 * User session schema
 */
export const userSessionSchema = z.object({
  id: z.string().uuid(),
  userId: z.string().uuid(),
  token: z.string().min(1),
  expiresAt: z.coerce.date(),
  createdAt: z.coerce.date(),
  ipAddress: z.string().ip().nullable(),
  userAgent: z.string().max(500).nullable(),
});

/**
 * Create user input schema
 */
export const createUserInputSchema = z.object({
  email: z.string().email(),
  displayName: z.string().min(1).max(100).optional(),
  preferences: userPreferencesSchema.partial().optional(),
});

/**
 * Update user input schema
 */
export const updateUserInputSchema = z.object({
  email: z.string().email().optional(),
  status: userStatusSchema.optional(),
  role: userRoleSchema.optional(),
});

/**
 * Update profile input schema
 */
export const updateProfileInputSchema = z.object({
  displayName: z.string().min(1).max(100).optional(),
  avatarUrl: z.string().url().nullable().optional(),
  bio: z.string().max(500).nullable().optional(),
  preferences: userPreferencesSchema.partial().optional(),
  metadata: z.record(z.unknown()).optional(),
});

/**
 * Type exports from schemas
 */
export type UserPreferencesSchema = z.infer<typeof userPreferencesSchema>;
export type ProfileSchema = z.infer<typeof profileSchema>;
export type UserStatusSchema = z.infer<typeof userStatusSchema>;
export type UserRoleSchema = z.infer<typeof userRoleSchema>;
export type UserSchema = z.infer<typeof userSchema>;
export type UserSessionSchema = z.infer<typeof userSessionSchema>;
export type CreateUserInputSchema = z.infer<typeof createUserInputSchema>;
export type UpdateUserInputSchema = z.infer<typeof updateUserInputSchema>;
export type UpdateProfileInputSchema = z.infer<typeof updateProfileInputSchema>;
