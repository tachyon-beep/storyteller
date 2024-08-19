"""
storyteller_configuration_manager.py

This module provides a centralized configuration management system for the storytelling pipeline.
It integrates configuration loading, validation, and path management into a single interface.
The module ensures that configuration is consistent across the application by employing a singleton pattern.

Usage:
    from config.storyteller_configuration_manager import storyteller_config

    # Get a nested configuration value
    value = storyteller_config.get_nested_config_value('some.nested.key')

    # Get a path from the configuration
    path = storyteller_config.get_path('some_path_key')

    # Get LLM configuration
    llm_config = storyteller_config.get_llm_config()

    # Override a configuration value
    storyteller_config.override_config_value('some.nested.key', 'new_value')

    # Reload configuration (e.g., after external changes to the config file)
    storyteller_config.reload_config()

Note:
    This module uses a singleton pattern to ensure consistent configuration across the application.
    It supports environment-specific configurations and provides thread-safe operations.
"""

import logging
import os
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Callable, cast


from config.storyteller_configuration_loader import StorytellerConfigurationLoader, StorytellerConfigurationError
from config.storyteller_configuration_validator import StorytellerConfigurationValidator
from config.storyteller_path_manager import StorytellerPathManager
from config.storyteller_configuration_types import (
    StorytellerConfig, LLMConfig, PluginConfig, StageConfig,
    BatchConfig, ContentProcessingConfig, GuidanceConfig, PlaceholderConfig,
    EnvironmentType
)

logger = logging.getLogger(__name__)


class StorytellerConfigurationManager:
    """
    Main configuration manager integrating other components.
    Manages loading, validation, and access to the storytelling pipeline configuration.

    This class is implemented as a singleton to ensure consistent configuration across the application.

    Attributes:
        environment (Optional[EnvironmentType]): The current environment (development, staging, or production).
        config_loader (Optional[StorytellerConfigurationLoader]): Loader for configuration files.
        config_validator (Optional[StorytellerConfigurationValidator]): Validator for configuration data.
        path_manager (Optional[StorytellerPathManager]): Manager for configuration-related paths.
        config (Optional[StorytellerConfig]): The validated configuration object.
        _observers (List[Callable[[str, Any], None]]): List of observers to be notified of configuration changes.
        version (int): The current configuration version.
        version_history (List[Dict[str, Any]]): History of configuration versions.
    """

    _instance: Optional['StorytellerConfigurationManager'] = None
    _lock: Lock = Lock()
    _initialized: bool = False

    def __new__(cls) -> 'StorytellerConfigurationManager':
        """
        Creates or returns the singleton instance of StorytellerConfigurationManager.

        Returns:
            StorytellerConfigurationManager: The singleton instance.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(StorytellerConfigurationManager, cls).__new__(cls)
                assert cls._instance is not None, "Failed to create StorytellerConfigurationManager instance"
        return cls._instance

    def __init__(self) -> None:
        """
        Initializes the StorytellerConfigurationManager instance.

        Ensures that the initialization is performed only once, even if the singleton instance is accessed multiple times.
        """
        if self._initialized:
            return

        self.environment: Optional[EnvironmentType] = None
        self.config_loader: Optional[StorytellerConfigurationLoader] = None
        self.config_validator: Optional[StorytellerConfigurationValidator] = None
        self.config: Optional[StorytellerConfig] = None
        self.path_manager: Optional[StorytellerPathManager] = None
        self._observers: List[Callable[[str, Any], None]] = []
        self.version: int = 1
        self.version_history: List[Dict[str, Any]] = []
        self._initialized = True

    def initialize(self, loader: StorytellerConfigurationLoader, validator: StorytellerConfigurationValidator) -> None:
        """
        Initializes the configuration manager with the provided loader and validator.

        Args:
            loader (StorytellerConfigurationLoader): The configuration loader.
            validator (StorytellerConfigurationValidator): The configuration validator.

        Raises:
            StorytellerConfigurationError: If the configuration file cannot be loaded or is not well formatted.
        """
        self.environment = cast(EnvironmentType, os.getenv('STORYTELLER_ENV', 'development'))
        self.config_loader = loader
        self.config_validator = validator

        config_path = Path(__file__).parent.parent.parent / "config" / f"pipeline.{self.environment}.yaml"
        try:
            raw_config = self.config_loader.load_config(config_path)
            logger.debug("Raw configuration loaded successfully")

            self.config = self.config_validator.validate_config(raw_config, self.config_validator.create_base_schema())
            logger.info("Configuration validated successfully")

            self.path_manager = StorytellerPathManager(self.config)
            self._apply_environment_overrides()
            logger.info("Configuration manager initialized")
        except FileNotFoundError as e:
            logger.error("Configuration file not found: %s", config_path)
            raise StorytellerConfigurationError(f"Configuration file not found: {config_path}") from e
        except StorytellerConfigurationError as e:
            logger.error("Configuration validation failed: %s", str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error during configuration initialization: %s", str(e))
            raise StorytellerConfigurationError(f"Unexpected error during configuration initialization: {str(e)}") from e

    def get_nested_config_value(self, key_path: str) -> Any:
        """
        Retrieves a nested configuration value using dot notation.

        Args:
            key_path (str): The dot-notated key path.

        Returns:
            Any: The configuration value.

        Raises:
            KeyError: If the key path is not found in the configuration.
        """
        keys = key_path.split('.')
        value: Any = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except KeyError as exc:
            logger.error("Key path not found in configuration: %s", key_path)
            raise KeyError(f"Key path not found in configuration: {key_path}") from exc

    def get_path(self, key: str) -> Path:
        """
        Retrieves a path from the configuration.

        Args:
            key (str): The key for the path in the configuration.

        Returns:
            Path: The requested path.

        Raises:
            KeyError: If the key is not found in the configuration.
        """
        try:
            return Path(str(self.get_nested_config_value(f"paths.{key}")))
        except KeyError as exc:
            logger.error("Path key not found in configuration: %s", key)
            raise KeyError(f"Path key not found in configuration: {key}") from exc

    def reload_config(self) -> None:
        """
        Reloads the configuration, clearing any cached values.

        This method is thread-safe.

        Raises:
            StorytellerConfigurationError: If the configuration file cannot be loaded or is invalid.
        """
        with self._lock:
            config_path = Path(__file__).parent.parent / "config" / f"pipeline.{self.environment}.yaml"
            try:
                assert self.config_loader is not None, StorytellerConfigurationError("Configuration loader not initialized")
                assert self.config_validator is not None, StorytellerConfigurationError("Configuration validator not initialized")

                self.config = self.config_loader.load_and_validate_config(config_path, self.config_validator)
                logger.info("Configuration reloaded")
            except (FileNotFoundError, StorytellerConfigurationError) as e:
                logger.error("Failed to reload configuration: %s", str(e))
                raise

    def get_llm_config(self) -> LLMConfig:
        """
        Retrieves the LLM configuration.

        Returns:
            LLMConfig: The LLM configuration object with defaults applied for optional fields.
        """
        assert self.config and 'llm' in self.config, "LLM Configuration not found."

        llm_config = self.config['llm']

        logger.debug("LLM Configuration Queried: PS is %s", llm_config['pass_schema'])

        return LLMConfig(
            type=llm_config['type'],
            default_temperature=llm_config.get('default_temperature', 1.0),
            config=llm_config['config'],
            pass_schema=llm_config.get('pass_schema', False),
            autocontinue=llm_config.get('autocontinue', False),
            max_continues=llm_config.get('max_continues', 0),
            max_retries=llm_config.get('max_retries', 3),
            max_output_tokens=llm_config.get('max_output_tokens', 8192)
        )

    def get_plugin_config(self) -> Dict[str, PluginConfig]:
        """
        Retrieves the plugin configuration.

        Returns:
            Dict[str, PluginConfig]: The plugin configuration dictionary.
        """
        assert self.config and self.config['plugins'], StorytellerConfigurationError("Plugins not found.")
        return self.config['plugins']

    def get_stage_config(self) -> List[StageConfig]:
        """
        Retrieves the stage configuration.

        Returns:
            List[StageConfig]: The list of stage configurations.
        """
        assert self.config and self.config['stages'], StorytellerConfigurationError("Stages not found.")
        return self.config['stages']

    def get_batch_config(self) -> BatchConfig:
        """
        Retrieves the batch configuration.

        Returns:
            BatchConfig: The batch configuration object.
        """
        assert self.config and self.config['batch'], StorytellerConfigurationError("Batches not found.")
        return self.config['batch']

    def get_content_processing_config(self) -> ContentProcessingConfig:
        """
        Retrieves the content processing configuration.

        Returns:
            ContentProcessingConfig: The content processing configuration object.
        """
        assert self.config and self.config['content_processing'], StorytellerConfigurationError("Content Processing config not found.")
        return self.config['content_processing']

    def get_guidance_config(self) -> GuidanceConfig:
        """
        Retrieves the guidance configuration.

        Returns:
            GuidanceConfig: The guidance configuration object.
        """
        assert self.config and self.config['guidance'], StorytellerConfigurationError("Guidance config not found.")
        return self.config['guidance']

    def get_placeholder_config(self, placeholder_name: str) -> Optional[PlaceholderConfig]:
        """
        Retrieves the configuration for a specific placeholder.

        Args:
            placeholder_name (str): The name of the placeholder.

        Returns:
            Optional[PlaceholderConfig]: The placeholder configuration object, or None if not found.
        """
        assert self.config and self.config['placeholders'], StorytellerConfigurationError("Placeholder config not found.")
        return self.config['placeholders'].get(placeholder_name)

    def get_all_placeholder_configs(self) -> Dict[str, PlaceholderConfig]:
        """
        Retrieves all placeholder configurations.

        Returns:
            Dict[str, PlaceholderConfig]: A dictionary of all placeholder configurations.
        """
        assert self.config and self.config['placeholders'], StorytellerConfigurationError("Placeholder config not found.")
        return self.config['placeholders']

    def override_multiple_config_values(self, updates: Dict[str, Any]) -> None:
        """
        Update multiple configuration values atomically.

        Args:
            updates (Dict[str, Any]): A dictionary of key paths and their new values.
        """
        with self._lock:
            for key_path, value in updates.items():
                self.override_config_value(key_path, value)

    def override_config_value(self, key_path: str, value: Any) -> None:
        """
        Overrides a specific configuration value.

        This method is thread-safe and notifies all registered observers of the change.

        Args:
            key_path (str): The dot-notated key path of the configuration value to override.
            value (Any): The new value to set.

        Raises:
            KeyError: If the key path is not found in the configuration.
        """
        with self._lock:
            keys = key_path.split('.')
            current = self.config

            if current is None:
                raise KeyError(f"Configuration is not initialized or is None for key path: {key_path}")

            for key in keys[:-1]:
                if not isinstance(current, dict):
                    raise KeyError(f"Key path not found in configuration: {key_path}")
                if key not in current:
                    raise KeyError(f"Key path not found in configuration: {key_path}")
                current = current[key]

            if not isinstance(current, dict) or keys[-1] not in current:
                raise KeyError(f"Key path not found in configuration: {key_path}")

            current[keys[-1]] = value
            for observer in self._observers:
                observer(key_path, value)
            self.version += 1
            self.version_history.append({
                'version': self.version,
                'key_path': key_path,
                'value': value
            })
            logger.info("Configuration value overridden: %s", key_path)

    def export_config(self) -> Dict[str, Any]:
        """
        Export the current configuration state.

        Returns:
            Dict[str, Any]: A dictionary representation of the current configuration.
        """
        if self.config is None:
            raise StorytellerConfigurationError("Configuration is not initialized")
        return dict(self.config)  # This creates a shallow copy of the configuration

    def get_environment(self) -> EnvironmentType:
        """
        Retrieves the current environment.

        Returns:
            EnvironmentType: The current environment (development, staging, or production).
        """
        assert self.environment is not None, "Environment must be initialized before accessing"
        return self.environment

    def add_observer(self, observer: Callable[[str, Any], None]) -> None:
        """
        Add an observer to be notified of configuration changes.

        Args:
            observer (Callable[[str, Any], None]): A function to be called when a configuration value changes.
                The function should accept two arguments: the key path of the changed value and the new value.
        """
        self._observers.append(observer)

    def remove_observer(self, observer: Callable[[str, Any], None]) -> None:
        """
        Remove an observer from the list of observers.

        Args:
            observer (Callable[[str, Any], None]): The observer function to remove.
        """
        self._observers.remove(observer)

    def _apply_environment_overrides(self) -> None:
        """
        Apply configuration overrides from environment variables.
        """
        for key, value in os.environ.items():
            if key.startswith('STORYTELLER_'):
                config_key = key[11:].lower().replace('_', '.')
                self.override_config_value(config_key, value)

    def get_config_version(self) -> int:
        """
        Get the current configuration version.

        Returns:
            int: The current version number.
        """
        return self.version

    def get_version_history(self) -> List[Dict[str, Any]]:
        """
        Get the configuration version history.

        Returns:
            List[Dict[str, Any]]: A list of version change records.
        """
        return self.version_history


# Create a singleton instance of StorytellerConfigurationManager
storyteller_config = StorytellerConfigurationManager()
config_validator = StorytellerConfigurationValidator()
config_loader = StorytellerConfigurationLoader()
storyteller_config.initialize(config_loader, config_validator)
