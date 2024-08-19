"""
Storyteller Configuration Loader Module

This module provides functionality for loading configuration files in YAML and JSON formats,
as well as plain text files. It ensures robust configuration management by implementing
caching, logging, and error handling.

Usage:
    from storyteller_configuration_loader import StorytellerConfigurationLoader
    from storyteller_configuration_validator import StorytellerConfigurationValidator

    loader = StorytellerConfigurationLoader()
    validator = StorytellerConfigurationValidator()
    config_path = Path('path/to/config.yaml')
    config = loader.load_and_validate_config(config_path, validator)

Classes:
    StorytellerConfigurationError: Custom exception for configuration-related errors.
    ParseError: Specific exception for parsing errors.
    StorytellerConfigurationLoader: Utility class for loading and caching configuration files.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any, Dict

import yaml
from jsonschema import ValidationError

from config.storyteller_configuration_types import StorytellerConfig
from config.storyteller_configuration_validator import StorytellerConfigurationValidator

logger = logging.getLogger(__name__)


class StorytellerConfigurationError(Exception):
    """Custom exception for configuration-related errors."""


class ParseError(StorytellerConfigurationError):
    """Exception raised when there is an error parsing a configuration file."""


class StorytellerConfigurationLoader:
    """
    A utility class for loading configuration files in YAML, JSON, and plain text formats.

    This class provides methods to load configuration files, with support for caching to
    improve performance for frequently accessed configurations.

    Attributes:
        _lock (Lock): A threading lock for ensuring thread-safe operations.
    """

    def __init__(self) -> None:
        """Initialize the StorytellerConfigurationLoader with a thread lock."""
        self._lock = Lock()

    @lru_cache(maxsize=32)
    def load_text(self, file_path: str | Path) -> str:
        """
        Load a plain text file.

        Args:
            file_path: Path to the plain text file.

        Returns:
            The content of the plain text file.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            StorytellerConfigurationError: If there's an error reading the file.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error("Text file not found: %s", file_path)
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with file_path.open('r', encoding='utf-8') as file:
                content = file.read()
            logger.info("Successfully loaded text file from %s", file_path)
            return content
        except IOError as e:
            logger.error("Error reading text file %s: %s", file_path, str(e))
            raise StorytellerConfigurationError(f"Failed to read text file: {str(e)}") from e

    @lru_cache(maxsize=32)
    def load_yaml(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Load a YAML configuration file.

        Args:
            file_path: Path to the YAML file.

        Returns:
            The loaded YAML data as a dictionary.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ParseError: If there's an error parsing the YAML file.
            ValidationError: If the loaded YAML does not contain a valid structure.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error("YAML file not found: %s", file_path)
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with file_path.open('r', encoding='utf-8') as file:
                config_dict = yaml.safe_load(file)
            logger.info("Successfully loaded YAML configuration from %s", file_path)
            if not isinstance(config_dict, dict):
                raise ValidationError("Loaded YAML file does not contain a valid dictionary")
            return config_dict
        except yaml.YAMLError as e:
            logger.error("Error parsing YAML file %s: %s", file_path, str(e))
            raise ParseError(f"Failed to parse YAML configuration: {str(e)}") from e
        except IOError as e:
            logger.error("Error reading YAML file %s: %s", file_path, str(e))
            raise StorytellerConfigurationError(f"Failed to read YAML file: {str(e)}") from e

    @lru_cache(maxsize=32)
    def load_json(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Load a JSON configuration file.

        Args:
            file_path: Path to the JSON file.

        Returns:
            The loaded JSON data as a dictionary.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ParseError: If there's an error parsing the JSON file.
            ValidationError: If the loaded JSON does not contain a valid structure.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error("JSON file not found: %s", file_path)
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with file_path.open('r', encoding='utf-8') as file:
                config_dict = json.load(file)
            logger.info("Successfully loaded JSON configuration from %s", file_path)
            if not isinstance(config_dict, dict):
                raise ValidationError("Loaded JSON file does not contain a valid dictionary")
            return config_dict
        except json.JSONDecodeError as e:
            logger.error("Error parsing JSON file %s: %s", file_path, str(e))
            raise ParseError(f"Failed to parse JSON configuration: {str(e)}") from e
        except IOError as e:
            logger.error("Error reading JSON file %s: %s", file_path, str(e))
            raise StorytellerConfigurationError(f"Failed to read JSON file: {str(e)}") from e

    def load_config(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Load a configuration file based on its extension.

        Args:
            file_path: Path to the configuration file.

        Returns:
            The loaded configuration data as a dictionary.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file type is not supported.
            ParseError: If there's an error parsing the file.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return self.load_yaml(file_path)

    def clear_cache(self) -> None:
        """
        Clear the cache for loaded configurations.

        This method clears the LRU cache for the load_text, load_yaml, and load_json methods.
        It is thread-safe.
        """
        with self._lock:
            self.load_text.cache_clear()
            self.load_yaml.cache_clear()
            self.load_json.cache_clear()
        logger.info("Configuration cache cleared")

    def reload_config(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Reload a specific configuration file.

        This method clears the cache entry for the specified file and reloads it.
        It is thread-safe.

        Args:
            file_path: Path to the configuration file to reload.

        Returns:
            The reloaded configuration as a dictionary.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file type is not supported.
            ParseError: If there's an error parsing the configuration file.
        """
        file_path = Path(file_path)
        with self._lock:
            self.clear_cache()
            return self.load_config(file_path)

    def load_and_validate_config(self, config_path: Path, config_validator: StorytellerConfigurationValidator) -> StorytellerConfig:
        """
        Load and validate the configuration file.

        Args:
            config_path: Path to the configuration file.

        Returns:
            The validated configuration.

        Raises:
            FileNotFoundError: If the configuration file is not found.
            StorytellerConfigurationError: If the configuration is invalid or the validator is not initialized.
        """
        try:
            raw_config = self.load_config(config_path)
            schema = config_validator.create_base_schema()
            return config_validator.validate_config(raw_config, schema)
        except FileNotFoundError as e:
            logger.error("Configuration file not found: %s", config_path)
            raise FileNotFoundError(f"Configuration file not found: {config_path}") from e
        except StorytellerConfigurationError as e:
            logger.error("Invalid configuration: %s", str(e))
            raise
