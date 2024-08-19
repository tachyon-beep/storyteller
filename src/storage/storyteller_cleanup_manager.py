"""
storyteller_cleanup_manager.py

This module provides functionality for managing and cleaning up old batch runs
in the Storyteller system. It includes the StorytellerCleanupManager class,
which is responsible for identifying and safely removing outdated batch folders
based on configurable criteria such as maximum number of folders or maximum age.

Usage:
    from storyteller_cleanup_manager import StorytellerCleanupManager
    from storyteller_batch_storage import StorytellerBatchStorage

    batch_storage = StorytellerBatchStorage(Path("/path/to/batch_storage"))
    cleanup_manager = StorytellerCleanupManager(batch_storage)
    cleanup_manager.cleanup_old_batch_runs(max_folders=10, max_days=30)
"""

import logging
from typing import Optional, List, Set
from pathlib import Path
from datetime import datetime, timedelta

from storage.storyteller_storage_types import (
    StorytellerStorageError,
    StorytellerStorageInitializationError
)
from storage.storyteller_batch_storage import StorytellerBatchStorage

from common.storyteller_types import StorytellerContentPacket

logger = logging.getLogger(__name__)

PROTECTED_EXTENSIONS = {".py", ".cfg", ".sh", ".bat"}


class StorytellerCleanupManager:
    """
    Manages the cleanup of old batch runs in the Storyteller storage system.

    This class provides methods to identify and safely remove old batch folders
    based on specific criteria such as the maximum number of folders to keep or
    the maximum age of the folders.

    Attributes:
        batch_storage (StorytellerBatchStorage): The batch storage instance to manage.
    """

    def __init__(self, batch_storage: StorytellerBatchStorage) -> None:
        """
        Initialize the StorytellerCleanupManager with a batch storage instance.

        Args:
            batch_storage (StorytellerBatchStorage): The batch storage instance to manage.

        Raises:
            StorytellerStorageInitializationError: If the batch storage is not properly initialized.
        """
        if not isinstance(batch_storage, StorytellerBatchStorage):
            raise StorytellerStorageInitializationError("Invalid batch storage instance provided.")
        self.batch_storage = batch_storage

    async def cleanup_old_batch_runs(self, max_folders: Optional[int] = None, max_days: Optional[int] = None) -> None:
        """
        Clean up old batch runs by removing folders that exceed the specified limits.

        Args:
            max_folders (Optional[int]): The maximum number of most recent folders to keep.
                Older folders will be removed.
            max_days (Optional[int]): The maximum age of folders to keep in days.
                Older folders will be removed.

        Raises:
            ValueError: If neither max_folders nor max_days is provided.
            StorytellerStorageError: If there's an error during the cleanup process.
        """
        if max_folders is None and max_days is None:
            raise ValueError("At least one of max_folders or max_days must be specified")

        try:
            datetime_folders = await self._get_sorted_datetime_folders()
            folders_to_keep = self._determine_folders_to_keep(datetime_folders, max_folders, max_days)

            for folder in datetime_folders:
                if folder not in folders_to_keep:
                    if await self._check_folder_safety(folder):
                        await self._remove_directory(folder)
                        logger.info("Removed old datetime folder: %s", folder)
                    else:
                        logger.warning("Skipped unsafe folder during cleanup: %s", folder)
        except (ValueError, OSError) as exc:
            logger.error("Error during batch run cleanup: %s", exc)
            raise StorytellerStorageError(f"Failed to clean up old batch runs: {exc}") from exc

    async def _get_sorted_datetime_folders(self) -> List[Path]:
        """
        Retrieve a list of folders in the batch storage directory sorted by their names in descending order.

        Returns:
            List[Path]: A sorted list of folder paths.

        Raises:
            StorytellerStorageError: If there's an error accessing the directory.
        """
        try:
            folders = [d for d in self.batch_storage.storage_path.iterdir() if d.is_dir()]
            return sorted(folders, key=lambda x: x.name, reverse=True)
        except OSError as exc:
            logger.error("Failed to access the batch storage directory: %s", exc)
            raise StorytellerStorageError(f"Failed to access batch storage directory: {exc}") from exc

    def _determine_folders_to_keep(self, folders: List[Path], max_folders: Optional[int], max_days: Optional[int]) -> Set[Path]:
        """
        Determine which folders should be kept based on the maximum number of folders and/or the maximum age of folders.

        Args:
            folders (List[Path]): The list of folders to evaluate.
            max_folders (Optional[int]): The maximum number of folders to keep.
            max_days (Optional[int]): The maximum age of folders to keep in days.

        Returns:
            Set[Path]: A set of folders that should be kept.
        """
        folders_to_keep: Set[Path] = set()

        if max_folders is not None:
            folders_to_keep.update(folders[:max_folders])

        if max_days is not None:
            cutoff_date = datetime.now() - timedelta(days=max_days)
            for folder in folders:
                folder_date = self._parse_folder_date(folder.name)
                if folder_date >= cutoff_date:
                    folders_to_keep.add(folder)

        return folders_to_keep

    @staticmethod
    def _parse_folder_date(folder_name: str) -> datetime:
        """
        Parse a folder name into a datetime object.

        Args:
            folder_name (str): The name of the folder to parse.

        Returns:
            datetime: The parsed datetime object.

        Raises:
            ValueError: If the folder name does not match the expected format.
        """
        try:
            return datetime.strptime(folder_name, '%Y%m%d_%H%M%S')
        except ValueError as exc:
            logger.error("Invalid folder name format: %s", folder_name)
            raise ValueError(f"Invalid folder name format: {folder_name}") from exc

    async def _check_folder_safety(self, folder: Path) -> bool:
        """
        Check whether a folder is safe to remove by verifying its contents.

        This method ensures that the folder is within the batch storage path and does not contain
        any protected files or unexpected subdirectories.

        Args:
            folder (Path): The folder to check.

        Returns:
            bool: True if the folder is safe to remove, False otherwise.
        """
        try:
            if not folder.resolve().is_relative_to(self.batch_storage.storage_path.resolve()):
                logger.warning("Folder outside of batch storage path: %s", folder)
                return False

            async for item in self._aiter_directory(folder):
                if not await self._is_safe_file(item):
                    return False
            return True
        except OSError as exc:
            logger.error("Error while checking folder safety: %s", exc)
            return False

    async def _is_safe_file(self, item: Path) -> bool:
        """
        Check if a file is safe to remove.

        Args:
            item (Path): The file to check.

        Returns:
            bool: True if the file is safe to remove, False otherwise.
        """
        if item.is_dir():
            logger.warning("Unexpected subdirectory found: %s", item)
            return False

        if item.suffix in PROTECTED_EXTENSIONS:
            logger.warning("Protected file found: %s", item)
            return False

        content_packet = StorytellerContentPacket(
            content="",
            file_name=item.name,
            file_extension=item.suffix[1:],
            stage_name="",
            phase_name=""
        )
        return await self.batch_storage.content_exists(content_packet)

    async def _remove_directory(self, directory: Path) -> None:
        """
        Recursively remove a directory and all its contents.

        Args:
            directory (Path): The directory to remove.

        Raises:
            StorytellerStorageError: If there's an error during the removal process.
        """
        try:
            async for item in self._aiter_directory(directory):
                if item.is_dir():
                    await self._remove_directory(item)
                else:
                    await self.batch_storage.remove_content(StorytellerContentPacket(
                        content="",
                        file_name=item.name,
                        file_extension=item.suffix[1:],
                        stage_name="",
                        phase_name=""
                    ))
            await self.batch_storage._remove_directory(directory)
        except OSError as exc:
            logger.error("Failed to remove directory: %s", exc)
            raise StorytellerStorageError(f"Failed to remove directory {directory}: {exc}") from exc

    @staticmethod
    async def _aiter_directory(directory: Path):
        """
        Asynchronously iterate over the contents of a directory.

        Args:
            directory (Path): The directory to iterate over.

        Yields:
            Path: Each item in the directory.
        """
        for item in directory.iterdir():
            yield item
