"""Entity and relationship models for knowledge graph."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Types of entities in the knowledge graph."""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    PROJECT = "project"
    CONCEPT = "concept"
    EVENT = "event"
    PRODUCT = "product"
    SKILL = "skill"
    INTEREST = "interest"
    GOAL = "goal"
    OTHER = "other"


class RelationType(str, Enum):
    """Types of relationships between entities."""

    # Personal relationships
    KNOWS = "knows"
    FRIEND_OF = "friend_of"
    FAMILY_OF = "family_of"
    COLLEAGUE_OF = "colleague_of"
    WORKS_WITH = "works_with"

    # Organizational relationships
    WORKS_AT = "works_at"
    MEMBER_OF = "member_of"
    LEADS = "leads"
    REPORTS_TO = "reports_to"

    # Locational relationships
    LOCATED_IN = "located_in"
    LIVES_IN = "lives_in"
    VISITED = "visited"

    # Project/Work relationships
    WORKS_ON = "works_on"
    CREATED = "created"
    OWNS = "owns"
    CONTRIBUTES_TO = "contributes_to"

    # Conceptual relationships
    INTERESTED_IN = "interested_in"
    SKILLED_IN = "skilled_in"
    STUDIED = "studied"
    RELATED_TO = "related_to"

    # Event relationships
    ATTENDED = "attended"
    PARTICIPATED_IN = "participated_in"

    # General
    ASSOCIATED_WITH = "associated_with"


class Entity(BaseModel):
    """Entity in the knowledge graph."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str = Field(..., description="Owner user ID")
    name: str = Field(..., description="Entity name")
    entity_type: EntityType = Field(..., description="Type of entity")
    description: str | None = Field(default=None, description="Entity description")
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternative names for this entity"
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Entity-specific attributes"
    )
    embedding: list[float] | None = Field(
        default=None,
        description="Vector embedding for similarity search"
    )
    mention_count: int = Field(
        default=1,
        description="Number of times this entity has been mentioned"
    )
    last_mentioned: datetime = Field(default_factory=datetime.utcnow)
    source_memories: list[UUID] = Field(
        default_factory=list,
        description="Memory IDs where this entity was mentioned"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        from_attributes = True

    def merge_with(self, other: "Entity") -> None:
        """Merge another entity into this one (for deduplication)."""
        # Add aliases
        for alias in other.aliases:
            if alias not in self.aliases and alias != self.name:
                self.aliases.append(alias)

        # Add the other entity's name as an alias if different
        if other.name != self.name and other.name not in self.aliases:
            self.aliases.append(other.name)

        # Merge attributes (prefer existing values)
        for key, value in other.attributes.items():
            if key not in self.attributes:
                self.attributes[key] = value

        # Update counts
        self.mention_count += other.mention_count

        # Add source memories
        for memory_id in other.source_memories:
            if memory_id not in self.source_memories:
                self.source_memories.append(memory_id)

        self.updated_at = datetime.utcnow()


class EntityRelation(BaseModel):
    """Relationship between two entities."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str = Field(..., description="Owner user ID")
    source_entity_id: UUID = Field(..., description="Source entity ID")
    target_entity_id: UUID = Field(..., description="Target entity ID")
    relation_type: RelationType = Field(..., description="Type of relationship")
    description: str | None = Field(
        default=None,
        description="Additional context about the relationship"
    )
    strength: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Relationship strength/confidence"
    )
    bidirectional: bool = Field(
        default=False,
        description="Whether relationship goes both ways"
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Relationship-specific attributes"
    )
    source_memories: list[UUID] = Field(
        default_factory=list,
        description="Memory IDs where this relationship was mentioned"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class EntityGraph(BaseModel):
    """Subgraph of entities and their relationships."""

    entities: list[Entity] = Field(default_factory=list)
    relations: list[EntityRelation] = Field(default_factory=list)
    center_entity_id: UUID | None = Field(
        default=None,
        description="The entity this graph is centered around"
    )
    depth: int = Field(
        default=1,
        description="How many hops from center entity"
    )

    def to_context_string(self) -> str:
        """Convert graph to string context for LLM."""
        if not self.entities:
            return ""

        lines = []
        entity_map = {e.id: e for e in self.entities}

        for entity in self.entities:
            entity_str = f"- {entity.name} ({entity.entity_type.value})"
            if entity.description:
                entity_str += f": {entity.description}"
            lines.append(entity_str)

        if self.relations:
            lines.append("\nRelationships:")
            for rel in self.relations:
                source = entity_map.get(rel.source_entity_id)
                target = entity_map.get(rel.target_entity_id)
                if source and target:
                    lines.append(
                        f"  - {source.name} --[{rel.relation_type.value}]--> {target.name}"
                    )

        return "\n".join(lines)


class EntitySearchResult(BaseModel):
    """Result from entity search."""

    entity: Entity
    score: float = Field(..., description="Relevance score")
    match_type: str = Field(
        default="name",
        description="How the entity was matched: name, alias, description, embedding"
    )
    related_entities: list[Entity] = Field(
        default_factory=list,
        description="Directly related entities"
    )
