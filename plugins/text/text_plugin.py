"""
Text Output Plugin Module

This module provides the TextOutputPlugin class for processing and validating plain text content
in the storytelling pipeline. It extends the StorytellerOutputPlugin base class to offer
text-specific functionality.

The plugin handles extraction, processing, and validation of plain text content,
ensuring minimal transformation of the input text.

Usage:
    config = {
        "debug": True,
        "schema": '{"type": "string", "minLength": 1, "maxLength": 1000}'
    }
    plugin = TextOutputPlugin(config)
    plugin.initialise_plugin(Path("/path/to/plugin"), storage_manager)
    processed_content = plugin.process("raw text content")
    is_valid = plugin.validate_content(processed_content, plugin.schema)
"""

import json
import logging
from typing import Any, Dict, Optional

from plugins.storyteller_output_plugin import StorytellerOutputPlugin

logger = logging.getLogger(__name__)


class TextOutputPlugin(StorytellerOutputPlugin):
    """
    A plugin for processing plain text output.

    This plugin handles the extraction, processing, and validation of plain text content.
    It does not perform any complex transformations on the input text.

    Attributes:
        parsed_schema (Optional[Dict[str, Any]]): The parsed JSON schema for validation, if available.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the TextOutputPlugin.

        Args:
            config (Dict[str, Any]): A dictionary containing configuration parameters for the plugin.

        Raises:
            ValueError: If the schema in the configuration is not valid JSON.
        """
        super().__init__(config)
        self.parsed_schema: Optional[Dict[str, Any]] = self._parse_schema()

    def _parse_schema(self) -> Optional[Dict[str, Any]]:
        """
        Parse the schema string into a JSON object.

        Returns:
            Optional[Dict[str, Any]]: The parsed schema as a dictionary, or None if no schema is available.

        Raises:
            ValueError: If the schema is not valid JSON.
        """
        if not self.schema:
            return None
        try:
            return json.loads(self.schema)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in schema: {exc}") from exc

    def extract_content(self, raw_content: str) -> str:
        """
        Extract relevant content from raw input.

        Args:
            raw_content (str): The raw input string containing the content to be extracted.

        Returns:
            str: The extracted content with leading and trailing whitespace removed.
        """
        return raw_content.strip()

    async def process(self, content: str) -> str:
        """
        Process the extracted content.

        For text content, this method simply returns the input unchanged.

        Args:
            content (str): The extracted content to be processed.

        Returns:
            str: The processed content, which is identical to the input.
        """
        return content

    async def validate_content(self, content: str, schema: Optional[str] = None) -> bool:
        """
        Validate the processed content against the loaded schema.

        Args:
            content (str): The processed content to be validated.
            schema (Optional[str]): The schema to validate against (unused in this implementation).

        Returns:
            bool: True if the content is valid, False otherwise.

        Raises:
            ValueError: If no schema is available for validation.
        """
        if not self.parsed_schema:
            raise ValueError("No schema available for validation")

        min_length = self.parsed_schema.get("minLength", 0)
        max_length = self.parsed_schema.get("maxLength", float("inf"))

        return min_length <= len(content) <= max_length

    def get_validation_errors(self, processed_content: str) -> str:
        """
        Get a string of validation error messages for the processed content.

        Args:
            processed_content (str): The processed content to be validated.

        Returns:
            str: A string describing the validation errors, if any.
        """
        if not self.parsed_schema:
            return "No schema available for validation"

        errors = []
        min_length = self.parsed_schema.get("minLength", 0)
        max_length = self.parsed_schema.get("maxLength", float("inf"))

        if len(processed_content) < min_length:
            errors.append(f"Text is too short. Minimum length: {min_length}, Actual length: {len(processed_content)}")
        elif len(processed_content) > max_length:
            errors.append(f"Text is too long. Maximum length: {max_length}, Actual length: {len(processed_content)}")

        return ". ".join(errors) if errors else "No validation errors"

    async def repair(self, content: str) -> str:
        """
        Attempt to repair invalid content.

        For text content, this method simply returns the input unchanged as there's no repair logic.

        Args:
            content (str): The content to be "repaired".

        Returns:
            str: The input content, unchanged.
        """
        return content

    def serialize(self, content: str) -> str:
        """
        Serialize the processed content to a string for storage.

        For text content, this is essentially a no-op, as the content is already in string format.

        Args:
            content (str): The processed text content.

        Returns:
            str: The content as a string, unchanged.
        """
        return content

    def get_format(self) -> str:
        """
        Return the format handled by this plugin.

        Returns:
            str: The string "text", indicating that this plugin handles plain text.
        """
        return "text"

    def get_extension(self) -> str:
        """
        Return the file extension for the output format.

        Returns:
            str: The string "txt", the standard file extension for plain text files.
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
        Attempt to repair invalid content using an LLM generator.

        Args:
            content (str): The invalid content to be repaired.
            llm_generator (Any): An instance of the LLM generator.
            storage_manager (Any): The storage manager instance.
            stage_name (str): The name of the current stage.
            phase_name (str): The name of the current phase.
            timeout (float): Timeout for the LLM generator call in seconds. Defaults to 30.0.
            deterministic_temp (float): Temperature setting for deterministic output. Defaults to 0.0.

        Returns:
            str: The repaired content.

        Raises:
            ValueError: If the repair process fails or if no repair prompt or schema is available.
        """
        if not self.repair_prompt:
            raise ValueError("No repair prompt available for repair attempt")
        if not self.parsed_schema:
            raise ValueError("No schema available for repair attempt")

        validation_errors = self.get_validation_errors(content)
        repair_prompt = self._prepare_repair_prompt(content, validation_errors)

        await storage_manager.save_ephemeral_content(
            stage_name, phase_name, "prompt", "repair_prompt", repair_prompt
        )

        try:
            repaired_content = await llm_generator.generate_content(repair_prompt, deterministic_temp, timeout=timeout)
            await storage_manager.save_ephemeral_content(
                stage_name, phase_name, "content", "repaired_content", repaired_content
            )

            if await self.validate_content(repaired_content, None):
                return repaired_content
            raise ValueError("Repaired content does not match the schema.")
        except Exception as e:
            logger.error("Error during text repair: %s", str(e))
            raise ValueError(f"Text repair failed: {e}") from e

    def _prepare_repair_prompt(self, content: str, validation_errors: str) -> str:
        """
        Prepare the repair prompt with content and validation errors.

        Args:
            content (str): The invalid text content.
            validation_errors (str): The validation errors to include in the prompt.

        Returns:
            str: The prepared repair prompt.

        Raises:
            AssertionError: If the repair prompt is not set.
        """
        assert self.repair_prompt is not None, "Repair prompt is not set"
        return self.repair_prompt.replace("{TEXT_CONTENT}", content).replace(
            "{VALIDATION_ERRORS}", validation_errors
        )

    def deserialize(self, content: str) -> str:
        """
        Deserialize the text content from a serialized format back into plain text.

        Since this plugin handles plain text, the deserialize method effectively ensures
        the text is in the correct format, performing minimal processing like trimming
        or normalizing newlines if necessary.

        Args:
            content (str): The serialized text content.

        Returns:
            str: The deserialized text, potentially with minor formatting corrections.
        """
        return content.strip().replace('\r\n', '\n')
