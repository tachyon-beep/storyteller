"""
JsonOutputPlugin Module

This module provides the JsonOutputPlugin class for processing and validating JSON content
in the storytelling pipeline. It extends the StorytellerOutputPlugin base class to offer
JSON-specific functionality.

The plugin handles extraction, processing, validation, and repair of JSON content,
ensuring that only the relevant content between specified tags is processed.

Usage:
    config = {
        "debug": True,
        "start_tag": "%%% JSON START %%%",
        "end_tag": "%%% JSON END %%%",
        "schema": '{"type": "object", "properties": {...}}'
    }
    plugin = JsonOutputPlugin(config)
    plugin.initialise_plugin(Path("/path/to/plugin"), storage_manager)
    processed_content = await plugin.process("raw JSON content")
    is_valid = await plugin.validate_content(processed_content, plugin.schema)
"""

import json
import logging
from typing import Any, Dict, Optional, Union
from pathlib import Path

import jsonschema
from plugins.storyteller_output_plugin import StorytellerOutputPlugin

logger = logging.getLogger(__name__)

CONTENT_ERROR_MSG = "Content causing the error: %s"


class JsonOutputPlugin(StorytellerOutputPlugin):
    """
    Plugin for processing and validating JSON content.

    This plugin handles the extraction, processing, validation, and repair of JSON content
    in the storytelling pipeline.

    Attributes:
        start_tag (str): Tag marking the start of JSON content.
        end_tag (str): Tag marking the end of JSON content.
        parsed_schema (Optional[Dict[str, Any]]): Parsed JSON schema for validation.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the JsonOutputPlugin.

        Args:
            config (Dict[str, Any]): Configuration dictionary for the plugin.
        """
        super().__init__(config)
        self.start_tag: str = config.get("start_tag", "%%% JSON START %%%")
        self.end_tag: str = config.get("end_tag", "%%% JSON END %%%")
        self.parsed_schema: Optional[Dict[str, Any]] = None

    def initialise_plugin(self, plugin_dir: Path, storage_manager: Any) -> None:
        """
        Initialize the plugin with its directory and storage manager.

        Args:
            plugin_dir (Path): Directory containing plugin-specific files.
            storage_manager (Any): Instance of the storage manager.
        """
        super().initialise_plugin(plugin_dir, storage_manager)
        self.parsed_schema = self._parse_schema()
        logger.debug("Initializing JSON plugin with schema: %s", self.schema)

    def _parse_schema(self) -> Optional[Dict[str, Any]]:
        """
        Parse the JSON schema from the schema string.

        Returns:
            Optional[Dict[str, Any]]: Parsed JSON schema as a dictionary, or None if parsing fails.

        Raises:
            json.JSONDecodeError: If the schema is not valid JSON.
        """
        if not self.schema:
            logger.warning("No schema file specified in the configuration")
            return None
        return json.loads(self.schema)

    def extract_content(self, raw_content: str) -> str:
        """
        Extract JSON content from between start and end tags.
        Be careful about doing any validation here unless you're sure that's what you want.

        Args:
            raw_content (str): The raw content containing JSON data.

        Returns:
            str: Extracted JSON content as a string.

        Raises:
            ValueError: If JSON markers are not found or are in incorrect order.
        """
        # First, try to extract content from between tags
        start_index = raw_content.find(self.start_tag)
        end_index = raw_content.find(self.end_tag)

        if start_index != -1 and end_index != -1 and start_index < end_index:
            return raw_content[start_index + len(self.start_tag): end_index].strip()

        # If tags are not found, return the entire content, this is useful for cases where the content was generated with pass_schema=True
        return raw_content.strip()

    async def process(self, content: Union[str, Dict[str, Any]]) -> str:
        """
        Process the JSON content, attempting to parse it as JSON.

        Args:
            content (Union[str, Dict[str, Any]]): The JSON content to process, either as a string or dictionary.

        Returns:
            str: Processed JSON content as a formatted string.

        Raises:
            ValueError: If the content cannot be parsed as valid JSON.
        """
        logger.debug("Process method received content of type: %s", type(content))

        if isinstance(content, str):
            extracted_content = self.extract_content(content)
            try:
                parsed_content = json.loads(extracted_content)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON content: %s", e)
                logger.debug(CONTENT_ERROR_MSG, extracted_content[:1000])
                raise ValueError(f"Invalid JSON content: {e}") from e
        elif isinstance(content, dict):
            parsed_content = content
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")

        return json.dumps(parsed_content, indent=2)

    async def validate_content(self, content: str, schema: Optional[str]) -> bool:
        """
        Validate the processed JSON content against the provided schema.

        Args:
            content (str): The JSON content to validate as a string.
            schema (Optional[str]): The schema to validate against, or None if no schema is available.

        Returns:
            bool: True if the content is valid, False otherwise.
        """
        if schema is None:
            logger.warning("No schema available for validation, considering content valid")
            return True

        try:
            content_dict = json.loads(content)
            schema_dict = json.loads(schema)
        except json.JSONDecodeError as e:
            logger.error("Error parsing JSON: %s", e)
            logger.debug(CONTENT_ERROR_MSG, content[:1000])
            return False

        try:
            jsonschema.validate(instance=content_dict, schema=schema_dict)
            return True
        except jsonschema.ValidationError as e:
            logger.error("Validation error: %s", e)
            return False

    async def repair(self, content: str) -> str:
        """
        Attempt to repair invalid JSON content.

        Args:
            content (str): The invalid JSON content to repair.

        Returns:
            str: Repaired JSON content as a formatted string.

        Raises:
            ValueError: If no schema is available for repair.
        """
        if not self.parsed_schema:
            raise ValueError("No schema available for repair")
        try:
            repaired = json.loads(content)
            if await self.validate_content(json.dumps(repaired), self.schema):
                return json.dumps(repaired, indent=2)
            logger.warning("Repaired JSON still doesn't match schema. Returning empty JSON object.")
            return "{}"
        except json.JSONDecodeError:
            logger.warning("Failed to repair JSON. Returning empty JSON object.")
            return "{}"

    def get_format(self) -> str:
        """
        Get the format handled by this plugin.

        Returns:
            str: The string "json".
        """
        return "json"

    def get_extension(self) -> str:
        """
        Get the file extension for the output format.

        Returns:
            str: The string "json".
        """
        return "json"

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
        Attempt to repair invalid JSON content using advanced techniques.

        This method uses an LLM generator to attempt to repair the JSON content
        that failed validation.

        Args:
            content (str): The invalid JSON content to repair.
            llm_generator (Any): The LLM generator for content repair.
            storage_manager (Any): The storage manager for saving repair attempts.
            stage_name (str): The name of the current pipeline stage.
            phase_name (str): The name of the current pipeline phase.
            timeout (float): Timeout for the repair attempt in seconds. Defaults to 30.0.
            deterministic_temp (float): Temperature setting for deterministic output. Defaults to 0.0.

        Returns:
            str: Repaired JSON content as a formatted string.

        Raises:
            ValueError: If no repair prompt or schema is available, or if repair fails.
        """
        if not self.repair_prompt:
            raise ValueError("No repair prompt available for repair attempt")
        if not self.parsed_schema:
            raise ValueError("No schema available for repair attempt")

        repair_prompt = self._prepare_repair_prompt(content, "JSON validation failed")

        await storage_manager.save_ephemeral_content(
            stage_name, phase_name, "prompt", "repair_prompt", repair_prompt
        )

        try:
            repaired_content = await llm_generator.generate_content(repair_prompt, deterministic_temp, timeout=timeout)
            await storage_manager.save_ephemeral_content(
                stage_name, phase_name, "content", "repaired_content", repaired_content
            )

            logger.debug("Repaired content: %s", repaired_content[:1000])

            processed_content = await self.process(repaired_content)
            if await self.validate_content(processed_content, self.schema):
                return processed_content
            logger.error("Repaired content does not match the schema")
            logger.debug("Invalid repaired content: %s", processed_content[:1000])
            raise ValueError("Repaired content does not match the schema.")
        except (json.JSONDecodeError, jsonschema.ValidationError) as e:
            logger.error("Error during JSON repair: %s", str(e))
            raise ValueError(f"JSON repair failed: {e}") from e

    def deserialize(self, content: str) -> Any:
        """
        Deserialize JSON content from a string to a Python data structure.

        Args:
            content (str): The JSON string to deserialize.

        Returns:
            Any: The deserialized Python data structure (usually a dictionary or list).

        Raises:
            ValueError: If the content cannot be parsed as JSON.
        """
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Error parsing JSON: %s", e)
            raise ValueError(f"Invalid JSON content: {e}") from e

    def _prepare_repair_prompt(self, content: str, validation_errors: str) -> str:
        """
        Prepare the repair prompt with content and validation errors.

        Args:
            content (str): The invalid JSON content.
            validation_errors (str): The validation errors to include in the prompt.

        Returns:
            str: The prepared repair prompt.

        Raises:
            AssertionError: If the repair prompt is not set.
        """
        assert self.repair_prompt is not None, "Repair prompt is not set"
        return self.repair_prompt.replace("{JSON_CONTENT}", content).replace(
            "{VALIDATION_ERRORS}", validation_errors
        )

    def serialize(self, content: Union[str, Dict[str, Any]]) -> str:
        """
        Serialize the JSON content to a formatted string.

        Args:
            content (Union[str, Dict[str, Any]]): The JSON content to serialize, either as a string or dictionary.

        Returns:
            str: Serialized JSON content as a formatted string.

        Raises:
            ValueError: If the content is neither a valid JSON string nor a dictionary.
        """
        if isinstance(content, str):
            try:
                # Attempt to parse and re-serialize to ensure it's valid JSON
                return json.dumps(json.loads(content), indent=2)
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON string: %s", e)
                logger.debug(CONTENT_ERROR_MSG, content[:1000])
                raise ValueError(f"Invalid JSON string: {e}") from e
        elif isinstance(content, dict):
            return json.dumps(content, indent=2)
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")
