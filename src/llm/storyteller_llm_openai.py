"""
StorytellerOpenAIGenerator Module

This module provides an implementation of the StorytellerLLMInterface for OpenAI's GPT models.
It handles initialization, content generation, and error management for OpenAI API interactions.
"""

import logging
from typing import Dict, Any, Optional
import openai
from openai import OpenAI
from llm.storyteller_llm_interface import StorytellerLLMInterface

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class StorytellerOpenAIError(Exception):
    """Custom exception class for OpenAI-specific errors."""


class StorytellerOpenAIGenerator(StorytellerLLMInterface):
    """
    A class to generate content using OpenAI's GPT models.

    This class implements the StorytellerLLMInterface and provides methods
    for initializing the OpenAI client and generating content using the specified model.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the StorytellerOpenAIGenerator with the provided configuration.

        Args:
            config (Dict[str, Any]): Configuration dictionary containing API key and model details.
        """
        self.config = config
        self.api_key: str = config["api_key"]
        self.model: str = config["model"]
        self.max_tokens: int = config.get("max_tokens", 100)
        self.client: Optional[OpenAI] = None

    async def initialize(self) -> None:
        """
        Initialize the OpenAI client.

        This method sets up the OpenAI client with the provided API key.

        Raises:
            StorytellerOpenAIError: If there's an error initializing the OpenAI client.
        """
        logger.info("Initializing OpenAI Client")
        try:
            self.client = OpenAI(api_key=self.api_key)
            # Attempt to list models to verify the API key
            self.client.models.list()
            logger.info("OpenAI client initialized successfully.")
        except openai.OpenAIError as exc:
            logger.error("Failed to initialize OpenAI client: %s", exc)
            raise StorytellerOpenAIError(f"Client initialization failed: {str(exc)}") from exc

    async def generate_content(self, prompt: str, temperature: Optional[float] = None) -> str:
        """
        Generate content using the OpenAI API.

        Args:
            prompt (str): The input prompt for content generation.
            temperature (Optional[float]): The sampling temperature to use. If None, defaults to 1.0.

        Returns:
            str: The generated content.

        Raises:
            StorytellerOpenAIError: If there's an error in content generation or the client is not initialized.
        """
        if self.client is None:
            raise StorytellerOpenAIError("OpenAI client not initialized. Call initialize() first.")

        try:
            logger.debug("Generating content with prompt: %s", prompt[:100] + "..." if len(prompt) > 100 else prompt)
            response = self.client.completions.create(
                model=self.model,
                prompt=prompt,
                max_tokens=self.max_tokens,
                temperature=temperature or 1.0,
            )

            content = response.choices[0].text.strip()

            if not content:
                raise StorytellerOpenAIError("OpenAI model returned empty content")

            logger.info("Content generated successfully. Length: %d characters", len(content))
            return content
        except openai.OpenAIError as exc:
            logger.error("Error in generate_content: %s", str(exc))
            raise StorytellerOpenAIError(f"Error in content generation: {str(exc)}") from exc
