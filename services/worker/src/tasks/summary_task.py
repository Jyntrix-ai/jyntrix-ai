"""
Session Summarization Task

Generates summaries for conversations and creates episodic memories.
Uses Gemini for intelligent summarization with context awareness.
"""

from typing import Any

import google.generativeai as genai

from src.config import config
from src.db.supabase import MemoryType, get_supabase_client
from src.utils.logger import TaskLogger, get_logger

logger = get_logger(__name__)

# Configure Gemini
genai.configure(api_key=config.google_ai_api_key.get_secret_value())

# Summarization prompt
SUMMARY_PROMPT = """Summarize the following conversation between a user and an AI assistant.

CONVERSATION:
{messages}

Create a concise summary that captures:
1. **Main Topic**: What was the conversation primarily about?
2. **Key Points**: What were the most important points discussed?
3. **Decisions/Actions**: Were any decisions made or actions taken?
4. **User Intent**: What was the user trying to accomplish?
5. **Outcome**: How was the conversation resolved?

Requirements:
- Write in third person (e.g., "The user asked about...", "The assistant explained...")
- Keep the summary under 200 words
- Focus on information worth remembering for future conversations
- Include any specific facts, preferences, or requests mentioned

Return ONLY the summary text, no additional formatting or headers.
"""

# Episodic memory prompt - creates a memorable narrative
EPISODIC_PROMPT = """Based on this conversation summary, create a brief episodic memory.

SUMMARY:
{summary}

Create a memorable narrative (2-3 sentences) that captures this interaction as an episode.
This should be written as if recalling a past event, suitable for future reference.

Example format:
"On [general timeframe], the user discussed [topic]. They were interested in [key point] and [outcome]."

Return ONLY the episodic memory text.
"""


async def summarize_conversation(
    ctx: dict[str, Any],
    conversation_id: str,
    force: bool = False,
) -> dict[str, Any]:
    """
    Generate a summary for a conversation and create episodic memory.

    This task:
    1. Fetches conversation messages from Supabase
    2. Generates a summary using Gemini
    3. Stores the summary as an episodic memory
    4. Updates the conversation with the summary
    5. Enqueues embedding task for the memory

    Args:
        ctx: ARQ context containing Redis pool.
        conversation_id: UUID of the conversation to summarize.
        force: If True, regenerate summary even if one exists.

    Returns:
        Result dict with summary and memory details.
    """
    supabase = get_supabase_client()

    with TaskLogger(logger, "summarize_conversation", task_id=conversation_id):
        try:
            # Step 1: Fetch conversation
            conversation = await supabase.get_conversation(conversation_id)
            if not conversation:
                logger.error(f"Conversation {conversation_id} not found")
                return {
                    "success": False,
                    "conversation_id": conversation_id,
                    "error": "Conversation not found",
                }

            # Check if already summarized (unless forced)
            if not force and conversation.get("summary"):
                logger.info(f"Conversation {conversation_id} already has a summary")
                return {
                    "success": True,
                    "conversation_id": conversation_id,
                    "already_summarized": True,
                }

            user_id = conversation.get("user_id")

            # Fetch messages
            messages = await supabase.get_conversation_messages(
                conversation_id,
                limit=100,  # Limit for summarization context
            )

            if not messages or len(messages) < 2:
                logger.warning(
                    f"Conversation {conversation_id} has insufficient messages for summarization"
                )
                return {
                    "success": True,
                    "conversation_id": conversation_id,
                    "skipped": True,
                    "reason": "Insufficient messages",
                }

            # Step 2: Format messages for summarization
            formatted_messages = _format_messages_for_summary(messages)

            # Step 3: Generate summary with Gemini
            summary = await _generate_summary(formatted_messages)
            if not summary:
                return {
                    "success": False,
                    "conversation_id": conversation_id,
                    "error": "Failed to generate summary",
                }

            # Step 4: Generate episodic memory narrative
            episodic_narrative = await _generate_episodic_memory(summary)
            if not episodic_narrative:
                episodic_narrative = summary  # Fallback to summary

            # Step 5: Create episodic memory
            memory = await supabase.create_memory(
                user_id=user_id,
                content=episodic_narrative,
                memory_type=MemoryType.EPISODIC,
                source_type="conversation_summary",
                source_id=conversation_id,
                metadata={
                    "conversation_id": conversation_id,
                    "message_count": len(messages),
                    "full_summary": summary,
                    "summary_type": "conversation",
                },
            )

            memory_id = memory["id"] if memory else None

            # Step 6: Update conversation with summary
            await supabase.update_conversation_summary(
                conversation_id=conversation_id,
                summary=summary,
                summary_memory_id=memory_id,
            )

            # Step 7: Enqueue embedding task
            redis_pool = ctx.get("redis")
            if redis_pool and memory_id:
                await redis_pool.enqueue_job(
                    "generate_embedding",
                    memory_id,
                )
                logger.info(f"Enqueued embedding task for memory {memory_id}")

            logger.info(
                f"Successfully summarized conversation {conversation_id}: "
                f"{len(messages)} messages -> {len(summary)} chars"
            )

            return {
                "success": True,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "message_count": len(messages),
                "summary_length": len(summary),
                "memory_id": memory_id,
            }

        except Exception as e:
            logger.exception(f"Summarization failed for conversation {conversation_id}: {e}")
            return {
                "success": False,
                "conversation_id": conversation_id,
                "error": str(e),
            }


def _format_messages_for_summary(messages: list[dict[str, Any]]) -> str:
    """
    Format messages into a readable conversation transcript.

    Args:
        messages: List of message records from Supabase.

    Returns:
        Formatted conversation string.
    """
    formatted = []

    for msg in messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")

        # Truncate very long messages
        if len(content) > 1000:
            content = content[:1000] + "..."

        formatted.append(f"{role}: {content}")

    return "\n\n".join(formatted)


async def _generate_summary(formatted_messages: str) -> str | None:
    """
    Generate conversation summary using Gemini.

    Args:
        formatted_messages: Formatted conversation transcript.

    Returns:
        Summary text or None on failure.
    """
    try:
        model = genai.GenerativeModel(config.gemini_model)

        prompt = SUMMARY_PROMPT.format(messages=formatted_messages)

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=config.gemini_temperature,
                max_output_tokens=config.gemini_max_tokens,
            ),
        )

        summary = response.text.strip()
        logger.debug(f"Generated summary: {len(summary)} characters")

        return summary

    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return None


async def _generate_episodic_memory(summary: str) -> str | None:
    """
    Generate episodic memory narrative from summary.

    Args:
        summary: Conversation summary.

    Returns:
        Episodic memory text or None on failure.
    """
    try:
        model = genai.GenerativeModel(config.gemini_model)

        prompt = EPISODIC_PROMPT.format(summary=summary)

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,  # Slightly more creative for narrative
                max_output_tokens=256,
            ),
        )

        episodic = response.text.strip()
        logger.debug(f"Generated episodic memory: {len(episodic)} characters")

        return episodic

    except Exception as e:
        logger.error(f"Episodic memory generation failed: {e}")
        return None


async def summarize_batch(
    ctx: dict[str, Any],
    conversation_ids: list[str],
    force: bool = False,
) -> dict[str, Any]:
    """
    Summarize multiple conversations.

    Args:
        ctx: ARQ context.
        conversation_ids: List of conversation UUIDs.
        force: If True, regenerate existing summaries.

    Returns:
        Aggregate result dict.
    """
    results = {
        "total": len(conversation_ids),
        "successful": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
    }

    for conversation_id in conversation_ids:
        result = await summarize_conversation(ctx, conversation_id, force)

        if result.get("success"):
            if result.get("skipped") or result.get("already_summarized"):
                results["skipped"] += 1
            else:
                results["successful"] += 1
        else:
            results["failed"] += 1
            results["errors"].append({
                "conversation_id": conversation_id,
                "error": result.get("error"),
            })

    logger.info(
        f"Batch summarization completed: "
        f"{results['successful']} successful, "
        f"{results['skipped']} skipped, "
        f"{results['failed']} failed"
    )

    return results


async def trigger_summary_for_idle_conversations(
    ctx: dict[str, Any],
    idle_minutes: int = 30,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Find and summarize conversations that have been idle.

    This is typically run on a schedule to catch conversations that
    weren't explicitly ended but should be summarized.

    Args:
        ctx: ARQ context.
        idle_minutes: How long a conversation must be idle to trigger summarization.
        limit: Maximum conversations to process.

    Returns:
        Result dict.
    """
    # Note: This would require a more complex Supabase query
    # Implementation depends on your schema having updated_at timestamps
    logger.info(f"Checking for idle conversations (>{idle_minutes} minutes)")

    # Placeholder - would need actual implementation based on schema
    return {
        "success": True,
        "conversations_processed": 0,
        "message": "Idle conversation check not fully implemented",
    }
