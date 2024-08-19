"""
Storyteller Batch Storage Module

This module provides the StorytellerBatchStorage class for managing long-term batch storage
operations in the Storyteller application. It handles saving, loading, and managing content
across different stages and phases of the storytelling process.

The StorytellerBatchStorage class implements the StorytellerStorageBase interface, ensuring
consistent storage operations across the Storyteller system. It uses a directory-based
structure for organizing batch data and provides methods for creating new batches, managing
batch runs, and handling content storage and retrieval.

Usage:
    from storyteller_batch_storage import StorytellerBatchStorage
    from pathlib import Path
    from storyteller_storage_types import StorytellerContentPacket

    # Initialize the batch storage
    batch_storage = StorytellerBatchStorage(Path("/path/to/batch/storage"))

    # Start a new batch and create a batch run
    await batch_storage.start_new_batch()
    await batch_storage.create_batch_run(1)

    # Save content
    content_packet = StorytellerContentPacket(...)
    await batch_storage.save_content(content_packet)

    # Load content
    loaded_content = await batch_storage.load_content(content_packet)

    # List content
    content_list = await batch_storage.list_content()

    # Clean up old batch runs
    await batch_storage.cleanup_old_batch_runs(max_folders=10, max_days=30)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

import aiofiles
import aiofiles.os
from dateutil import parser

from storage.storyteller_storage_base import StorytellerStorageBase
from storage.storyteller_storage_types import (
    StorytellerBatchRunError,
    StorytellerStorageValidationError,
    StorytellerStorageNotFoundError,
    StorytellerStorageError,
    StorytellerAtomicFileWriter
)

from common.storyteller_types import StorytellerContentPacket

logger = logging.getLogger(__name__)

NO_ACTIVE_BATCH_RUN = "No active batch run"


class StorytellerBatchStorage(StorytellerStorageBase):
    """
    Manages batch storage operations for the Storyteller application.

    This class provides methods for creating new batches, saving and loading batch content,
    and cleaning up old batch runs. It uses a directory-based structure for organizing batch data.

    Attributes:
        storage_path (Path): The root path where batch storage will be managed.
        current_datetime_folder (Optional[str]): The folder name for the current datetime batch.
        current_batch_run_folder (Optional[Path]): The path to the current batch run folder.
        _lock (asyncio.Lock): A lock to ensure thread-safe operations on the storage.
    """

    def __init__(self, batch_storage_path: Path) -> None:
        """
        Initialize the StorytellerBatchStorage with the given storage path.

        Args:
            batch_storage_path (Path): The root path where batches will be stored.
        """
        super().__init__(batch_storage_path)
        self.current_datetime_folder: Optional[str] = None
        self.current_batch_run_folder: Optional[Path] = None
        self._lock: asyncio.Lock = asyncio.Lock()

    async def start_new_batch(self) -> None:
        """
        Start a new batch by creating a directory based on the current datetime.

        This method resets the current batch run folder and creates a new directory
        for the batch identified by the current datetime.

        Raises:
            StorytellerStorageError: If there's an error creating the directory.
        """
        async with self._lock:
            if self.current_datetime_folder is None:
                self.current_datetime_folder = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.current_batch_run_folder = None
                datetime_storage_path = self.storage_path / self.current_datetime_folder
                try:
                    await asyncio.to_thread(datetime_storage_path.mkdir, parents=True, exist_ok=True)
                    logger.info("Created new batch: %s", self.current_datetime_folder)
                except OSError as e:
                    logger.error("Failed to create new batch directory: %s", str(e))
                    raise StorytellerStorageError(f"Failed to create new batch directory: {str(e)}") from e
            else:
                logger.info("Using existing batch: %s", self.current_datetime_folder)

    async def create_batch_run(self, batch_id: int) -> None:
        """
        Create a new directory for a specific batch run within the current datetime batch.

        Args:
            batch_id (int): The unique identifier for the batch run.

        Raises:
            ValueError: If `start_new_batch` has not been called prior to this method.
            StorytellerStorageError: If there's an error creating the directory.
        """
        async with self._lock:
            if self.current_datetime_folder is None:
                raise ValueError("start_new_batch() must be called before create_batch_run()")
            self.current_batch_run_folder = (
                self.storage_path / self.current_datetime_folder / str(batch_id)
            )
            try:
                await asyncio.to_thread(self.current_batch_run_folder.mkdir, parents=True, exist_ok=True)
                logger.info("Created batch run folder: %s", self.current_batch_run_folder)
            except OSError as e:
                logger.error("Failed to create batch run folder: %s", str(e))
                raise StorytellerStorageError(f"Failed to create batch run folder: {str(e)}") from e

    async def save_content(self, content_packet: StorytellerContentPacket) -> None:
        """
        Save content to the current batch run folder.

        Args:
            content_packet (StorytellerContentPacket): The packet containing the content and metadata to be saved.

        Raises:
            StorytellerBatchRunError: If `create_batch_run` has not been called before saving content.
            StorytellerStorageValidationError: If the content fails validation.
            StorytellerStorageError: If there's an error saving the content.
        """
        await self.validate_content_packet(content_packet)
        async with self._lock:
            if self.current_batch_run_folder is None:
                raise StorytellerBatchRunError("create_batch_run() must be called before save_content()")
            try:
                file_path = self.get_file_path(content_packet)
                async with StorytellerAtomicFileWriter(file_path) as f:
                    await f.write(content_packet.content)
                logger.info("Saved to batch storage: %s", file_path)
            except OSError as e:
                logger.error("Failed to save to batch storage: %s. Error: %s", content_packet.file_name, str(e))
                raise StorytellerStorageError(f"Failed to save content: {str(e)}") from e

    async def load_content(self, content_packet: StorytellerContentPacket) -> StorytellerContentPacket:
        """
        Load content from the current batch run folder.

        Args:
            content_packet (StorytellerContentPacket): The packet containing the metadata to locate the content.

        Returns:
            StorytellerContentPacket: A new packet containing the loaded content and metadata.

        Raises:
            StorytellerBatchRunError: If `create_batch_run` has not been called before loading content.
            StorytellerStorageNotFoundError: If the content file does not exist.
            StorytellerStorageError: If there's an error loading the content.
        """
        file_path = None
        async with self._lock:
            if self.current_batch_run_folder is None:
                raise StorytellerBatchRunError(NO_ACTIVE_BATCH_RUN)
            try:
                file_path = self.get_file_path(content_packet)
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                return StorytellerContentPacket(
                    content=content,
                    file_name=content_packet.file_name,
                    file_extension=content_packet.file_extension,
                    plugin_name=content_packet.plugin_name,
                    stage_name=content_packet.stage_name,
                    phase_name=content_packet.phase_name,
                    metadata=content_packet.metadata,
                )
            except FileNotFoundError as e:
                logger.error("File not found in batch storage: %s", file_path)
                raise StorytellerStorageNotFoundError(f"Content not found: {content_packet.file_name}") from e
            except OSError as e:
                logger.error("Failed to load from batch storage: %s. Error: %s", content_packet.file_name, str(e))
                raise StorytellerStorageError(f"Failed to load content: {str(e)}") from e

    def get_file_path(self, content_packet: StorytellerContentPacket) -> Path:
        """
        Construct and return the file path based on the ContentPacket.

        Args:
            content_packet (StorytellerContentPacket): The packet containing metadata for constructing the file path.

        Returns:
            Path: The full file path within the current batch run folder.

        Raises:
            StorytellerBatchRunError: If no batch run is currently active.
        """
        if self.current_batch_run_folder is None:
            raise StorytellerBatchRunError(NO_ACTIVE_BATCH_RUN)

        filename = content_packet.file_name
        return self.current_batch_run_folder / filename

    async def content_exists(self, content_packet: StorytellerContentPacket) -> bool:
        """
        Check if specific content exists in the current batch run folder.

        Args:
            content_packet (StorytellerContentPacket): The packet containing metadata to identify the content.

        Returns:
            bool: True if the content exists, False otherwise.

        Raises:
            StorytellerBatchRunError: If no batch run is currently active.
        """
        if self.current_batch_run_folder is None:
            raise StorytellerBatchRunError(NO_ACTIVE_BATCH_RUN)

        file_path = self.get_file_path(content_packet)
        return await asyncio.to_thread(file_path.exists)

    async def remove_content(self, content_packet: StorytellerContentPacket) -> None:
        """
        Remove specific content from the current batch run folder.

        Args:
            content_packet (StorytellerContentPacket): The packet containing metadata to identify the content.

        Raises:
            StorytellerBatchRunError: If no batch run is currently active.
            StorytellerStorageNotFoundError: If the specified file does not exist.
            StorytellerStorageError: If there's an error removing the file.
        """
        if self.current_batch_run_folder is None:
            raise StorytellerBatchRunError(NO_ACTIVE_BATCH_RUN)

        file_path = self.get_file_path(content_packet)
        if not await asyncio.to_thread(file_path.exists):
            raise StorytellerStorageNotFoundError(f"File not found: {file_path}")

        try:
            await aiofiles.os.remove(file_path)
            logger.info("Removed content: %s", file_path)
        except OSError as e:
            logger.error("Failed to remove content: %s. Error: %s", file_path, str(e))
            raise StorytellerStorageError(f"Failed to remove content: {str(e)}") from e

    async def list_content(self, stage_name: Optional[str] = None, phase_name: Optional[str] = None) -> List[StorytellerContentPacket]:
        """
        List content in the current batch run folder, optionally filtered by stage and phase.

        Args:
            stage_name (Optional[str]): Filter for stage name.
            phase_name (Optional[str]): Filter for phase name.

        Returns:
            List[StorytellerContentPacket]: A list of ContentPackets representing the content in the folder.

        Raises:
            StorytellerBatchRunError: If no batch run is currently active.
        """
        if self.current_batch_run_folder is None:
            raise StorytellerBatchRunError(NO_ACTIVE_BATCH_RUN)

        content_list = []
        for item in await asyncio.to_thread(self.current_batch_run_folder.iterdir):
            if item.is_file():
                parts = item.stem.split("_")
                if len(parts) >= 3:
                    item_stage, item_phase = parts[:2]
                    item_file_name = "_".join(parts[2:])
                    if (stage_name is None or item_stage == stage_name) and (phase_name is None or item_phase == phase_name):
                        content_list.append(
                            StorytellerContentPacket(
                                content="",  # Actual content can be loaded separately if needed
                                file_name=item_file_name,
                                file_extension=item.suffix[1:],
                                plugin_name="",
                                stage_name=item_stage,
                                phase_name=item_phase,
                                metadata={}
                            )
                        )

        return content_list

    async def update_metadata(self, content_packet: StorytellerContentPacket, new_metadata: Dict[str, Any]) -> None:
        """
        Update the metadata of an existing content packet in storage.

        Args:
            content_packet (StorytellerContentPacket): The content packet to update.
            new_metadata (Dict[str, Any]): The new metadata to merge with existing metadata.

        Raises:
            StorytellerStorageNotFoundError: If the content does not exist in storage.
            StorytellerBatchRunError: If no batch run is currently active.
            StorytellerStorageError: If there's an error updating the file.
        """
        if self.current_batch_run_folder is None:
            raise StorytellerBatchRunError(NO_ACTIVE_BATCH_RUN)

        file_path = self.get_file_path(content_packet)
        if not await asyncio.to_thread(file_path.exists):
            raise StorytellerStorageNotFoundError(f"Content not found: {content_packet.file_name}")

        content_packet.metadata.update(new_metadata)
        await self.save_content(content_packet)

    async def cleanup_old_batch_runs(self, max_folders: Optional[int] = None, max_days: Optional[int] = None) -> None:
        """
        Clean up old batch runs based on the maximum number of folders or the age of folders.

        The method removes folders exceeding the `max_folders` limit or those older than `max_days`.

        Args:
            max_folders (Optional[int]): The maximum number of folders to keep. Older folders will be removed.
            max_days (Optional[int]): The maximum age (in days) of folders to keep. Older folders will be removed.

        Raises:
            ValueError: If neither `max_folders` nor `max_days` is specified.
            StorytellerStorageError: If there's an error removing directories.
        """
        async with self._lock:
            if max_folders is None and max_days is None:
                raise ValueError("At least one of max_folders or max_days must be specified")

            datetime_folders = self._get_datetime_folders()
            folders_to_keep = set(datetime_folders[:max_folders]) if max_folders is not None else set()

            if max_days is not None:
                cutoff_date = datetime.now() - timedelta(days=max_days)

                folders_to_keep.update(
                    folder for folder in datetime_folders
                    if self._should_keep_folder(folder, cutoff_date)
                )

            for folder in datetime_folders:
                if folder not in folders_to_keep:
                    try:
                        await self._remove_directory(folder)
                        logger.info("Removed old datetime folder: %s", folder)
                    except OSError as e:
                        logger.error("Failed to remove old datetime folder: %s. Error: %s", folder, str(e))
                        raise StorytellerStorageError(f"Failed to remove old datetime folder: {str(e)}") from e

    def _get_datetime_folders(self) -> List[Path]:
        """
        Get a sorted list of datetime folders in the storage path.

        Returns:
            List[Path]: A list of datetime folders sorted in descending order.
        """
        return sorted(
            [d for d in self.storage_path.iterdir() if d.is_dir()],
            key=lambda x: x.name,
            reverse=True,
        )

    def _should_keep_folder(self, folder: Path, cutoff_date: Optional[datetime]) -> bool:
        """
        Determine if a folder should be kept based on its date.

        Args:
            folder (Path): The folder to check.
            cutoff_date (Optional[datetime]): The cutoff date for keeping folders.

        Returns:
            bool: True if the folder should be kept, False otherwise.
        """
        if cutoff_date is None:
            return True
        folder_date = parser.parse(folder.name, fuzzy=True)
        return isinstance(folder_date, datetime) and folder_date >= cutoff_date

    async def _remove_directory(self, directory: Path) -> None:
        """
        Recursively remove a directory and all its contents.

        Args:
            directory (Path): The directory to remove.

        Raises:
            OSError: If a file or directory cannot be removed.
        """
        for item in directory.iterdir():
            if item.is_file():
                await aiofiles.os.remove(item)
            elif item.is_dir():
                await self._remove_directory(item)
        await aiofiles.os.rmdir(directory)

    async def query_by_metadata(self, query: Dict[str, Any]) -> List[StorytellerContentPacket]:
        """
        Query content packets based on metadata.

        Args:
            query (Dict[str, Any]): The metadata key-value pairs to match.

        Returns:
            List[StorytellerContentPacket]: A list of content packets matching the query.

        Raises:
            StorytellerBatchRunError: If no batch run is currently active.
        """
        all_content = await self.list_content()
        return [cp for cp in all_content if all(cp.metadata.get(k) == v for k, v in query.items())]

    async def retry_operation(self, operation: Callable, *args: Any, max_retries: int = 3, **kwargs: Any) -> Any:
        """
        Retry an operation with exponential backoff.

        Args:
            operation (Callable): The async operation to retry.
            max_retries (int): The maximum number of retry attempts.
            *args: Positional arguments to pass to the operation.
            **kwargs: Keyword arguments to pass to the operation.

        Returns:
            Any: The result of the successful operation.

        Raises:
            StorytellerStorageError: If all retry attempts fail.
        """
        for attempt in range(max_retries):
            try:
                return await operation(*args, **kwargs)
            except (StorytellerStorageError, OSError) as e:
                if attempt == max_retries - 1:
                    raise StorytellerStorageError(f"Operation failed after {max_retries} attempts: {str(e)}") from e
                logger.warning("Operation failed, retrying (%d/%d): %s", attempt + 1, max_retries, str(e))
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about the current state of batch storage.

        Returns:
            Dict[str, Any]: A dictionary containing information about the storage state,
            including total size, number of files, and current batch run details.

        Raises:
            StorytellerBatchRunError: If no batch run is currently active.
        """
        if self.current_batch_run_folder is None:
            raise StorytellerBatchRunError(NO_ACTIVE_BATCH_RUN)

        total_size = 0
        file_count = 0
        file_list = []

        for item in await asyncio.to_thread(self.current_batch_run_folder.iterdir):
            if await asyncio.to_thread(item.is_file):
                file_stat = await asyncio.to_thread(item.stat)
                total_size += file_stat.st_size
                file_count += 1
                file_list.append(item.name)

        return {
            "total_size_bytes": total_size,
            "file_count": file_count,
            "files": file_list,
            "current_datetime_folder": self.current_datetime_folder,
            "current_batch_run_folder": str(self.current_batch_run_folder)
        }

    async def validate_content_packet(self, content_packet: StorytellerContentPacket) -> None:
        """
        Validate the content of a ContentPacket.

        This method performs validation on the content before saving it to storage.

        Args:
            content_packet (StorytellerContentPacket): The content packet to validate.

        Raises:
            StorytellerStorageValidationError: If the content fails validation.
        """
        required_fields = ['content', 'file_name', 'file_extension', 'plugin_name', 'stage_name', 'phase_name']
        for field in required_fields:
            if getattr(content_packet, field, None) is None:
                raise StorytellerStorageValidationError(f"Missing required field in content packet: {field}")

        if not content_packet.content.strip():
            raise StorytellerStorageValidationError(f"Content validation failed for {content_packet.file_name}: Content is empty")

        # Add any additional validation logic here
