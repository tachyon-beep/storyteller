"""
Pipeline Orchestrator Module

This module implements a pipeline orchestrator for executing predefined workloads against
a specified LLM using a configuration-based approach with a plugin system for content processing.

The orchestrator handles multi-stage processes as defined in the pipeline_config.yaml file.
It provides functionality for initializing the pipeline, running implemented stages,
saving and loading progress, and finalizing generated story data.

Usage:
    orchestrator = PipelineOrchestrator()
    await orchestrator.initialize()
    await orchestrator.run_batch()

Note: This module requires asyncio and should be run in an async environment.
"""

import logging
from typing import List

from config.storyteller_configuration_manager import storyteller_config
from config.storyteller_configuration_types import StageConfig
from storage.storyteller_storage_manager import StorytellerStorageManager
from common.storyteller_exceptions import StorytellerContentProcessingError
from orchestration.storyteller_stage_executor import StageExecutor
from orchestration.storyteller_pipeline_coordinator import PipelineCoordinator
from orchestration.storyteller_phase_executor import StorytellerPhaseExecutor
from orchestration.storyteller_stage_manager import (
    StorytellerStageManager,
    StorytellerProgressTracker,
)
from orchestration.storyteller_batch_manager import BatchManager
from llm.storyteller_llm_factory import StorytellerLLMFactory
from content.storyteller_library import StorytellerLibrary
from content.storyteller_prompt_manager import StorytellerPromptManager
from plugins.storyteller_plugin_manager import (
    PluginError,
    PluginLoadError,
    StorytellerPluginManager,
)


logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the story generation pipeline.

    This class manages the progression through various stages and phases of content creation
    as defined in the configuration file. It uses StorytellerProgressTracker for state management
    and StorytellerStageManager for stage and phase data management.

    Attributes:
        config_manager (StorytellerConfigManager): Configuration manager instance.
        batch_manager (BatchManager): Manages batch ID and batch name.
        stage_manager (StorytellerStageManager): Stage manager instance.
        progress_tracker (StorytellerProgressTracker): Progress tracker instance.
        plugin_manager (StorytellerPluginManager): Plugin manager instance.
        storage_manager (StorytellerStorageManager): Storage manager instance.
        prompt_manager (StorytellerPromptManager): Prompt manager instance.
        llm_factory (StorytellerLLMFactory): Factory for creating LLM instances.
        llm_instance (StorytellerLLMInterface): LLM instance.
        content_processor (StorytellerContentProcessor): Content processor instance.
        phase_executor (StorytellerPhaseExecutor): Phase executor instance.
        stage_executor (StageExecutor): Stage executor instance.
        stages (List[Dict[str, Any]]): List of stage configurations.
        root_path (str): Root path for the project.
        pipeline_coordinator (PipelineCoordinator): Pipeline coordinator instance.
    """

    def __init__(self) -> None:
        """Initialize the PipelineOrchestrator with all necessary components."""
        self.config_manager = storyteller_config
        batch_name = self.config_manager.get_nested_config_value("batch.name")
        starting_id = int(self.config_manager.get_nested_config_value("batch.starting_id"))
        self.root_path = self.config_manager.get_path("root")

        self.batch_manager = BatchManager(batch_name, starting_id)
        self.stage_manager = StorytellerStageManager()
        self.progress_tracker = StorytellerProgressTracker(self.stage_manager)
        self.plugin_manager = StorytellerPluginManager(self.stage_manager)
        self.library = StorytellerLibrary()
        self.prompt_manager = StorytellerPromptManager(
            self.stage_manager, self.progress_tracker, self, self.plugin_manager, self.library
        )
        self.llm_factory = StorytellerLLMFactory()
        self.llm_instance = None
        self.storage_manager = None
        self.stage_executor = None
        self.phase_executor = None
        self.pipeline_coordinator = None
        self.content_processor = None
        self.stages: List[StageConfig] = self.stage_manager.get_stages()

    async def initialize(self) -> None:
        """
        Initialize the PipelineOrchestrator and its components.

        This method initializes the LLM instance and logs the loaded plugins.

        Raises:
            RuntimeError: If initialization fails.
        """

        # The factory creates and initializes the LLM instance
        self.llm_instance = await self.llm_factory.get_llm_instance()
        self.storage_manager = StorytellerStorageManager(self.plugin_manager, self.stage_manager, self.llm_instance, self.progress_tracker)
        self.plugin_manager.set_storage_manager(self.storage_manager)
        self.content_processor = self.storage_manager.content_processor
        self.phase_executor = StorytellerPhaseExecutor(
            self.progress_tracker,
            self.content_processor,
            self.storage_manager,
            self.prompt_manager,
            self.plugin_manager,
            self.llm_instance
        )
        self.stage_executor = StageExecutor(
            self.progress_tracker,
            self.content_processor,
            self.storage_manager,
            self.prompt_manager,
            self.plugin_manager,
            self.llm_instance,
        )
        self.pipeline_coordinator = PipelineCoordinator(
            self.stage_executor, self.phase_executor, self.stage_manager
        )

        logger.info("Initializing PipelineOrchestrator")
        try:

            logger.info("LLM instance initialized successfully")
            logger.info(
                "Loaded plugins: %s",
                ", ".join(self.plugin_manager.get_loaded_plugins()),
            )
        except (PluginLoadError, RuntimeError) as e:
            logger.error("Failed to initialize PipelineOrchestrator: %s", str(e))
            raise RuntimeError("PipelineOrchestrator initialization failed") from e

    async def run_batch(self) -> None:
        """
        Run a batch of pipeline executions.

        This method executes the pipeline for the number of times specified in the batch configuration.

        Raises:
            RuntimeError: If batch execution fails.
        """
        logger.info("Starting batch execution")
        batch_size = self.config_manager.get_nested_config_value("batch.size")
        logger.info("Batch size: %d", batch_size)

        if self.batch_manager is None:
            raise RuntimeError("Batch manager not initialized")

        if self.storage_manager is None:
            raise RuntimeError("Storage manager not initialized")

        try:
            for _ in range(batch_size):
                self.batch_manager.start_batch()
                await self.storage_manager.start_new_batch()  # Start a new batch in the storage manager
                logger.info(
                    "Starting run for Batch ID: %d",
                    self.batch_manager.get_current_batch_id()
                )
                await self.run_pipeline()
                logger.info(
                    "Completed run for Batch ID: %d",
                    self.batch_manager.get_current_batch_id()
                )
                self.batch_manager.end_batch()
            logger.info("Batch execution completed successfully")
        except (StorytellerContentProcessingError, PluginError, PluginLoadError, RuntimeError) as e:
            logger.error("Error during batch execution: %s", str(e))
            raise RuntimeError("Batch execution failed") from e

    async def run_pipeline(self) -> None:
        """
        Execute the pipeline for a single batch.

        This method creates batch storage, resets the progress tracker,
        and runs the pipeline coordinator.

        Raises:
            RuntimeError: If pipeline execution fails.
        """
        batch_id = self.batch_manager.get_current_batch_id()

        logger.info(
            "Starting pipeline execution for Batch ID: %d",
            batch_id
        )

        if self.batch_manager is None:
            raise RuntimeError("Batch manager not initialized")

        if self.storage_manager is None:
            raise RuntimeError("Storage manager not initialized")

        if self.pipeline_coordinator is None:
            raise RuntimeError("Pipeline coordinator not initialized")

        try:
            await self.storage_manager.create_batch_run(batch_id)
            self.progress_tracker.reset()
            await self.pipeline_coordinator.run_pipeline()
        except (StorytellerContentProcessingError, PluginError, PluginLoadError) as e:
            logger.error(
                "An unexpected error occurred during pipeline execution: %s", str(e)
            )
            raise RuntimeError("Pipeline execution failed") from e

    def get_current_batch_id(self) -> int:
        """
        Get the current batch ID.

        Returns:
            int: The current batch ID.
        """
        return self.batch_manager.get_current_batch_id()

    def get_batch_name(self) -> str:
        """
        Get the current batch name.

        Returns:
            str: The current batch name.
        """
        return self.batch_manager.get_batch_name()
