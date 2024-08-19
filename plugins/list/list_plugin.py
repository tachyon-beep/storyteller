"""
List Output Plugin Module

This module provides the ListOutputPlugin class for processing and validating list content
in the storytelling pipeline. It extends the StorytellerOutputPlugin base class to offer
list-specific functionality.

The plugin handles extraction, processing, and validation of list content,
ensuring that only the relevant content between specified tags is processed.

Usage:
    config = {
        "debug": True,
        "start_tag": "%%% LIST START %%%",
        "end_tag": "%%% LIST END %%%",
    }
    plugin = ListOutputPlugin(config)
    plugin.initialise_plugin(Path("/path/to/plugin"), storage_manager)
    processed_content = plugin.process("raw list content")
    is_valid = plugin.validate_content(processed_content, None)
"""

import logging
from typing import Any, Dict, List, Optional

from plugins.storyteller_output_plugin import StorytellerOutputPlugin

logger = logging.getLogger(__name__)


class ListOutputPlugin(StorytellerOutputPlugin):
    """
    A plugin for processing list output.

    This plugin handles the extraction, processing, and validation of list content
    while preserving whitespace and formatting.

    Attributes:
        start_tag (str): The tag marking the start of the list content.
        end_tag (str): The tag marking the end of the list content.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the ListOutputPlugin.

        Args:
            config (Dict[str, Any]): A dictionary containing configuration parameters for the plugin.
        """
        super().__init__(config)
        self.start_tag: str = config.get("start_tag", "%%% LIST START %%%")
        self.end_tag: str = config.get("end_tag", "%%% LIST END %%%")

    def extract_content(self, raw_content: str) -> str:
        """
        Extract list content from between the start and end tags.

        Args:
            raw_content (str): The raw content to extract from.

        Returns:
            str: The extracted list content as a string.
        """
        start_index = raw_content.find(self.start_tag)
        end_index = raw_content.find(self.end_tag)

        if start_index == -1 or end_index == -1 or start_index >= end_index:
            logger.warning("List markers not found or are in incorrect order. Returning original content.")
            return raw_content

        return raw_content[start_index + len(self.start_tag): end_index].strip()

    async def process(self, content: str | List[str]) -> str:
        """
        Process the extracted list content while preserving whitespace.

        Args:
            content (Union[str, List[str]]): The list content to process, either as a string or a list of strings.

        Returns:
            str: The processed list as a string with items separated by newlines.

        Raises:
            ValueError: If the content is neither a string nor a list.
        """
        logger.debug("Process method received content of type: %s", type(content))

        if isinstance(content, str):
            content = self.extract_content(content)
        elif isinstance(content, list):
            content = self.extract_content("\n".join(content))
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")

        processed_list = [item for item in content.split("\n") if item.strip()]
        return "\n".join(processed_list)

    async def validate_content(self, content: Any, schema: Optional[str]) -> bool:
        """
        Validate the processed list content.

        Args:
            content (Any): The content to validate.
            schema (Optional[str]): The schema to validate against (not used in this method).

        Returns:
            bool: True if the content is valid, False otherwise.
        """
        logger.debug("Validate method received content of type: %s", type(content))

        if not isinstance(content, str):
            logger.warning("Invalid content type for validation")
            return False

        items = content.strip().split('\n')
        if not items:
            logger.warning("List is empty")
            return False

        return True

    def get_format(self) -> str:
        """
        Get the format handled by this plugin.

        Returns:
            str: The string 'list' to indicate that this plugin handles lists.
        """
        return "list"

    def get_extension(self) -> str:
        """
        Get the file extension for the output format.

        Returns:
            str: The string 'lst' as the file extension for list files.
        """
        return "lst"

    def serialize(self, content: str | List[str]) -> str:
        """
        Serialize the content to a string for storage, preserving whitespace.

        Args:
            content (Union[str, List[str]]): The content to serialize, either as a string or a list of strings.

        Returns:
            str: The serialized content as a string with whitespace preserved.

        Raises:
            ValueError: If the content is neither a string nor a list.
        """
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            return "\n".join(str(item) for item in content if item is not None)
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")

    def deserialize(self, content: str) -> List[str]:
        """
        Deserialize list content from a string back into a Python list.

        This method assumes that the content is serialized as a single string
        with items separated by newlines. It will split the string into a list,
        preserving whitespace and formatting.

        Args:
            content (str): The serialized list content as a string.

        Returns:
            List[str]: The deserialized list of strings.

        Raises:
            ValueError: If the content cannot be split into a list.
        """
        try:
            return content.split("\n")
        except Exception as e:
            logger.error("Failed to deserialize list content: %s", str(e))
            raise ValueError("Failed to deserialize list content.") from e

    async def repair(self, content: str) -> str:
        """
        Stub method for repairing content. This plugin does not support repair.

        Args:
            content (str): The content to repair.

        Raises:
            RuntimeError: Always raised as this plugin does not support repair.
        """
        raise RuntimeError("ListOutputPlugin does not support content repair.")

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
        Stub method for attempting to repair content. This plugin does not support repair.

        Args:
            content (str): The content to repair.
            llm_generator (Any): The LLM generator (not used).
            storage_manager (Any): The storage manager (not used).
            stage_name (str): The stage name (not used).
            phase_name (str): The phase name (not used).
            timeout (float): The timeout (not used).
            deterministic_temp (float): The deterministic temperature (not used).

        Raises:
            RuntimeError: Always raised as this plugin does not support repair.
        """
        raise RuntimeError("ListOutputPlugin does not support content repair.")
