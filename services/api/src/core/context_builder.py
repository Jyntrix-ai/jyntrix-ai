"""Context builder with token budget management.

Token Budget (8K total):
- Profile memories: 1000 tokens
- Semantic memories: 2500 tokens
- Episodic memories: 2500 tokens
- Procedural memories: 1000 tokens
- Entity context: 500 tokens
- Conversation history: 500 tokens
"""

import logging
from typing import Any, List

from src.config import settings
from src.models.memory import (
    EpisodicMemory,
    Memory,
    MemoryContext,
    MemoryType,
    ProceduralMemory,
    ProfileMemory,
    SemanticMemory,
)
from src.utils.token_counter import TokenCounter

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Build memory context within token budget.

    Assembles relevant memories into a structured context
    while respecting token limits for each memory type.
    """

    def __init__(
        self,
        max_tokens: int | None = None,
        profile_tokens: int | None = None,
        semantic_tokens: int | None = None,
        episodic_tokens: int | None = None,
        procedural_tokens: int | None = None,
        entity_tokens: int | None = None,
        history_tokens: int | None = None,
    ):
        """Initialize context builder with token budgets.

        Args:
            max_tokens: Maximum total tokens (default from settings)
            profile_tokens: Budget for profile memories
            semantic_tokens: Budget for semantic memories
            episodic_tokens: Budget for episodic memories
            procedural_tokens: Budget for procedural memories
            entity_tokens: Budget for entity context
            history_tokens: Budget for conversation history
        """
        self.max_tokens = max_tokens or settings.max_context_tokens
        self.profile_tokens = profile_tokens or settings.profile_memory_tokens
        self.semantic_tokens = semantic_tokens or settings.semantic_memory_tokens
        self.episodic_tokens = episodic_tokens or settings.episodic_memory_tokens
        self.procedural_tokens = procedural_tokens or settings.procedural_memory_tokens
        self.entity_tokens = entity_tokens or settings.entity_memory_tokens
        self.history_tokens = history_tokens or settings.conversation_history_tokens

        self.token_counter = TokenCounter()

    async def build(
        self,
        memories: List[dict[str, Any]],
        max_tokens: int | None = None,
        entity_context: str | None = None,
    ) -> MemoryContext:
        """Build memory context from ranked results.

        Args:
            memories: List of ranked memory results
            max_tokens: Override maximum tokens
            entity_context: Pre-built entity context string

        Returns:
            MemoryContext with categorized memories
        """
        max_tokens = max_tokens or self.max_tokens

        # Categorize memories by type
        categorized = self._categorize_memories(memories)

        # Build each section within budget
        profile_memories = await self._build_profile_section(
            categorized.get("profile", []),
            self.profile_tokens,
        )

        semantic_memories = await self._build_semantic_section(
            categorized.get("semantic", []),
            self.semantic_tokens,
        )

        episodic_memories = await self._build_episodic_section(
            categorized.get("episodic", []),
            self.episodic_tokens,
        )

        procedural_memories = await self._build_procedural_section(
            categorized.get("procedural", []),
            self.procedural_tokens,
        )

        # Truncate entity context if needed
        if entity_context:
            entity_context = self._truncate_to_tokens(
                entity_context,
                self.entity_tokens,
            )

        # Calculate total tokens
        total_tokens = self._calculate_total_tokens(
            profile_memories,
            semantic_memories,
            episodic_memories,
            procedural_memories,
            entity_context,
        )

        truncated = total_tokens > max_tokens

        return MemoryContext(
            profile_memories=profile_memories,
            semantic_memories=semantic_memories,
            episodic_memories=episodic_memories,
            procedural_memories=procedural_memories,
            entity_context=entity_context,
            total_tokens=min(total_tokens, max_tokens),
            truncated=truncated,
        )

    def _categorize_memories(
        self,
        memories: List[dict[str, Any]],
    ) -> dict[str, List[dict[str, Any]]]:
        """Categorize memories by type.

        Args:
            memories: List of memory results

        Returns:
            Dict mapping type to list of memories
        """
        categorized: dict[str, List[dict[str, Any]]] = {
            "profile": [],
            "semantic": [],
            "episodic": [],
            "procedural": [],
        }

        for memory in memories:
            memory_type = memory.get("memory_type", "semantic")
            if memory_type in categorized:
                categorized[memory_type].append(memory)

        return categorized

    async def _build_profile_section(
        self,
        memories: List[dict[str, Any]],
        token_budget: int,
    ) -> List[ProfileMemory]:
        """Build profile memories section.

        Args:
            memories: Profile memory results
            token_budget: Token budget for this section

        Returns:
            List of ProfileMemory objects within budget
        """
        result = []
        current_tokens = 0

        for mem in memories:
            content = mem.get("content", "")
            tokens = self.token_counter.count(content)

            if current_tokens + tokens > token_budget:
                break

            # Convert to ProfileMemory
            profile_mem = ProfileMemory(
                id=mem.get("memory_id"),
                user_id=mem.get("user_id", ""),
                content=content,
                category=mem.get("category", "general"),
                attribute=mem.get("attribute", "info"),
                value=mem.get("value", content),
                keywords=mem.get("keywords", []),
                reliability=mem.get("reliability", 0.5),
            )

            result.append(profile_mem)
            current_tokens += tokens

        return result

    async def _build_semantic_section(
        self,
        memories: List[dict[str, Any]],
        token_budget: int,
    ) -> List[SemanticMemory]:
        """Build semantic memories section.

        Args:
            memories: Semantic memory results
            token_budget: Token budget for this section

        Returns:
            List of SemanticMemory objects within budget
        """
        result = []
        current_tokens = 0

        for mem in memories:
            content = mem.get("content", "")
            tokens = self.token_counter.count(content)

            if current_tokens + tokens > token_budget:
                break

            semantic_mem = SemanticMemory(
                id=mem.get("memory_id"),
                user_id=mem.get("user_id", ""),
                content=content,
                topic=mem.get("topic", "general"),
                fact=mem.get("fact", content),
                keywords=mem.get("keywords", []),
                reliability=mem.get("reliability", 0.5),
            )

            result.append(semantic_mem)
            current_tokens += tokens

        return result

    async def _build_episodic_section(
        self,
        memories: List[dict[str, Any]],
        token_budget: int,
    ) -> List[EpisodicMemory]:
        """Build episodic memories section.

        Args:
            memories: Episodic memory results
            token_budget: Token budget for this section

        Returns:
            List of EpisodicMemory objects within budget
        """
        result = []
        current_tokens = 0

        for mem in memories:
            content = mem.get("content", "")
            tokens = self.token_counter.count(content)

            if current_tokens + tokens > token_budget:
                break

            from uuid import uuid4
            episodic_mem = EpisodicMemory(
                id=mem.get("memory_id"),
                user_id=mem.get("user_id", ""),
                content=content,
                conversation_id=mem.get("conversation_id") or uuid4(),
                event_type=mem.get("event_type", "conversation"),
                summary=mem.get("summary", content[:200]),
                keywords=mem.get("keywords", []),
                reliability=mem.get("reliability", 0.5),
            )

            result.append(episodic_mem)
            current_tokens += tokens

        return result

    async def _build_procedural_section(
        self,
        memories: List[dict[str, Any]],
        token_budget: int,
    ) -> List[ProceduralMemory]:
        """Build procedural memories section.

        Args:
            memories: Procedural memory results
            token_budget: Token budget for this section

        Returns:
            List of ProceduralMemory objects within budget
        """
        result = []
        current_tokens = 0

        for mem in memories:
            content = mem.get("content", "")
            tokens = self.token_counter.count(content)

            if current_tokens + tokens > token_budget:
                break

            procedural_mem = ProceduralMemory(
                id=mem.get("memory_id"),
                user_id=mem.get("user_id", ""),
                content=content,
                procedure_name=mem.get("procedure_name", "unnamed"),
                trigger=mem.get("trigger", "user request"),
                steps=mem.get("steps", [content]),
                keywords=mem.get("keywords", []),
                reliability=mem.get("reliability", 0.5),
            )

            result.append(procedural_mem)
            current_tokens += tokens

        return result

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token budget.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens

        Returns:
            Truncated text
        """
        if not text:
            return ""

        tokens = self.token_counter.count(text)

        if tokens <= max_tokens:
            return text

        # Binary search for truncation point
        words = text.split()
        low, high = 0, len(words)

        while low < high:
            mid = (low + high + 1) // 2
            truncated = " ".join(words[:mid])
            if self.token_counter.count(truncated) <= max_tokens:
                low = mid
            else:
                high = mid - 1

        return " ".join(words[:low]) + "..."

    def _calculate_total_tokens(
        self,
        profile_memories: List[ProfileMemory],
        semantic_memories: List[SemanticMemory],
        episodic_memories: List[EpisodicMemory],
        procedural_memories: List[ProceduralMemory],
        entity_context: str | None,
    ) -> int:
        """Calculate total tokens in context.

        Args:
            profile_memories: Profile memories
            semantic_memories: Semantic memories
            episodic_memories: Episodic memories
            procedural_memories: Procedural memories
            entity_context: Entity context string

        Returns:
            Total token count
        """
        total = 0

        for mem in profile_memories:
            total += self.token_counter.count(mem.content)

        for mem in semantic_memories:
            total += self.token_counter.count(mem.content)

        for mem in episodic_memories:
            total += self.token_counter.count(mem.content)

        for mem in procedural_memories:
            total += self.token_counter.count(mem.content)

        if entity_context:
            total += self.token_counter.count(entity_context)

        return total

    def format_for_prompt(self, context: MemoryContext) -> str:
        """Format memory context for LLM prompt.

        Args:
            context: MemoryContext to format

        Returns:
            Formatted string for prompt
        """
        sections = []

        if context.profile_memories:
            profile_lines = ["## User Profile"]
            for mem in context.profile_memories:
                profile_lines.append(f"- {mem.category}/{mem.attribute}: {mem.value}")
            sections.append("\n".join(profile_lines))

        if context.semantic_memories:
            semantic_lines = ["## Known Facts"]
            for mem in context.semantic_memories:
                semantic_lines.append(f"- [{mem.topic}] {mem.fact}")
            sections.append("\n".join(semantic_lines))

        if context.episodic_memories:
            episodic_lines = ["## Recent Interactions"]
            for mem in context.episodic_memories:
                date_str = mem.timestamp.strftime("%Y-%m-%d") if hasattr(mem, 'timestamp') else "recently"
                episodic_lines.append(f"- {date_str}: {mem.summary}")
            sections.append("\n".join(episodic_lines))

        if context.procedural_memories:
            procedural_lines = ["## Learned Procedures"]
            for mem in context.procedural_memories:
                procedural_lines.append(f"- {mem.procedure_name}: {mem.trigger}")
            sections.append("\n".join(procedural_lines))

        if context.entity_context:
            sections.append(f"## Entity Context\n{context.entity_context}")

        return "\n\n".join(sections)


class AdaptiveContextBuilder(ContextBuilder):
    """Context builder that adapts budgets based on available content."""

    async def build(
        self,
        memories: List[dict[str, Any]],
        max_tokens: int | None = None,
        entity_context: str | None = None,
    ) -> MemoryContext:
        """Build with adaptive token allocation.

        Redistributes unused budget from sparse categories
        to categories with more content.

        Args:
            memories: List of memory results
            max_tokens: Maximum tokens
            entity_context: Entity context

        Returns:
            Optimally allocated MemoryContext
        """
        max_tokens = max_tokens or self.max_tokens

        # Categorize memories
        categorized = self._categorize_memories(memories)

        # Calculate content per category
        category_sizes = {}
        for cat, mems in categorized.items():
            size = sum(self.token_counter.count(m.get("content", "")) for m in mems)
            category_sizes[cat] = size

        # Reallocate budget from sparse to full categories
        budgets = self._reallocate_budgets(category_sizes, max_tokens)

        # Build with adapted budgets
        profile_memories = await self._build_profile_section(
            categorized.get("profile", []),
            budgets["profile"],
        )

        semantic_memories = await self._build_semantic_section(
            categorized.get("semantic", []),
            budgets["semantic"],
        )

        episodic_memories = await self._build_episodic_section(
            categorized.get("episodic", []),
            budgets["episodic"],
        )

        procedural_memories = await self._build_procedural_section(
            categorized.get("procedural", []),
            budgets["procedural"],
        )

        if entity_context:
            entity_context = self._truncate_to_tokens(
                entity_context,
                budgets.get("entity", self.entity_tokens),
            )

        total_tokens = self._calculate_total_tokens(
            profile_memories,
            semantic_memories,
            episodic_memories,
            procedural_memories,
            entity_context,
        )

        return MemoryContext(
            profile_memories=profile_memories,
            semantic_memories=semantic_memories,
            episodic_memories=episodic_memories,
            procedural_memories=procedural_memories,
            entity_context=entity_context,
            total_tokens=total_tokens,
            truncated=total_tokens > max_tokens,
        )

    def _reallocate_budgets(
        self,
        category_sizes: dict[str, int],
        max_tokens: int,
    ) -> dict[str, int]:
        """Reallocate token budgets based on content.

        Args:
            category_sizes: Tokens needed per category
            max_tokens: Total budget

        Returns:
            Adjusted budgets per category
        """
        base_budgets = {
            "profile": self.profile_tokens,
            "semantic": self.semantic_tokens,
            "episodic": self.episodic_tokens,
            "procedural": self.procedural_tokens,
            "entity": self.entity_tokens,
        }

        # Find unused budget
        unused = 0
        need_more = []

        for cat, base in base_budgets.items():
            if cat in category_sizes:
                if category_sizes[cat] < base:
                    unused += base - category_sizes[cat]
                elif category_sizes[cat] > base:
                    need_more.append(cat)

        # Distribute unused to categories that need more
        if unused > 0 and need_more:
            extra_each = unused // len(need_more)
            for cat in need_more:
                base_budgets[cat] += extra_each

        return base_budgets
