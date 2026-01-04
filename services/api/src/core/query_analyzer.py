"""Query analyzer for intent detection and keyword extraction."""

import logging
import re
from typing import List

from src.models.chat import QueryAnalysis

logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """Analyze user queries for intent, keywords, and entities.

    Performs lightweight NLP to understand query characteristics
    and determine optimal retrieval strategy.
    """

    def __init__(self):
        """Initialize query analyzer."""
        # Intent patterns
        self.recall_patterns = [
            r'\b(remember|recall|told|said|mentioned|discussed|talked about)\b',
            r'\b(last time|before|previously|earlier|when did)\b',
            r'\b(what was|what were|what did)\b',
            r'\b(my|our) (favorite|preference|choice)\b',
        ]

        self.question_patterns = [
            r'^(what|who|where|when|why|how|which|can|could|would|should|is|are|do|does)\b',
            r'\?$',
            r'\b(explain|describe|tell me about|define)\b',
        ]

        self.command_patterns = [
            r'^(create|make|build|write|generate|add|update|delete|remove)\b',
            r'^(set|configure|change|modify|fix|solve|help)\b',
            r'^(please|can you|could you|would you)\s+(create|make|write|help)\b',
        ]

        # Time reference patterns
        self.time_patterns = [
            (r'\b(today|now|currently)\b', 'present'),
            (r'\b(yesterday|last night)\b', 'recent'),
            (r'\b(last week|past week)\b', 'week'),
            (r'\b(last month|past month)\b', 'month'),
            (r'\b(last year|past year)\b', 'year'),
            (r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b', 'specific_date'),
            (r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b', 'month_name'),
        ]

        # Stopwords for keyword extraction
        self.stopwords = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'were', 'will', 'with', 'this', 'they', 'their',
            'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why',
            'would', 'could', 'should', 'have', 'has', 'had', 'been', 'being',
            'can', 'do', 'does', 'did', 'done', 'i', 'me', 'my', 'myself',
            'we', 'our', 'ours', 'you', 'your', 'yours', 'he', 'him', 'his',
            'she', 'her', 'hers', 'it', 'its', 'them', 'theirs', 'please',
            'thanks', 'thank', 'hello', 'hi', 'hey',
        }

        # Common entity prefixes/patterns
        self.entity_patterns = [
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # Proper names (First Last)
            r'\b([A-Z][a-z]+\'s)\b',  # Possessive names
            r'\b(Mr\.|Mrs\.|Ms\.|Dr\.) ([A-Z][a-z]+)\b',  # Titles
            r'\b(@\w+)\b',  # Handles
            r'\b([A-Z][A-Z]+)\b',  # Acronyms
        ]

    async def analyze(self, query: str) -> QueryAnalysis:
        """Analyze a user query.

        Args:
            query: User's query text

        Returns:
            QueryAnalysis with intent, keywords, entities, etc.
        """
        query_lower = query.lower().strip()

        # Detect intent
        intent = self._detect_intent(query_lower)

        # Extract keywords
        keywords = self._extract_keywords(query)

        # Extract topics (noun phrases)
        topics = self._extract_topics(query)

        # Detect entities
        entities = self._detect_entities(query)

        # Detect time references
        time_reference = self._detect_time_reference(query_lower)

        # Determine if memory is needed
        requires_memory = self._requires_memory(intent, query_lower)

        # Determine memory types to search
        memory_types = self._determine_memory_types(intent, query_lower)

        # Calculate confidence
        confidence = self._calculate_confidence(intent, keywords, query_lower)

        return QueryAnalysis(
            original_query=query,
            intent=intent,
            topics=topics,
            keywords=keywords,
            entities_mentioned=entities,
            time_reference=time_reference,
            requires_memory=requires_memory,
            memory_types_needed=memory_types,
            confidence=confidence,
        )

    def _detect_intent(self, query: str) -> str:
        """Detect the intent of the query.

        Args:
            query: Lowercase query text

        Returns:
            Intent string: recall, question, command, or conversation
        """
        # Check for recall intent
        for pattern in self.recall_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return "recall"

        # Check for command intent
        for pattern in self.command_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return "command"

        # Check for question intent
        for pattern in self.question_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return "question"

        # Default to conversation
        return "conversation"

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query.

        Args:
            query: Original query text

        Returns:
            List of keywords
        """
        # Tokenize
        words = re.findall(r'\b\w+\b', query.lower())

        # Filter stopwords and short words
        keywords = [
            w for w in words
            if w not in self.stopwords and len(w) > 2
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique_keywords.append(k)

        return unique_keywords[:15]  # Limit to 15 keywords

    def _extract_topics(self, query: str) -> List[str]:
        """Extract topics/noun phrases from query.

        Args:
            query: Original query text

        Returns:
            List of topics
        """
        # Simple noun phrase extraction using patterns
        topics = []

        # Match quoted phrases
        quoted = re.findall(r'"([^"]+)"', query)
        topics.extend(quoted)

        # Match "about X" patterns
        about_matches = re.findall(r'\babout\s+(\w+(?:\s+\w+)?)\b', query, re.IGNORECASE)
        topics.extend(about_matches)

        # Match "regarding X" patterns
        regarding_matches = re.findall(r'\bregarding\s+(\w+(?:\s+\w+)?)\b', query, re.IGNORECASE)
        topics.extend(regarding_matches)

        # Clean and deduplicate
        topics = list(set(t.strip().lower() for t in topics if len(t) > 2))

        return topics[:10]

    def _detect_entities(self, query: str) -> List[str]:
        """Detect named entities in query.

        Args:
            query: Original query text

        Returns:
            List of entity names
        """
        entities = []

        for pattern in self.entity_patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                if isinstance(match, tuple):
                    entity = " ".join(match).strip()
                else:
                    entity = match.strip()

                if len(entity) > 1:
                    entities.append(entity)

        # Deduplicate
        return list(set(entities))[:10]

    def _detect_time_reference(self, query: str) -> str | None:
        """Detect time references in query.

        Args:
            query: Lowercase query text

        Returns:
            Time reference type or None
        """
        for pattern, time_type in self.time_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return time_type

        return None

    def _requires_memory(self, intent: str, query: str) -> bool:
        """Determine if query requires memory retrieval.

        Args:
            intent: Detected intent
            query: Lowercase query

        Returns:
            True if memory is needed
        """
        # Recall always needs memory
        if intent == "recall":
            return True

        # Commands usually don't need memory (unless personalized)
        if intent == "command":
            # Check for personalization hints
            personal_hints = ['my', 'prefer', 'usual', 'always', 'like']
            return any(h in query for h in personal_hints)

        # Questions often need memory
        if intent == "question":
            # Factual questions about the user need memory
            personal_hints = ['my', 'i', 'me', 'we', 'our']
            return any(h in query.split() for h in personal_hints)

        # Conversation benefits from memory for personalization
        return True

    def _determine_memory_types(self, intent: str, query: str) -> List[str]:
        """Determine which memory types to search.

        Args:
            intent: Detected intent
            query: Lowercase query

        Returns:
            List of memory type strings
        """
        memory_types = []

        if intent == "recall":
            # Search all for recall
            memory_types = ["profile", "semantic", "episodic", "procedural"]

        elif intent == "question":
            # Questions usually need semantic and profile
            memory_types = ["semantic", "profile"]
            if "how" in query or "process" in query or "step" in query:
                memory_types.append("procedural")

        elif intent == "command":
            # Commands might need procedural
            memory_types = ["procedural", "profile"]

        else:
            # Conversation - recent context and profile
            memory_types = ["episodic", "semantic", "profile"]

        return memory_types

    def _calculate_confidence(
        self,
        intent: str,
        keywords: List[str],
        query: str,
    ) -> float:
        """Calculate confidence in the analysis.

        Args:
            intent: Detected intent
            keywords: Extracted keywords
            query: Lowercase query

        Returns:
            Confidence score (0-1)
        """
        confidence = 0.5

        # More keywords = higher confidence
        if len(keywords) >= 3:
            confidence += 0.1
        if len(keywords) >= 5:
            confidence += 0.1

        # Clear intent patterns = higher confidence
        if intent == "recall":
            confidence += 0.2
        elif intent == "question":
            confidence += 0.15
        elif intent == "command":
            confidence += 0.15

        # Query length affects confidence
        words = len(query.split())
        if 5 <= words <= 30:
            confidence += 0.1
        elif words > 30:
            confidence -= 0.1

        return min(1.0, max(0.0, confidence))


class LLMQueryAnalyzer(QueryAnalyzer):
    """Query analyzer that can use LLM for complex analysis."""

    def __init__(self, llm_client=None):
        """Initialize with optional LLM client.

        Args:
            llm_client: Optional LLM client for enhanced analysis
        """
        super().__init__()
        self.llm_client = llm_client

    async def analyze_with_llm(self, query: str) -> QueryAnalysis:
        """Analyze query using LLM for complex cases.

        Args:
            query: User query

        Returns:
            Enhanced QueryAnalysis
        """
        # First do rule-based analysis
        base_analysis = await self.analyze(query)

        # If confidence is low and LLM available, enhance with LLM
        if base_analysis.confidence < 0.6 and self.llm_client:
            try:
                enhanced = await self._llm_enhance(query, base_analysis)
                return enhanced
            except Exception as e:
                logger.warning(f"LLM enhancement failed: {e}")
                return base_analysis

        return base_analysis

    async def _llm_enhance(
        self,
        query: str,
        base_analysis: QueryAnalysis,
    ) -> QueryAnalysis:
        """Enhance analysis using LLM.

        Args:
            query: Original query
            base_analysis: Rule-based analysis

        Returns:
            Enhanced analysis
        """
        # This would call the LLM for entity extraction, intent clarification, etc.
        # For now, return base analysis
        return base_analysis
