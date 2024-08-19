"""
storyteller_path_manager.py

This module provides a comprehensive path management system for the storytelling application.
It handles path construction, validation, and ensures the existence of required directories.

The StorytellerPathManager class is the main component of this module, offering methods to
retrieve, construct, and validate paths for various resources such as configuration files,
plugins, prompts, and storage locations.

Usage:
    from storyteller_path_manager import StorytellerPathManager
    from config.storyteller_configuration_types import StorytellerConfig

    config: StorytellerConfig = {
        'paths': {
            'root': '/path/to/project',
            'config': 'config',
            'plugins': 'plugins',
            # ... other path configurations
        },
        'guidance': {
            'folder': 'guidance'
        }
    }

    path_manager = StorytellerPathManager(config)
    config_path = path_manager.get_config_path('pipeline')
    prompt_path = path_manager.get_prompt_path('stage1_prompt')
    path_manager.ensure_directory(some_path)
"""

import logging
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

from config.storyteller_configuration_types import StorytellerConfig, GuidanceConfig, StageConfig

logger = logging.getLogger(__name__)


class StorytellerPathError(Exception):
    """Custom exception for path-related errors in the storytelling system."""


class StorytellerPathManager:
    """
    Manages file and directory paths used throughout the storytelling system.

    This class provides methods for constructing, validating, and managing paths for various
    components of the storytelling system, including configuration files, plugins, prompts, and
    storage locations.

    Attributes:
        root_path (Path): The root path of the project.
        paths (Dict[str, Path]): A dictionary of predefined paths.
        _lock (Lock): A threading lock for ensuring thread-safe operations.
    """

    def __init__(self, config: StorytellerConfig) -> None:
        """
        Initialize the StorytellerPathManager.

        Args:
            config (StorytellerConfig): Configuration dictionary for paths and guidance.

        Raises:
            StorytellerPathError: If required configuration keys are missing or if paths are invalid.
        """
        self._lock = Lock()
        try:
            # Ensure the root path is valid and resolvable
            self.root_path = Path(config['paths']['root']).resolve(strict=True)
            self.config: StorytellerConfig = config
            self.paths: Dict[str, Path] = {}

            for key, value in config['paths'].items():
                if key == 'root':
                    continue
                if not isinstance(value, (str, Path)):
                    raise StorytellerPathError(f"Invalid path type for key {key}: {type(value)}")

                # Use Path(self.root_path, value) to correctly handle relative paths
                self.paths[key] = Path(self.root_path, value).resolve()

            # Handle guidance path
            guidance_folder = config['guidance']['folder']
            if not isinstance(guidance_folder, (str, Path)):
                raise StorytellerPathError("Invalid guidance folder path type")
            self.paths['guidance'] = Path(self.root_path, guidance_folder).resolve()

        except KeyError as e:
            logger.error("Missing required configuration key: %s", e)
            raise StorytellerPathError(f"Missing required configuration key: {e}") from e
        except (OSError, ValueError) as e:
            logger.error("Invalid path configuration: %s", e)
            raise StorytellerPathError(f"Invalid path configuration: {e}") from e

        for key, path in self.paths.items():
            if not path.parent.exists():
                logger.warning("Parent directory for %s does not exist: %s", key, path.parent)

    def construct_path(self, *path_parts: str | Path) -> Path:
        """
        Construct a path from the given parts, relative to the root path.

        Args:
            *path_parts: Path parts to join.

        Returns:
            Path: The constructed path.
        """
        return self.root_path.joinpath(*[Path(part) for part in path_parts])

    def validate_path(self, path: Path, expected_type: str = 'any') -> None:
        """
        Validate that a path exists and is of the expected type.

        Args:
            path (Path): The path to validate.
            expected_type (str): The expected type ('file', 'directory', or 'any'). Defaults to 'any'.

        Raises:
            StorytellerPathError: If the path is invalid or of the wrong type.
        """
        if not path.exists():
            logger.error("Path does not exist: %s", path)
            raise StorytellerPathError(f"Path does not exist: {path}")

        if expected_type == 'file' and not path.is_file():
            logger.error("Expected file, but found directory: %s", path)
            raise StorytellerPathError(f"Expected file, but found directory: {path}")
        elif expected_type == 'directory' and not path.is_dir():
            logger.error("Expected directory, but found file: %s", path)
            raise StorytellerPathError(f"Expected directory, but found file: {path}")

    def ensure_directory(self, path: Path) -> None:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path (Path): The directory path to ensure.

        Raises:
            StorytellerPathError: If the directory cannot be created.
        """
        with self._lock:
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.info("Ensured directory exists: %s", path)
            except OSError as e:
                logger.error("Failed to create directory %s: %s", path, e)
                raise StorytellerPathError(f"Failed to create directory: {e}") from e

    def get_path(self, key: str) -> Path:
        """
        Get a predefined path.

        Args:
            key (str): The key for the path in the configuration.

        Returns:
            Path: The requested path.

        Raises:
            StorytellerPathError: If the key is not found in the configuration.
        """
        try:
            return self.paths[key]
        except KeyError as e:
            logger.error("Path key not found: %s", key)
            raise StorytellerPathError(f"Path key not found: {key}") from e

    def ensure_file_exists(self, path: Path) -> None:
        """
        Ensure a file exists.

        Args:
            path (Path): The file path to check.

        Raises:
            StorytellerPathError: If the file does not exist.
        """
        if not path.is_file():
            logger.error("File not found: %s", path)
            raise StorytellerPathError(f"File not found: {path}")

    def get_config_path(self, config_name: str) -> Path:
        """
        Get the path for a configuration file.

        Args:
            config_name (str): The name of the configuration file (without extension).

        Returns:
            Path: The full path to the configuration file.

        Raises:
            StorytellerPathError: If the configuration file does not exist.
        """
        path = self.get_path('config') / f"{config_name}.yaml"
        self.ensure_file_exists(path)
        return path

    def get_plugin_path(self, plugin_name: str) -> Path:
        """
        Get the path for a plugin file.

        Args:
            plugin_name (str): The name of the plugin file (without extension).

        Returns:
            Path: The full path to the plugin file.

        Raises:
            StorytellerPathError: If the plugin file does not exist.
        """
        path = self.get_path('plugins') / f"{plugin_name}.py"
        self.ensure_file_exists(path)
        return path

    def get_prompt_path(self, prompt_name: str) -> Path:
        """
        Get the path for a prompt file.

        Args:
            prompt_name (str): The name of the prompt file (without extension).

        Returns:
            Path: The full path to the prompt file.

        Raises:
            StorytellerPathError: If the prompt file does not exist.
        """
        path = self.get_path('prompts') / f"{prompt_name}"
        self.ensure_file_exists(path)
        return path

    def get_schema_path(self, schema_name: str) -> Path:
        """
        Get the path for a schema file.

        Args:
            schema_name (str): The name of the schema file (without extension).

        Returns:
            Path: The full path to the schema file.

        Raises:
            StorytellerPathError: If the schema file does not exist.
        """
        path = self.get_path('schemas') / f"{schema_name}"
        self.ensure_file_exists(path)
        return path

    def get_data_path(self, data_name: str) -> Path:
        """
        Get the path for a data file.

        Args:
            data_name (str): The name of the data file (including extension).

        Returns:
            Path: The full path to the data file.

        Raises:
            StorytellerPathError: If the data file does not exist.
        """
        path = self.get_path('data') / data_name
        self.ensure_file_exists(path)
        return path

    def get_batch_storage_path(self, batch_name: str) -> Path:
        """
        Get the path for batch storage.

        Args:
            batch_name (str): The name of the batch.

        Returns:
            Path: The full path to the batch storage directory.
        """
        path = self.get_path('batch_storage') / batch_name
        self.ensure_directory(path)
        return path

    def get_ephemeral_storage_path(self, storage_name: str) -> Path:
        """
        Get the path for ephemeral storage.

        Args:
            storage_name (str): The name of the ephemeral storage.

        Returns:
            Path: The full path to the ephemeral storage directory.
        """
        path = self.get_path('ephemeral_storage') / storage_name
        self.ensure_directory(path)
        return path

    def get_output_storage_path(self, folder_name: str) -> Path:
        """
        Get the path for an output folder.

        Args:
            folder_name (str): The name of the output folder.

        Returns:
            Path: The full path to the output folder.
        """
        path = self.get_path('output_folder') / folder_name
        self.ensure_directory(path)
        return path

    def get_run_specific_guidance_path(self, guidance_key: str) -> Path:
        """
        Get the full path for a run-specific guidance file.
        Args:
            guidance_key (str): The key for the specific guidance file (e.g., "generic", "hats", "cats").
        Returns:
            Path: The full path to the guidance file.
        Raises:
            StorytellerPathError: If the guidance file is not found.
        """
        guidance: GuidanceConfig = self.config['guidance']
        guidance_config = next((gconfig for key, gconfig in guidance.items()
                                if key != 'folder' and isinstance(gconfig, dict) and gconfig.get('tag') == guidance_key), None)
        if not guidance_config:
            raise StorytellerPathError(f"Guidance configuration not found for key: {guidance_key}")
        guidance_path = self.get_path('guidance') / guidance_config.get('path', '')
        self.ensure_file_exists(guidance_path)
        return guidance_path

    def get_stage_specific_guidance_path(self, stage_name: str) -> Path:
        """
        Get the full path for a stage-specific guidance file.
        Args:
            stage_name (str): The name of the stage.
        Returns:
            Path: The full path to the guidance file.
        Raises:
            StorytellerPathError: If the stage is not found or the guidance file is not found.
        """
        stage_config: Optional[StageConfig] = next(
            (stage for stage in self.config['stages'] if stage['name'] == stage_name),
            None
        )
        if stage_config is None:
            raise StorytellerPathError(f"Stage not found: {stage_name}")

        guidance_filename = stage_config['guidance']
        guidance_path = self.get_path('guidance') / guidance_filename
        self.ensure_file_exists(guidance_path)
        return guidance_path

    def get_relative_path(self, path: Path) -> Path:
        """
        Get a path relative to the root path.

        Args:
            path (Path): The path to make relative.

        Returns:
            Path: The relative path.
        """
        return path.relative_to(self.root_path)
