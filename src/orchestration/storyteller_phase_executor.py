"""
Storyteller Phase Executor Module

This module provides functionality for executing individual phases within the storytelling pipeline.
It handles the preparation of prompts, content generation, processing of generated content,
and interaction with the LLM (Large Language Model) interface.

Usage:
    executor = StorytellerPhaseExecutor(progress_tracker, content_processor, storage_manager, prompt_manager, plugin_manager, llm_instance)
    await executor.execute_phase(stage, phase)

The module is designed to work asynchronously and integrates with various components of the storytelling system.
"""

import logging
from pathlib import Path

from config.storyteller_configuration_types import StageConfig, PhaseConfig
from storage.storyteller_storage_manager import StorytellerStorageManager
from content.storyteller_prompt_manager import StorytellerPromptManager
from content.storyteller_content_processor import (
    StorytellerContentProcessor,
    StorytellerContentProcessingError,
)
from llm.storyteller_llm_interface import StorytellerLLMInterface
from orchestration.storyteller_stage_manager import StorytellerProgressTracker
from plugins.storyteller_plugin_manager import (
    PluginError,
    PluginLoadError,
    StorytellerPluginManager,
)

logger = logging.getLogger(__name__)


class StorytellerPhaseExecutor:
    """
    Executes the current phase of the storytelling pipeline.

    This class manages the execution of a single phase within a stage,
    including the preparation of prompts, generation of content, processing
    of the generated content, and saving of results.

    Attributes:
        progress_tracker (StorytellerProgressTracker): Tracks the progress of the pipeline.
        content_processor (StorytellerContentProcessor): Processes and validates content.
        storage_manager (StorytellerStorageManager): Manages the storage of generated content.
        prompt_manager (StorytellerPromptManager): Manages the preparation of prompts.
        plugin_manager (StorytellerPluginManager): Manages the loading and execution of plugins.
        llm_instance (StorytellerLLMInterface): The LLM instance used for content generation.
    """

    def __init__(
        self,
        progress_tracker: StorytellerProgressTracker,
        content_processor: StorytellerContentProcessor,
        storage_manager: StorytellerStorageManager,
        prompt_manager: StorytellerPromptManager,
        plugin_manager: StorytellerPluginManager,
        llm_instance: StorytellerLLMInterface,
    ) -> None:
        """
        Initializes the StorytellerPhaseExecutor.

        Args:
            progress_tracker: An instance of the progress tracker.
            content_processor: An instance of the content processor.
            storage_manager: An instance of the storage manager.
            prompt_manager: An instance of the prompt manager.
            plugin_manager: An instance of the plugin manager.
            llm_instance: An instance of the LLM interface.
        """
        self.progress_tracker = progress_tracker
        self.content_processor = content_processor
        self.storage_manager = storage_manager
        self.prompt_manager = prompt_manager
        self.plugin_manager = plugin_manager
        self.llm_instance = llm_instance

    async def execute_phase(self, stage: StageConfig, phase: PhaseConfig) -> None:
        """
        Executes the specified phase of the pipeline.

        This method handles the preparation of prompts, content generation,
        content processing, and saving of results.

        Args:
            stage: The configuration for the current stage.
            phase: The configuration for the current phase.

        Raises:
            RuntimeError: If an error occurs during phase execution.
        """
        logger.info("Starting phase: %s_%s", stage["name"], phase["name"])

        plugin_name = phase.get("plugin", "text").lower()
        plugin = self.plugin_manager.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Unsupported plugin: {plugin_name}")

        stage_name = stage["name"]
        phase_name = phase["name"]

        self._log_phase_config(stage, phase)

        try:
            temperature = phase.get("temperature")
            prompt = self.prompt_manager.prepare_prompt(stage, phase)

            # Create and save prompt packet
            prompt_packet = self.storage_manager.create_content_packet(
                content=prompt,
                stage_name=stage_name,
                phase_name=phase_name,
                plugin_name=plugin_name,
                identifier="prompt",
                prompt=prompt,
                file_extension="txt",
                metadata={"content_type": "text/plain"},
            )
            await self.storage_manager.save_ephemeral_content(prompt_packet)

            logger.info("Generating content for phase: %s_%s", stage_name, phase_name)

            logger.info("Generating content for phase: %s_%s", stage_name, phase_name)

            # Set schema for LLM if available
            has_schema, schema = self.progress_tracker.stage_manager.get_phase_schema(stage_name, phase_name)
            pass_schema = getattr(self.llm_instance, 'pass_schema', False)
            logger.debug("Pass schema value: %s", pass_schema)

            if has_schema and pass_schema:
                logger.debug("Setting schema for LLM")
                self.llm_instance.set_schema(schema)
            else:
                logger.debug("No schema set for LLM. Has schema: %s, Pass schema: %s",
                             has_schema, pass_schema)
                self.llm_instance.set_schema(None)  # Clear any previous schema

            content = await self.llm_instance.generate_content(prompt, temperature)

            if not isinstance(content, str):
                raise TypeError(
                    f"Expected str from generate_content, got {type(content).__name__}"
                )

            logger.info(
                "Content generated successfully for phase: %s_%s",
                stage_name,
                phase_name,
            )

            # Create content packet
            content_packet = self.storage_manager.create_content_packet(
                content=content,
                stage_name=stage_name,
                phase_name=phase_name,
                plugin_name=plugin_name,
                identifier="response",
                prompt=prompt,
                file_extension=plugin.get_extension(),
            )

            # Process content
            processed_packet, success = await self.content_processor.process_content(
                content_packet
            )

            if not success:
                raise StorytellerContentProcessingError(
                    f"Content processing failed for {stage_name}_{phase_name}"
                )

            logger.info(
                "Output processed successfully for phase: %s_%s", stage_name, phase_name
            )

            # Save processed content
            await self.storage_manager.save_batch_content(processed_packet)
            await self.storage_manager.save_ephemeral_content(processed_packet)

            self.progress_tracker.update_story_data(
                stage_name, phase_name, processed_packet
            )

            logger.info("Completed phase: %s_%s", stage_name, phase_name)
        except (
            StorytellerContentProcessingError,
            PluginError,
            PluginLoadError,
            ValueError,
            TypeError,
        ) as e:
            logger.error("Error in %s_%s: %s", stage_name, phase_name, str(e))
            raise RuntimeError(f"Error in {stage_name}_{phase_name}: {str(e)}") from e

    def _log_phase_config(self, stage: StageConfig, phase: PhaseConfig) -> None:
        """
        Logs the configuration for the current phase.

        Args:
            stage: The configuration for the current stage.
            phase: The configuration for the current phase.
        """
        logger.info("Phase configuration:")
        logger.info("  Stage: %s", stage["name"])
        logger.info("  Phase: %s", phase["name"])

        prompt_path = self._get_prompt_path(phase["prompt_file"])
        logger.info("  Prompt file: %s", prompt_path)

        schema_file = phase.get("schema", "")
        if schema_file:
            schema_path = self._get_schema_path(schema_file)
            logger.info("  Schema file: %s", schema_path)
        else:
            logger.info("  Schema file: Not specified")

        logger.info("  Plugin: %s", phase.get("plugin", "text"))

    def _get_prompt_path(self, prompt_file: str) -> Path | None:
        """
        Safely retrieves the prompt file path.

        Args:
            prompt_file: The name of the prompt file.

        Returns:
            The path to the prompt file, or None if it cannot be retrieved.
        """
        if self.prompt_manager.config_manager and self.prompt_manager.config_manager.path_manager:
            return self.prompt_manager.config_manager.path_manager.get_prompt_path(prompt_file)
        return None

    def _get_schema_path(self, schema_file: str) -> Path | None:
        """
        Safely retrieves the schema file path.

        Args:
            schema_file: The name of the schema file.

        Returns:
            The path to the schema file, or None if it cannot be retrieved.
        """
        if self.prompt_manager.config_manager and self.prompt_manager.config_manager.path_manager:
            return self.prompt_manager.config_manager.path_manager.get_schema_path(schema_file)
        return None
