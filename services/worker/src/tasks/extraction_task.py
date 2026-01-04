"""
Entity Extraction Task

Extracts entities and facts from messages using Gemini.
Creates entities, relations, and semantic memories from extracted information.
"""

import json
from typing import Any

import google.generativeai as genai

from src.config import config
from src.db.supabase import MemoryType, get_supabase_client
from src.utils.logger import TaskLogger, get_logger

logger = get_logger(__name__)

# Configure Gemini
genai.configure(api_key=config.google_ai_api_key.get_secret_value())

# Entity extraction prompt
EXTRACTION_PROMPT = """Analyze the following message and extract structured information.

MESSAGE:
{content}

CONTEXT (if available):
{context}

Extract the following information and return as JSON:

1. **entities**: List of named entities mentioned
   - name: The entity name
   - type: One of [person, organization, location, date, product, event, concept]
   - description: Brief description based on context

2. **facts**: List of factual statements that can be remembered
   - statement: The fact in a clear, standalone sentence
   - confidence: How confident (0.0-1.0) this is a reliable fact
   - entities_involved: Names of entities involved in this fact

3. **relations**: Relationships between entities
   - source: Source entity name
   - target: Target entity name
   - relation_type: Type of relationship (e.g., works_at, lives_in, knows, owns, created, etc.)
   - description: Brief description of the relationship

Return ONLY valid JSON in this exact format:
{{
  "entities": [
    {{"name": "...", "type": "...", "description": "..."}}
  ],
  "facts": [
    {{"statement": "...", "confidence": 0.9, "entities_involved": ["..."]}}
  ],
  "relations": [
    {{"source": "...", "target": "...", "relation_type": "...", "description": "..."}}
  ]
}}

If no entities, facts, or relations can be extracted, return empty arrays.
"""


async def extract_entities(
    ctx: dict[str, Any],
    message_id: str,
    context: str | None = None,
) -> dict[str, Any]:
    """
    Extract entities and facts from a message.

    This task:
    1. Fetches message from Supabase
    2. Extracts entities using Gemini (person, location, org, date, etc.)
    3. Extracts facts and relationships
    4. Stores entities in Supabase entities table
    5. Stores relations in entity_relations table
    6. Creates semantic memories from facts
    7. Enqueues embedding tasks for new memories

    Args:
        ctx: ARQ context containing Redis pool for enqueueing follow-up tasks.
        message_id: UUID of the message to process.
        context: Optional additional context for extraction.

    Returns:
        Result dict with extracted entities, facts, and relation counts.
    """
    supabase = get_supabase_client()

    with TaskLogger(logger, "extract_entities", task_id=message_id):
        try:
            # Step 1: Fetch message from Supabase
            message = await supabase.get_message(message_id)
            if not message:
                logger.error(f"Message {message_id} not found")
                return {
                    "success": False,
                    "message_id": message_id,
                    "error": "Message not found",
                }

            user_id = message.get("user_id")
            content = message.get("content")

            if not content:
                logger.warning(f"Message {message_id} has no content")
                return {
                    "success": True,
                    "message_id": message_id,
                    "entities_count": 0,
                    "facts_count": 0,
                    "relations_count": 0,
                }

            # Step 2: Extract using Gemini
            extraction = await _extract_with_gemini(content, context or "")

            if not extraction:
                logger.warning(f"No extraction results for message {message_id}")
                return {
                    "success": True,
                    "message_id": message_id,
                    "entities_count": 0,
                    "facts_count": 0,
                    "relations_count": 0,
                }

            # Step 3: Store entities
            entity_map: dict[str, str] = {}  # name -> entity_id
            entities = extraction.get("entities", [])

            for entity in entities:
                entity_record = await supabase.create_entity(
                    user_id=user_id,
                    name=entity["name"],
                    entity_type=entity["type"],
                    description=entity.get("description"),
                    metadata={"source_message_id": message_id},
                )
                if entity_record:
                    entity_map[entity["name"]] = entity_record["id"]

            logger.info(f"Created/updated {len(entity_map)} entities")

            # Step 4: Store relations
            relations = extraction.get("relations", [])
            relations_created = 0

            for relation in relations:
                source_name = relation.get("source")
                target_name = relation.get("target")

                # Get entity IDs (may need to look up if not in map)
                source_id = entity_map.get(source_name)
                target_id = entity_map.get(target_name)

                if source_id and target_id:
                    relation_record = await supabase.create_entity_relation(
                        user_id=user_id,
                        source_entity_id=source_id,
                        target_entity_id=target_id,
                        relation_type=relation["relation_type"],
                        description=relation.get("description"),
                        confidence=0.8,  # Default confidence for extracted relations
                        metadata={"source_message_id": message_id},
                    )
                    if relation_record:
                        relations_created += 1
                else:
                    logger.warning(
                        f"Could not find entities for relation: {source_name} -> {target_name}"
                    )

            logger.info(f"Created {relations_created} entity relations")

            # Step 5: Create semantic memories from facts
            facts = extraction.get("facts", [])
            memory_ids: list[str] = []

            for fact in facts:
                statement = fact.get("statement")
                confidence = fact.get("confidence", 0.8)

                if statement and confidence >= 0.7:  # Only store confident facts
                    memory = await supabase.create_memory(
                        user_id=user_id,
                        content=statement,
                        memory_type=MemoryType.SEMANTIC,
                        source_type="extraction",
                        source_id=message_id,
                        metadata={
                            "confidence": confidence,
                            "entities_involved": fact.get("entities_involved", []),
                            "source_message_id": message_id,
                        },
                    )
                    if memory:
                        memory_ids.append(memory["id"])

            logger.info(f"Created {len(memory_ids)} semantic memories from facts")

            # Step 6: Enqueue embedding tasks for new memories
            redis_pool = ctx.get("redis")
            if redis_pool and memory_ids:
                from arq import create_pool

                for memory_id in memory_ids:
                    await redis_pool.enqueue_job(
                        "generate_embedding",
                        memory_id,
                    )
                logger.info(f"Enqueued {len(memory_ids)} embedding tasks")

            return {
                "success": True,
                "message_id": message_id,
                "user_id": user_id,
                "entities_count": len(entity_map),
                "facts_count": len(facts),
                "relations_count": relations_created,
                "memories_created": len(memory_ids),
            }

        except Exception as e:
            logger.exception(f"Entity extraction failed for message {message_id}: {e}")
            return {
                "success": False,
                "message_id": message_id,
                "error": str(e),
            }


async def _extract_with_gemini(
    content: str,
    context: str,
) -> dict[str, Any] | None:
    """
    Use Gemini to extract entities, facts, and relations.

    Args:
        content: The message content to analyze.
        context: Additional context for extraction.

    Returns:
        Extracted data dict or None on failure.
    """
    try:
        model = genai.GenerativeModel(config.gemini_model)

        prompt = EXTRACTION_PROMPT.format(
            content=content,
            context=context or "No additional context provided.",
        )

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=config.gemini_temperature,
                max_output_tokens=config.gemini_max_tokens,
            ),
        )

        # Parse JSON response
        response_text = response.text.strip()

        # Handle potential markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        extraction = json.loads(response_text.strip())

        logger.debug(
            f"Gemini extraction: {len(extraction.get('entities', []))} entities, "
            f"{len(extraction.get('facts', []))} facts, "
            f"{len(extraction.get('relations', []))} relations"
        )

        return extraction

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Gemini extraction failed: {e}")
        return None


async def extract_entities_batch(
    ctx: dict[str, Any],
    message_ids: list[str],
) -> dict[str, Any]:
    """
    Extract entities from multiple messages.

    Args:
        ctx: ARQ context.
        message_ids: List of message UUIDs to process.

    Returns:
        Aggregate result dict.
    """
    results = {
        "total": len(message_ids),
        "successful": 0,
        "failed": 0,
        "total_entities": 0,
        "total_facts": 0,
        "total_relations": 0,
        "errors": [],
    }

    for message_id in message_ids:
        result = await extract_entities(ctx, message_id)

        if result.get("success"):
            results["successful"] += 1
            results["total_entities"] += result.get("entities_count", 0)
            results["total_facts"] += result.get("facts_count", 0)
            results["total_relations"] += result.get("relations_count", 0)
        else:
            results["failed"] += 1
            results["errors"].append({
                "message_id": message_id,
                "error": result.get("error"),
            })

    logger.info(
        f"Batch extraction completed: {results['successful']}/{results['total']} successful"
    )
    return results
