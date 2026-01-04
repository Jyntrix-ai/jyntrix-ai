/**
 * Chat and conversation types for the AI Memory Architecture
 */

/**
 * Message role enum
 */
export type MessageRole = 'user' | 'assistant' | 'system';

/**
 * Message status
 */
export type MessageStatus = 'pending' | 'sent' | 'delivered' | 'read' | 'failed';

/**
 * Conversation status
 */
export type ConversationStatus = 'active' | 'archived' | 'deleted';

/**
 * Message attachment type
 */
export type AttachmentType = 'image' | 'file' | 'audio' | 'video' | 'link';

/**
 * Message attachment
 */
export interface MessageAttachment {
  id: string;
  type: AttachmentType;
  url: string;
  fileName: string;
  fileSize: number;
  mimeType: string;
  metadata: Record<string, unknown>;
}

/**
 * Message content block for structured content
 */
export interface MessageContentBlock {
  type: 'text' | 'code' | 'image' | 'tool_use' | 'tool_result';
  content: string;
  language?: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolResult?: unknown;
}

/**
 * Message metadata
 */
export interface MessageMetadata {
  tokenCount: number;
  processingTime: number;
  model: string | null;
  temperature: number | null;
  memoriesUsed: string[];
  entitiesExtracted: string[];
  toolsUsed: string[];
  [key: string]: unknown;
}

/**
 * Chat message
 */
export interface Message {
  id: string;
  conversationId: string;
  role: MessageRole;
  content: string;
  contentBlocks: MessageContentBlock[];
  attachments: MessageAttachment[];
  status: MessageStatus;
  metadata: MessageMetadata;
  parentMessageId: string | null;
  replyCount: number;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Conversation metadata
 */
export interface ConversationMetadata {
  messageCount: number;
  tokenCount: number;
  lastModel: string | null;
  topics: string[];
  entities: string[];
  summary: string | null;
  [key: string]: unknown;
}

/**
 * Conversation settings
 */
export interface ConversationSettings {
  model: string;
  temperature: number;
  maxTokens: number;
  systemPrompt: string | null;
  memoryEnabled: boolean;
  streamEnabled: boolean;
}

/**
 * Conversation
 */
export interface Conversation {
  id: string;
  userId: string;
  title: string;
  status: ConversationStatus;
  settings: ConversationSettings;
  metadata: ConversationMetadata;
  pinnedAt: Date | null;
  lastMessageAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Conversation with messages
 */
export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

/**
 * Conversation summary
 */
export interface ConversationSummary {
  id: string;
  title: string;
  preview: string;
  messageCount: number;
  lastMessageAt: Date | null;
  createdAt: Date;
}

/**
 * Create conversation input
 */
export interface CreateConversationInput {
  userId: string;
  title?: string;
  settings?: Partial<ConversationSettings>;
  metadata?: Partial<ConversationMetadata>;
}

/**
 * Update conversation input
 */
export interface UpdateConversationInput {
  title?: string;
  status?: ConversationStatus;
  settings?: Partial<ConversationSettings>;
  metadata?: Partial<ConversationMetadata>;
  pinnedAt?: Date | null;
}

/**
 * Create message input
 */
export interface CreateMessageInput {
  conversationId: string;
  role: MessageRole;
  content: string;
  contentBlocks?: MessageContentBlock[];
  attachments?: MessageAttachment[];
  parentMessageId?: string;
  metadata?: Partial<MessageMetadata>;
}

/**
 * Update message input
 */
export interface UpdateMessageInput {
  content?: string;
  status?: MessageStatus;
  metadata?: Partial<MessageMetadata>;
}

/**
 * Chat completion request
 */
export interface ChatCompletionRequest {
  conversationId: string;
  message: string;
  attachments?: MessageAttachment[];
  settings?: Partial<ConversationSettings>;
  stream?: boolean;
}

/**
 * Chat completion response
 */
export interface ChatCompletionResponse {
  messageId: string;
  conversationId: string;
  content: string;
  contentBlocks: MessageContentBlock[];
  metadata: MessageMetadata;
  memoriesCreated: string[];
  memoriesUpdated: string[];
}

/**
 * Streaming chat chunk
 */
export interface ChatStreamChunk {
  type: 'start' | 'delta' | 'tool_use' | 'tool_result' | 'end' | 'error';
  messageId: string;
  content?: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolResult?: unknown;
  error?: string;
  metadata?: Partial<MessageMetadata>;
}

/**
 * Default conversation settings
 */
export const DEFAULT_CONVERSATION_SETTINGS: ConversationSettings = {
  model: 'claude-3-5-sonnet-20241022',
  temperature: 0.7,
  maxTokens: 4096,
  systemPrompt: null,
  memoryEnabled: true,
  streamEnabled: true,
};

/**
 * Default message metadata
 */
export const DEFAULT_MESSAGE_METADATA: MessageMetadata = {
  tokenCount: 0,
  processingTime: 0,
  model: null,
  temperature: null,
  memoriesUsed: [],
  entitiesExtracted: [],
  toolsUsed: [],
};
