"""
StorytellerOutputPlugin Base Module

This module defines the base class for output plugins used in the storytelling pipeline.
It provides a common interface and shared functionality for all output plugins, including
schema handling, content processing, and repair functionality.

Usage:
    class MyCustomPlugin(StorytellerOutputPlugin):
        def process(self, content: str) -> Any:
            # Custom processing logic here
            pass

        # Implement other abstract methods...

    config = {"debug": True, "name": "MyPlugin", "some_setting": "value"}
    plugin = MyCustomPlugin(config)
    plugin.initialise_plugin(Path("/path/to/plugin"), storage_manager)
    result = await plugin.process_wrapper("raw content", "stage_name", "phase_name")
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
import logging
import json

logger = logging.getLogger(__name__)


class StorytellerOutputPlugin(ABC):
    """
    Abstract base class for Storyteller output plugins.

    This class defines the interface and common functionality for all output plugins
    used in the storytelling pipeline, including schema handling and content processing.

    Attributes:
        config (Dict[str, Any]): Configuration dictionary for the plugin.
        plugin_dir (Optional[Path]): Directory containing plugin-specific files.
        schema (Optional[str]): JSON schema for content validation.
        repair_prompt (Optional[str]): Prompt template for content repair.
        debug (bool): Flag to enable debug mode.
        storage_manager (Any): Instance of the storage manager.
        schema_fetcher (Optional[Callable[[str, str], Optional[Tuple[bool, Optional[str]]]]]): Function to fetch schemas.
        name (str): Name of the plugin.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the StorytellerOutputPlugin.

        Args:
            config: Configuration dictionary for the plugin.
        """
        self.config: Dict[str, Any] = config
        self.plugin_dir: Optional[Path] = None
        self.repair_prompt: Optional[str] = None
        self.debug: bool = config.get("debug", False)
        self.storage_manager: Any = None
        self.schema_fetcher: Optional[Callable[[str, str], Optional[Tuple[bool, Optional[str]]]]] = None
        self.schema: Optional[str] = None
        self.name: str = config.get("name", "Unnamed Plugin")

    def get_name(self) -> str:
        """
        Get the name of the plugin.

        Returns:
            str: The name of the plugin.
        """
        return self.name

    def set_name(self, name: str) -> None:
        """
        Set the name of the plugin.

        Args:
            name (str): The new name for the plugin.
        """
        self.name = name

    def initialise_plugin(self, plugin_dir: Path, storage_manager: Any) -> None:
        """
        Initialize the plugin with its directory and storage manager.

        Args:
            plugin_dir (Path): Directory containing plugin-specific files.
            storage_manager (Any): Instance of the storage manager.
        """
        self.plugin_dir = plugin_dir
        self.storage_manager = storage_manager
        self.schema = self._load_file_content("default_schema")
        self.repair_prompt = self._load_file_content("repair_prompt")
        logger.debug("Initialised plugin %s. Debug: %s", self.get_name(), self.debug)

    def set_schema_fetcher(self, fetcher: Callable[[str, str], Optional[Tuple[bool, Optional[str]]]]) -> None:
        """
        Set the schema fetcher function.

        Args:
            fetcher (Callable[[str, str], Optional[Tuple[bool, Optional[str]]]]): A function that takes stage_name and phase_name
                as arguments and returns a tuple containing a boolean and either a string or None.
        """
        self.schema_fetcher = fetcher

    def _load_file_content(self, config_key: str) -> Optional[str]:
        """
        Load content from a file specified in the plugin's configuration.

        Args:
            config_key (str): Key in the configuration dictionary specifying the file.

        Returns:
            Optional[str]: Content of the file as a string, or None if the file is not found or cannot be read.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            IOError: If there's an error reading the file.
        """
        file_name = self.config.get(config_key)
        if not file_name or not self.plugin_dir:
            return None
        file_path = self.plugin_dir / file_name
        if not file_path.exists():
            logger.warning("File not found: %s", file_path)
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except IOError as error:
            logger.error("Error reading file %s: %s", file_path, str(error))
            raise

    def get_current_schema(self, stage_name: str, phase_name: str) -> Optional[str]:
        """
        Get the schema for the current stage and phase.

        Args:
            stage_name (str): The name of the current stage.
            phase_name (str): The name of the current phase.

        Returns:
            Optional[str]: The schema as a string, or None if no schema is found.
        """
        if self.schema_fetcher:
            result = self.schema_fetcher(stage_name, phase_name)
            if result is not None:
                schema_bool, schema_data = result
                if schema_bool:
                    return schema_data
            return self.schema
        return None

    async def process_wrapper(self, content: str, stage_name: str, phase_name: str) -> Any:
        """
        Wrapper method for processing content, with optional debug output.

        Args:
            content (str): Raw content to be processed.
            stage_name (str): Name of the current pipeline stage.
            phase_name (str): Name of the current pipeline phase.

        Returns:
            Any: Processed content.

        Raises:
            ValueError: If content extraction or processing fails.
        """
        if self.debug:
            # Save the raw content to ephemeral storage for debugging (using the text plugin)
            await self.storage_manager.save_to_ephemeral(content, stage_name, phase_name, "text", "preprocessing")
            logger.debug("Saved raw content to ephemeral storage for %s_%s", stage_name, phase_name)

        extracted_content = self.extract_content(content)
        processed_content = await self.process(extracted_content)
        return processed_content

    def prepare_repair_prompt(self, content: Any, validation_errors: str) -> str:
        """
        Prepare the repair prompt by replacing placeholders with actual content and schema.

        Args:
            content (Any): The content that needs to be repaired.
            validation_errors (str): Description of validation errors.

        Returns:
            str: The prepared repair prompt.

        Raises:
            ValueError: If the repair prompt template is not available.
        """
        if not self.repair_prompt:
            raise ValueError("Repair prompt template is not available")

        content_str = self.serialize(content) if not isinstance(content, str) else content

        return (self.repair_prompt.replace("{CONTENT}", content_str)
                                  .replace("{SCHEMA}", self.schema or "No schema available")
                                  .replace("{VALIDATION_ERRORS}", validation_errors))

    @abstractmethod
    def extract_content(self, raw_content: str) -> str:
        """
        Extract relevant content from raw input.

        Args:
            raw_content (str): The raw content to extract from.

        Returns:
            str: Extracted content as a string.
        """

    @abstractmethod
    async def process(self, content: str) -> Any:
        """
        Process the extracted content.

        Args:
            content (str): The extracted content to process.

        Returns:
            Any: Processed content in the appropriate format.
        """

    @abstractmethod
    async def validate_content(self, content: Any, schema: Optional[str]) -> bool:
        """
        Validate the processed content against the provided schema.

        Args:
            content (Any): The processed content to validate.
            schema (Optional[str]): The schema to validate against, or None if no schema is available.

        Returns:
            bool: True if the content is valid, False otherwise.
        """

    async def validate(self, content: Any, stage_name: str, phase_name: str) -> bool:
        """
        Validate the content and save invalid content if necessary.

        Args:
            content (Any): The content to validate.
            stage_name (str): The name of the current stage.
            phase_name (str): The name of the current phase.

        Returns:
            bool: True if the content is valid, False otherwise.
        """
        schema = self.get_current_schema(stage_name, phase_name)
        is_valid = await self.validate_content(content, schema)

        if not is_valid:
            await self._save_invalid_content(content, stage_name, phase_name)

        return is_valid

    async def _save_invalid_content(self, content: Any, stage_name: str, phase_name: str) -> None:
        """
        Save invalid content to ephemeral storage.

        Args:
            content (Any): The invalid content to save.
            stage_name (str): The name of the current stage.
            phase_name (str): The name of the current phase.

        Raises:
            ValueError: If the storage manager is not initialized.
            IOError: If there's an error saving the content.
        """
        if self.storage_manager is None:
            logger.warning("Storage manager is not initialized. Unable to save invalid content.")
            raise ValueError("Storage manager is not initialized")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        identifier = f"invalid_{timestamp}"

        try:
            serialized_content = self.serialize(content)
            await self.storage_manager.save_to_ephemeral(
                serialized_content,
                stage_name,
                phase_name,
                self.get_name(),
                identifier,
                {"content_type": "invalid"}
            )
            logger.info("Saved invalid content to ephemeral storage: %s", identifier)
        except (IOError, json.JSONDecodeError) as e:
            logger.error("Failed to save invalid content to ephemeral storage: %s", str(e))
            raise

    @abstractmethod
    async def repair(self, content: str) -> Any:
        """
        Attempt to repair invalid content.

        Args:
            content (str): The invalid content to repair.

        Returns:
            Any: Repaired content in the appropriate format.
        """

    @abstractmethod
    def get_format(self) -> str:
        """
        Get the format handled by this plugin.

        Returns:
            str: A string representing the format (e.g., "json", "text").
        """

    @abstractmethod
    def get_extension(self) -> str:
        """
        Get the file extension for the output format.

        Returns:
            str: A string representing the file extension (e.g., "json", "txt").
        """

    @abstractmethod
    async def attempt_repair(
        self,
        content: str,
        llm_generator: Any,
        storage_manager: Any,
        stage_name: str,
        phase_name: str,
        timeout: float = 30.0,
        deterministic_temp: float = 0.0,
    ) -> Any:
        """
        Attempt to repair invalid content using advanced techniques.

        Args:
            content (str): The invalid content to repair.
            llm_generator (Any): The language model generator to use for repair.
            storage_manager (Any): The storage manager instance.
            stage_name (str): The name of the current stage.
            phase_name (str): The name of the current phase.
            timeout (float): Maximum time allowed for repair attempt, defaults to 30.0 seconds.
            deterministic_temp (float): Temperature setting for deterministic output, defaults to 0.0.

        Returns:
            Any: Repaired content in the appropriate format.
        """

    @abstractmethod
    def serialize(self, content: Any) -> str:
        """
        Serialize the processed content to a string for storage.

        Args:
            content (Any): The processed content to serialize.

        Returns:
            str: Serialized content as a string.
        """

    @abstractmethod
    def deserialize(self, content: str) -> Any:
        """
        Deserialize content from a string format to the appropriate Python data structure.

        This method must be implemented by subclasses to handle specific serialization formats.

        Args:
            content (str): The content in string format to deserialize.

        Returns:
            Any: The deserialized content as a Python data structure.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
            json.JSONDecodeError: If the content cannot be deserialized as JSON (for JSON-based plugins).
            ValueError: If the content is in an invalid format.
        """
