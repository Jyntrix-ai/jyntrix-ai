/**
 * API-related constants for the AI Memory Architecture
 */

/**
 * API version
 */
export const API_VERSION = 'v1';

/**
 * Base API routes
 */
export const API_ROUTES = {
  // Health & Status
  HEALTH: '/health',
  STATUS: '/status',
  METRICS: '/metrics',

  // Authentication
  AUTH: {
    BASE: '/auth',
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REGISTER: '/auth/register',
    REFRESH: '/auth/refresh',
    VERIFY_EMAIL: '/auth/verify-email',
    FORGOT_PASSWORD: '/auth/forgot-password',
    RESET_PASSWORD: '/auth/reset-password',
    ME: '/auth/me',
  },

  // Users
  USERS: {
    BASE: '/users',
    BY_ID: '/users/:id',
    PROFILE: '/users/:id/profile',
    PREFERENCES: '/users/:id/preferences',
    SESSIONS: '/users/:id/sessions',
  },

  // Memories
  MEMORIES: {
    BASE: '/memories',
    BY_ID: '/memories/:id',
    SEARCH: '/memories/search',
    BATCH: '/memories/batch',
    CONSOLIDATE: '/memories/consolidate',
    DECAY: '/memories/decay',
    STATS: '/memories/stats',
    BY_TYPE: '/memories/type/:type',
  },

  // Conversations
  CONVERSATIONS: {
    BASE: '/conversations',
    BY_ID: '/conversations/:id',
    MESSAGES: '/conversations/:id/messages',
    MESSAGE_BY_ID: '/conversations/:id/messages/:messageId',
    SUMMARY: '/conversations/:id/summary',
    EXPORT: '/conversations/:id/export',
  },

  // Chat (real-time)
  CHAT: {
    BASE: '/chat',
    COMPLETIONS: '/chat/completions',
    STREAM: '/chat/stream',
  },

  // Entities (Knowledge Graph)
  ENTITIES: {
    BASE: '/entities',
    BY_ID: '/entities/:id',
    RELATIONS: '/entities/:id/relations',
    SEARCH: '/entities/search',
    GRAPH: '/entities/graph',
  },

  // Relations
  RELATIONS: {
    BASE: '/relations',
    BY_ID: '/relations/:id',
  },

  // Working Memory
  WORKING_MEMORY: {
    BASE: '/working-memory',
    BY_SESSION: '/working-memory/:sessionId',
    CLEAR: '/working-memory/:sessionId/clear',
  },

  // Analytics
  ANALYTICS: {
    BASE: '/analytics',
    USAGE: '/analytics/usage',
    MEMORIES: '/analytics/memories',
    CONVERSATIONS: '/analytics/conversations',
    TOKENS: '/analytics/tokens',
  },

  // Export/Import
  DATA: {
    EXPORT: '/data/export',
    IMPORT: '/data/import',
    EXPORT_STATUS: '/data/export/:id/status',
    IMPORT_STATUS: '/data/import/:id/status',
  },

  // Webhooks
  WEBHOOKS: {
    BASE: '/webhooks',
    BY_ID: '/webhooks/:id',
    EVENTS: '/webhooks/events',
  },
} as const;

/**
 * HTTP status codes
 */
export const HTTP_STATUS = {
  // Success
  OK: 200,
  CREATED: 201,
  ACCEPTED: 202,
  NO_CONTENT: 204,

  // Redirection
  MOVED_PERMANENTLY: 301,
  FOUND: 302,
  NOT_MODIFIED: 304,

  // Client Errors
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  METHOD_NOT_ALLOWED: 405,
  CONFLICT: 409,
  GONE: 410,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,

  // Server Errors
  INTERNAL_SERVER_ERROR: 500,
  NOT_IMPLEMENTED: 501,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,
  GATEWAY_TIMEOUT: 504,
} as const;

/**
 * Rate limiting configuration
 */
export const RATE_LIMITS = {
  /** Global rate limit (requests per minute) */
  GLOBAL: {
    windowMs: 60 * 1000, // 1 minute
    max: 1000,
  },
  /** Authentication endpoints */
  AUTH: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 10,
  },
  /** Chat completions */
  CHAT: {
    windowMs: 60 * 1000, // 1 minute
    max: 60,
  },
  /** Memory search */
  MEMORY_SEARCH: {
    windowMs: 60 * 1000, // 1 minute
    max: 100,
  },
  /** Memory write operations */
  MEMORY_WRITE: {
    windowMs: 60 * 1000, // 1 minute
    max: 200,
  },
  /** Batch operations */
  BATCH: {
    windowMs: 60 * 1000, // 1 minute
    max: 10,
  },
  /** Export operations */
  EXPORT: {
    windowMs: 60 * 60 * 1000, // 1 hour
    max: 5,
  },
} as const;

/**
 * Request size limits
 */
export const REQUEST_LIMITS = {
  /** Maximum JSON body size */
  MAX_JSON_SIZE: '10mb',
  /** Maximum file upload size */
  MAX_FILE_SIZE: '50mb',
  /** Maximum URL length */
  MAX_URL_LENGTH: 2048,
  /** Maximum header size */
  MAX_HEADER_SIZE: '8kb',
} as const;

/**
 * Pagination defaults
 */
export const PAGINATION = {
  DEFAULT_PAGE: 1,
  DEFAULT_LIMIT: 20,
  MAX_LIMIT: 100,
  DEFAULT_SORT_ORDER: 'desc' as const,
} as const;

/**
 * Cache configuration
 */
export const CACHE_CONFIG = {
  /** Default cache TTL in seconds */
  DEFAULT_TTL: 300,
  /** User profile cache TTL */
  USER_PROFILE_TTL: 3600,
  /** Memory cache TTL */
  MEMORY_TTL: 600,
  /** Conversation list cache TTL */
  CONVERSATION_LIST_TTL: 120,
  /** Entity cache TTL */
  ENTITY_TTL: 1800,
  /** Health check cache TTL */
  HEALTH_CHECK_TTL: 30,
} as const;

/**
 * Timeout configuration (in milliseconds)
 */
export const TIMEOUTS = {
  /** Default request timeout */
  DEFAULT: 30000,
  /** Long-running operations */
  LONG: 120000,
  /** Chat completion timeout */
  CHAT_COMPLETION: 60000,
  /** Streaming timeout */
  STREAM: 300000,
  /** Database query timeout */
  DATABASE: 10000,
  /** External API timeout */
  EXTERNAL_API: 30000,
  /** File upload timeout */
  FILE_UPLOAD: 120000,
} as const;

/**
 * Retry configuration
 */
export const RETRY_CONFIG = {
  /** Maximum retry attempts */
  MAX_RETRIES: 3,
  /** Initial retry delay in milliseconds */
  INITIAL_DELAY: 1000,
  /** Maximum retry delay */
  MAX_DELAY: 30000,
  /** Backoff multiplier */
  BACKOFF_MULTIPLIER: 2,
  /** Jitter factor (0-1) */
  JITTER: 0.1,
} as const;

/**
 * CORS configuration
 */
export const CORS_CONFIG = {
  ALLOWED_METHODS: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  ALLOWED_HEADERS: [
    'Content-Type',
    'Authorization',
    'X-Request-ID',
    'X-API-Version',
    'X-Client-Version',
  ],
  EXPOSED_HEADERS: [
    'X-Request-ID',
    'X-RateLimit-Limit',
    'X-RateLimit-Remaining',
    'X-RateLimit-Reset',
  ],
  MAX_AGE: 86400, // 24 hours
} as const;

/**
 * Content types
 */
export const CONTENT_TYPES = {
  JSON: 'application/json',
  FORM_DATA: 'multipart/form-data',
  URL_ENCODED: 'application/x-www-form-urlencoded',
  TEXT: 'text/plain',
  HTML: 'text/html',
  CSV: 'text/csv',
  STREAM: 'text/event-stream',
} as const;

/**
 * Request headers
 */
export const HEADERS = {
  CONTENT_TYPE: 'Content-Type',
  AUTHORIZATION: 'Authorization',
  REQUEST_ID: 'X-Request-ID',
  API_VERSION: 'X-API-Version',
  CLIENT_VERSION: 'X-Client-Version',
  RATE_LIMIT: 'X-RateLimit-Limit',
  RATE_REMAINING: 'X-RateLimit-Remaining',
  RATE_RESET: 'X-RateLimit-Reset',
  RETRY_AFTER: 'Retry-After',
} as const;
