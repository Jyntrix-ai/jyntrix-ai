"""Google Gemini LLM client with async streaming."""

import asyncio
import logging
from typing import Any, AsyncGenerator, List

import google.generativeai as genai

from src.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM client using Google Gemini with async streaming.

    Provides both streaming and non-streaming chat completions
    using the Gemini API.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        """Initialize LLM client.

        Args:
            api_key: Google API key (default from settings)
            model: Model name (default from settings)
            temperature: Sampling temperature (default from settings)
            max_tokens: Max output tokens (default from settings)
        """
        self.api_key = api_key or settings.google_ai_api_key
        self.model_name = model or settings.gemini_model
        self.temperature = temperature if temperature is not None else settings.gemini_temperature
        self.max_tokens = max_tokens or settings.gemini_max_tokens

        # Configure the API
        genai.configure(api_key=self.api_key)

        # Create model instance
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=genai.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            ),
        )

        self._initialized = True
        logger.info(f"LLM client initialized with model: {self.model_name}")

    async def stream_chat(
        self,
        messages: List[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream chat completion response.

        Args:
            messages: List of messages in format [{"role": str, "content": str}]
            temperature: Override temperature
            max_tokens: Override max tokens

        Yields:
            Dict with type ("text" or "error") and content
        """
        try:
            # Convert messages to Gemini format
            gemini_messages = self._convert_messages(messages)

            # Create generation config with overrides
            gen_config = genai.GenerationConfig(
                temperature=temperature if temperature is not None else self.temperature,
                max_output_tokens=max_tokens or self.max_tokens,
            )

            # Start streaming generation
            response = await asyncio.to_thread(
                lambda: self.model.generate_content(
                    gemini_messages,
                    generation_config=gen_config,
                    stream=True,
                )
            )

            # Stream chunks - use to_thread for each iteration to avoid blocking
            def get_next_chunk(iterator):
                """Get the next chunk from the iterator."""
                try:
                    return next(iterator)
                except StopIteration:
                    return None

            iterator = iter(response)
            while True:
                chunk = await asyncio.to_thread(get_next_chunk, iterator)
                if chunk is None:
                    break
                if chunk.text:
                    yield {
                        "type": "text",
                        "content": chunk.text,
                    }

        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield {
                "type": "error",
                "error": str(e),
            }

    async def complete(
        self,
        messages: List[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Non-streaming chat completion.

        Args:
            messages: List of messages
            temperature: Override temperature
            max_tokens: Override max tokens

        Returns:
            Complete response text

        Raises:
            Exception: If generation fails
        """
        try:
            # Convert messages
            gemini_messages = self._convert_messages(messages)

            # Create generation config
            gen_config = genai.GenerationConfig(
                temperature=temperature if temperature is not None else self.temperature,
                max_output_tokens=max_tokens or self.max_tokens,
            )

            # Generate response
            response = await asyncio.to_thread(
                lambda: self.model.generate_content(
                    gemini_messages,
                    generation_config=gen_config,
                )
            )

            return response.text

        except Exception as e:
            logger.error(f"Complete error: {e}")
            raise

    async def generate_with_context(
        self,
        prompt: str,
        context: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate response with optional context.

        Args:
            prompt: User prompt
            context: Optional context to include
            system_prompt: Optional system instructions
            temperature: Override temperature

        Returns:
            Generated response
        """
        messages = []

        # Add system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add context as part of user message
        if context:
            full_prompt = f"Context:\n{context}\n\nUser: {prompt}"
        else:
            full_prompt = prompt

        messages.append({"role": "user", "content": full_prompt})

        return await self.complete(messages, temperature=temperature)

    def _convert_messages(
        self,
        messages: List[dict[str, str]],
    ) -> List[dict[str, Any]]:
        """Convert messages to Gemini format.

        Gemini uses a different format than OpenAI-style messages.

        Args:
            messages: OpenAI-style messages

        Returns:
            Gemini-compatible content list
        """
        # Combine system prompt with first user message
        system_content = ""
        converted = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_content = content
            elif role == "user":
                if system_content:
                    content = f"{system_content}\n\n{content}"
                    system_content = ""
                converted.append({
                    "role": "user",
                    "parts": [content],
                })
            elif role == "assistant":
                converted.append({
                    "role": "model",
                    "parts": [content],
                })

        # If only system message, treat as user message
        if system_content and not converted:
            converted.append({
                "role": "user",
                "parts": [system_content],
            })

        return converted

    async def count_tokens(self, text: str) -> int:
        """Count tokens in text using Gemini tokenizer.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        try:
            result = await asyncio.to_thread(
                lambda: self.model.count_tokens(text)
            )
            return result.total_tokens
        except Exception as e:
            logger.warning(f"Token count error, using estimate: {e}")
            # Fallback to rough estimate
            return len(text) // 4

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding using Gemini embedding model.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            result = await asyncio.to_thread(
                lambda: genai.embed_content(
                    model="models/embedding-001",
                    content=text,
                    task_type="retrieval_document",
                )
            )
            return result["embedding"]
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""

    def __init__(self):
        """Initialize mock client."""
        self._initialized = True
        self.model_name = "mock"
        self.temperature = 0.7
        self.max_tokens = 4096

    async def stream_chat(
        self,
        messages: List[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Mock streaming response."""
        response = "This is a mock response for testing purposes."

        for word in response.split():
            yield {"type": "text", "content": word + " "}
            await asyncio.sleep(0.05)

    async def complete(
        self,
        messages: List[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Mock complete response."""
        return "This is a mock response for testing purposes."


def get_llm_client(use_mock: bool = False) -> LLMClient:
    """Get LLM client instance.

    Args:
        use_mock: Whether to use mock client

    Returns:
        LLM client instance
    """
    if use_mock or not settings.google_ai_api_key:
        logger.warning("Using mock LLM client")
        return MockLLMClient()

    return LLMClient()
