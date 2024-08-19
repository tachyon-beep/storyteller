"""
Storyteller Plugin Manager Module

This module provides the `StorytellerPluginManager` class for managing plugins
in the storytelling pipeline. It implements a singleton pattern to ensure
only one instance of the plugin manager exists throughout the application.

The plugin manager is responsible for:
1. Discovering and loading enabled plugins
2. Providing access to plugin instances, configurations, and schemas
3. Managing plugin reloading and error handling

Usage Example:
    from storyteller_plugin_manager import StorytellerPluginManager
    from storyteller_stage_manager import StorytellerStageManager

    stage_manager = StorytellerStageManager(storyteller_config)
    plugin_manager = StorytellerPluginManager(stage_manager)

    plugin = plugin_manager.get_plugin("json")
    schema = plugin_manager.get_plugin_schema("json")
    repair_setting = plugin_manager.get_plugin_repair_setting("json")

Note:
    This class implements a singleton pattern. Multiple calls to 
    `StorytellerPluginManager()` will return the same instance after it's first created.
"""

import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List, Type

from config.storyteller_configuration_manager import storyteller_config
from config.storyteller_configuration_validator import StorytellerConfigurationError
from config.storyteller_configuration_types import PluginConfig
from orchestration.storyteller_stage_manager import StorytellerStageManager
from plugins.storyteller_output_plugin import StorytellerOutputPlugin

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class PluginError(Exception):
    """Custom exception for plugin-related errors."""


class PluginLoadError(Exception):
    """Custom exception for plugin loading errors."""


class StorytellerPluginManager:
    """
    Manages plugins for the storytelling pipeline.

    This class is responsible for discovering, loading, and managing plugins,
    as well as providing access to plugin-specific configurations and schemas.
    It implements a singleton pattern to ensure only one instance exists.

    Attributes:
        config_manager: Configuration manager instance.
        stage_manager: Stage manager instance.
        plugins: Dictionary of loaded plugin instances.
        plugin_configs: Dictionary of plugin configurations.
        storage_manager: Storage manager instance.
        plugins_loaded: Flag indicating whether plugins have been loaded.
    """

    _instance: Optional['StorytellerPluginManager'] = None

    def __new__(cls, stage_manager: StorytellerStageManager) -> 'StorytellerPluginManager':
        """
        Create a new instance of StorytellerPluginManager or return the existing one.

        Args:
            stage_manager: The stage manager instance.

        Returns:
            StorytellerPluginManager: The single instance of StorytellerPluginManager.
        """
        if cls._instance is None:
            logger.info("Creating new instance of StorytellerPluginManager")
            cls._instance = super(StorytellerPluginManager, cls).__new__(cls)
            assert cls._instance is not None, "Instance creation failed"
            cls._instance.__init__(stage_manager)
        else:
            logger.info("Returning existing instance of StorytellerPluginManager")
        return cls._instance

    def __init__(self, stage_manager: StorytellerStageManager) -> None:
        """
        Initialize the StorytellerPluginManager instance.

        Args:
            stage_manager: The stage manager instance.
        """
        if not hasattr(self, "initialized"):  # Prevent re-initialization
            self.config_manager = storyteller_config
            self.stage_manager = stage_manager
            self.plugins: Dict[str, StorytellerOutputPlugin] = {}
            self.plugin_configs: Dict[str, PluginConfig] = {}
            self.storage_manager: Any = None
            self.plugins_loaded: bool = False
            self._initialize()
            self.initialized = True

    def _initialize(self) -> None:
        """Initialize the StorytellerPluginManager instance."""
        self._validate_plugin_configs()

    def set_storage_manager(self, storage_manager: Any) -> None:
        """
        Set the storage manager and load plugins if not already loaded.

        Args:
            storage_manager: The storage manager instance.
        """
        self.storage_manager = storage_manager
        if not self.plugins_loaded:
            self._load_plugins()

    def _validate_plugin_configs(self) -> None:
        """
        Validate all plugin configurations.

        Raises:
            ValueError: If any plugin configuration is invalid.
        """
        required_fields = ["file", "class_name", "enabled"]
        plugin_configs = self.config_manager.get_plugin_config()

        logger.debug("Validating plugin configurations: %s", plugin_configs)
        logger.debug("Plugins directory: %s", self.config_manager.get_path('plugins'))

        for plugin_name, config in plugin_configs.items():
            logger.debug("Validating configuration for plugin: %s", plugin_name)
            for field in required_fields:
                if field not in config:
                    logger.error("Missing required field '%s' in configuration for plugin: %s", field, plugin_name)
                    raise ValueError(f"Missing required field '{field}' in configuration for plugin: {plugin_name}")

            file_name = config.get("file")
            logger.debug("Constructing file path for plugin %s with file name: %s", plugin_name, file_name)
            file_path = self._get_plugin_file_path(plugin_name, f"{file_name}.py")
            logger.debug("Constructed file path: %s", file_path)

            if file_path is None:
                logger.error("Failed to construct file path for plugin: %s", plugin_name)
                raise ValueError(f"Failed to construct file path for plugin: {plugin_name}")

            if not file_path.is_file():
                logger.error("Plugin file not found: %s", file_path)
                raise ValueError(f"Plugin file not found: {file_path}")
            else:
                logger.debug("Plugin file found: %s", file_path)

        logger.info("All plugin configurations validated successfully")

    def _get_plugin_file_path(self, plugin_name: str, file_name: str) -> Optional[Path]:
        """
        Construct the path to a file within a specific plugin's directory.

        Args:
            plugin_name: The name of the plugin.
            file_name: The name of the file.

        Returns:
            Optional[Path]: The constructed path, or None if the plugins directory is not defined.
        """
        root_path = self.config_manager.get_path("root")
        assert root_path and Path(root_path).is_dir(), "Root path not found!"

        plugins_dir = self.config_manager.get_path("plugins")
        if not plugins_dir:
            logger.error("Plugins directory is not defined in the configuration")
            return None

        plugins_dir = Path(root_path) / plugins_dir
        if not plugins_dir.is_dir():
            logger.error("Plugins directory not found: %s", plugins_dir)
            return None

        return plugins_dir / plugin_name / file_name

    def _load_plugins(self) -> None:
        """
        Load all enabled plugins.

        Raises:
            ValueError: If storage manager is not set before loading plugins.
            PluginLoadError: If there's an error loading a plugin.
        """
        if self.storage_manager is None:
            raise ValueError("Storage manager must be set before loading plugins")

        logger.info("Starting to load plugins")
        plugin_configs = self.config_manager.get_plugin_config()
        enabled_plugins = [name for name, config in plugin_configs.items() if config.get('enabled', False)]

        for plugin_name in enabled_plugins:
            config = plugin_configs.get(plugin_name)
            if config is not None:
                try:
                    self._load_single_plugin(plugin_name, config)
                except (ImportError, AttributeError, TypeError) as exc:
                    logger.error("Failed to load plugin %s: %s", plugin_name, str(exc))
                    raise PluginLoadError(f"Failed to load plugin {plugin_name}") from exc
            else:
                logger.warning("Configuration for plugin %s not found", plugin_name)
        self.plugins_loaded = True
        logger.info("Finished loading plugins")

    def _load_single_plugin(self, plugin_name: str, config: PluginConfig) -> None:
        """
        Load a single plugin.

        Args:
            plugin_name: The name of the plugin to load.
            config: The configuration for the plugin.

        Raises:
            ValueError: If the plugin configuration is invalid or storage manager is not set.
            ImportError: If the plugin module or class cannot be imported.
            AttributeError: If the plugin class is not found in the module.
            TypeError: If the plugin class is not a subclass of StorytellerOutputPlugin.
        """
        plugin_dir = self._get_plugin_file_path(plugin_name, "")
        assert plugin_dir is not None, "Plugin directory path is None!"

        file_name = config.get("file") or ""
        if not file_name:
            raise ValueError(f"Missing 'file' in plugin configuration for {plugin_name}")

        module_path = plugin_dir / f"{file_name}.py"
        if not module_path.exists():
            raise ImportError(f"Plugin file not found: {module_path}")

        spec = importlib.util.spec_from_file_location(f"{plugin_name}_plugin", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to load spec for plugin: {plugin_name}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class_name = config.get("class_name")
        if not class_name:
            raise ValueError(f"Missing 'class_name' in plugin configuration for {plugin_name}")

        plugin_class: Type[StorytellerOutputPlugin] = getattr(module, class_name)

        if not issubclass(plugin_class, StorytellerOutputPlugin):
            raise TypeError(f"Plugin class for {plugin_name} must be a subclass of StorytellerOutputPlugin")

        plugin_instance = plugin_class(dict(config))
        plugin_instance.set_name(plugin_name)

        if self.storage_manager is None:
            raise ValueError(f"Storage manager not set when initializing plugin: {plugin_name}")

        plugin_instance.set_schema_fetcher(self.stage_manager.get_phase_schema)
        plugin_instance.initialise_plugin(plugin_dir, self.storage_manager)
        self.plugins[plugin_name] = plugin_instance
        self.plugin_configs[plugin_name] = config
        logger.info("Loaded plugin: %s", plugin_name)

    def get_plugin(self, plugin_name: str) -> StorytellerOutputPlugin:
        """
        Get a plugin instance by name.

        Args:
            plugin_name: The name of the plugin.

        Returns:
            StorytellerOutputPlugin: The plugin instance.

        Raises:
            PluginError: If the plugin is not found or not enabled.
        """
        plugin_name = plugin_name.lower()
        if plugin_name not in self.plugins:
            raise PluginError(f"Plugin not found or not enabled: {plugin_name}")
        return self.plugins[plugin_name]

    def get_plugin_schema(self, plugin_name: str) -> Optional[str]:
        """
        Get the schema for a specific plugin.

        Args:
            plugin_name: The name of the plugin.

        Returns:
            Optional[str]: The schema for the specified plugin, or None if not found.

        Raises:
            PluginError: If there's an error loading the schema file.
        """
        assert self.config_manager.config_loader is not None, "Config loader is not set!"

        config = self.plugin_configs.get(plugin_name)
        if config and "default_schema" in config:
            schema_file = config["default_schema"]

            logger.debug("Loading schema: %s", schema_file)

            if not schema_file:
                logger.debug("No schema defined for plugin: %s", plugin_name)
                return None

            schema_path = self._get_plugin_file_path(plugin_name, schema_file)
            if schema_path is None:
                logger.warning("Schema file path could not be constructed for plugin: %s", plugin_name)
                return None

            try:
                schema_content = self.config_manager.config_loader.load_text(schema_path)
                logger.info("Successfully loaded schema for plugin: %s", plugin_name)
                return schema_content
            except StorytellerConfigurationError as exc:
                logger.warning("Failed to load schema for plugin %s: %s", plugin_name, str(exc))
                return None

        logger.debug("No configuration found for plugin: %s", plugin_name)
        return None

    def get_plugin_repair_setting(self, plugin_name: str) -> bool:
        """
        Get the repair setting for a specific plugin.

        Args:
            plugin_name: The name of the plugin.

        Returns:
            bool: True if repair is enabled for the plugin, False otherwise.

        Raises:
            PluginError: If the plugin configuration is not found.
        """
        plugin_name = plugin_name.lower()
        config = self.plugin_configs.get(plugin_name)
        if config is None:
            raise PluginError(f"Plugin configuration not found: {plugin_name}")
        return bool(config.get("repair", False))

    def get_plugin_retry_setting(self, plugin_name: str) -> bool:
        """
        Get the retry setting for a specific plugin.

        Args:
            plugin_name: The name of the plugin.

        Returns:
            bool: True if retry is enabled for the plugin, False otherwise.

        Raises:
            PluginError: If the plugin configuration is not found.
        """
        plugin_name = plugin_name.lower()
        config = self.plugin_configs.get(plugin_name)
        if config is None:
            raise PluginError(f"Plugin configuration not found: {plugin_name}")
        return bool(config.get("retry", False))

    def get_plugin_config(self, plugin_name: str) -> PluginConfig:
        """
        Get the configuration for a specific plugin.

        Args:
            plugin_name: The name of the plugin.

        Returns:
            PluginConfig: The configuration for the specified plugin.

        Raises:
            PluginError: If the plugin configuration is not found.
        """
        plugin_name = plugin_name.lower()
        config = self.plugin_configs.get(plugin_name)
        if config is None:
            raise PluginError(f"Plugin configuration not found: {plugin_name}")
        return config

    def reload_plugin(self, plugin_name: str) -> None:
        """
        Reload a specific plugin.

        Args:
            plugin_name: The name of the plugin to reload.

        Raises:
            PluginError: If the plugin is not found or fails to reload.
        """
        plugin_name = plugin_name.lower()
        if plugin_name not in self.plugin_configs:
            raise PluginError(f"Plugin not found: {plugin_name}")

        config = self.plugin_configs[plugin_name]
        try:
            self._load_single_plugin(plugin_name, config)
            logger.info("Reloaded plugin: %s", plugin_name)
        except (ImportError, AttributeError, TypeError) as exc:
            logger.error("Failed to reload plugin %s: %s", plugin_name, str(exc))
            raise PluginError(f"Failed to reload plugin {plugin_name}") from exc

    def get_loaded_plugins(self) -> List[str]:
        """
        Get a list of all loaded plugins.

        Returns:
            List[str]: A list of names of all loaded plugins.
        """
        return list(self.plugins.keys())

    def get_plugin_guidance(self, plugin_name: str) -> Optional[str]:
        """
        Get the guidance file name for a specific plugin.

        Args:
            plugin_name: The name of the plugin.

        Returns:
            Optional[str]: The guidance file name for the specified plugin, or None if not found.

        Raises:
            PluginError: If the plugin configuration is not found.
        """
        plugin_name = plugin_name.lower()
        config = self.plugin_configs.get(plugin_name)
        if config is None:
            raise PluginError(f"Plugin configuration not found: {plugin_name}")
        return config.get("guidance")

    def get_plugin_tag(self, plugin_name: str) -> Optional[str]:
        """
        Get the tag for a specific plugin.

        Args:
            plugin_name: The name of the plugin.

        Returns:
            Optional[str]: The tag for the specified plugin, or None if not found.

        Raises:
            PluginError: If the plugin configuration is not found.
        """
        plugin_name = plugin_name.lower()
        config = self.plugin_configs.get(plugin_name)
        if config is None:
            raise PluginError(f"Plugin configuration not found: {plugin_name}")
        return config.get("tag")

    def get_repair_script(self, plugin_name: str) -> Optional[str]:
        """
        Get the repair script for a specific plugin.

        Args:
            plugin_name: The name of the plugin.

        Returns:
            Optional[str]: The content of the repair script, or None if not found.

        Raises:
            PluginError: If the plugin configuration is not found or if there's an error loading the repair script.
        """
        assert self.config_manager.config_loader is not None, "Config loader is not set!"
        config = self.plugin_configs.get(plugin_name.lower())
        if config is None:
            raise PluginError(f"Plugin configuration not found: {plugin_name}")

        repair_script_name = config.get("repair_prompt")
        if not repair_script_name:
            return None

        repair_script_path = self._get_plugin_file_path(plugin_name, repair_script_name)
        if repair_script_path is None:
            logger.warning("Repair script path could not be constructed for plugin: %s", plugin_name)
            return None

        try:
            return self.config_manager.config_loader.load_text(repair_script_path)
        except StorytellerConfigurationError as exc:
            logger.error("Failed to load repair script for plugin %s: %s", plugin_name, str(exc))
            raise PluginError(f"Failed to load repair script for plugin {plugin_name}") from exc

    def get_plugin_configs(self) -> Dict[str, PluginConfig]:
        """
        Get the configurations for all plugins.

        Returns:
            Dict[str, PluginConfig]: A dictionary containing the configurations for all plugins.
        """
        return self.plugin_configs

    def get_enabled_plugins(self) -> List[str]:
        """
        Get a list of all enabled plugins.

        Returns:
            List[str]: A list of names of enabled plugins.
        """
        return [name for name, config in self.plugin_configs.items() if config.get("enabled", False)]

    def validate_plugin_output(self, plugin_name: str, content: Any, stage_name: str, phase_name: str) -> bool:
        """
        Validate the output of a specific plugin.

        Args:
            plugin_name: The name of the plugin.
            content: The content to validate.
            stage_name: The name of the current stage.
            phase_name: The name of the current phase.

        Returns:
            bool: True if the content is valid, False otherwise.

        Raises:
            PluginError: If the plugin is not found or validation fails.
        """
        try:
            plugin = self.get_plugin(plugin_name)
            return plugin.validate(content, stage_name, phase_name)
        except PluginError as exc:
            logger.error("Error validating output for plugin %s: %s", plugin_name, str(exc))
            raise

    async def attempt_plugin_repair(self, plugin_name: str, content: str, stage_name: str, phase_name: str, **kwargs: Any) -> Any:
        """
        Attempt to repair invalid content using the specified plugin.

        Args:
            plugin_name: The name of the plugin.
            content: The invalid content to repair.
            stage_name: The name of the current stage.
            phase_name: The name of the current phase.
            **kwargs: Additional keyword arguments for the repair process.

        Returns:
            Any: The repaired content.

        Raises:
            PluginError: If the plugin is not found or repair fails.
        """
        try:
            plugin = self.get_plugin(plugin_name)
            return await plugin.attempt_repair(content, stage_name=stage_name, phase_name=phase_name, **kwargs)
        except PluginError as exc:
            logger.error("Error attempting repair for plugin %s: %s", plugin_name, str(exc))
            raise

    def get_plugin_format(self, plugin_name: str) -> str:
        """
        Get the format handled by a specific plugin.

        Args:
            plugin_name: The name of the plugin.

        Returns:
            str: The format handled by the plugin.

        Raises:
            PluginError: If the plugin is not found.
        """
        try:
            plugin = self.get_plugin(plugin_name)
            return plugin.get_format()
        except PluginError as exc:
            logger.error("Error getting format for plugin %s: %s", plugin_name, str(exc))
            raise

    def get_plugin_extension(self, plugin_name: str) -> str:
        """
        Get the file extension for the output format of a specific plugin.

        Args:
            plugin_name: The name of the plugin.

        Returns:
            str: The file extension for the plugin's output format.

        Raises:
            PluginError: If the plugin is not found.
        """
        try:
            plugin = self.get_plugin(plugin_name)
            return plugin.get_extension()
        except PluginError as exc:
            logger.error("Error getting extension for plugin %s: %s", plugin_name, str(exc))
            raise
