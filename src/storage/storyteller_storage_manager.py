"""
Storyteller Storage Manager Module

This module provides a centralized management system for storage operations
in the Storyteller application. It coordinates batch storage, ephemeral storage,
and output storage operations, abstracting the complexities of different storage
types and content processing.

The `StorytellerStorageManager` class serves as the main interface for all
storage-related operations, using the `StorytellerContentPacket` class to standardize
the handling of content across the system.

Usage:
    from storyteller_storage_manager import StorytellerStorageManager
    from storyteller_plugin_manager import StorytellerPluginManager
    from storyteller_stage_manager import StorytellerStageManager
    from storyteller_progress_tracker import StorytellerProgressTracker
    from llm.storyteller_llm_interface import StorytellerLLMInterface

    plugin_manager = StorytellerPluginManager()
    stage_manager = StorytellerStageManager()
    llm_instance = StorytellerLLMInterface()
    progress_tracker = StorytellerProgressTracker()

    async with StorytellerStorageManager(
        plugin_manager, stage_manager, llm_instance, progress_tracker
    ) as storage_manager:
        await storage_manager.start_new_batch()
        await storage_manager.create_batch_run(1)
        content_packet = StorytellerContentPacket(...)
        processed_packet = await storage_manager.process_content(content_packet)
        await storage_manager.save_batch_content(processed_packet)
"""

import asyncio
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, List, Optional, Dict, Type, Tuple, cast, Callable

from config.storyteller_configuration_manager import storyteller_config
from content.storyteller_content_processor import StorytellerContentProcessor
from llm.storyteller_llm_interface import StorytellerLLMInterface
from storage.storyteller_batch_storage import StorytellerBatchStorage
from storage.storyteller_ephemeral_storage import StorytellerEphemeralStorage
from storage.storyteller_output_storage import StorytellerOutputStorage
from storage.storyteller_storage_validator import StorageValidator
from storage.storyteller_storage_types import (
    StorytellerStorageInitializationError,
    StorytellerStorageReadError,
    StorytellerStorageWriteError,
    StorytellerStorageError,
)
from plugins.storyteller_plugin_manager import StorytellerPluginManager
from orchestration.storyteller_stage_manager import (
    StorytellerStageManager,
    StorytellerProgressTracker,
)

from common.storyteller_types import StorytellerContentPacket

logger = logging.getLogger(__name__)


class StorageFactory:
    """Factory class for creating storage instances based on type."""

    @staticmethod
    def get_storage(storage_type: str,
                    config: Dict[str, Any]) -> StorytellerBatchStorage | StorytellerEphemeralStorage | StorytellerOutputStorage:
        """
        Create and return a storage instance based on the specified type.

        Args:
            storage_type (str): The type of storage to create ("batch", "ephemeral", or "output").
            config (Dict[str, Any]): The configuration dictionary containing paths for storage.

        Returns:
            Union[StorytellerBatchStorage, StorytellerEphemeralStorage, StorytellerOutputStorage]: The storage instance.

        Raises:
            ValueError: If an invalid storage type is provided.
        """
        if storage_type == "batch":
            return StorytellerBatchStorage(Path(config["batch_path"]))
        elif storage_type == "ephemeral":
            return StorytellerEphemeralStorage(Path(config["ephemeral_path"]))
        elif storage_type == "output":
            return StorytellerOutputStorage(Path(config["output_path"]))
        else:
            raise ValueError(f"Invalid storage type: {storage_type}")


class StorytellerStorageManager:
    """
    Manages the lifecycle and operations of batch, ephemeral, and output storage,
    as well as content processing and cleanup.

    This class provides a unified interface for managing storage operations
    within the Storyteller system. It handles the initialization of storage,
    processing, saving and retrieving content, and cleaning up old storage runs.

    Attributes:
        plugin_manager (StorytellerPluginManager): Manages plugins used for content processing and serialization.
        stage_manager (StorytellerStageManager): Manages stages and phases in the content processing pipeline.
        llm_instance (StorytellerLLMInterface): Instance of the LLM used for content generation and repair.
        progress_tracker (StorytellerProgressTracker): Tracks progress across stages and phases.
        ephemeral_storage (StorytellerEphemeralStorage): Manages ephemeral storage operations.
        batch_storage (StorytellerBatchStorage): Manages batch storage operations.
        output_storage (StorytellerOutputStorage): Manages output storage operations.
        content_processor (StorytellerContentProcessor): Processes content using plugins.
    """

    def __init__(
        self,
        plugin_manager: StorytellerPluginManager,
        stage_manager: StorytellerStageManager,
        llm_instance: StorytellerLLMInterface,
        progress_tracker: StorytellerProgressTracker,
    ) -> None:
        """
        Initialize the StorytellerStorageManager with necessary components.

        Args:
            plugin_manager (StorytellerPluginManager): The plugin manager instance.
            stage_manager (StorytellerStageManager): The stage manager instance.
            llm_instance (StorytellerLLMInterface): The LLM interface instance.
            progress_tracker (StorytellerProgressTracker): The progress tracker instance.

        Raises:
            StorytellerStorageInitializationError: If storage paths cannot be initialized or validated.
        """
        self.config_manager = storyteller_config
        self.plugin_manager = plugin_manager
        self.stage_manager = stage_manager
        self.llm_instance = llm_instance
        self.progress_tracker = progress_tracker

        if self.config_manager.path_manager is None:
            raise StorytellerStorageInitializationError(
                "Path manager is not initialized"
            )

        batch_name = self.config_manager.get_nested_config_value("batch.name")

        try:
            paths = {
                "ephemeral_path": self.config_manager.path_manager.get_ephemeral_storage_path(batch_name),
                "batch_path": self.config_manager.path_manager.get_batch_storage_path(batch_name),
                "output_path": self.config_manager.path_manager.get_output_storage_path(batch_name),
            }

            for storage_type, path in paths.items():
                StorageValidator.validate_storage_path(Path(path), f"{storage_type.capitalize()} storage")

            self.ephemeral_storage: StorytellerEphemeralStorage = cast(
                StorytellerEphemeralStorage, StorageFactory.get_storage("ephemeral", paths)
            )
            self.batch_storage: StorytellerBatchStorage = cast(
                StorytellerBatchStorage, StorageFactory.get_storage("batch", paths)
            )
            self.output_storage: StorytellerOutputStorage = cast(
                StorytellerOutputStorage, StorageFactory.get_storage("output", paths)
            )

            assert isinstance(self.ephemeral_storage, StorytellerEphemeralStorage), \
                "Ephemeral storage is not an instance of StorytellerEphemeralStorage"
            assert isinstance(self.batch_storage, StorytellerBatchStorage), \
                "Batch storage is not an instance of StorytellerBatchStorage"
            assert isinstance(self.output_storage, StorytellerOutputStorage), \
                "Output storage is not an instance of StorytellerOutputStorage"

            self.content_processor = StorytellerContentProcessor(
                plugin_manager,
                stage_manager,
                llm_instance,
                progress_tracker,
                self.batch_storage,
                self.ephemeral_storage,
            )
        except (ValueError, OSError) as e:
            raise StorytellerStorageInitializationError(
                f"Failed to initialize storage: {e}"
            ) from e

    async def __aenter__(self) -> "StorytellerStorageManager":
        """
        Async enter method for context manager support.

        Returns:
            StorytellerStorageManager: The StorytellerStorageManager instance.
        """
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """
        Async exit method for context manager support.

        Args:
            exc_type (Optional[Type[BaseException]]): The type of the exception that caused the context to be exited.
            exc_val (Optional[BaseException]): The instance of the exception that caused the context to be exited.
            exc_tb (Optional[Any]): A traceback object encoding the stack trace.
        """
        await self.cleanup()

    async def cleanup(self) -> None:
        """
        Cleanup method to clear ephemeral storage.

        This method is called during the exit of the context manager to ensure
        ephemeral storage is cleaned up.

        Raises:
            OSError: If the cleanup operation fails.
        """
        try:
            await self.ephemeral_storage.clear_storage()
            logger.info("Cleaned up ephemeral storage.")
        except OSError as e:
            logger.error("Error during storage manager cleanup: %s", e)

    async def start_new_batch(self) -> None:
        """
        Start a new batch and clear ephemeral storage.

        This method initializes a new batch storage and clears any existing ephemeral storage.

        Raises:
            StorytellerStorageInitializationError: If batch or ephemeral storage is not initialized.
            OSError: If the operation fails.
        """
        if not self.batch_storage or not self.ephemeral_storage:
            raise StorytellerStorageInitializationError("Batch or ephemeral storage is not initialized")

        try:
            await self.batch_storage.start_new_batch()
            await self.ephemeral_storage.clear_storage()  # Clear at the end of each run.
            logger.info("Started new batch and cleared ephemeral storage.")
        except OSError as e:
            raise StorytellerStorageInitializationError(f"Failed to start new batch: {e}") from e

    async def create_batch_run(self, batch_id: int) -> None:
        """
        Create a new batch run folder within the current batch.

        Args:
            batch_id (int): The unique identifier for the batch run.

        Raises:
            StorytellerBatchRunError: If start_new_batch has not been called before creating a batch run.
            OSError: If the directory creation fails.
        """
        await self.batch_storage.create_batch_run(batch_id)

    async def process_content(self, packet: StorytellerContentPacket) -> Tuple[StorytellerContentPacket, bool]:
        """
        Process content using the content processor.

        Args:
            packet (StorytellerContentPacket): A ContentPacket containing the content and metadata to be processed.

        Returns:
            Tuple[StorytellerContentPacket, bool]: The processed content packaged in a ContentPacket and a success flag.

        Raises:
            StorytellerContentProcessingError: If the content cannot be processed.
        """
        processed_packet, success = await self.content_processor.process_content(packet)
        return processed_packet, success

    async def save_to_ephemeral(
        self,
        content: str,
        stage_name: str,
        phase_name: str,
        plugin_name: str,
        identifier: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StorytellerContentPacket:
        """
        Save content to ephemeral storage and return a copy of the created content packet.

        Args:
            content (str): The content to be saved.
            stage_name (str): The name of the stage.
            phase_name (str): The name of the phase.
            plugin_name (str): The name of the plugin used.
            identifier (str): A free text field that is appended to the file name.
            metadata (Optional[Dict[str, Any]]): Additional metadata for the content.

        Returns:
            StorytellerContentPacket: A copy of the created content packet.

        Raises:
            StorytellerStorageWriteError: If the content cannot be saved.
            ValueError: If the specified plugin is not found.
        """
        packet = self.create_content_packet(content=content, stage_name=stage_name, phase_name=phase_name,
                                            plugin_name=plugin_name, identifier=identifier, metadata=metadata)
        await self.save_ephemeral_content(packet)
        return deepcopy(packet)

    async def save_to_batch(
        self,
        content: str,
        stage_name: str,
        phase_name: str,
        plugin_name: str,
        identifier: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StorytellerContentPacket:
        """
        Save content to batch storage and return a copy of the created content packet.

        Args:
            content (str): The content to be saved.
            stage_name (str): The name of the stage.
            phase_name (str): The name of the phase.
            plugin_name (str): The name of the plugin used.
            identifier (str): A free text field that is appended to the file name.
            metadata (Optional[Dict[str, Any]]): Additional metadata for the content.

        Returns:
            StorytellerContentPacket: A copy of the created content packet.

        Raises:
            StorytellerStorageWriteError: If the content cannot be saved.
            ValueError: If the specified plugin is not found.
        """
        packet = self.create_content_packet(content=content, stage_name=stage_name, phase_name=phase_name,
                                            plugin_name=plugin_name, identifier=identifier, metadata=metadata)
        await self.save_batch_content(packet)
        return deepcopy(packet)

    async def save_to_output(
        self,
        content: str,
        stage_name: str,
        phase_name: str,
        plugin_name: str,
        identifier: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StorytellerContentPacket:
        """
        Save content to output storage and return a copy of the created content packet.

        Args:
            content (str): The content to be saved.
            stage_name (str): The name of the stage.
            phase_name (str): The name of the phase.
            plugin_name (str): The name of the plugin used.
            identifier (str): A free text field that is appended to the file name.
            metadata (Optional[Dict[str, Any]]): Additional metadata for the content.

        Returns:
            StorytellerContentPacket: A copy of the created content packet.

        Raises:
            StorytellerStorageWriteError: If the content cannot be saved.
            ValueError: If the specified plugin is not found.
        """
        packet = self.create_content_packet(content=content, stage_name=stage_name, phase_name=phase_name,
                                            plugin_name=plugin_name, identifier=identifier, metadata=metadata)
        await self.save_output_content(packet)
        return deepcopy(packet)

    def create_content_packet(
        self,
        *,
        content: str,
        stage_name: str,
        phase_name: str,
        plugin_name: str,
        identifier: str,
        prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        file_extension: Optional[str] = None
    ) -> StorytellerContentPacket:
        """
        Create a StorytellerContentPacket from the given parameters.

        Args:
            content (str): The content to be saved.
            stage_name (str): The name of the stage.
            phase_name (str): The name of the phase.
            plugin_name (str): The name of the plugin used.
            identifier (str): A unique identifier for the content packet.
            prompt (Optional[str]): The prompt used to generate the content. Defaults to None.
            metadata (Optional[Dict[str, Any]]): Additional metadata for the content. Defaults to None.
            file_extension (Optional[str]): Custom file extension to override the plugin's default. Defaults to None.

        Returns:
            StorytellerContentPacket: A newly created content packet.

        Raises:
            ValueError: If the specified plugin is not found.
        """
        plugin = self.plugin_manager.get_plugin(plugin_name)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_name} not found")

        # Use the provided file_extension if given, otherwise use the plugin's default
        extension = file_extension if file_extension is not None else plugin.get_extension()

        file_name = f"{stage_name}_{phase_name}_{identifier}.{extension}"

        # Initialize metadata if it's None
        metadata = metadata or {}

        # Add prompt to metadata if provided
        if prompt is not None:
            metadata['prompt'] = prompt

        return StorytellerContentPacket(
            content=content,
            file_name=file_name,
            file_extension=extension,
            plugin_name=plugin_name,
            stage_name=stage_name,
            phase_name=phase_name,
            metadata=metadata
        )

    async def save_output_content(self, packet: StorytellerContentPacket) -> None:
        """
        Save final content to output storage when a run ends.

        Args:
            packet (StorytellerContentPacket): A ContentPacket containing the content and metadata to be saved.

        Raises:
            StorytellerStorageWriteError: If the content cannot be saved.
        """
        try:
            await self.output_storage.save_content(packet)
        except StorytellerStorageError as e:
            raise StorytellerStorageWriteError(
                f"Failed to save output content: {e}"
            ) from e

    async def save_ephemeral_content(self, packet: StorytellerContentPacket) -> None:
        """
        Save content to ephemeral storage.

        Args:
            packet (StorytellerContentPacket): A ContentPacket containing the content and metadata to be saved.

        Raises:
            StorytellerStorageWriteError: If the content cannot be saved.
        """
        try:
            await self.ephemeral_storage.save_content(packet)
        except StorytellerStorageError as e:
            raise StorytellerStorageWriteError(
                f"Failed to save ephemeral content: {e}"
            ) from e

    async def save_batch_content(self, packet: StorytellerContentPacket) -> None:
        """
        Save content to batch storage.

        Args:
            packet (StorytellerContentPacket): A ContentPacket containing the content and metadata to be saved.

        Raises:
            StorytellerStorageWriteError: If the content cannot be saved.
        """
        try:
            await self.batch_storage.save_content(packet)
        except StorytellerStorageError as e:
            raise StorytellerStorageWriteError(
                f"Failed to save batch content: {e}"
            ) from e

    async def get_batch_content(
        self, packet: StorytellerContentPacket
    ) -> StorytellerContentPacket:
        """
        Retrieve content from batch storage.

        Args:
            packet (StorytellerContentPacket): A ContentPacket containing metadata to identify the content.

        Returns:
            StorytellerContentPacket: The retrieved content packaged in a ContentPacket.

        Raises:
            StorytellerStorageReadError: If the content cannot be retrieved.
        """
        try:
            return await self.batch_storage.load_content(packet)
        except StorytellerStorageError as e:
            raise StorytellerStorageReadError(
                f"Failed to retrieve batch content: {e}"
            ) from e

    async def get_ephemeral_content(
        self, packet: StorytellerContentPacket
    ) -> StorytellerContentPacket:
        """
        Retrieve content from ephemeral storage.

        Args:
            packet (StorytellerContentPacket): A ContentPacket containing metadata to identify the content.

        Returns:
            StorytellerContentPacket: The retrieved content packaged in a ContentPacket.

        Raises:
            StorytellerStorageReadError: If the content cannot be retrieved.
        """
        try:
            return await self.ephemeral_storage.load_content(packet)
        except StorytellerStorageError as e:
            raise StorytellerStorageReadError(
                f"Failed to retrieve ephemeral content: {e}"
            ) from e

    async def get_output_content(
        self, packet: StorytellerContentPacket
    ) -> StorytellerContentPacket:
        """
        Get the content of the output file.

        Args:
            packet (StorytellerContentPacket): A ContentPacket containing metadata to identify the content.

        Returns:
            StorytellerContentPacket: The retrieved content packaged in a ContentPacket.

        Raises:
            StorytellerStorageReadError: If the content cannot be retrieved.
        """
        try:
            return await self.output_storage.load_content(packet)
        except StorytellerStorageError as e:
            raise StorytellerStorageReadError(
                f"Failed to retrieve output content: {e}"
            ) from e

    async def cleanup_old_batch_runs(
        self, max_folders: Optional[int] = None, max_days: Optional[int] = None
    ) -> None:
        """
        Clean up old batch run folders based on the specified constraints.

        Args:
            max_folders (Optional[int]): The maximum number of batch run folders to keep.
            max_days (Optional[int]): The maximum age (in days) of batch run folders to keep.

        Raises:
            ValueError: If neither max_folders nor max_days is specified.
            StorytellerStorageError: If cleanup operation fails.
        """
        try:
            await self.batch_storage.cleanup_old_batch_runs(max_folders, max_days)
            logger.info("Cleaned up old batch runs.")
        except (ValueError, OSError) as e:
            logger.error("Failed to clean up old batch runs: %s", e)
            raise StorytellerStorageError(
                f"Failed to clean up old batch runs: {e}"
            ) from e

    def get_current_datetime_folder(self) -> Optional[str]:
        """
        Get the current datetime folder name used in batch storage.

        Returns:
            Optional[str]: The name of the current datetime folder, or None if not set.
        """
        return getattr(self.batch_storage, 'current_datetime_folder', None)

    def get_current_batch_run_folder(self) -> Optional[Path]:
        """
        Get the path to the current batch run folder.

        Returns:
            Optional[Path]: The path to the current batch run folder, or None if not set.
        """
        return getattr(self.batch_storage, 'current_batch_run_folder', None)

    def get_ephemeral_storage_path(self) -> Path:
        """
        Get the path to the ephemeral storage.

        Returns:
            Path: The path to the ephemeral storage.
        """
        return self.ephemeral_storage.storage_path

    def get_batch_storage_path(self) -> Path:
        """
        Get the path to the batch storage.

        Returns:
            Path: The path to the batch storage.

        Raises:
            AssertionError: If batch storage is not initialized.
        """
        assert self.batch_storage is not None, "Batch storage is not initialized"
        return getattr(self.batch_storage, 'batch_storage_path', self.batch_storage.storage_path)

    async def content_exists(
        self, storage_type: str, packet: StorytellerContentPacket
    ) -> bool:
        """
        Check if specific content exists in the given storage type.

        Args:
            storage_type (str): The type of storage to check ("ephemeral", "batch", or "output").
            packet (StorytellerContentPacket): The content packet to check for existence.

        Returns:
            bool: True if the content exists, False otherwise.

        Raises:
            ValueError: If an invalid storage_type is provided.
        """
        if storage_type == "ephemeral":
            return await self.ephemeral_storage.content_exists(packet)
        elif storage_type == "batch":
            return await self.batch_storage.content_exists(packet)
        elif storage_type == "output":
            return await self.output_storage.content_exists(packet)
        else:
            raise ValueError(
                f"Invalid storage type: {storage_type}. Must be 'ephemeral', 'batch', or 'output'"
            )

    async def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about the current state of storage.

        Returns:
            Dict[str, Any]: A dictionary containing information about the current storage state,
            including current batch and run folders, and storage paths.
        """
        return {
            "current_datetime_folder": self.get_current_datetime_folder(),
            "current_batch_run_folder": str(self.get_current_batch_run_folder()),
            "ephemeral_storage_path": str(self.get_ephemeral_storage_path()),
            "batch_storage_path": str(self.get_batch_storage_path()),
        }

    async def validate_storage_integrity(self) -> bool:
        """
        Validate the integrity of the storage system.

        This method checks if all required storage paths exist and are accessible.

        Returns:
            bool: True if the storage system is valid, False otherwise.

        Raises:
            StorytellerStorageInitializationError: If there's an error during validation.
        """
        try:
            StorageValidator.validate_storage_path(
                self.get_ephemeral_storage_path(), "Ephemeral storage"
            )
            StorageValidator.validate_storage_path(
                self.get_batch_storage_path(), "Batch storage"
            )
            return True
        except ValueError as e:
            logger.error("Storage integrity validation failed: %s", e)
            return False
        except OSError as e:
            raise StorytellerStorageInitializationError(
                f"Error during storage integrity validation: {e}"
            ) from e

    async def move_content(
        self, source_storage: str, target_storage: str, packet: StorytellerContentPacket
    ) -> None:
        """
        Move content from one storage type to another.

        Args:
            source_storage (str): The source storage type ("ephemeral", "batch", or "output").
            target_storage (str): The target storage type ("ephemeral", "batch", or "output").
            packet (StorytellerContentPacket): The content packet to be moved.

        Raises:
            ValueError: If an invalid storage type is provided.
            StorytellerStorageError: If the content cannot be moved.
        """
        valid_storage_types = {"ephemeral", "batch", "output"}
        if source_storage not in valid_storage_types or target_storage not in valid_storage_types:
            raise ValueError(
                "Invalid storage type. Must be 'ephemeral', 'batch', or 'output'"
            )

        try:
            source = getattr(self, f"{source_storage}_storage")
            target = getattr(self, f"{target_storage}_storage")

            content = await source.load_content(packet)
            await target.save_content(content)
            await source.remove_content(packet)

            logger.info(
                "Moved content from %s to %s: %s",
                source_storage,
                target_storage,
                packet.file_name,
            )
        except StorytellerStorageError as e:
            logger.error(
                "Failed to move content from %s to %s: %s",
                source_storage,
                target_storage,
                e,
            )
            raise StorytellerStorageError(f"Content move failed: {e}") from e

    async def copy_content(
        self, source_storage: str, target_storage: str, packet: StorytellerContentPacket
    ) -> None:
        """
        Copy content from one storage type to another.

        Args:
            source_storage (str): The source storage type ("ephemeral", "batch", or "output").
            target_storage (str): The target storage type ("ephemeral", "batch", or "output").
            packet (StorytellerContentPacket): The content packet to be copied.

        Raises:
            ValueError: If an invalid storage type is provided.
            StorytellerStorageError: If the content cannot be copied.
        """
        valid_storage_types = {"ephemeral", "batch", "output"}
        if source_storage not in valid_storage_types or target_storage not in valid_storage_types:
            raise ValueError(
                "Invalid storage type. Must be 'ephemeral', 'batch', or 'output'"
            )

        try:
            source = getattr(self, f"{source_storage}_storage")
            target = getattr(self, f"{target_storage}_storage")

            content = await source.load_content(packet)
            await target.save_content(content)

            logger.info(
                "Copied content from %s to %s: %s",
                source_storage,
                target_storage,
                packet.file_name,
            )
        except StorytellerStorageError as e:
            logger.error(
                "Failed to copy content from %s to %s: %s",
                source_storage,
                target_storage,
                e,
            )
            raise StorytellerStorageError(f"Content copy failed: {e}") from e

    async def list_content(
        self,
        storage_type: str,
        stage_name: Optional[str] = None,
        phase_name: Optional[str] = None,
    ) -> List[StorytellerContentPacket]:
        """
        List content in the specified storage type, optionally filtered by stage and phase.

        Args:
            storage_type (str): The type of storage to list ("ephemeral", "batch", or "output").
            stage_name (Optional[str]): Optional filter for stage name.
            phase_name (Optional[str]): Optional filter for phase name.

        Returns:
            List[StorytellerContentPacket]: A list of ContentPackets containing information about each content item.

        Raises:
            ValueError: If an invalid storage_type is provided.
        """
        if storage_type not in {"ephemeral", "batch", "output"}:
            raise ValueError(
                f"Invalid storage type: {storage_type}. Must be 'ephemeral', 'batch', or 'output'"
            )

        storage = getattr(self, f"{storage_type}_storage")
        return await storage.list_content(stage_name, phase_name)

    async def retry_operation(
        self, operation: Callable[..., Any], *args: Any, max_retries: int = 3, **kwargs: Any
    ) -> Any:
        """
        Retry an operation with exponential backoff.

        Args:
            operation (Callable): The operation to retry.
            *args: Positional arguments to pass to the operation.
            max_retries (int): The maximum number of retry attempts.
            **kwargs: Keyword arguments to pass to the operation.

        Returns:
            Any: The result of the successful operation.

        Raises:
            StorytellerStorageError: If all retry attempts fail.
        """
        for attempt in range(max_retries):
            try:
                return await operation(*args, **kwargs)
            except StorytellerStorageError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(
                    "Operation failed, retrying (%d/%d): %s",
                    attempt + 1,
                    max_retries,
                    str(e),
                )
                await asyncio.sleep(2**attempt)  # Exponential backoff

    async def get_storage_stats(self, storage_type: str) -> Dict[str, Any]:
        """
        Get detailed statistics about the specified storage type.

        Args:
            storage_type (str): The type of storage to get stats for ("ephemeral", "batch", or "output").

        Returns:
            Dict[str, Any]: A dictionary containing detailed storage statistics.

        Raises:
            ValueError: If an invalid storage_type is provided.
        """
        if storage_type not in {"ephemeral", "batch", "output"}:
            raise ValueError(
                f"Invalid storage type: {storage_type}. Must be 'ephemeral', 'batch', or 'output'"
            )

        storage = getattr(self, f"{storage_type}_storage")
        return await storage.get_storage_stats()
