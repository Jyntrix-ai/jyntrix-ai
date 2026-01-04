/**
 * Memory-related constants for the AI Memory Architecture
 */

/**
 * Memory types
 */
export const MEMORY_TYPES = {
  PROFILE: 'profile',
  SEMANTIC: 'semantic',
  EPISODIC: 'episodic',
  PROCEDURAL: 'procedural',
} as const;

export type MemoryTypeConstant = typeof MEMORY_TYPES[keyof typeof MEMORY_TYPES];

/**
 * Memory importance levels
 */
export const MEMORY_IMPORTANCE = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical',
} as const;

export type MemoryImportanceConstant = typeof MEMORY_IMPORTANCE[keyof typeof MEMORY_IMPORTANCE];

/**
 * Memory status values
 */
export const MEMORY_STATUS = {
  ACTIVE: 'active',
  ARCHIVED: 'archived',
  DELETED: 'deleted',
  DECAYED: 'decayed',
} as const;

export type MemoryStatusConstant = typeof MEMORY_STATUS[keyof typeof MEMORY_STATUS];

/**
 * Profile memory categories
 */
export const PROFILE_CATEGORIES = {
  IDENTITY: 'identity',
  PREFERENCE: 'preference',
  CHARACTERISTIC: 'characteristic',
  GOAL: 'goal',
  RELATIONSHIP: 'relationship',
  CONTEXT: 'context',
} as const;

/**
 * Semantic memory categories
 */
export const SEMANTIC_CATEGORIES = {
  FACT: 'fact',
  CONCEPT: 'concept',
  DEFINITION: 'definition',
  RELATIONSHIP: 'relationship',
  RULE: 'rule',
  KNOWLEDGE: 'knowledge',
} as const;

/**
 * Episodic memory categories
 */
export const EPISODIC_CATEGORIES = {
  CONVERSATION: 'conversation',
  INTERACTION: 'interaction',
  EVENT: 'event',
  EXPERIENCE: 'experience',
  MILESTONE: 'milestone',
} as const;

/**
 * Procedural memory categories
 */
export const PROCEDURAL_CATEGORIES = {
  WORKFLOW: 'workflow',
  PATTERN: 'pattern',
  SKILL: 'skill',
  ROUTINE: 'routine',
  STRATEGY: 'strategy',
} as const;

/**
 * Entity types for knowledge graph
 */
export const ENTITY_TYPES = {
  PERSON: 'person',
  ORGANIZATION: 'organization',
  LOCATION: 'location',
  EVENT: 'event',
  CONCEPT: 'concept',
  PRODUCT: 'product',
  TOPIC: 'topic',
  OTHER: 'other',
} as const;

/**
 * Relation types for knowledge graph
 */
export const RELATION_TYPES = {
  RELATED_TO: 'related_to',
  PART_OF: 'part_of',
  INSTANCE_OF: 'instance_of',
  CAUSES: 'causes',
  PRECEDES: 'precedes',
  LOCATED_IN: 'located_in',
  ASSOCIATED_WITH: 'associated_with',
  CREATED_BY: 'created_by',
  BELONGS_TO: 'belongs_to',
  SIMILAR_TO: 'similar_to',
  OPPOSITE_OF: 'opposite_of',
  CUSTOM: 'custom',
} as const;

/**
 * Token budgets for different context window sizes
 */
export const TOKEN_BUDGETS = {
  /** 8k context window (legacy models) */
  SMALL: {
    total: 8000,
    systemPrompt: 500,
    profileMemory: 500,
    semanticMemory: 1000,
    episodicMemory: 1500,
    proceduralMemory: 500,
    workingMemory: 500,
    conversation: 2500,
    response: 500,
    reserved: 500,
  },
  /** 32k context window */
  MEDIUM: {
    total: 32000,
    systemPrompt: 1000,
    profileMemory: 2000,
    semanticMemory: 4000,
    episodicMemory: 6000,
    proceduralMemory: 2000,
    workingMemory: 2000,
    conversation: 10000,
    response: 4000,
    reserved: 1000,
  },
  /** 128k context window (default) */
  LARGE: {
    total: 128000,
    systemPrompt: 4000,
    profileMemory: 8000,
    semanticMemory: 16000,
    episodicMemory: 24000,
    proceduralMemory: 8000,
    workingMemory: 8000,
    conversation: 40000,
    response: 16000,
    reserved: 4000,
  },
  /** 200k context window */
  XLARGE: {
    total: 200000,
    systemPrompt: 6000,
    profileMemory: 12000,
    semanticMemory: 25000,
    episodicMemory: 38000,
    proceduralMemory: 12000,
    workingMemory: 12000,
    conversation: 65000,
    response: 25000,
    reserved: 5000,
  },
} as const;

/**
 * Memory decay constants
 */
export const MEMORY_DECAY = {
  /** Base decay rate per day for unused memories */
  BASE_DECAY_RATE: 0.01,
  /** Minimum decay factor (memories never fully decay) */
  MIN_DECAY_FACTOR: 0.1,
  /** Boost factor when memory is accessed */
  ACCESS_BOOST: 0.1,
  /** Maximum decay factor */
  MAX_DECAY_FACTOR: 1.0,
  /** Days after which decay starts */
  GRACE_PERIOD_DAYS: 7,
  /** Importance multipliers for decay resistance */
  IMPORTANCE_MULTIPLIERS: {
    low: 1.0,
    medium: 0.75,
    high: 0.5,
    critical: 0.25,
  },
} as const;

/**
 * Memory search defaults
 */
export const MEMORY_SEARCH_DEFAULTS = {
  /** Default number of results to return */
  DEFAULT_LIMIT: 10,
  /** Maximum number of results to return */
  MAX_LIMIT: 100,
  /** Default similarity threshold for vector search */
  DEFAULT_THRESHOLD: 0.7,
  /** Minimum similarity threshold */
  MIN_THRESHOLD: 0.3,
  /** Maximum similarity threshold */
  MAX_THRESHOLD: 0.99,
} as const;

/**
 * Memory embedding configuration
 */
export const EMBEDDING_CONFIG = {
  /** Embedding model to use */
  MODEL: 'text-embedding-3-small',
  /** Embedding dimensions */
  DIMENSIONS: 1536,
  /** Maximum input tokens for embedding */
  MAX_INPUT_TOKENS: 8192,
  /** Batch size for embedding requests */
  BATCH_SIZE: 100,
} as const;

/**
 * Working memory configuration
 */
export const WORKING_MEMORY_CONFIG = {
  /** Default capacity (number of items) */
  DEFAULT_CAPACITY: 10,
  /** Maximum capacity */
  MAX_CAPACITY: 50,
  /** Default expiration time in minutes */
  DEFAULT_EXPIRATION_MINUTES: 60,
  /** Maximum expiration time in minutes */
  MAX_EXPIRATION_MINUTES: 480,
} as const;

/**
 * Memory consolidation configuration
 */
export const CONSOLIDATION_CONFIG = {
  /** Minimum memories before consolidation */
  MIN_MEMORIES_FOR_CONSOLIDATION: 10,
  /** Maximum memories to consolidate at once */
  MAX_MEMORIES_PER_CONSOLIDATION: 50,
  /** Similarity threshold for merging memories */
  MERGE_THRESHOLD: 0.85,
  /** Time window for episodic consolidation (hours) */
  EPISODIC_TIME_WINDOW_HOURS: 24,
} as const;
