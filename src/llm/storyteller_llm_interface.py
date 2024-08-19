"""
This module defines the interface for Language Model (LLM) implementations in the Storyteller system.

It provides an abstract base class that all LLM implementations should inherit from,
ensuring a consistent interface across different LLM providers. The interface includes
methods for initialization, content generation, schema setting, auto-continuation, 
and chat history management.

Usage:
    class MyLLMImplementation(StorytellerLLMInterface):
        # Implement abstract methods

    llm = MyLLMImplementation()
    await llm.initialize(config)
    llm.set_schema(schema)
    response = await llm.generate_content("Hello, world!")
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class StorytellerLLMInterface(ABC):
    """
    Abstract base class for Storyteller LLM implementations.

    This class defines the interface that all LLM implementations should follow,
    providing common functionality and abstract methods to be implemented by subclasses.

    Attributes:
        chat_history (List[Dict[str, str]]): A list of chat history entries.
        config (Dict[str, Any]): Configuration parameters for the LLM.
    """

    def __init__(self) -> None:
        """Initialize the StorytellerLLMInterface."""
        self.chat_history: List[Dict[str, str]] = []
        self.config: Dict[str, Any] = {}
        self.pass_schema: bool = False
        logger.debug("Initialized StorytellerLLMInterface")

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the LLM with the provided configuration.

        Args:
            config: Configuration parameters for the LLM.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """

    @abstractmethod
    async def generate_content(self, prompt: str, temperature: Optional[float] = None) -> str:
        """
        Generate content based on the given prompt.

        Args:
            prompt: The input prompt for content generation.
            temperature: The sampling temperature to use.

        Returns:
            The generated content.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """

    @abstractmethod
    def set_schema(self, schema: Optional[str]) -> None:
        """
        Set the schema for content generation.

        Args:
            schema: The schema to be used for content generation, or None to clear the schema.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """

    async def auto_continue_generation(self, initial_prompt: str, max_continuations: int = 3) -> str:
        """
        Automatically continue generating content based on the initial prompt.

        Args:
            initial_prompt: The initial prompt to start generation.
            max_continuations: Maximum number of continuations to generate.

        Returns:
            The full generated content, including continuations.

        Raises:
            RuntimeError: If content generation fails.
        """
        logger.info("Starting auto-continuation with initial prompt: %s", initial_prompt)
        try:
            full_response = await self.generate_content(initial_prompt)
            continuations = 0

            while continuations < max_continuations:
                if self._should_continue(full_response):
                    continuation_prompt = "Continue:"
                    continuation = await self.generate_content(continuation_prompt)
                    full_response = self._glue_responses(full_response, continuation)
                    continuations += 1
                    logger.debug("Generated continuation %d", continuations)
                else:
                    logger.debug("Auto-continuation complete after %d continuations", continuations)
                    break

            return full_response
        except (ValueError, TypeError) as exc:
            logger.error("Error in auto_continue_generation: %s", str(exc))
            raise RuntimeError(f"Auto-continuation failed: {str(exc)}") from exc

    def _glue_responses(self, previous_response: str, continuation: str, overlap_threshold: float = 0.5, context_length: int = 200) -> str:
        """
        Glue two responses together, attempting to find and remove overlapping content.

        Args:
            previous_response: The previous generated response.
            continuation: The new continuation to be glued.
            overlap_threshold: The minimum overlap ratio to consider for gluing.
            context_length: The number of characters to consider for overlap detection.

        Returns:
            The glued response.
        """
        last_context = previous_response[-context_length:]

        matcher = SequenceMatcher(None, last_context, continuation[:context_length])
        match = matcher.find_longest_match(0, len(last_context), 0, len(continuation[:context_length]))

        if match.size / context_length >= overlap_threshold:
            glued_response = f"{previous_response[:-context_length + match.a + match.size]}{continuation[match.b + match.size:]}"
            logger.debug("Responses glued with overlap of %d characters", match.size)
        else:
            glued_response = f"{previous_response} {continuation}"
            logger.debug("Responses concatenated without significant overlap")

        return glued_response

    def _should_continue(self, text: str) -> bool:
        """
        Determine if the generation should continue based on the last character of the text.

        Args:
            text: The text to check.

        Returns:
            True if generation should continue, False otherwise.
        """
        return text[-1] not in ('.', '!', '?', '}', ']', '>')

    def get_chat_history(self) -> List[Dict[str, str]]:
        """
        Get the current chat history.

        Returns:
            The chat history.
        """
        return self.chat_history

    def clear_chat_history(self) -> None:
        """Clear the chat history."""
        self.chat_history.clear()
        logger.info("Chat history cleared")
