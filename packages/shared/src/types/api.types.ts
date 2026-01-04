/**
 * API request/response types for the AI Memory Architecture
 */

/**
 * API response status
 */
export type ApiStatus = 'success' | 'error';

/**
 * Base API response
 */
export interface ApiResponse<T = unknown> {
  status: ApiStatus;
  data?: T;
  error?: ApiError;
  meta?: ApiMeta;
}

/**
 * API error
 */
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  stack?: string;
}

/**
 * API metadata
 */
export interface ApiMeta {
  requestId: string;
  timestamp: string;
  duration: number;
  version: string;
}

/**
 * Pagination parameters
 */
export interface PaginationParams {
  page: number;
  limit: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

/**
 * Pagination metadata
 */
export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

/**
 * Paginated response
 */
export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: PaginationMeta;
}

/**
 * Health check response
 */
export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime: number;
  services: ServiceHealth[];
  timestamp: string;
}

/**
 * Service health
 */
export interface ServiceHealth {
  name: string;
  status: 'up' | 'down' | 'degraded';
  latency: number;
  lastCheck: string;
  details?: Record<string, unknown>;
}

/**
 * Authentication request
 */
export interface AuthRequest {
  email: string;
  password?: string;
  provider?: 'email' | 'google' | 'github';
  token?: string;
}

/**
 * Authentication response
 */
export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  tokenType: 'Bearer';
  user: {
    id: string;
    email: string;
    role: string;
  };
}

/**
 * Token refresh request
 */
export interface TokenRefreshRequest {
  refreshToken: string;
}

/**
 * Token refresh response
 */
export interface TokenRefreshResponse {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

/**
 * User list request
 */
export interface UserListRequest extends PaginationParams {
  status?: string;
  role?: string;
  search?: string;
}

/**
 * Memory list request
 */
export interface MemoryListRequest extends PaginationParams {
  userId: string;
  type?: string;
  importance?: string;
  status?: string;
  tags?: string[];
  dateFrom?: string;
  dateTo?: string;
}

/**
 * Memory search request
 */
export interface MemorySearchRequest {
  userId: string;
  query: string;
  types?: string[];
  limit?: number;
  threshold?: number;
  includeArchived?: boolean;
}

/**
 * Memory search response
 */
export interface MemorySearchResponse {
  results: Array<{
    memoryId: string;
    score: number;
    matchType: string;
    content: string;
    type: string;
    createdAt: string;
  }>;
  query: string;
  totalResults: number;
  searchTime: number;
}

/**
 * Conversation list request
 */
export interface ConversationListRequest extends PaginationParams {
  userId: string;
  status?: string;
  pinned?: boolean;
  search?: string;
}

/**
 * Message list request
 */
export interface MessageListRequest extends PaginationParams {
  conversationId: string;
  role?: string;
  before?: string;
  after?: string;
}

/**
 * Entity list request
 */
export interface EntityListRequest extends PaginationParams {
  userId: string;
  type?: string;
  search?: string;
}

/**
 * Entity relation list request
 */
export interface EntityRelationListRequest extends PaginationParams {
  userId: string;
  sourceEntityId?: string;
  targetEntityId?: string;
  relationType?: string;
}

/**
 * Batch operation request
 */
export interface BatchOperationRequest<T> {
  operations: Array<{
    id: string;
    action: 'create' | 'update' | 'delete';
    data?: T;
  }>;
}

/**
 * Batch operation response
 */
export interface BatchOperationResponse {
  results: Array<{
    id: string;
    success: boolean;
    error?: string;
  }>;
  totalSuccess: number;
  totalFailed: number;
}

/**
 * Export request
 */
export interface ExportRequest {
  userId: string;
  format: 'json' | 'csv';
  includeMemories?: boolean;
  includeConversations?: boolean;
  includeEntities?: boolean;
  dateFrom?: string;
  dateTo?: string;
}

/**
 * Export response
 */
export interface ExportResponse {
  exportId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  downloadUrl?: string;
  expiresAt?: string;
  progress?: number;
}

/**
 * Import request
 */
export interface ImportRequest {
  userId: string;
  format: 'json' | 'csv';
  data: string;
  mergeStrategy: 'replace' | 'merge' | 'skip';
}

/**
 * Import response
 */
export interface ImportResponse {
  importId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  totalItems: number;
  processedItems: number;
  successItems: number;
  failedItems: number;
  errors?: Array<{
    item: number;
    error: string;
  }>;
}

/**
 * Analytics request
 */
export interface AnalyticsRequest {
  userId: string;
  metrics: string[];
  dateFrom: string;
  dateTo: string;
  granularity: 'hour' | 'day' | 'week' | 'month';
}

/**
 * Analytics response
 */
export interface AnalyticsResponse {
  metrics: Record<string, Array<{
    timestamp: string;
    value: number;
  }>>;
  summary: Record<string, number>;
  dateFrom: string;
  dateTo: string;
}

/**
 * Webhook event
 */
export interface WebhookEvent {
  id: string;
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
  userId: string;
  signature: string;
}

/**
 * Rate limit info
 */
export interface RateLimitInfo {
  limit: number;
  remaining: number;
  reset: number;
  retryAfter?: number;
}

/**
 * API error codes
 */
export const API_ERROR_CODES = {
  // Authentication errors (1xxx)
  UNAUTHORIZED: 'ERR_1001',
  INVALID_TOKEN: 'ERR_1002',
  TOKEN_EXPIRED: 'ERR_1003',
  INVALID_CREDENTIALS: 'ERR_1004',
  ACCOUNT_SUSPENDED: 'ERR_1005',

  // Validation errors (2xxx)
  VALIDATION_FAILED: 'ERR_2001',
  INVALID_INPUT: 'ERR_2002',
  MISSING_REQUIRED_FIELD: 'ERR_2003',
  INVALID_FORMAT: 'ERR_2004',

  // Resource errors (3xxx)
  NOT_FOUND: 'ERR_3001',
  ALREADY_EXISTS: 'ERR_3002',
  CONFLICT: 'ERR_3003',
  GONE: 'ERR_3004',

  // Rate limiting errors (4xxx)
  RATE_LIMITED: 'ERR_4001',
  QUOTA_EXCEEDED: 'ERR_4002',

  // Server errors (5xxx)
  INTERNAL_ERROR: 'ERR_5001',
  SERVICE_UNAVAILABLE: 'ERR_5002',
  TIMEOUT: 'ERR_5003',
  DATABASE_ERROR: 'ERR_5004',
  EXTERNAL_SERVICE_ERROR: 'ERR_5005',
} as const;

export type ApiErrorCode = typeof API_ERROR_CODES[keyof typeof API_ERROR_CODES];
