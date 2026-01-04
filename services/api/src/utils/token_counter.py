"""Token counting utilities."""

import logging
from functools import lru_cache
from typing import List

logger = logging.getLogger(__name__)


class TokenCounter:
    """Token counter using tiktoken for accurate counts.

    Falls back to character-based estimation if tiktoken is unavailable.
    """

    def __init__(self, model: str = "gpt-4"):
        """Initialize token counter.

        Args:
            model: Model name for tokenizer selection
        """
        self.model = model
        self._encoder = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy load the tokenizer."""
        if self._initialized:
            return

        try:
            import tiktoken

            # Try to get encoding for the model
            try:
                self._encoder = tiktoken.encoding_for_model(self.model)
            except KeyError:
                # Fall back to cl100k_base for unknown models
                self._encoder = tiktoken.get_encoding("cl100k_base")

            self._initialized = True
            logger.debug(f"Token counter initialized with tiktoken")

        except ImportError:
            logger.warning("tiktoken not available, using estimation")
            self._initialized = True

    def count(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Token count
        """
        if not text:
            return 0

        self._ensure_initialized()

        if self._encoder:
            try:
                return len(self._encoder.encode(text))
            except Exception as e:
                logger.warning(f"Token encoding error, using estimate: {e}")

        # Fallback: rough estimation (4 chars per token on average)
        return len(text) // 4

    def count_messages(self, messages: List[dict]) -> int:
        """Count tokens in a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Total token count including message overhead
        """
        self._ensure_initialized()

        total = 0

        for message in messages:
            # Message overhead (role, formatting)
            total += 4  # Approximate overhead per message

            if isinstance(message, dict):
                content = message.get("content", "")
                role = message.get("role", "")
                total += self.count(content)
                total += self.count(role)
            elif isinstance(message, str):
                total += self.count(message)

        # Final formatting overhead
        total += 2

        return total

    def truncate_to_tokens(
        self,
        text: str,
        max_tokens: int,
        add_ellipsis: bool = True,
    ) -> str:
        """Truncate text to fit within token limit.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
            add_ellipsis: Whether to add "..." at end

        Returns:
            Truncated text
        """
        if not text:
            return ""

        current_tokens = self.count(text)

        if current_tokens <= max_tokens:
            return text

        self._ensure_initialized()

        if self._encoder:
            # Precise truncation using tokenizer
            tokens = self._encoder.encode(text)
            ellipsis_tokens = 1 if add_ellipsis else 0
            truncated_tokens = tokens[:max_tokens - ellipsis_tokens]
            truncated = self._encoder.decode(truncated_tokens)

            if add_ellipsis:
                truncated += "..."

            return truncated

        # Fallback: character-based truncation
        # Estimate chars from tokens (4 chars per token)
        max_chars = max_tokens * 4
        if add_ellipsis:
            max_chars -= 3

        truncated = text[:max_chars]

        # Try to break at word boundary
        if " " in truncated:
            truncated = truncated.rsplit(" ", 1)[0]

        if add_ellipsis:
            truncated += "..."

        return truncated

    def split_by_tokens(
        self,
        text: str,
        chunk_size: int,
        overlap: int = 0,
    ) -> List[str]:
        """Split text into chunks of specified token size.

        Args:
            text: Text to split
            chunk_size: Target tokens per chunk
            overlap: Overlap tokens between chunks

        Returns:
            List of text chunks
        """
        if not text:
            return []

        if self.count(text) <= chunk_size:
            return [text]

        self._ensure_initialized()

        if self._encoder:
            tokens = self._encoder.encode(text)
            chunks = []
            start = 0

            while start < len(tokens):
                end = min(start + chunk_size, len(tokens))
                chunk_tokens = tokens[start:end]
                chunk_text = self._encoder.decode(chunk_tokens)
                chunks.append(chunk_text)
                start = end - overlap

            return chunks

        # Fallback: sentence-based splitting
        sentences = text.replace("! ", "!|").replace("? ", "?|").replace(". ", ".|").split("|")
        chunks = []
        current_chunk = ""
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count(sentence)

            if current_tokens + sentence_tokens > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
                current_tokens = sentence_tokens
            else:
                current_chunk += sentence + " "
                current_tokens += sentence_tokens

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks


# Singleton instance
_token_counter: TokenCounter | None = None


@lru_cache(maxsize=1)
def get_token_counter() -> TokenCounter:
    """Get the singleton token counter.

    Returns:
        TokenCounter instance
    """
    global _token_counter

    if _token_counter is None:
        _token_counter = TokenCounter()

    return _token_counter


def count_tokens(text: str) -> int:
    """Convenience function to count tokens.

    Args:
        text: Text to count

    Returns:
        Token count
    """
    return get_token_counter().count(text)


def count_message_tokens(messages: List[dict]) -> int:
    """Convenience function to count tokens in messages.

    Args:
        messages: List of messages

    Returns:
        Total token count
    """
    return get_token_counter().count_messages(messages)


def truncate_text(text: str, max_tokens: int) -> str:
    """Convenience function to truncate text.

    Args:
        text: Text to truncate
        max_tokens: Maximum tokens

    Returns:
        Truncated text
    """
    return get_token_counter().truncate_to_tokens(text, max_tokens)
