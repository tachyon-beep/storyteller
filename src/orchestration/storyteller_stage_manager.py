"""
Storyteller Stage Manager and Progress Tracker Module

This module provides the StorytellerStageManager and StorytellerProgressTracker classes
for managing pipeline stages and tracking progress in the storytelling system.

The StorytellerStageManager is the authoritative source for stage and phase information
in the storytelling pipeline.

The StorytellerProgressTracker is responsible for tracking and managing the progress
of the storytelling pipeline.

Usage Example:
    from storyteller_stage_manager import StorytellerStageManager, StorytellerProgressTracker
    from storyteller_configuration_manager import storyteller_config

    config_manager = StorytellerConfigurationManager()
    stage_manager = StorytellerStageManager()
    progress_tracker = StorytellerProgressTracker(stage_manager)

    current_stage = stage_manager.get_current_stage()
    print(f"Current Stage: {current_stage['name']}")

    next_stage = stage_manager.get_next_stage()
    if next_stage:
        print(f"Next Stage: {next_stage['name']}")
    else:
        print("Pipeline is complete.")

    # Update progress
    progress_tracker.update_story_data("WORLD_BUILDING", "A", world_building_data)

    # Get current progress
    stage_index, phase_index = progress_tracker.get_current_progress()

    # Retrieve story data
    world_building_data = progress_tracker.get_story_data("WORLD_BUILDING", "A")
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from config.storyteller_configuration_manager import storyteller_config
from config.storyteller_configuration_types import StageConfig, PhaseConfig

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StorytellerStageManager:
    """
    Manages stages and phases for the storytelling pipeline.

    This class is the sole manager of stage and phase data, providing methods to access
    stages and phases based on indices or names.

    Attributes:
        stages (List[Dict[str, Any]]): List of enabled stages from the configuration.
        stage_name_to_index (Dict[str, int]): Mapping of stage names to their indices.
        phase_name_to_index (Dict[str, Dict[str, int]]): Mapping of phase names to their indices within each stage.
    """

    def __init__(self) -> None:
        """
        Initialize the StageManager with the pipeline configuration.

        Raises:
            RuntimeError: If stages cannot be loaded from the configuration.
        """
        self.config_manager = storyteller_config
        self.stages = self._load_enabled_stages()
        self.stage_name_to_index = self._create_stage_name_index_mapping()
        self.phase_name_to_index = self._create_phase_name_index_mapping()
        logger.debug(
            "Initialized StorytellerStageManager with stages: %s",
            list(self.stage_name_to_index.keys()),
        )

    def _load_enabled_stages(self) -> List[StageConfig]:
        """
        Load all enabled stages from the configuration.

        Returns:
            List[Dict[str, Any]]: A list of enabled stage configurations.

        Raises:
            RuntimeError: If stages cannot be loaded from the configuration.
        """
        try:
            stages = self.config_manager.get_stage_config()
            return [stage for stage in stages if stage.get("enabled", False)]
        except Exception as exc:
            logger.error("Failed to load stages from configuration: %s", str(exc))
            raise RuntimeError("Failed to load stages from configuration") from exc

    def _create_stage_name_index_mapping(self) -> Dict[str, int]:
        """
        Create a mapping of stage names to their indices.

        Returns:
            Dict[str, int]: A dictionary mapping stage names to their indices.
        """
        return {stage["name"]: index for index, stage in enumerate(self.stages)}

    def _create_phase_name_index_mapping(self) -> Dict[str, Dict[str, int]]:
        """
        Create a mapping of phase names to their indices within each stage.

        Returns:
            Dict[str, Dict[str, int]]: A nested dictionary mapping stage names to phase names to their indices.
        """
        return {
            stage["name"]: {
                phase["name"]: index for index, phase in enumerate(stage["phases"])
            }
            for stage in self.stages
        }

    def get_stage(self, stage_index: int) -> Optional[StageConfig]:
        """
        Get a specific stage by index.

        Args:
            stage_index (int): The index of the stage to retrieve.

        Returns:
            Optional[Dict[str, Any]]: The stage configuration, or None if the index is out of range.
        """
        if 0 <= stage_index < len(self.stages):
            return self.stages[stage_index]
        return None

    def get_phase(self, stage_index: int, phase_index: int) -> Optional[PhaseConfig]:
        """
        Get a specific phase by stage index and phase index.

        Args:
            stage_index (int): The index of the stage.
            phase_index (int): The index of the phase within the stage.

        Returns:
            Optional[Dict[str, Any]]: The phase configuration, or None if the indices are out of range.

        Raises:
            IndexError: If either stage_index or phase_index is out of range.
        """
        if 0 <= stage_index < len(self.stages):
            stage = self.stages[stage_index]
            phases = stage.get("phases", [])
            if 0 <= phase_index < len(phases):
                return phases[phase_index]
            raise IndexError(
                f"Phase index {phase_index} is out of range for stage {stage_index}"
            )

        raise IndexError(f"Stage index {stage_index} is out of range")

    def get_stage_name(self, stage_index: int) -> str:
        """
        Get the name of the stage at the specified index.

        Args:
            stage_index (int): The index of the stage.

        Returns:
            str: The name of the stage.

        Raises:
            IndexError: If the stage index is out of range.
        """
        if 0 <= stage_index < len(self.stages):
            return self.stages[stage_index]["name"]
        raise IndexError(f"Stage index {stage_index} is out of range")

    def get_stages(self) -> List[StageConfig]:
        """
        Get all active (enabled) stages known to the stage manager.

        Returns:
            List[Dict[str, Any]]: A list of all active stage configurations.
        """
        return self.stages.copy()

    def get_phase_name(self, stage_index: int, phase_index: int) -> str:
        """
        Get the name of the phase at the specified indices.

        Args:
            stage_index (int): The index of the stage.
            phase_index (int): The index of the phase within the stage.

        Returns:
            str: The name of the phase.

        Raises:
            IndexError: If either stage_index or phase_index is out of range.
        """
        if 0 <= stage_index < len(self.stages):
            stage = self.stages[stage_index]
            phases = stage.get("phases", [])
            if 0 <= phase_index < len(phases):
                return phases[phase_index]["name"]
            raise IndexError(
                f"Phase index {phase_index} is out of range for stage {stage_index}"
            )
        raise IndexError(f"Stage index {stage_index} is out of range")

    def get_stage_index_by_name(self, stage_name: str) -> int:
        """
        Get the index of a stage by its name.

        Args:
            stage_name (str): The name of the stage to find.

        Returns:
            int: The index of the stage.

        Raises:
            ValueError: If the stage is not found.
        """
        try:
            return self.stage_name_to_index[stage_name]
        except KeyError as exc:
            raise ValueError(f"Stage '{stage_name}' not found") from exc

    def get_phase_index_by_name(self, stage_name: str, phase_name: str) -> int:
        """
        Get the index of a phase within a stage by their names.

        Args:
            stage_name (str): The name of the stage.
            phase_name (str): The name of the phase.

        Returns:
            int: The index of the phase within the stage.

        Raises:
            ValueError: If the stage or phase is not found.
        """
        try:
            return self.phase_name_to_index[stage_name][phase_name]
        except KeyError as exc:
            raise ValueError(
                f"Phase '{phase_name}' not found in stage '{stage_name}'"
            ) from exc

    def get_stage_by_name(self, stage_name: str) -> Optional[StageConfig]:
        """
        Get a specific stage by name.

        Args:
            stage_name (str): The name of the stage to retrieve.

        Returns:
            Optional[Dict[str, Any]]: The stage configuration, or None if not found.
        """
        try:
            index = self.stage_name_to_index[stage_name]
            return self.stages[index]
        except KeyError:
            return None

    def is_valid_stage(self, stage_name: str) -> bool:
        """
        Check if a given stage name is valid.

        Args:
            stage_name (str): The name of the stage to check.

        Returns:
            bool: True if the stage name is valid, False otherwise.
        """
        return stage_name in self.stage_name_to_index

    def get_all_stage_names(self) -> List[str]:
        """
        Get a list of all stage names.

        Returns:
            List[str]: A list of all stage names.
        """
        return list(self.stage_name_to_index.keys())

    def get_phase_temperature(self, stage_index: int, phase_index: int) -> float:
        """
        Get the temperature for a specific phase.

        Args:
            stage_index (int): The index of the stage.
            phase_index (int): The index of the phase within the stage.

        Returns:
            float: The temperature for the specified phase.

        Raises:
            ValueError: If the stage or phase index is invalid, or if the temperature is missing.
        """
        try:
            stage = self.stages[stage_index]
            phase = stage["phases"][phase_index]
            default_temperature = self.config_manager.get_llm_config().get("default_temperature")

            temperature = phase.get(
                "temperature",
                default_temperature
            )

            logger.debug(
                "Retrieved temperature %s for stage %s, phase %s (indices: %d, %d)",
                temperature,
                stage["name"],
                phase["name"],
                stage_index,
                phase_index,
            )
            assert isinstance(temperature, float), "No temp for LLM."
            return temperature
        except (IndexError, KeyError) as exc:
            logger.error(
                "Error retrieving temperature for stage %d, phase %d: %s",
                stage_index,
                phase_index,
                exc,
            )
            raise ValueError(
                "Invalid stage or phase index, or missing temperature"
            ) from exc

    def get_phase_schema(self, stage_name: str, phase_name: str) -> Tuple[bool, Optional[str]]:
        """
        Get the schema for a specific phase within a stage.

        Args:
            stage_name (str): The name of the stage.
            phase_name (str): The name of the phase.

        Returns:
            Tuple[bool, Optional[str]]: A tuple where the first element is a boolean indicating
            whether a schema was found, and the second element is the schema string if found,
            or None if not found.

        Raises:
            RuntimeError: If the path manager or config loader is not initialized.
            ValueError: If the stage or phase is not found.
        """
        try:
            stage_index = self.get_stage_index_by_name(stage_name)
            phase_index = self.get_phase_index_by_name(stage_name, phase_name)
            phase = self.get_phase(stage_index, phase_index)

            if self.config_manager.path_manager is None or self.config_manager.config_loader is None:
                raise RuntimeError("Can't get schema without path manager or config loader.")

            if phase and "schema" in phase:
                schema_file = phase["schema"]
                if schema_file:  # Ensure schema_file is not None
                    schema_path = self.config_manager.path_manager.get_schema_path(schema_file)
                    return True, self.config_manager.config_loader.load_text(schema_path)

            return False, None

        except (ValueError, IndexError) as exc:
            logger.error(
                "Error retrieving schema for stage %s, phase %s: %s",
                stage_name,
                phase_name,
                str(exc),
            )
            return False, None


class StorytellerProgressTracker:
    """
    Manages progress tracking for the storytelling pipeline.

    This class is responsible for tracking the current state of the pipeline,
    including current stage and phase indices and story data.

    Attributes:
        story_data (Dict[str, Dict[str, Any]]): Storage for generated content indexed by stage and phase.
        current_stage_index (int): Index of the current stage in the pipeline.
        current_phase_index (int): Index of the current phase in the current stage.
    """

    def __init__(self, stage_manager: StorytellerStageManager) -> None:
        """
        Initialize the StorytellerProgressTracker.
        """
        self.story_data: Dict[str, Dict[str, Any]] = {}
        self.current_stage_index: int = 0
        self.current_phase_index: int = 0
        self.stage_manager = stage_manager

    def reset(self) -> None:
        """
        Reset the progress tracker to its initial state.

        This method clears all story data and resets the current stage and phase indices to 0.
        """
        self.story_data.clear()
        self.current_stage_index = 0
        self.current_phase_index = 0
        logger.info("Progress tracker reset")

    def get_current_progress(self) -> Tuple[int, int]:
        """
        Get the current progress of the pipeline.

        Returns:
            Tuple[int, int]: A tuple containing the current stage index and phase index.
        """
        return self.current_stage_index, self.current_phase_index

    def set_current_progress(
        self, stage_index: int, phase_index: int
    ) -> None:
        """
        Set the current progress of the pipeline.

        Args:
            stage_index (int): The index of the current stage.
            phase_index (int): The index of the current phase.

        Raises:
            ValueError: If stage_index or phase_index is negative or out of range.
        """
        stages = self.stage_manager.get_stages()

        if stage_index < 0 or stage_index >= len(stages):
            raise ValueError(f"Invalid stage_index: {stage_index}")

        current_stage = stages[stage_index]
        phases = current_stage.get("phases", [])

        if phase_index < 0 or phase_index >= len(phases):
            raise ValueError(f"Invalid phase_index: {phase_index}")

        self.current_stage_index = stage_index
        self.current_phase_index = phase_index
        logger.debug(
            "Set current progress to stage %d, phase %d", stage_index, phase_index
        )

    def update_story_data(
        self,
        stage_name: str,
        phase_name: str,
        content: Any,
    ) -> None:
        """
        Update the story data for a specific stage and phase.

        Args:
            stage_name (str): The name of the stage.
            phase_name (str): The name of the phase.
            content (Any): The content to be stored for this stage and phase.

        Raises:
            ValueError: If the stage_name or phase_name is invalid.
        """
        if not self.stage_manager.is_valid_stage(stage_name):
            raise ValueError(f"Invalid stage name: {stage_name}")

        if stage_name not in self.story_data:
            self.story_data[stage_name] = {}

        if phase_name not in self.stage_manager.phase_name_to_index[stage_name]:
            raise ValueError(
                f"Invalid phase name: {phase_name} for stage: {stage_name}"
            )

        self.story_data[stage_name][phase_name] = content
        logger.debug("Updated story data for %s_%s", stage_name, phase_name)

    def get_story_data(self, stage_name: str, phase_name: str) -> Optional[Any]:
        """
        Retrieve the story data for a specific stage and phase.

        Args:
            stage_name (str): The name of the stage.
            phase_name (str): The name of the phase.

        Returns:
            Optional[Any]: The story data for the specified stage and phase, or None if not found.
        """
        return self.story_data.get(stage_name, {}).get(phase_name)

    def get_all_story_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all story data.

        Returns:
            Dict[str, Dict[str, Any]]: A dictionary containing all story data.
        """
        return dict(self.story_data)

    def get_progress_summary(self) -> str:
        """
        Get a summary of the current progress.

        Returns:
            str: A string summarizing the current progress.
        """
        stages = self.stage_manager.get_stages()
        current_stage = stages[self.current_stage_index]
        current_phase = current_stage["phases"][self.current_phase_index]

        completed_phases = sum(
            len(stage_data) for stage_data in self.story_data.values()
        )
        total_phases = sum(len(stage.get("phases", [])) for stage in stages)

        return (
            f"Current progress: Stage '{current_stage['name']}', Phase '{current_phase['name']}'. "
            f"Completed {completed_phases} out of {total_phases} total phases."
        )
