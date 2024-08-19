"""
PipelineCoordinator Module

This module contains the PipelineCoordinator class, which is responsible for orchestrating
the execution of the storytelling pipeline. It manages the flow of data and control
through various stages and phases of the storytelling process.

The PipelineCoordinator works in conjunction with the StageExecutor, StorytellerPhaseExecutor,
and StorytellerStageManager to ensure that each stage and phase of the pipeline is
executed in the correct order and with the appropriate data.

Key features:
- Sequentially executes enabled stages in the pipeline
- Manages the execution of individual phases within each stage
- Handles progress tracking and logging throughout the pipeline execution
- Provides error handling and reporting for stage and phase execution

Usage:
    from orchestration.storyteller_stage_executor import StageExecutor
    from orchestration.storyteller_phase_executor import StorytellerPhaseExecutor
    from storyteller_stage_manager import StorytellerStageManager
    from pipeline_coordinator import PipelineCoordinator

    stage_executor = StageExecutor(...)
    phase_executor = StorytellerPhaseExecutor(...)
    stage_manager = StorytellerStageManager(...)

    coordinator = PipelineCoordinator(stage_executor, phase_executor, stage_manager)
    
    # Run the entire pipeline
    await coordinator.run_pipeline()

Note:
    This module requires asyncio and should be run in an async environment.

Raises:
    RuntimeError: If an error occurs during pipeline or stage execution.
"""

import logging

from config.storyteller_configuration_manager import storyteller_config
from config.storyteller_configuration_types import StageConfig
from common.storyteller_exceptions import StorytellerContentProcessingError
from orchestration.storyteller_phase_executor import StorytellerPhaseExecutor
from orchestration.storyteller_stage_executor import StageExecutor
from orchestration.storyteller_stage_manager import StorytellerStageManager
from plugins.storyteller_plugin_manager import PluginError, PluginLoadError

logger = logging.getLogger(__name__)


class PipelineCoordinator:
    """Coordinates the execution of the storytelling pipeline."""

    def __init__(
        self,
        stage_executor: StageExecutor,
        phase_executor: StorytellerPhaseExecutor,
        stage_manager: StorytellerStageManager,
    ) -> None:
        """Initialize the PipelineCoordinator with necessary executors and managers.

        Args:
            stage_executor (StageExecutor): Executor for handling stage-level execution.
            phase_executor (StorytellerPhaseExecutor): Executor for handling phase-level execution.
            stage_manager (StorytellerStageManager): Manager for stage and phase data.
        """
        self.stage_executor = stage_executor
        self.phase_executor = phase_executor
        self.stage_manager = stage_manager
        self.config_manager = storyteller_config

    async def run_pipeline(self) -> None:
        """Run the pipeline for all enabled stages.

        This method executes each enabled stage in the pipeline sequentially.

        Raises:
            RuntimeError: If an error occurs during pipeline execution.
        """
        logger.info("Starting pipeline execution")

        try:
            stages = self.stage_manager.get_stages()
            for stage_index, stage in enumerate(stages):
                if stage["enabled"]:
                    logger.info("Running stage %d: %s", stage_index, stage["name"])
                    try:
                        await self.run_stage(stage)
                    except RuntimeError as e:
                        logger.error("Error in stage %s: %s", stage["name"], str(e))
                        break

                    # Check if there's a next stage before updating progress
                    if stage_index + 1 < len(stages):
                        self.stage_executor.progress_tracker.set_current_progress(
                            stage_index + 1, 0
                        )
                    else:
                        logger.info("All stages completed")

                    logger.info("Completed stage %d: %s", stage_index, stage["name"])

            logger.info("Pipeline execution completed successfully")
        except (PluginError, PluginLoadError) as e:
            logger.error(
                "An unexpected error occurred during pipeline execution: %s", str(e)
            )
            raise RuntimeError("Pipeline execution failed") from e

    async def run_stage(self, stage: StageConfig) -> None:
        """Execute the specified stage of the pipeline.

        Args:
            stage (Dict[str, Any]): The configuration dictionary for the stage to run.

        Raises:
            RuntimeError: If an error occurs during stage execution.
        """
        logger.info("Starting stage: %s", stage["display_name"])
        logger.info("Description: %s", stage["description"])

        for phase_index, phase in enumerate(stage["phases"]):
            try:
                await self.phase_executor.execute_phase(stage, phase)
                current_stage_index, _ = (
                    self.stage_executor.progress_tracker.get_current_progress()
                )

                # Check if this is the last phase in the stage
                if phase_index + 1 < len(stage["phases"]):
                    # If not the last phase, move to the next phase
                    self.stage_executor.progress_tracker.set_current_progress(
                        current_stage_index, phase_index + 1
                    )
                # If it's the last phase, don't update the progress here
                # The progress to the next stage will be handled in run_pipeline
            except (StorytellerContentProcessingError, PluginError, PluginLoadError) as e:
                logger.error(
                    "Error in phase %s_%s: %s", stage["name"], phase["name"], str(e)
                )
                raise RuntimeError(
                    f"Error in phase {stage['name']}_{phase['name']}: {str(e)}"
                ) from e

        logger.info("Completed stage: %s", stage["name"])
