/**
 * ID generation utilities using nanoid
 */

import { nanoid, customAlphabet } from 'nanoid';

/**
 * Default ID length
 */
const DEFAULT_ID_LENGTH = 21;

/**
 * Short ID length (for user-facing IDs)
 */
const SHORT_ID_LENGTH = 12;

/**
 * Alphabets for different ID types
 */
const ALPHABETS = {
  /** Standard alphanumeric (case-sensitive) */
  ALPHANUMERIC: '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
  /** Lowercase alphanumeric only */
  LOWERCASE: '0123456789abcdefghijklmnopqrstuvwxyz',
  /** URL-safe characters */
  URL_SAFE: '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_',
  /** Numeric only */
  NUMERIC: '0123456789',
  /** Hexadecimal */
  HEX: '0123456789abcdef',
} as const;

/**
 * Prefixes for different entity types
 */
export const ID_PREFIXES = {
  USER: 'usr',
  PROFILE: 'prf',
  SESSION: 'ses',
  MEMORY: 'mem',
  CONVERSATION: 'cnv',
  MESSAGE: 'msg',
  ENTITY: 'ent',
  RELATION: 'rel',
  WORKING_MEMORY: 'wmm',
  EXPORT: 'exp',
  IMPORT: 'imp',
  WEBHOOK: 'whk',
  API_KEY: 'key',
} as const;

export type IdPrefix = typeof ID_PREFIXES[keyof typeof ID_PREFIXES];

/**
 * Generate a standard nanoid
 * @param length - Optional custom length (default: 21)
 */
export function generateId(length: number = DEFAULT_ID_LENGTH): string {
  return nanoid(length);
}

/**
 * Generate a short ID for user-facing purposes
 */
export function generateShortId(): string {
  return nanoid(SHORT_ID_LENGTH);
}

/**
 * Generate a prefixed ID for a specific entity type
 * @param prefix - The entity type prefix
 * @param length - Optional custom length for the ID portion
 */
export function generatePrefixedId(prefix: IdPrefix, length: number = 16): string {
  return `${prefix}_${nanoid(length)}`;
}

/**
 * Generate a URL-safe ID
 * @param length - Optional custom length
 */
export function generateUrlSafeId(length: number = DEFAULT_ID_LENGTH): string {
  const generator = customAlphabet(ALPHABETS.URL_SAFE, length);
  return generator();
}

/**
 * Generate a lowercase alphanumeric ID
 * @param length - Optional custom length
 */
export function generateLowercaseId(length: number = DEFAULT_ID_LENGTH): string {
  const generator = customAlphabet(ALPHABETS.LOWERCASE, length);
  return generator();
}

/**
 * Generate a numeric ID
 * @param length - Optional custom length
 */
export function generateNumericId(length: number = 8): string {
  const generator = customAlphabet(ALPHABETS.NUMERIC, length);
  return generator();
}

/**
 * Generate a hexadecimal ID
 * @param length - Optional custom length
 */
export function generateHexId(length: number = 32): string {
  const generator = customAlphabet(ALPHABETS.HEX, length);
  return generator();
}

/**
 * Generate a user ID
 */
export function generateUserId(): string {
  return generatePrefixedId(ID_PREFIXES.USER);
}

/**
 * Generate a profile ID
 */
export function generateProfileId(): string {
  return generatePrefixedId(ID_PREFIXES.PROFILE);
}

/**
 * Generate a session ID
 */
export function generateSessionId(): string {
  return generatePrefixedId(ID_PREFIXES.SESSION);
}

/**
 * Generate a memory ID
 */
export function generateMemoryId(): string {
  return generatePrefixedId(ID_PREFIXES.MEMORY);
}

/**
 * Generate a conversation ID
 */
export function generateConversationId(): string {
  return generatePrefixedId(ID_PREFIXES.CONVERSATION);
}

/**
 * Generate a message ID
 */
export function generateMessageId(): string {
  return generatePrefixedId(ID_PREFIXES.MESSAGE);
}

/**
 * Generate an entity ID
 */
export function generateEntityId(): string {
  return generatePrefixedId(ID_PREFIXES.ENTITY);
}

/**
 * Generate a relation ID
 */
export function generateRelationId(): string {
  return generatePrefixedId(ID_PREFIXES.RELATION);
}

/**
 * Generate a working memory ID
 */
export function generateWorkingMemoryId(): string {
  return generatePrefixedId(ID_PREFIXES.WORKING_MEMORY);
}

/**
 * Generate an API key
 * Format: key_xxxx...xxxx (32 character random part)
 */
export function generateApiKey(): string {
  return `${ID_PREFIXES.API_KEY}_${nanoid(32)}`;
}

/**
 * Generate a request ID for tracing
 * Format: req-timestamp-random
 */
export function generateRequestId(): string {
  const timestamp = Date.now().toString(36);
  const random = nanoid(8);
  return `req-${timestamp}-${random}`;
}

/**
 * Generate a correlation ID for distributed tracing
 */
export function generateCorrelationId(): string {
  return generateHexId(32);
}

/**
 * Validate if a string matches a prefixed ID format
 * @param id - The ID to validate
 * @param prefix - The expected prefix
 */
export function isValidPrefixedId(id: string, prefix: IdPrefix): boolean {
  if (!id || typeof id !== 'string') {
    return false;
  }

  const pattern = new RegExp(`^${prefix}_[A-Za-z0-9_-]{10,32}$`);
  return pattern.test(id);
}

/**
 * Extract the prefix from a prefixed ID
 * @param id - The prefixed ID
 */
export function extractPrefix(id: string): string | null {
  if (!id || typeof id !== 'string') {
    return null;
  }

  const parts = id.split('_');
  if (parts.length >= 2) {
    return parts[0];
  }

  return null;
}

/**
 * Get the entity type from a prefixed ID
 * @param id - The prefixed ID
 */
export function getEntityTypeFromId(id: string): keyof typeof ID_PREFIXES | null {
  const prefix = extractPrefix(id);
  if (!prefix) {
    return null;
  }

  const entries = Object.entries(ID_PREFIXES);
  for (const [key, value] of entries) {
    if (value === prefix) {
      return key as keyof typeof ID_PREFIXES;
    }
  }

  return null;
}
