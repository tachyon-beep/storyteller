"""
storage_types.py

This module defines custom exceptions and data types for the Storyteller storage system.
The exceptions handle various storage-related errors, while the data types are used
to standardize the data structure for serialization and deserialization operations
across the storage system.

Usage:
    from storage.storage_types import (
        StorytellerStorageError,
        StorytellerStorageInitializationError,
        StorytellerStorageWriteError,
        StorytellerStorageReadError,
        StorytellerStoragePermissionError,
        StorytellerStorageFullError,
        StorytellerStorageNotFoundError,
        ContentPacket
    )

    try:
        # Some storage operation
    except StorytellerStorageInitializationError as e:
        logger.error("Storage initialization failed: %s", e)
    except StorytellerStorageWriteError as e:
        logger.error("Failed to write to storage: %s", e)
    except StorytellerStorageReadError as e:
        logger.error("Failed to read from storage: %s", e)
    except StorytellerStorageError as e:
        logger.error("An unexpected storage error occurred: %s", e)
"""
import asyncio
from typing import Optional
from pathlib import Path
import aiofiles


class StorytellerStorageError(Exception):
    """
    Base exception for storage-related errors in the Storyteller system.

    This exception serves as a parent class for more specific storage-related exceptions.
    It can be used to catch any storage-related exception in the Storyteller system.

    Attributes:
        message (str): Description of the error.
        storage_type (Optional[str]): Type of storage where the error occurred.
        operation (Optional[str]): Operation being performed when the error occurred.
    """

    def __init__(self, message: str, storage_type: Optional[str] = None, operation: Optional[str] = None) -> None:
        super().__init__(message)
        self.storage_type = storage_type
        self.operation = operation

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.storage_type and self.operation:
            return f"{base_msg} (Storage: {self.storage_type}, Operation: {self.operation})"
        elif self.storage_type:
            return f"{base_msg} (Storage: {self.storage_type})"
        elif self.operation:
            return f"{base_msg} (Operation: {self.operation})"
        return base_msg


class StorytellerStorageInitializationError(StorytellerStorageError):
    """
    Exception raised when storage initialization fails in the Storyteller system.

    This exception is typically raised when there are issues with setting up
    or accessing the required storage directories or resources.
    """


class StorytellerStorageWriteError(StorytellerStorageError):
    """
    Exception raised when writing to storage fails in the Storyteller system.

    This exception is typically raised when there are issues with writing data
    to the storage, such as permission errors or disk space issues.
    """


class StorytellerStorageReadError(StorytellerStorageError):
    """
    Exception raised when reading from storage fails in the Storyteller system.

    This exception is typically raised when there are issues with reading data
    from the storage, such as missing files or permission errors.
    """


class StorytellerStoragePermissionError(StorytellerStorageError):
    """
    Exception raised when there is a permission issue with storage operations in the Storyteller system.

    This exception is typically raised when a storage operation fails due to insufficient
    permissions to read, write, or execute the required files or directories.
    """


class StorytellerStorageFullError(StorytellerStorageError):
    """
    Exception raised when the storage is full or the quota is exceeded in the Storyteller system.

    This exception is typically raised when a storage operation fails due to lack of disk space
    or when the allocated storage quota has been exceeded.
    """


class StorytellerStorageNotFoundError(StorytellerStorageError):
    """
    Exception raised when the requested storage item is not found in the Storyteller system.

    This exception is typically raised when an operation attempts to access a file or directory
    that does not exist in the storage system.
    """


class StorytellerStorageMetadataError(StorytellerStorageError):
    """Custom exception."""


class StorytellerStorageValidationError(StorytellerStorageError):
    """Custom exception."""


class StorytellerBatchRunError(StorytellerStorageError):
    """Custom exception."""


class StorytellerAtomicFileWriter:
    """
    A context manager for atomic file writing operations.

    This class ensures that file write operations are atomic by writing to a temporary file
    and then renaming it to the target file name upon successful completion.

    Attributes:
        file_path (Path): The target file path for the write operation.
        temp_file (Path): The temporary file path used during the write operation.
        file (aiofiles.base.AiofilesContextManager): The file object for writing.
    """

    def __init__(self, file_path: Path):
        """
        Initialize the AtomicFileWriter.

        Args:
            file_path (Path): The target file path for the write operation.
        """
        self.file_path = file_path
        self.temp_file = file_path.with_suffix(file_path.suffix + '.tmp')
        self.file = None

    async def __aenter__(self):
        """
        Enter the context manager, opening the temporary file for writing.

        Returns:
            aiofiles.base.AiofilesContextManager: The file object for writing.
        """
        self.file = await aiofiles.open(self.temp_file, 'w')
        return self.file

    async def __aexit__(self, exc_type, exc, tb):
        """
        Exit the context manager, finalizing the write operation.

        If no exception occurred, rename the temporary file to the target file.
        Otherwise, remove the temporary file.

        Args:
            exc_type: The type of the exception that occurred, if any.
            exc: The exception instance that occurred, if any.
            tb: The traceback object for the exception, if any.
        """
        try:
            if self.file:
                await self.file.flush()
                await self.file.close()
            if exc_type is None:
                await asyncio.to_thread(self.temp_file.rename, self.file_path)
            elif self.temp_file.exists():
                await asyncio.to_thread(self.temp_file.unlink)
        finally:
            self.file = None
