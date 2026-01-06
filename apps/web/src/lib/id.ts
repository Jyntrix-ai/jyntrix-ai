/**
 * Unique ID generator for temporary message IDs.
 * Avoids collisions from rapid successive calls.
 */

let counter = 0;

/**
 * Generate a unique temporary ID.
 * Uses crypto.randomUUID when available, falls back to timestamp + counter + random.
 */
export function generateUniqueId(prefix: string = 'temp'): string {
  // Use crypto.randomUUID if available (modern browsers)
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  // Fallback: timestamp + incrementing counter + random suffix
  counter = (counter + 1) % Number.MAX_SAFE_INTEGER;
  const timestamp = Date.now();
  const random = Math.random().toString(36).slice(2, 9);

  return `${prefix}-${timestamp}-${counter}-${random}`;
}

/**
 * Generate a unique message ID with 'msg' prefix.
 */
export function generateMessageId(): string {
  return generateUniqueId('msg');
}
