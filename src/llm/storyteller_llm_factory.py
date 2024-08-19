"""
Storyteller LLM Factory Module

This module provides a factory class for creating instances of different Large Language Models (LLMs)
based on the configuration. The `StorytellerLLMFactory` uses a registry pattern to map LLM types to
their respective generator classes, allowing for easy extension and maintenance.

Usage:
    factory = StorytellerLLMFactory()
    llm_instance = factory.get_llm_instance()

The factory will instantiate the appropriate LLM based on the configuration in storyteller_config.
"""

import logging
from typing import Dict, Any, Type, cast
from config.storyteller_configuration_manager import storyteller_config
from config.storyteller_configuration_types import LLMConfig
from llm.storyteller_llm_interface import StorytellerLLMInterface
from llm.storyteller_llm_openai import StorytellerOpenAIGenerator
from llm.storyteller_llm_gemini import StorytellerGeminiGenerator

# Initialize the logger
logger = logging.getLogger(__name__)


class StorytellerLLMFactory:
    """
    A factory class for creating LLM instances based on configuration.
    This class is responsible for initializing and returning the appropriate
    LLM implementation based on the configuration provided.

    Attributes:
        config (Dict[str, Any]): The LLM configuration retrieved from the storyteller configuration manager.
    """

    # TODO - Dynamic loading of LLMs from plugins - Clean an LLM plugin up at the end of each stage so we can mix and match between stages.
    _registry: Dict[str, Type[StorytellerLLMInterface]] = {
        "openai": StorytellerOpenAIGenerator,
        "google_vertex_ai": StorytellerGeminiGenerator,
    }

    def __init__(self) -> None:
        """
        Initialize the StorytellerLLMFactory with configuration from storyteller_config.

        Raises:
            KeyError: If the required configuration keys are missing.
            TypeError: If the configuration values are not of the expected types.
        """
        try:
            self.config: LLMConfig = storyteller_config.get_llm_config()
            logger.info(
                "StorytellerLLMFactory initialized with config: %s", self.config
            )
        except (KeyError, TypeError) as exc:
            logger.error("Error initializing StorytellerLLMFactory: %s", str(exc))
            raise

    async def get_llm_instance(self) -> StorytellerLLMInterface:
        """
        Get an instance of the configured LLM.
        This method retrieves the LLM type from the configuration and initializes the corresponding
        LLM generator class.
        Returns:
            StorytellerLLMInterface: An instance of the configured LLM.
        Raises:
            ValueError: If an unsupported LLM type is specified in the configuration.
            TypeError: If the configuration is not in the expected format.
            KeyError: If required configuration keys are missing.
        """
        try:
            llm_type: str = self.config["type"]
            llm_config: Dict[str, Any] = cast(Dict[str, Any], self.config)

            if not isinstance(llm_config["config"], dict):
                raise TypeError(f"Expected dict for LLM config, got {type(llm_config['config'])}")

            llm_class = self._registry.get(llm_type)
            if llm_class is None:
                raise ValueError(f"Unsupported LLM type: {llm_type}")

            llm = llm_class()
            await llm.initialize(config=llm_config)
            logger.info(
                "Created and initialized %s LLM with config: %s", llm_type, llm_config
            )
            return llm
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("Error creating LLM instance: %s", str(exc))
            raise


if __name__ == "__main__":
    try:
        factory = StorytellerLLMFactory()
        llm_instance = factory.get_llm_instance()
        print(f"Created LLM instance: {llm_instance}")
    except (KeyError, TypeError, ValueError) as e:
        print(f"An error occurred: {e}")
