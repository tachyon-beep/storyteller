"""
Storyteller Prompt Manager Module

This module contains the `StorytellerPromptManager` class, which is responsible for
preparing and managing prompts used in the storytelling orchestration pipeline.
It handles the replacement of placeholders in prompt templates, loads various
types of guidance, and interacts with other components of the storytelling system
to retrieve necessary information for prompt construction.

Usage:
    from storyteller_prompt_manager import StorytellerPromptManager
    from storyteller_configuration_manager import storyteller_config
    from storyteller_stage_manager import StorytellerStageManager, StorytellerProgressTracker
    from storyteller_orchestrator import PipelineOrchestrator
    from storyteller_plugin_manager import StorytellerPluginManager
    from storyteller_library import StorytellerLibrary

    stage_manager = StorytellerStageManager(storyteller_config)
    progress_tracker = StorytellerProgressTracker(storyteller_config)
    orchestrator = PipelineOrchestrator()
    plugin_manager = StorytellerPluginManager(storyteller_config)
    storyteller_library = StorytellerLibrary()

    prompt_manager = StorytellerPromptManager(
        stage_manager, progress_tracker, orchestrator, plugin_manager, storyteller_library
    )

    prepared_prompt = prompt_manager.prepare_prompt(stage, phase)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Match, Optional, Callable, TYPE_CHECKING
from pathlib import Path

from config.storyteller_configuration_manager import storyteller_config
from config.storyteller_configuration_types import StageConfig, PhaseConfig
from common.storyteller_types import StorytellerContentPacket
from common.storyteller_exceptions import (
    StorytellerConfigurationError,
    StorytellerInvalidContentTypeError,
    StorytellerInvalidGuidanceTypeError,
)
from content.storyteller_library import StorytellerLibrary
from orchestration.storyteller_stage_manager import (
    StorytellerStageManager,
    StorytellerProgressTracker,
)
from plugins.storyteller_plugin_manager import StorytellerPluginManager

if TYPE_CHECKING:
    from orchestration.storyteller_orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)

CONFIG_LOADER_NOT_INITIALIZED = "Configuration loader is not initialized"
PATH_MANAGER_NOT_INITIALIZED = "Path manager is not initialized"


class StorytellerPromptManager:
    """
    Manages the preparation and handling of prompts for the orchestration pipeline.

    This class is responsible for loading prompt templates, replacing placeholders,
    and incorporating various types of guidance into the prompts used at different
    stages of the orchestration process.

    Attributes:
        stage_manager (StorytellerStageManager): Manages the stages of the orchestration process.
        progress_tracker (StorytellerProgressTracker): Tracks the progress of the run.
        orchestrator (PipelineOrchestrator): Manages the overall pipeline execution.
        plugin_manager (StorytellerPluginManager): Manages the plugin system.
        config_manager (Any): Manages configuration settings.
        storyteller_library (StorytellerLibrary): Manages orchestration dynamic data sets.
        batch_pattern (re.Pattern): Compiled regex pattern for batch-related placeholders.
        output_pattern (re.Pattern): Compiled regex pattern for stage output placeholders.
        guidance_pattern (re.Pattern): Compiled regex pattern for guidance placeholders.
        plugin_guidance_pattern (re.Pattern): Compiled regex pattern for plugin-specific guidance placeholders.
        plugin_schema_pattern (re.Pattern): Compiled regex pattern for plugin-specific schema placeholders.
    """

    def __init__(
        self,
        stage_manager: StorytellerStageManager,
        progress_tracker: StorytellerProgressTracker,
        orchestrator: PipelineOrchestrator,
        plugin_manager: StorytellerPluginManager,
        storyteller_library: StorytellerLibrary
    ):
        """
        Initializes the StorytellerPromptManager.

        Args:
            stage_manager: An instance of StorytellerStageManager.
            progress_tracker: An instance of StorytellerProgressTracker.
            orchestrator: An instance of PipelineOrchestrator.
            plugin_manager: An instance of StorytellerPluginManager.
            storyteller_library: An instance of StorytellerLibrary.

        Raises:
            RuntimeError: If initialization of StorytellerLibrary fails.
        """
        self.stage_manager = stage_manager
        self.progress_tracker = progress_tracker
        self.orchestrator = orchestrator
        self.plugin_manager = plugin_manager
        self.config_manager = storyteller_config
        self.storyteller_library = storyteller_library

        try:
            logger.info("StorytellerLibrary initialized successfully.")
        except (OSError, IOError, ValueError) as error:
            logger.error("Failed to initialize StorytellerLibrary: %s", error)
            raise RuntimeError("Failed to initialize StorytellerLibrary") from error

        self.batch_pattern = re.compile(r"\{BATCH_(NAME|ID)\}")
        self.output_pattern = re.compile(
            r"\{OUTPUT:STAGE:(\w+)(?::PHASE:(\w+))?(?::FORMAT:(\w+))?\}"
        )
        self.guidance_pattern = re.compile(
            r"\{GUIDANCE:TYPE:(\w+)(?::(\w+))?(?::(\w+))?\}"
        )
        self.plugin_guidance_pattern = re.compile(r"\{GUIDANCE:PLUGIN:(\w+)\}")
        self.plugin_schema_pattern = re.compile(r"\{SCHEMA:PLUGIN:(\w+)\}")

    def prepare_prompt(self, stage: StageConfig, phase: PhaseConfig) -> str:
        """
        Prepares the prompt for a given phase by loading the template and replacing placeholders.

        Args:
            stage: The configuration dictionary for the current stage.
            phase: The configuration dictionary for the current phase.

        Returns:
            The prepared prompt with all placeholders replaced.

        Raises:
            FileNotFoundError: If the prompt template file is not found.
            IOError: If there's an error reading the prompt template file.
        """
        if self.config_manager.path_manager is None:
            raise StorytellerConfigurationError(PATH_MANAGER_NOT_INITIALIZED)

        logger.info("Preparing prompt for stage '%s', phase '%s'", stage["name"], phase["name"])

        prompt_file = self.config_manager.path_manager.get_prompt_path(phase["prompt_file"])
        try:
            with open(prompt_file, "r", encoding="utf-8") as file:
                prompt_content = file.read()
        except FileNotFoundError:
            logger.error("Prompt file not found: %s", prompt_file)
            raise
        except IOError as e:
            logger.error("Error reading prompt file %s: %s", prompt_file, e)
            raise

        if not prompt_content:
            logger.warning("Prompt file is empty: %s", prompt_file)

        prompt_content = self.replace_content_placeholders(prompt_content)
        prompt_content = self.replace_process_placeholders(prompt_content, stage, phase)
        return prompt_content

    def replace_content_placeholders(self, prompt_content: str) -> str:
        """
        Replaces content placeholders in the prompt template with actual values.

        Args:
            prompt_content: The original prompt content with placeholders.

        Returns:
            The prompt content with content placeholders replaced.
        """
        current_stage_index, current_phase_index = self.progress_tracker.get_current_progress()
        logger.debug(
            "Replacing content placeholders for stage %s, phase %s",
            current_stage_index,
            current_phase_index,
        )

        if not self.storyteller_library.data:
            logger.warning("StorytellerLibrary is empty, skipping content placeholder replacement")
            return prompt_content

        for key in self.storyteller_library.get_keys():
            try:
                tag = self.storyteller_library.get_tag(key)
                values = self.storyteller_library.get_value(key)

                # Handle different types of values
                if isinstance(values, list):
                    replacement = self._handle_list_values(values)
                elif isinstance(values, StorytellerContentPacket):
                    replacement = self._get_content_safely(values)
                else:
                    replacement = str(values)

                # Replace the placeholder in the prompt content (handle both formats)
                curly_placeholder = tag  # The tag is already wrapped in curly braces
                square_placeholder = f"[{tag}]"

                if curly_placeholder in prompt_content:
                    prompt_content = prompt_content.replace(curly_placeholder, replacement)
                    logger.debug("Replaced placeholder '%s' with '%s'", curly_placeholder, replacement)
                elif square_placeholder in prompt_content:
                    prompt_content = prompt_content.replace(square_placeholder, replacement)
                    logger.debug("Replaced placeholder '%s' with '%s'", square_placeholder, replacement)
                else:
                    logger.debug("Placeholder '%s' not found in prompt content", tag)

            except KeyError:
                logger.error("Placeholder '%s' not found in StorytellerLibrary data.", key)
            except (TypeError, ValueError, AttributeError) as e:
                logger.error("Error processing placeholder '%s': %s", key, e)

        return prompt_content

    def _handle_list_values(self, values: list) -> str:
        """
        Handles list values, converting them to a string representation.

        Args:
            values: A list of values to process.

        Returns:
            A string representation of the list values.
        """
        if all(isinstance(item, StorytellerContentPacket) for item in values):
            return ", ".join(self._get_content_safely(packet) for packet in values if self._get_content_safely(packet))
        else:
            return ", ".join(str(value) for value in values if value)

    def _get_content_safely(self, packet: Any) -> str:
        """
        Safely retrieves the content from a StorytellerContentPacket or converts the input to a string.

        Args:
            packet: A StorytellerContentPacket or any other object.

        Returns:
            The content as a string, or an empty string if content is not available.
        """
        if isinstance(packet, StorytellerContentPacket) and hasattr(packet, 'content'):
            return str(packet.content) if packet.content is not None else ""
        return str(packet)

    def replace_process_placeholders(
        self, prompt: str, stage: StageConfig, phase: PhaseConfig
    ) -> str:
        """
        Replaces process placeholders in the prompt with dynamic content.

        Args:
            prompt: The prompt content with process placeholders.
            stage: The configuration dictionary for the current stage.
            phase: The configuration dictionary for the current phase.

        Returns:
            The prompt with process placeholders replaced.
        """
        placeholder_handlers = self._get_placeholder_handlers(stage, phase)

        for pattern, handler in placeholder_handlers.items():
            prompt = self._handle_placeholder_matches(prompt, pattern, handler)

        return prompt

    def _get_placeholder_handlers(self, stage: StageConfig, phase: PhaseConfig):
        return {
            self.output_pattern: self.process_output_placeholder,
            self.guidance_pattern: self.process_guidance_placeholder,
            self.plugin_schema_pattern: lambda m: self.process_plugin_schema_placeholder(
                m, stage["name"], phase["name"]
            ),
            self.batch_pattern: self.process_batch_placeholder,
            self.plugin_guidance_pattern: self.process_plugin_guidance_placeholder,
        }

    def _handle_placeholder_matches(self, prompt: str, pattern: re.Pattern, handler: Callable) -> str:
        matches = list(pattern.finditer(prompt))
        for match in matches:
            try:
                replacement = handler(match)
                prompt = prompt.replace(match.group(), replacement)
                logger.debug("Replaced placeholder '%s'", match.group())
            except (ValueError, KeyError, AttributeError, IOError, FileNotFoundError) as e:
                logger.error("Error processing placeholder '%s': %s", match.group(), e)
                prompt = prompt.replace(match.group(), f"[Error: {e}]")
        return prompt

    def process_output_placeholder(self, match: Match[str]) -> str:
        """
        Processes output placeholders and fetches corresponding content.

        Args:
            match: A regex match object for the output placeholder.

        Returns:
            The formatted content for the output placeholder.

        Raises:
            KeyError: If there's an error fetching output content.
            ValueError: If there's an error formatting content.
            AttributeError: If there's an error processing the output placeholder.
        """
        stage, phase, format_type = match.groups()
        logger.debug("Processing output placeholder for stage '%s', phase '%s'", stage, phase)
        try:
            content = self._fetch_output_content(stage, phase)
            return self._format_content(content, format_type)
        except (KeyError, ValueError, AttributeError) as e:
            logger.error("Error processing output placeholder: %s", e)
            raise

    def process_guidance_placeholder(self, match: Match[str]) -> str:
        """
        Processes guidance placeholders and fetches corresponding guidance.

        Args:
            match: A regex match object for the guidance placeholder.

        Returns:
            The content for the guidance placeholder.

        Raises:
            InvalidGuidanceTypeError: If an invalid guidance type is provided.
            FileNotFoundError: If the guidance file is not found.
            IOError: If there's an error reading the guidance file.
        """
        guidance_type, stage, phase = match.groups()
        guidance_type = guidance_type.lower() if guidance_type else ""
        logger.debug("Processing guidance placeholder for type '%s'", guidance_type)
        try:
            if guidance_type in ["stage", "generic"]:
                return self._get_guidance_content(guidance_type, stage, phase)
            else:
                # Handle plugin-specific guidance
                plugin_guidance_string = f"{{GUIDANCE:PLUGIN:{guidance_type}}}"
                plugin_match = re.match(self.plugin_guidance_pattern, plugin_guidance_string)
                if plugin_match:
                    return self.process_plugin_guidance_placeholder(plugin_match)
                else:
                    raise StorytellerInvalidGuidanceTypeError(f"Invalid guidance type: {guidance_type}")
        except (StorytellerInvalidGuidanceTypeError, FileNotFoundError, IOError) as e:
            logger.error("Error processing guidance placeholder: %s", e)
            raise

    def process_plugin_schema_placeholder(
        self, match: Match[str], stage_name: str, phase_name: str
    ) -> str:
        """
        Processes plugin-specific schema placeholders.
        This method first checks for a phase-specific schema, and if not found,
        falls back to the default plugin schema.

        Args:
            match: A regex match object for the plugin schema placeholder.
            stage_name: The name of the current stage.
            phase_name: The name of the current phase.

        Returns:
            The content of the schema (either phase-specific or plugin default).

        Raises:
            ValueError: If no schema is found for the plugin.
        """
        plugin_name = match.group(1).lower()
        logger.debug("Processing plugin schema placeholder for plugin '%s'", plugin_name)

        has_schema, phase_schema = self.stage_manager.get_phase_schema(stage_name, phase_name)
        if has_schema and phase_schema is not None:
            return str(phase_schema)

        plugin_schema = self.plugin_manager.get_plugin_schema(plugin_name)
        if plugin_schema:
            return str(plugin_schema)

        logger.warning("No schema found for plugin: %s", plugin_name)
        raise ValueError(f"No schema found for plugin: {plugin_name}")

    def process_batch_placeholder(self, match: Match[str]) -> str:
        """
        Processes batch-related placeholders.

        Args:
            match: A regex match object for the batch placeholder.

        Returns:
            The batch name or ID.
        """
        placeholder_type = match.group(1)
        logger.debug("Processing batch placeholder of type '%s'", placeholder_type)
        if placeholder_type == "NAME":
            return self.orchestrator.get_batch_name()
        elif placeholder_type == "ID":
            return str(self.orchestrator.get_current_batch_id())
        return match.group(0)  # Return the original placeholder if not recognized

    def process_plugin_guidance_placeholder(self, match: Match[str]) -> str:
        """
        Processes plugin-specific guidance placeholders.

        Args:
            match: A regex match object for the plugin guidance placeholder.

        Returns:
            The content of the plugin-specific guidance.

        Raises:
            ValueError: If an invalid plugin name is provided or no guidance file is specified.
            FileNotFoundError: If the guidance file is not found.
            IOError: If there's an error reading the guidance file.
            StorytellerConfigurationError: If the path manager or config loader is not initialized.
        """
        if self.config_manager.path_manager is None:
            raise StorytellerConfigurationError(PATH_MANAGER_NOT_INITIALIZED)

        plugin_name = match.group(1).lower()
        logger.debug("Processing plugin guidance placeholder for plugin '%s'", plugin_name)
        try:
            plugin_config = self.config_manager.get_plugin_config().get(plugin_name)
            if not plugin_config or 'guidance' not in plugin_config:
                raise ValueError(f"No guidance file specified for plugin: {plugin_name}")

            guidance_file = plugin_config['guidance']
            plugins_path = self.config_manager.path_manager.get_path('plugins')

            if plugins_path is None:
                raise StorytellerConfigurationError("Plugins path is not set in the configuration")
            if not isinstance(plugins_path, Path):
                raise StorytellerConfigurationError("Plugins path is not a valid Path object")
            if guidance_file is None:
                raise ValueError(f"Guidance file for plugin '{plugin_name}' is None")

            guidance_path = plugins_path / plugin_name / guidance_file

            if self.config_manager.config_loader is None:
                raise StorytellerConfigurationError(CONFIG_LOADER_NOT_INITIALIZED)

            content = self.config_manager.config_loader.load_text(guidance_path)
            if not content:
                logger.warning("Plugin guidance file is empty: %s", guidance_path)
            return content
        except (ValueError, FileNotFoundError, IOError) as e:
            logger.error("Error processing plugin guidance placeholder: %s", e)
            raise
        except StorytellerConfigurationError as e:
            logger.error("Configuration error: %s", e)
            raise

    def _fetch_output_content(self, stage: str, phase: Optional[str]) -> str:
        """
        Fetches content based on stage and phase.

        Args:
            stage: The name of the stage.
            phase: The name of the phase, or None to get the last phase.

        Returns:
            The fetched content.

        Raises:
            ValueError: If the stage or phase is invalid.
            KeyError: If the stage or phase is not found in the configuration.
            AttributeError: If there's an unexpected structure in the stage configuration.
        """
        stage_config = self.stage_manager.get_stage_by_name(stage)
        if not stage_config:
            raise ValueError(f"Invalid stage: {stage}")

        if phase:
            phase_index = self.stage_manager.get_phase_index_by_name(stage, phase)
        else:
            phase_index = len(stage_config["phases"]) - 1

        if not stage_config["phases"]:
            raise ValueError(f"No phases found for stage: {stage}")

        phase_name = stage_config["phases"][phase_index]["name"]
        content = self.progress_tracker.get_story_data(stage, phase_name)

        if content is None:
            raise ValueError(f"No content found for stage '{stage}' and phase '{phase_name}'")

        if not isinstance(content, StorytellerContentPacket):
            raise AttributeError("Content is not a StorytellerContentPacket")
        return content.content

    def _format_content(self, content: Any, format_type: Optional[str]) -> str:
        """
        Formats content based on the specified format type using the appropriate plugin.

        Args:
            content: The content to format.
            format_type: The format type, or None for default formatting.

        Returns:
            The formatted content.

        Raises:
            ValueError: If an unsupported format type is provided.
        """
        if format_type is None:
            return self._convert_content_to_string(content)

        try:
            plugin = self.plugin_manager.get_plugin(format_type.lower())
            processed_content = plugin.process(content)
            return (
                json.dumps(processed_content, indent=2)
                if isinstance(processed_content, (dict, list))
                else str(processed_content)
            )
        except ValueError as e:
            logger.error("Error formatting content: %s", e)
            raise

    def _get_guidance_content(
        self, guidance_type: str, stage: Optional[str], _phase: Optional[str]
    ) -> str:
        """
        Fetches guidance content based on type and stage.

        Args:
            guidance_type: The type of guidance.
            stage: The name of the stage, or None.
            _phase: The name of the phase, or None (unused).

        Returns:
            The fetched guidance content.

        Raises:
            ValueError: If an invalid guidance type is provided.
            FileNotFoundError: If the guidance file is not found.
            IOError: If there's an error reading the guidance file.
        """
        if self.config_manager.config_loader is None:
            raise StorytellerConfigurationError(CONFIG_LOADER_NOT_INITIALIZED)
        if self.config_manager.path_manager is None:
            raise StorytellerConfigurationError(PATH_MANAGER_NOT_INITIALIZED)

        guidance_path: Optional[Path] = None

        try:
            if guidance_type == "stage":
                if not stage:
                    raise ValueError("Stage name is required for stage-specific guidance")
                guidance_path = self.config_manager.path_manager.get_stage_specific_guidance_path(stage)
            elif guidance_type == "generic":
                guidance_path = self.config_manager.path_manager.get_run_specific_guidance_path("generic")
            else:
                raise ValueError(f"Invalid guidance type: {guidance_type}")

            content = self.config_manager.config_loader.load_text(guidance_path)
            if not content:
                logger.warning("Guidance file is empty: %s", guidance_path)
            return content

        except FileNotFoundError:
            logger.error("Guidance file not found: %s", guidance_path)
            raise
        except IOError as e:
            logger.error("Error reading guidance file %s: %s", guidance_path, e)
            raise

    def _convert_content_to_string(self, content: Any) -> str:
        """
        Converts the given content to a string representation.

        Args:
            content: The content to be converted to a string.

        Returns:
            The string representation of the content.
        """
        if content is None:
            return "None"
        if isinstance(content, (dict, list)):
            try:
                return json.dumps(content, indent=2)
            except TypeError as e:
                logger.error("Error converting content to JSON: %s", e)
                return str(content)
        return str(content)

    def get_content(
        self,
        content_type: str,
        stage: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> str:
        """
        Gets content based on the specified type, stage, and phase.

        Args:
            content_type: The type of content to retrieve ("stage_guidance" or "phase_schema").
            stage: The name of the stage (required for "stage_guidance").
            phase: The name of the phase (required for "phase_schema").

        Returns:
            The content based on the specified type.

        Raises:
            InvalidContentTypeError: If an invalid content type is provided.
            ValueError: If required parameters are missing.
        """
        logger.debug(
            "Getting content of type '%s' for stage '%s', phase '%s'",
            content_type, stage, phase
        )
        try:
            if content_type == "stage_guidance":
                if stage is None:
                    raise ValueError("stage is required for 'stage_guidance' content type")
                stage_info = self.stage_manager.get_stage_by_name(stage)
                if stage_info is None:
                    raise ValueError(f"Stage '{stage}' not found")
                stage_index = stage_info.get("index")
                if stage_index is None:
                    raise ValueError(f"Stage '{stage}' does not have an index")
                return self.load_guidance("stage", stage_index)

            elif content_type == "phase_schema":
                if stage is None or phase is None:
                    raise ValueError("stage and phase are required for 'phase_schema' content type")
                schema = self.stage_manager.get_phase_schema(stage, phase)
                if schema is None:
                    raise ValueError(f"No schema found for stage '{stage}' and phase '{phase}'")
                return json.dumps(schema, indent=2)

            else:
                raise StorytellerInvalidContentTypeError(f"Invalid content type: {content_type}")

        except (StorytellerInvalidContentTypeError, ValueError) as e:
            logger.error("Error getting content for type %s: %s", content_type, e)
            raise

    def load_guidance(
        self, guidance_type: str, stage_index: Optional[int] = None
    ) -> str:
        """
        Loads guidance content based on the type and optional stage index.

        Args:
            guidance_type: The type of guidance to load ("generic" or "stage").
            stage_index: The index of the stage (required for "stage" type).

        Returns:
            The content of the guidance file.

        Raises:
            InvalidGuidanceTypeError: If an invalid guidance type is provided.
            ValueError: If stage_index is missing for "stage" type.
            FileNotFoundError: If the guidance file is not found.
            IOError: If there's an error reading the guidance file.
        """
        if self.config_manager.path_manager is None:
            raise StorytellerConfigurationError(PATH_MANAGER_NOT_INITIALIZED)

        guidance_file: Optional[Path] = None
        logger.debug("Loading guidance for type '%s'", guidance_type)

        try:
            if guidance_type == "generic":
                guidance_file = self.config_manager.path_manager.get_run_specific_guidance_path("generic")
            elif guidance_type == "stage":
                if stage_index is None:
                    raise ValueError("stage_index is required for 'stage' guidance type")
                stage = self.stage_manager.get_stage(stage_index)
                if not stage:
                    logger.warning("No stage found for index %d", stage_index)
                    return ""
                guidance_file = self.config_manager.path_manager.get_run_specific_guidance_path(stage["name"])
            else:
                raise StorytellerInvalidGuidanceTypeError(f"Invalid guidance type: {guidance_type}")

            if self.config_manager.config_loader is None:
                raise StorytellerConfigurationError(CONFIG_LOADER_NOT_INITIALIZED)
            content = self.config_manager.config_loader.load_text(guidance_file)
            if not content:
                logger.warning("Guidance file is empty: %s", guidance_file)
            logger.info("Successfully loaded guidance for type: %s", guidance_type)
            return content
        except FileNotFoundError:
            logger.error("Guidance file not found: %s", guidance_file)
            raise
        except IOError as e:
            logger.error("Error reading guidance file %s: %s", guidance_file, e)
            raise
