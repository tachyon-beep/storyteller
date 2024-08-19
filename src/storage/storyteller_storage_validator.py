"""
storage_validator.py

This module provides functionality for validating storage paths in the Storyteller system.
It ensures that the required directories exist and are writable.

Usage:
    from storage.storage_validator import StorageValidator
    from pathlib import Path

    path = Path("/path/to/storage")
    StorageValidator.validate_storage_path(path, "Main storage")
"""

import os
from pathlib import Path
from storage.storyteller_storage_types import StorytellerStorageInitializationError


class StorageValidator:
    """
    A utility class for validating storage paths in the Storyteller system.

    This class provides static methods to check if a given path exists and is writable.
    It is used to ensure that the necessary storage directories are properly set up
    before initializing the storage components of the Storyteller system.
    """

    @staticmethod
    def validate_storage_path(path: Path, description: str) -> None:
        """
        Validates that a given path exists and is writable.

        This method checks if the specified path exists and if the current process
        has write access to it. If either condition is not met, it raises an exception.

        Args:
            path (Path): The path to validate.
            description (str): A description of the path for error reporting.

        Raises:
            StorytellerStorageInitializationError: If the path does not exist or is not writable.
        """
        if not path.exists():
            raise StorytellerStorageInitializationError(
                f"{description} directory does not exist: {path}"
            )
        if not os.access(path, os.W_OK):
            raise StorytellerStorageInitializationError(
                f"No write access to {description} directory: {path}"
            )
