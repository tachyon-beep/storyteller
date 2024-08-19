"""
SubtextOutputPlugin Module

This module provides the SubtextOutputPlugin class for extracting and processing subtext content
in the storytelling pipeline. It extends the StorytellerOutputPlugin base class to offer
subtext-specific functionality.

The plugin handles extraction and processing of subtext content,
ensuring that only the relevant content between specified tags is processed.

Usage:
    config = {
        "debug": True,
        "start_tag": "%%% SUBTEXT START %%%",
        "end_tag": "%%% SUBTEXT END %%%"
    }
    plugin = SubtextOutputPlugin(config)
    plugin.initialise_plugin(Path("/path/to/plugin"), storage_manager)
    processed_content = plugin.process("raw content with subtext tags")
"""

import logging
from typing import Any, Dict, Optional
from pathlib import Path

from plugins.storyteller_output_plugin import StorytellerOutputPlugin

logger = logging.getLogger(__name__)


class SubtextOutputPlugin(StorytellerOutputPlugin):
    """
    Plugin for extracting and processing subtext content.

    This plugin handles the extraction and processing of subtext content
    in the storytelling pipeline.

    Attributes:
        start_tag (str): Tag marking the start of subtext content.
        end_tag (str): Tag marking the end of subtext content.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the SubtextOutputPlugin.

        Args:
            config: Configuration dictionary for the plugin.
        """
        super().__init__(config)
        self.start_tag: str = config.get("start_tag", "%%% SUBTEXT START %%%")
        self.end_tag: str = config.get("end_tag", "%%% SUBTEXT END %%%")

    def initialise_plugin(self, plugin_dir: Path, storage_manager: Any) -> None:
        """
        Initialize the plugin with its directory and storage manager.

        Args:
            plugin_dir: Directory containing plugin-specific files.
            storage_manager: Instance of the storage manager.
        """
        super().initialise_plugin(plugin_dir, storage_manager)
        logger.debug("Initializing Subtext plugin")

    def extract_content(self, raw_content: str) -> str:
        """
        Extract subtext content from between start and end tags.

        Args:
            raw_content: The raw content containing subtext data.

        Returns:
            str: Extracted subtext content as a string.
        """
        start_index = raw_content.find(self.start_tag)
        end_index = raw_content.find(self.end_tag)

        if start_index == -1 or end_index == -1 or start_index >= end_index:
            logger.warning("Subtext markers not found or are in incorrect order. Returning original content.")
            return raw_content

        return raw_content[start_index + len(self.start_tag): end_index].strip()

    async def process(self, content: str) -> str:
        """
        Process the extracted subtext content.

        Args:
            content: The subtext content to process.

        Returns:
            str: Processed subtext content as a string.
        """
        logger.debug("Process method received content of type: %s", type(content))

        extracted_content = self.extract_content(content)
        return extracted_content

    async def validate_content(self, content: str, schema: Optional[str] = None) -> bool:
        """
        Validate the processed subtext content.

        For subtext, we consider all extracted content valid.

        Args:
            content: The subtext content to validate as a string.
            schema: Unused for subtext validation.

        Returns:
            bool: Always returns True for subtext.
        """
        return True

    async def repair(self, content: str) -> str:
        """
        Attempt to repair invalid subtext content.

        For subtext, we don't perform any repairs and return the content as is.

        Args:
            content: The subtext content.

        Returns:
            str: The original subtext content.
        """
        return content

    def get_format(self) -> str:
        """
        Get the format handled by this plugin.

        Returns:
            str: The string "subtext".
        """
        return "subtext"

    def get_extension(self) -> str:
        """
        Get the file extension for the output format.

        Returns:
            str: The string "txt".
        """
        return "txt"

    async def attempt_repair(
        self,
        content: str,
        llm_generator: Any,
        storage_manager: Any,
        stage_name: str,
        phase_name: str,
        timeout: float = 30.0,
        deterministic_temp: float = 0.0,
    ) -> str:
        """
        Attempt to repair invalid subtext content.

        For subtext, we don't perform any repairs and return the content as is.

        Args:
            content: The subtext content.
            llm_generator: Unused for subtext.
            storage_manager: Unused for subtext.
            stage_name: Unused for subtext.
            phase_name: Unused for subtext.
            timeout: Unused for subtext.
            deterministic_temp: Unused for subtext.

        Returns:
            str: The original subtext content.
        """
        return content

    def deserialize(self, content: str) -> str:
        """
        Deserialize subtext content.

        For subtext, we return the content as is.

        Args:
            content: The subtext string.

        Returns:
            str: The original subtext content.
        """
        return content

    def serialize(self, content: str) -> str:
        """
        Serialize the subtext content.

        For subtext, we return the content as is.

        Args:
            content: The subtext content to serialize.

        Returns:
            str: The original subtext content.
        """
        return content
