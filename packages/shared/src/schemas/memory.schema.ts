/**
 * Memory validation schemas using Zod
 */

import { z } from 'zod';

/**
 * Memory type schema
 */
export const memoryTypeSchema = z.enum(['profile', 'semantic', 'episodic', 'procedural']);

/**
 * Memory importance schema
 */
export const memoryImportanceSchema = z.enum(['low', 'medium', 'high', 'critical']);

/**
 * Memory status schema
 */
export const memoryStatusSchema = z.enum(['active', 'archived', 'deleted', 'decayed']);

/**
 * Memory metadata schema
 */
export const memoryMetadataSchema = z.object({
  source: z.string().min(1),
  conversationId: z.string().uuid().optional(),
  messageId: z.string().uuid().optional(),
  tags: z.array(z.string()).default([]),
  entities: z.array(z.string()).default([]),
  confidence: z.number().min(0).max(1).default(1),
  version: z.number().int().min(1).default(1),
}).passthrough();

/**
 * Base memory schema
 */
export const baseMemorySchema = z.object({
  id: z.string().uuid(),
  userId: z.string().uuid(),
  type: memoryTypeSchema,
  content: z.string().min(1).max(100000),
  embedding: z.array(z.number()).nullable(),
  importance: memoryImportanceSchema.default('medium'),
  status: memoryStatusSchema.default('active'),
  accessCount: z.number().int().min(0).default(0),
  lastAccessedAt: z.coerce.date().nullable(),
  decayFactor: z.number().min(0).max(1).default(1),
  metadata: memoryMetadataSchema,
  createdAt: z.coerce.date(),
  updatedAt: z.coerce.date(),
});

/**
 * Profile category schema
 */
export const profileCategorySchema = z.enum([
  'identity',
  'preference',
  'characteristic',
  'goal',
  'relationship',
  'context',
]);

/**
 * Profile data schema
 */
export const profileDataSchema = z.object({
  key: z.string().min(1),
  value: z.string().min(1),
  confidence: z.number().min(0).max(1),
  source: z.string().min(1),
  validFrom: z.coerce.date(),
  validUntil: z.coerce.date().nullable(),
});

/**
 * Profile memory schema
 */
export const profileMemorySchema = baseMemorySchema.extend({
  type: z.literal('profile'),
  category: profileCategorySchema,
  profileData: profileDataSchema,
});

/**
 * Semantic category schema
 */
export const semanticCategorySchema = z.enum([
  'fact',
  'concept',
  'definition',
  'relationship',
  'rule',
  'knowledge',
]);

/**
 * Semantic data schema
 */
export const semanticDataSchema = z.object({
  subject: z.string().min(1),
  predicate: z.string().min(1),
  object: z.string().min(1),
  context: z.string().nullable(),
  certainty: z.number().min(0).max(1),
  sources: z.array(z.string()),
});

/**
 * Semantic memory schema
 */
export const semanticMemorySchema = baseMemorySchema.extend({
  type: z.literal('semantic'),
  category: semanticCategorySchema,
  semanticData: semanticDataSchema,
});

/**
 * Episodic category schema
 */
export const episodicCategorySchema = z.enum([
  'conversation',
  'interaction',
  'event',
  'experience',
  'milestone',
]);

/**
 * Episodic data schema
 */
export const episodicDataSchema = z.object({
  summary: z.string().min(1),
  participants: z.array(z.string()),
  location: z.string().nullable(),
  duration: z.number().int().min(0).nullable(),
  emotionalTone: z.string().nullable(),
  outcomes: z.array(z.string()),
  timestamp: z.coerce.date(),
});

/**
 * Episodic memory schema
 */
export const episodicMemorySchema = baseMemorySchema.extend({
  type: z.literal('episodic'),
  category: episodicCategorySchema,
  episodicData: episodicDataSchema,
});

/**
 * Procedural category schema
 */
export const proceduralCategorySchema = z.enum([
  'workflow',
  'pattern',
  'skill',
  'routine',
  'strategy',
]);

/**
 * Procedural step schema
 */
export const proceduralStepSchema = z.object({
  order: z.number().int().min(0),
  action: z.string().min(1),
  parameters: z.record(z.unknown()).default({}),
  expectedOutcome: z.string().min(1),
  fallback: z.string().nullable(),
});

/**
 * Procedural data schema
 */
export const proceduralDataSchema = z.object({
  name: z.string().min(1),
  description: z.string().min(1),
  steps: z.array(proceduralStepSchema),
  triggerConditions: z.array(z.string()),
  successCriteria: z.array(z.string()),
  executionCount: z.number().int().min(0).default(0),
  successRate: z.number().min(0).max(1).default(0),
});

/**
 * Procedural memory schema
 */
export const proceduralMemorySchema = baseMemorySchema.extend({
  type: z.literal('procedural'),
  category: proceduralCategorySchema,
  proceduralData: proceduralDataSchema,
});

/**
 * Memory union schema
 */
export const memorySchema = z.discriminatedUnion('type', [
  profileMemorySchema,
  semanticMemorySchema,
  episodicMemorySchema,
  proceduralMemorySchema,
]);

/**
 * Working memory context schema
 */
export const workingMemoryContextSchema = z.object({
  currentTopic: z.string().nullable(),
  conversationSummary: z.string().nullable(),
  recentEntities: z.array(z.string()).default([]),
  activatedMemories: z.array(z.string()).default([]),
  pendingActions: z.array(z.string()).default([]),
});

/**
 * Short term memory item schema
 */
export const shortTermMemoryItemSchema = z.object({
  id: z.string().uuid(),
  content: z.string().min(1),
  type: z.enum(['input', 'output', 'thought', 'observation']),
  relevance: z.number().min(0).max(1),
  timestamp: z.coerce.date(),
});

/**
 * Working memory schema
 */
export const workingMemorySchema = z.object({
  id: z.string().uuid(),
  userId: z.string().uuid(),
  sessionId: z.string().uuid(),
  context: workingMemoryContextSchema,
  shortTermItems: z.array(shortTermMemoryItemSchema).default([]),
  activeGoals: z.array(z.string()).default([]),
  attentionFocus: z.array(z.string()).default([]),
  capacity: z.number().int().min(1).default(10),
  usedCapacity: z.number().int().min(0).default(0),
  expiresAt: z.coerce.date(),
  createdAt: z.coerce.date(),
  updatedAt: z.coerce.date(),
});

/**
 * Entity type schema
 */
export const entityTypeSchema = z.enum([
  'person',
  'organization',
  'location',
  'event',
  'concept',
  'product',
  'topic',
  'other',
]);

/**
 * Entity schema
 */
export const entitySchema = z.object({
  id: z.string().uuid(),
  userId: z.string().uuid(),
  name: z.string().min(1).max(500),
  type: entityTypeSchema,
  description: z.string().max(2000).nullable(),
  properties: z.record(z.unknown()).default({}),
  embedding: z.array(z.number()).nullable(),
  mentionCount: z.number().int().min(0).default(0),
  lastMentionedAt: z.coerce.date().nullable(),
  createdAt: z.coerce.date(),
  updatedAt: z.coerce.date(),
});

/**
 * Relation type schema
 */
export const relationTypeSchema = z.enum([
  'related_to',
  'part_of',
  'instance_of',
  'causes',
  'precedes',
  'located_in',
  'associated_with',
  'created_by',
  'belongs_to',
  'similar_to',
  'opposite_of',
  'custom',
]);

/**
 * Entity relation schema
 */
export const entityRelationSchema = z.object({
  id: z.string().uuid(),
  userId: z.string().uuid(),
  sourceEntityId: z.string().uuid(),
  targetEntityId: z.string().uuid(),
  relationType: relationTypeSchema,
  strength: z.number().min(0).max(1).default(0.5),
  properties: z.record(z.unknown()).default({}),
  evidence: z.array(z.string()).default([]),
  createdAt: z.coerce.date(),
  updatedAt: z.coerce.date(),
});

/**
 * Memory search query schema
 */
export const memorySearchQuerySchema = z.object({
  userId: z.string().uuid(),
  query: z.string().min(1).max(1000),
  types: z.array(memoryTypeSchema).optional(),
  categories: z.array(z.string()).optional(),
  importance: z.array(memoryImportanceSchema).optional(),
  dateRange: z.object({
    start: z.coerce.date(),
    end: z.coerce.date(),
  }).optional(),
  tags: z.array(z.string()).optional(),
  limit: z.number().int().min(1).max(100).default(10),
  offset: z.number().int().min(0).default(0),
  includeArchived: z.boolean().default(false),
});

/**
 * Create memory input schema
 */
export const createMemoryInputSchema = z.object({
  userId: z.string().uuid(),
  type: memoryTypeSchema,
  content: z.string().min(1).max(100000),
  importance: memoryImportanceSchema.optional(),
  metadata: memoryMetadataSchema.partial().optional(),
});

/**
 * Update memory input schema
 */
export const updateMemoryInputSchema = z.object({
  content: z.string().min(1).max(100000).optional(),
  importance: memoryImportanceSchema.optional(),
  status: memoryStatusSchema.optional(),
  metadata: memoryMetadataSchema.partial().optional(),
});

/**
 * Token budget schema
 */
export const tokenBudgetSchema = z.object({
  total: z.number().int().min(1000),
  systemPrompt: z.number().int().min(0),
  profileMemory: z.number().int().min(0),
  semanticMemory: z.number().int().min(0),
  episodicMemory: z.number().int().min(0),
  proceduralMemory: z.number().int().min(0),
  workingMemory: z.number().int().min(0),
  conversation: z.number().int().min(0),
  response: z.number().int().min(0),
  reserved: z.number().int().min(0),
});

/**
 * Type exports from schemas
 */
export type MemoryTypeSchema = z.infer<typeof memoryTypeSchema>;
export type MemoryImportanceSchema = z.infer<typeof memoryImportanceSchema>;
export type MemoryStatusSchema = z.infer<typeof memoryStatusSchema>;
export type MemoryMetadataSchema = z.infer<typeof memoryMetadataSchema>;
export type BaseMemorySchema = z.infer<typeof baseMemorySchema>;
export type ProfileMemorySchema = z.infer<typeof profileMemorySchema>;
export type SemanticMemorySchema = z.infer<typeof semanticMemorySchema>;
export type EpisodicMemorySchema = z.infer<typeof episodicMemorySchema>;
export type ProceduralMemorySchema = z.infer<typeof proceduralMemorySchema>;
export type MemorySchema = z.infer<typeof memorySchema>;
export type WorkingMemorySchema = z.infer<typeof workingMemorySchema>;
export type EntitySchema = z.infer<typeof entitySchema>;
export type EntityRelationSchema = z.infer<typeof entityRelationSchema>;
export type MemorySearchQuerySchema = z.infer<typeof memorySearchQuerySchema>;
export type CreateMemoryInputSchema = z.infer<typeof createMemoryInputSchema>;
export type UpdateMemoryInputSchema = z.infer<typeof updateMemoryInputSchema>;
export type TokenBudgetSchema = z.infer<typeof tokenBudgetSchema>;
