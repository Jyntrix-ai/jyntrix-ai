"""Entity graph traversal for knowledge graph search."""

import logging
from datetime import datetime
from typing import Any, List
from uuid import UUID

from supabase import Client as SupabaseClient

from src.models.entity import Entity, EntityGraph, EntityRelation, EntityType, RelationType

logger = logging.getLogger(__name__)


class GraphSearch:
    """Entity graph traversal and search.

    Provides methods for searching entities and traversing relationships
    in the knowledge graph.
    """

    def __init__(self, supabase: SupabaseClient):
        """Initialize graph search with Supabase client.

        Args:
            supabase: Configured Supabase client
        """
        self.supabase = supabase

    async def search_by_entities(
        self,
        user_id: str,
        entity_names: List[str],
        limit: int = 10,
    ) -> List[dict[str, Any]]:
        """Search memories related to mentioned entities.

        Args:
            user_id: User ID for isolation
            entity_names: List of entity names to search for
            limit: Maximum results

        Returns:
            List of related memory results
        """
        if not entity_names:
            return []

        try:
            # Find entities matching the names
            entities = await self._find_entities_by_name(user_id, entity_names)

            if not entities:
                return []

            # Get memories related to these entities
            entity_ids = [e["id"] for e in entities]
            related_memories = await self._get_memories_for_entities(
                user_id, entity_ids, limit
            )

            return related_memories

        except Exception as e:
            logger.error(f"Entity search error: {e}")
            return []

    async def get_entity_graph(
        self,
        user_id: str,
        entity_id: str,
        depth: int = 2,
    ) -> EntityGraph:
        """Get subgraph around an entity.

        Args:
            user_id: User ID for isolation
            entity_id: Center entity ID
            depth: Number of hops from center

        Returns:
            EntityGraph with entities and relations
        """
        visited_entities = set()
        visited_relations = set()
        entities = []
        relations = []

        await self._traverse_graph(
            user_id=user_id,
            entity_id=entity_id,
            depth=depth,
            current_depth=0,
            visited_entities=visited_entities,
            visited_relations=visited_relations,
            entities=entities,
            relations=relations,
        )

        return EntityGraph(
            entities=entities,
            relations=relations,
            center_entity_id=UUID(entity_id),
            depth=depth,
        )

    async def find_path(
        self,
        user_id: str,
        source_entity_id: str,
        target_entity_id: str,
        max_depth: int = 5,
    ) -> List[dict[str, Any]] | None:
        """Find path between two entities.

        Args:
            user_id: User ID for isolation
            source_entity_id: Starting entity
            target_entity_id: Target entity
            max_depth: Maximum path length

        Returns:
            List of entities and relations in path, or None if no path
        """
        if source_entity_id == target_entity_id:
            return []

        # BFS to find shortest path
        queue = [(source_entity_id, [])]
        visited = {source_entity_id}

        while queue:
            current_id, path = queue.pop(0)

            if len(path) >= max_depth:
                continue

            # Get related entities
            relations = await self._get_entity_relations(user_id, current_id)

            for relation in relations:
                next_id = (
                    relation["target_entity_id"]
                    if relation["source_entity_id"] == current_id
                    else relation["source_entity_id"]
                )

                if next_id == target_entity_id:
                    return path + [relation]

                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [relation]))

        return None

    async def search_entities(
        self,
        user_id: str,
        query: str,
        entity_types: List[EntityType] | None = None,
        limit: int = 10,
    ) -> List[dict[str, Any]]:
        """Search entities by name or description.

        Args:
            user_id: User ID for isolation
            query: Search query
            entity_types: Optional type filter
            limit: Maximum results

        Returns:
            List of matching entities with scores
        """
        try:
            # Build query - search in name, aliases, and description
            supabase_query = (
                self.supabase.table("entities")
                .select("*")
                .eq("user_id", user_id)
            )

            if entity_types:
                type_values = [t.value for t in entity_types]
                supabase_query = supabase_query.in_("entity_type", type_values)

            # Text search using ilike
            supabase_query = supabase_query.or_(
                f"name.ilike.%{query}%,description.ilike.%{query}%"
            )

            response = supabase_query.limit(limit).execute()

            results = []
            for entity in response.data or []:
                # Calculate simple relevance score
                name_match = query.lower() in entity["name"].lower()
                score = 1.0 if name_match else 0.5

                results.append({
                    "entity_id": entity["id"],
                    "name": entity["name"],
                    "entity_type": entity["entity_type"],
                    "description": entity.get("description"),
                    "score": score,
                    "match_type": "entity",
                    "mention_count": entity.get("mention_count", 1),
                })

            return results

        except Exception as e:
            logger.error(f"Entity search error: {e}")
            return []

    async def get_related_entities(
        self,
        user_id: str,
        entity_id: str,
        relation_types: List[RelationType] | None = None,
        limit: int = 20,
    ) -> List[dict[str, Any]]:
        """Get entities related to a given entity.

        Args:
            user_id: User ID for isolation
            entity_id: Source entity ID
            relation_types: Optional relation type filter
            limit: Maximum results

        Returns:
            List of related entities with relation info
        """
        try:
            # Get outgoing relations
            out_query = (
                self.supabase.table("entity_relations")
                .select("*, target:target_entity_id(*)")
                .eq("user_id", user_id)
                .eq("source_entity_id", entity_id)
            )

            if relation_types:
                type_values = [t.value for t in relation_types]
                out_query = out_query.in_("relation_type", type_values)

            out_response = out_query.limit(limit // 2).execute()

            # Get incoming relations
            in_query = (
                self.supabase.table("entity_relations")
                .select("*, source:source_entity_id(*)")
                .eq("user_id", user_id)
                .eq("target_entity_id", entity_id)
            )

            if relation_types:
                type_values = [t.value for t in relation_types]
                in_query = in_query.in_("relation_type", type_values)

            in_response = in_query.limit(limit // 2).execute()

            results = []

            # Process outgoing relations
            for rel in out_response.data or []:
                if rel.get("target"):
                    results.append({
                        "entity": rel["target"],
                        "relation_type": rel["relation_type"],
                        "direction": "outgoing",
                        "strength": rel.get("strength", 0.5),
                    })

            # Process incoming relations
            for rel in in_response.data or []:
                if rel.get("source"):
                    results.append({
                        "entity": rel["source"],
                        "relation_type": rel["relation_type"],
                        "direction": "incoming",
                        "strength": rel.get("strength", 0.5),
                    })

            return results

        except Exception as e:
            logger.error(f"Get related entities error: {e}")
            return []

    async def _find_entities_by_name(
        self,
        user_id: str,
        names: List[str],
    ) -> List[dict[str, Any]]:
        """Find entities by name or alias.

        Args:
            user_id: User ID
            names: Entity names to search

        Returns:
            List of matching entities
        """
        try:
            entities = []

            for name in names:
                response = (
                    self.supabase.table("entities")
                    .select("*")
                    .eq("user_id", user_id)
                    .ilike("name", f"%{name}%")
                    .limit(5)
                    .execute()
                )

                entities.extend(response.data or [])

            # Deduplicate by ID
            seen = set()
            unique_entities = []
            for e in entities:
                if e["id"] not in seen:
                    seen.add(e["id"])
                    unique_entities.append(e)

            return unique_entities

        except Exception as e:
            logger.error(f"Find entities by name error: {e}")
            return []

    async def _get_memories_for_entities(
        self,
        user_id: str,
        entity_ids: List[str],
        limit: int,
    ) -> List[dict[str, Any]]:
        """Get memories related to entities.

        Args:
            user_id: User ID
            entity_ids: List of entity IDs
            limit: Maximum results

        Returns:
            List of related memories
        """
        try:
            # Query memories that reference these entities
            # This assumes memories have a related_entities field or we check content
            response = (
                self.supabase.table("memories")
                .select("*")
                .eq("user_id", user_id)
                .limit(limit * 2)  # Get more to filter
                .execute()
            )

            results = []
            for memory in response.data or []:
                # Check if memory is related to any entity
                related = memory.get("related_entities", [])
                if any(eid in related for eid in entity_ids):
                    results.append({
                        "memory_id": memory["id"],
                        "content": memory["content"],
                        "memory_type": memory["memory_type"],
                        "keywords": memory.get("keywords", []),
                        "reliability": memory.get("reliability", 0.5),
                        "created_at": memory["created_at"],
                        "access_count": memory.get("access_count", 0),
                        "score": 0.8,  # Entity match score
                        "match_type": "entity",
                    })

            return results[:limit]

        except Exception as e:
            logger.error(f"Get memories for entities error: {e}")
            return []

    async def _get_entity_relations(
        self,
        user_id: str,
        entity_id: str,
    ) -> List[dict[str, Any]]:
        """Get all relations for an entity.

        Args:
            user_id: User ID
            entity_id: Entity ID

        Returns:
            List of relations
        """
        try:
            # Get both directions
            response = (
                self.supabase.table("entity_relations")
                .select("*")
                .eq("user_id", user_id)
                .or_(
                    f"source_entity_id.eq.{entity_id},target_entity_id.eq.{entity_id}"
                )
                .execute()
            )

            return response.data or []

        except Exception as e:
            logger.error(f"Get entity relations error: {e}")
            return []

    async def _traverse_graph(
        self,
        user_id: str,
        entity_id: str,
        depth: int,
        current_depth: int,
        visited_entities: set,
        visited_relations: set,
        entities: List[Entity],
        relations: List[EntityRelation],
    ) -> None:
        """Recursively traverse the graph.

        Args:
            user_id: User ID
            entity_id: Current entity ID
            depth: Target depth
            current_depth: Current traversal depth
            visited_entities: Set of visited entity IDs
            visited_relations: Set of visited relation IDs
            entities: Accumulator for entities
            relations: Accumulator for relations
        """
        if current_depth > depth or entity_id in visited_entities:
            return

        visited_entities.add(entity_id)

        try:
            # Get entity
            response = (
                self.supabase.table("entities")
                .select("*")
                .eq("id", entity_id)
                .eq("user_id", user_id)
                .single()
                .execute()
            )

            if response.data:
                entities.append(Entity(**response.data))

            # Get relations
            entity_relations = await self._get_entity_relations(user_id, entity_id)

            for rel in entity_relations:
                rel_id = rel["id"]
                if rel_id not in visited_relations:
                    visited_relations.add(rel_id)
                    relations.append(EntityRelation(**rel))

                    # Traverse to connected entity
                    next_id = (
                        rel["target_entity_id"]
                        if rel["source_entity_id"] == entity_id
                        else rel["source_entity_id"]
                    )

                    await self._traverse_graph(
                        user_id=user_id,
                        entity_id=next_id,
                        depth=depth,
                        current_depth=current_depth + 1,
                        visited_entities=visited_entities,
                        visited_relations=visited_relations,
                        entities=entities,
                        relations=relations,
                    )

        except Exception as e:
            logger.error(f"Graph traversal error at {entity_id}: {e}")

    async def create_entity(
        self,
        user_id: str,
        name: str,
        entity_type: EntityType,
        description: str | None = None,
        attributes: dict | None = None,
    ) -> dict[str, Any]:
        """Create a new entity.

        Args:
            user_id: User ID
            name: Entity name
            entity_type: Type of entity
            description: Optional description
            attributes: Optional attributes

        Returns:
            Created entity
        """
        from uuid import uuid4

        entity_data = {
            "id": str(uuid4()),
            "user_id": user_id,
            "name": name,
            "entity_type": entity_type.value,
            "description": description,
            "attributes": attributes or {},
            "mention_count": 1,
            "last_mentioned": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = self.supabase.table("entities").insert(entity_data).execute()

        return response.data[0] if response.data else entity_data

    async def create_relation(
        self,
        user_id: str,
        source_entity_id: str,
        target_entity_id: str,
        relation_type: RelationType,
        description: str | None = None,
        strength: float = 0.5,
    ) -> dict[str, Any]:
        """Create a relation between entities.

        Args:
            user_id: User ID
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID
            relation_type: Type of relation
            description: Optional description
            strength: Relation strength (0-1)

        Returns:
            Created relation
        """
        from uuid import uuid4

        relation_data = {
            "id": str(uuid4()),
            "user_id": user_id,
            "source_entity_id": source_entity_id,
            "target_entity_id": target_entity_id,
            "relation_type": relation_type.value,
            "description": description,
            "strength": strength,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = self.supabase.table("entity_relations").insert(relation_data).execute()

        return response.data[0] if response.data else relation_data
