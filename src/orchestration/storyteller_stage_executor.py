"""
Storyteller Stage Executor Module

This module provides functionality for executing stages in the storytelling pipeline.
It manages the execution of phases within a stage, handling content generation,
processing, and storage. The StageExecutor interacts with the progress tracker,
content processor, and storage manager to ensure seamless execution of each stage.

Usage:
    stage_executor = StageExecutor(progress_tracker, content_processor, storage_manager)
    await stage_executor.execute_stage(stage)
"""

import logging


from config.storyteller_configuration_types import StageConfig, PhaseConfig
from content.storyteller_content_processor import StorytellerContentProcessor
from storage.storyteller_storage_types import StorytellerStorageError
from storage.storyteller_storage_manager import StorytellerStorageManager
from common.storyteller_exceptions import StorytellerContentProcessingError
from llm.storyteller_llm_interface import StorytellerLLMInterface
from orchestration.storyteller_stage_manager import (
    StorytellerProgressTracker,
    StorytellerStageManager,
)
from content.storyteller_prompt_manager import StorytellerPromptManager
from plugins.storyteller_plugin_manager import (
    StorytellerPluginManager,
    PluginError,
    PluginLoadError,
)


logger = logging.getLogger(__name__)


class StageExecutor:
    """Manages the execution of stages in the storytelling pipeline.

    Attributes:
        progress_tracker: Tracks the progress of the pipeline execution.
        content_processor: Processes and validates generated content.
        storage_manager: Manages storage of generated content.
        prompt_manager: Manages prompt preparation and handling.
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
        """Initializes the StageExecutor with necessary components.

        Args:
            progress_tracker: An instance of StorytellerProgressTracker.
            content_processor: An instance of StorytellerContentProcessor.
            storage_manager: An instance of StorytellerStorageManager.
            prompt_manager: An instance of StorytellerPromptManager.
        """
        self.progress_tracker = progress_tracker
        self.content_processor = content_processor
        self.storage_manager = storage_manager
        self.prompt_manager = prompt_manager
        self.plugin_manager = plugin_manager
        self.llm_instance = llm_instance
        self.stage_manager = StorytellerStageManager()

    async def execute_stage(self, stage: StageConfig) -> None:
        """Executes a specified stage of the pipeline.

        Args:
            stage: The configuration dictionary for the stage to run.

        Raises:
            RuntimeError: If an error occurs during stage execution.
        """
        logger.info("Starting stage: %s", stage["display_name"])
        logger.info("Description: %s", stage["description"])

        for _, phase in enumerate(stage["phases"]):
            await self.execute_phase(stage, phase)

        logger.info("Completed stage: %s", stage["name"])

    async def execute_phase(self, stage: StageConfig, phase: PhaseConfig) -> None:
        logger.info("Starting phase: %s_%s", stage["name"], phase["name"])
        self.log_phase_config(stage, phase)

        plugin_name = phase.get("plugin", "text")
        if not self.validate_plugin(plugin_name):
            raise ValueError(f"Unsupported plugin: {plugin_name}")

        try:
            stage_index, phase_index = self.progress_tracker.get_current_progress()
            temperature = self.stage_manager.get_phase_temperature(
                stage_index, phase_index
            )
            generated_prompt = self.prompt_manager.prepare_prompt(stage, phase)

            prompt_packet = self.storage_manager.create_content_packet(
                stage_name=stage["name"],
                phase_name=phase["name"],
                identifier="prompt",
                plugin_name=plugin_name,
                content=generated_prompt,
                prompt=generated_prompt,
                file_extension="txt",
            )
            await self.storage_manager.save_ephemeral_content(prompt_packet)
            logger.info(
                "Saved prompt to ephemeral storage: %s_%s", stage["name"], phase["name"]
            )

            logger.info(
                "Generating content for phase: %s_%s", stage["name"], phase["name"]
            )
            content = await self.llm_instance.generate_content(
                generated_prompt, temperature
            )

            if not isinstance(content, str):
                raise TypeError(
                    f"Expected str from generate_content, got {type(content).__name__}"
                )

            logger.info(
                "Content generated successfully for phase: %s_%s",
                stage["name"],
                phase["name"],
            )

            content_packet = self.storage_manager.create_content_packet(
                stage_name=stage["name"],
                phase_name=phase["name"],
                identifier="response",
                plugin_name=plugin_name,
                content=content,
                prompt=generated_prompt,
            )
            processed_content, _ = await self.content_processor.process_content(
                content_packet
            )

            logger.info(
                "Output processed successfully for phase: %s_%s",
                stage["name"],
                phase["name"],
            )

            try:
                await self.storage_manager.save_ephemeral_content(processed_content)
                await self.storage_manager.save_batch_content(processed_content)
                logger.info(
                    "Saved processed content to ephemeral and batch storage: %s_%s",
                    stage["name"],
                    phase["name"],
                )
            except StorytellerStorageError as storage_error:
                logger.error(
                    "Storage error in %s_%s: %s",
                    stage["name"],
                    phase["name"],
                    str(storage_error),
                )
                raise

            self.progress_tracker.update_story_data(
                stage["name"], phase["name"], processed_content
            )

            logger.info("Completed phase: %s_%s", stage["name"], phase["name"])
        except (
            StorytellerContentProcessingError,
            PluginError,
            PluginLoadError,
            ValueError,
            TypeError,
        ) as exc:
            logger.error("Error in %s_%s: %s", stage["name"], phase["name"], str(exc))
            raise RuntimeError(
                f"Error in {stage['name']}_{phase['name']}: {str(exc)}"
            ) from exc

    def validate_plugin(self, plugin_name: str) -> bool:
        return plugin_name in self.plugin_manager.get_loaded_plugins()

    def log_phase_config(self, stage: StageConfig, phase: PhaseConfig) -> None:
        """Logs the configuration for the current phase."""
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

    def _get_prompt_path(self, prompt_file: str) -> str:
        """Safely constructs the path for the prompt file."""
        if self.prompt_manager and self.prompt_manager.config_manager and self.prompt_manager.config_manager.path_manager:
            path = self.prompt_manager.config_manager.path_manager.construct_path("prompts", prompt_file)
            return str(path)  # Convert Path to str
        return f"prompts/{prompt_file}"

    def _get_schema_path(self, schema_file: str) -> str:
        """Safely constructs the path for the schema file."""
        if self.prompt_manager and self.prompt_manager.config_manager and self.prompt_manager.config_manager.path_manager:
            path = self.prompt_manager.config_manager.path_manager.construct_path("schemas", schema_file)
            return str(path)  # Convert Path to str
        return f"schemas/{schema_file}"
