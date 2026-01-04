/**
 * Chat validation schemas using Zod
 */

import { z } from 'zod';

/**
 * Message role schema
 */
export const messageRoleSchema = z.enum(['user', 'assistant', 'system']);

/**
 * Message status schema
 */
export const messageStatusSchema = z.enum(['pending', 'sent', 'delivered', 'read', 'failed']);

/**
 * Conversation status schema
 */
export const conversationStatusSchema = z.enum(['active', 'archived', 'deleted']);

/**
 * Attachment type schema
 */
export const attachmentTypeSchema = z.enum(['image', 'file', 'audio', 'video', 'link']);

/**
 * Message attachment schema
 */
export const messageAttachmentSchema = z.object({
  id: z.string().uuid(),
  type: attachmentTypeSchema,
  url: z.string().url(),
  fileName: z.string().min(1).max(255),
  fileSize: z.number().int().min(0),
  mimeType: z.string().min(1),
  metadata: z.record(z.unknown()).default({}),
});

/**
 * Message content block schema
 */
export const messageContentBlockSchema = z.object({
  type: z.enum(['text', 'code', 'image', 'tool_use', 'tool_result']),
  content: z.string(),
  language: z.string().optional(),
  toolName: z.string().optional(),
  toolInput: z.record(z.unknown()).optional(),
  toolResult: z.unknown().optional(),
});

/**
 * Message metadata schema
 */
export const messageMetadataSchema = z.object({
  tokenCount: z.number().int().min(0).default(0),
  processingTime: z.number().min(0).default(0),
  model: z.string().nullable().default(null),
  temperature: z.number().min(0).max(2).nullable().default(null),
  memoriesUsed: z.array(z.string()).default([]),
  entitiesExtracted: z.array(z.string()).default([]),
  toolsUsed: z.array(z.string()).default([]),
}).passthrough();

/**
 * Message schema
 */
export const messageSchema = z.object({
  id: z.string().uuid(),
  conversationId: z.string().uuid(),
  role: messageRoleSchema,
  content: z.string().max(1000000),
  contentBlocks: z.array(messageContentBlockSchema).default([]),
  attachments: z.array(messageAttachmentSchema).default([]),
  status: messageStatusSchema.default('sent'),
  metadata: messageMetadataSchema,
  parentMessageId: z.string().uuid().nullable(),
  replyCount: z.number().int().min(0).default(0),
  createdAt: z.coerce.date(),
  updatedAt: z.coerce.date(),
});

/**
 * Conversation metadata schema
 */
export const conversationMetadataSchema = z.object({
  messageCount: z.number().int().min(0).default(0),
  tokenCount: z.number().int().min(0).default(0),
  lastModel: z.string().nullable().default(null),
  topics: z.array(z.string()).default([]),
  entities: z.array(z.string()).default([]),
  summary: z.string().nullable().default(null),
}).passthrough();

/**
 * Conversation settings schema
 */
export const conversationSettingsSchema = z.object({
  model: z.string().default('claude-3-5-sonnet-20241022'),
  temperature: z.number().min(0).max(2).default(0.7),
  maxTokens: z.number().int().min(1).max(200000).default(4096),
  systemPrompt: z.string().max(100000).nullable().default(null),
  memoryEnabled: z.boolean().default(true),
  streamEnabled: z.boolean().default(true),
});

/**
 * Conversation schema
 */
export const conversationSchema = z.object({
  id: z.string().uuid(),
  userId: z.string().uuid(),
  title: z.string().min(1).max(255),
  status: conversationStatusSchema.default('active'),
  settings: conversationSettingsSchema,
  metadata: conversationMetadataSchema,
  pinnedAt: z.coerce.date().nullable(),
  lastMessageAt: z.coerce.date().nullable(),
  createdAt: z.coerce.date(),
  updatedAt: z.coerce.date(),
});

/**
 * Conversation with messages schema
 */
export const conversationWithMessagesSchema = conversationSchema.extend({
  messages: z.array(messageSchema),
});

/**
 * Conversation summary schema
 */
export const conversationSummarySchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  preview: z.string(),
  messageCount: z.number().int().min(0),
  lastMessageAt: z.coerce.date().nullable(),
  createdAt: z.coerce.date(),
});

/**
 * Create conversation input schema
 */
export const createConversationInputSchema = z.object({
  userId: z.string().uuid(),
  title: z.string().min(1).max(255).optional(),
  settings: conversationSettingsSchema.partial().optional(),
  metadata: conversationMetadataSchema.partial().optional(),
});

/**
 * Update conversation input schema
 */
export const updateConversationInputSchema = z.object({
  title: z.string().min(1).max(255).optional(),
  status: conversationStatusSchema.optional(),
  settings: conversationSettingsSchema.partial().optional(),
  metadata: conversationMetadataSchema.partial().optional(),
  pinnedAt: z.coerce.date().nullable().optional(),
});

/**
 * Create message input schema
 */
export const createMessageInputSchema = z.object({
  conversationId: z.string().uuid(),
  role: messageRoleSchema,
  content: z.string().min(1).max(1000000),
  contentBlocks: z.array(messageContentBlockSchema).optional(),
  attachments: z.array(messageAttachmentSchema).optional(),
  parentMessageId: z.string().uuid().optional(),
  metadata: messageMetadataSchema.partial().optional(),
});

/**
 * Update message input schema
 */
export const updateMessageInputSchema = z.object({
  content: z.string().min(1).max(1000000).optional(),
  status: messageStatusSchema.optional(),
  metadata: messageMetadataSchema.partial().optional(),
});

/**
 * Chat completion request schema
 */
export const chatCompletionRequestSchema = z.object({
  conversationId: z.string().uuid(),
  message: z.string().min(1).max(1000000),
  attachments: z.array(messageAttachmentSchema).optional(),
  settings: conversationSettingsSchema.partial().optional(),
  stream: z.boolean().optional(),
});

/**
 * Chat completion response schema
 */
export const chatCompletionResponseSchema = z.object({
  messageId: z.string().uuid(),
  conversationId: z.string().uuid(),
  content: z.string(),
  contentBlocks: z.array(messageContentBlockSchema),
  metadata: messageMetadataSchema,
  memoriesCreated: z.array(z.string()),
  memoriesUpdated: z.array(z.string()),
});

/**
 * Chat stream chunk schema
 */
export const chatStreamChunkSchema = z.object({
  type: z.enum(['start', 'delta', 'tool_use', 'tool_result', 'end', 'error']),
  messageId: z.string().uuid(),
  content: z.string().optional(),
  toolName: z.string().optional(),
  toolInput: z.record(z.unknown()).optional(),
  toolResult: z.unknown().optional(),
  error: z.string().optional(),
  metadata: messageMetadataSchema.partial().optional(),
});

/**
 * Type exports from schemas
 */
export type MessageRoleSchema = z.infer<typeof messageRoleSchema>;
export type MessageStatusSchema = z.infer<typeof messageStatusSchema>;
export type ConversationStatusSchema = z.infer<typeof conversationStatusSchema>;
export type AttachmentTypeSchema = z.infer<typeof attachmentTypeSchema>;
export type MessageAttachmentSchema = z.infer<typeof messageAttachmentSchema>;
export type MessageContentBlockSchema = z.infer<typeof messageContentBlockSchema>;
export type MessageMetadataSchema = z.infer<typeof messageMetadataSchema>;
export type MessageSchema = z.infer<typeof messageSchema>;
export type ConversationMetadataSchema = z.infer<typeof conversationMetadataSchema>;
export type ConversationSettingsSchema = z.infer<typeof conversationSettingsSchema>;
export type ConversationSchema = z.infer<typeof conversationSchema>;
export type ConversationWithMessagesSchema = z.infer<typeof conversationWithMessagesSchema>;
export type ConversationSummarySchema = z.infer<typeof conversationSummarySchema>;
export type CreateConversationInputSchema = z.infer<typeof createConversationInputSchema>;
export type UpdateConversationInputSchema = z.infer<typeof updateConversationInputSchema>;
export type CreateMessageInputSchema = z.infer<typeof createMessageInputSchema>;
export type UpdateMessageInputSchema = z.infer<typeof updateMessageInputSchema>;
export type ChatCompletionRequestSchema = z.infer<typeof chatCompletionRequestSchema>;
export type ChatCompletionResponseSchema = z.infer<typeof chatCompletionResponseSchema>;
export type ChatStreamChunkSchema = z.infer<typeof chatStreamChunkSchema>;
