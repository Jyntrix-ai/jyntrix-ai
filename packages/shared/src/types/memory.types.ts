/**
 * Memory-related types for the AI Memory Architecture
 * Supports profile, semantic, episodic, and procedural memory types
 */

/**
 * Memory type enum - the four pillars of AI memory
 */
export type MemoryType = 'profile' | 'semantic' | 'episodic' | 'procedural';

/**
 * Memory importance level
 */
export type MemoryImportance = 'low' | 'medium' | 'high' | 'critical';

/**
 * Memory status
 */
export type MemoryStatus = 'active' | 'archived' | 'deleted' | 'decayed';

/**
 * Base memory interface
 */
export interface BaseMemory {
  id: string;
  userId: string;
  type: MemoryType;
  content: string;
  embedding: number[] | null;
  importance: MemoryImportance;
  status: MemoryStatus;
  accessCount: number;
  lastAccessedAt: Date | null;
  decayFactor: number;
  metadata: MemoryMetadata;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Memory metadata
 */
export interface MemoryMetadata {
  source: string;
  conversationId?: string;
  messageId?: string;
  tags: string[];
  entities: string[];
  confidence: number;
  version: number;
  [key: string]: unknown;
}

/**
 * Profile memory - user identity, preferences, and characteristics
 */
export interface ProfileMemory extends BaseMemory {
  type: 'profile';
  category: ProfileCategory;
  profileData: ProfileData;
}

export type ProfileCategory =
  | 'identity'
  | 'preference'
  | 'characteristic'
  | 'goal'
  | 'relationship'
  | 'context';

export interface ProfileData {
  key: string;
  value: string;
  confidence: number;
  source: string;
  validFrom: Date;
  validUntil: Date | null;
}

/**
 * Semantic memory - facts, knowledge, and general information
 */
export interface SemanticMemory extends BaseMemory {
  type: 'semantic';
  category: SemanticCategory;
  semanticData: SemanticData;
}

export type SemanticCategory =
  | 'fact'
  | 'concept'
  | 'definition'
  | 'relationship'
  | 'rule'
  | 'knowledge';

export interface SemanticData {
  subject: string;
  predicate: string;
  object: string;
  context: string | null;
  certainty: number;
  sources: string[];
}

/**
 * Episodic memory - specific events and experiences
 */
export interface EpisodicMemory extends BaseMemory {
  type: 'episodic';
  category: EpisodicCategory;
  episodicData: EpisodicData;
}

export type EpisodicCategory =
  | 'conversation'
  | 'interaction'
  | 'event'
  | 'experience'
  | 'milestone';

export interface EpisodicData {
  summary: string;
  participants: string[];
  location: string | null;
  duration: number | null;
  emotionalTone: string | null;
  outcomes: string[];
  timestamp: Date;
}

/**
 * Procedural memory - learned patterns, workflows, and how-to knowledge
 */
export interface ProceduralMemory extends BaseMemory {
  type: 'procedural';
  category: ProceduralCategory;
  proceduralData: ProceduralData;
}

export type ProceduralCategory =
  | 'workflow'
  | 'pattern'
  | 'skill'
  | 'routine'
  | 'strategy';

export interface ProceduralData {
  name: string;
  description: string;
  steps: ProceduralStep[];
  triggerConditions: string[];
  successCriteria: string[];
  executionCount: number;
  successRate: number;
}

export interface ProceduralStep {
  order: number;
  action: string;
  parameters: Record<string, unknown>;
  expectedOutcome: string;
  fallback: string | null;
}

/**
 * Working memory - temporary context for active sessions
 */
export interface WorkingMemory {
  id: string;
  userId: string;
  sessionId: string;
  context: WorkingMemoryContext;
  shortTermItems: ShortTermMemoryItem[];
  activeGoals: string[];
  attentionFocus: string[];
  capacity: number;
  usedCapacity: number;
  expiresAt: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface WorkingMemoryContext {
  currentTopic: string | null;
  conversationSummary: string | null;
  recentEntities: string[];
  activatedMemories: string[];
  pendingActions: string[];
}

export interface ShortTermMemoryItem {
  id: string;
  content: string;
  type: 'input' | 'output' | 'thought' | 'observation';
  relevance: number;
  timestamp: Date;
}

/**
 * Memory union type
 */
export type Memory = ProfileMemory | SemanticMemory | EpisodicMemory | ProceduralMemory;

/**
 * Entity for knowledge graph
 */
export interface Entity {
  id: string;
  userId: string;
  name: string;
  type: EntityType;
  description: string | null;
  properties: Record<string, unknown>;
  embedding: number[] | null;
  mentionCount: number;
  lastMentionedAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}

export type EntityType =
  | 'person'
  | 'organization'
  | 'location'
  | 'event'
  | 'concept'
  | 'product'
  | 'topic'
  | 'other';

/**
 * Entity relation for knowledge graph edges
 */
export interface EntityRelation {
  id: string;
  userId: string;
  sourceEntityId: string;
  targetEntityId: string;
  relationType: RelationType;
  strength: number;
  properties: Record<string, unknown>;
  evidence: string[];
  createdAt: Date;
  updatedAt: Date;
}

export type RelationType =
  | 'related_to'
  | 'part_of'
  | 'instance_of'
  | 'causes'
  | 'precedes'
  | 'located_in'
  | 'associated_with'
  | 'created_by'
  | 'belongs_to'
  | 'similar_to'
  | 'opposite_of'
  | 'custom';

/**
 * Memory retrieval result
 */
export interface RetrievalResult {
  memory: Memory;
  score: number;
  matchType: 'vector' | 'keyword' | 'hybrid' | 'graph';
  explanation: string | null;
}

/**
 * Ranked memory for hybrid search
 */
export interface RankedMemory {
  memoryId: string;
  vectorScore: number;
  keywordScore: number;
  graphScore: number;
  recencyScore: number;
  importanceScore: number;
  finalScore: number;
  rank: number;
}

/**
 * Memory search query
 */
export interface MemorySearchQuery {
  userId: string;
  query: string;
  types?: MemoryType[];
  categories?: string[];
  importance?: MemoryImportance[];
  dateRange?: {
    start: Date;
    end: Date;
  };
  tags?: string[];
  limit?: number;
  offset?: number;
  includeArchived?: boolean;
}

/**
 * Memory creation input
 */
export interface CreateMemoryInput {
  userId: string;
  type: MemoryType;
  content: string;
  importance?: MemoryImportance;
  metadata?: Partial<MemoryMetadata>;
}

/**
 * Memory update input
 */
export interface UpdateMemoryInput {
  content?: string;
  importance?: MemoryImportance;
  status?: MemoryStatus;
  metadata?: Partial<MemoryMetadata>;
}

/**
 * Token budget for context window management
 */
export interface TokenBudget {
  total: number;
  systemPrompt: number;
  profileMemory: number;
  semanticMemory: number;
  episodicMemory: number;
  proceduralMemory: number;
  workingMemory: number;
  conversation: number;
  response: number;
  reserved: number;
}

/**
 * Default token budget for a 128k context window
 */
export const DEFAULT_TOKEN_BUDGET: TokenBudget = {
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
};
