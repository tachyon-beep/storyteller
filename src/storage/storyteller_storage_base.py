"""
Storyteller Storage Base Module

This module provides the base classes for storage operations in the Storyteller application.
It defines the `StorytellerStorageBase` class, which serves as the base class for different
storage types, including batch, ephemeral, and output storage.

Subclasses of `StorytellerStorageBase` are expected to implement specific methods for saving,
loading, and managing content within their respective storage types.

Usage:
    from storyteller_storage_base import StorytellerStorageBase

    class CustomStorage(StorytellerStorageBase):
        async def save_content(self, content_packet: StorytellerContentPacket) -> None:
            # Implementation for saving content
            pass

        async def load_content(self, content_packet: StorytellerContentPacket) -> StorytellerContentPacket:
            # Implementation for loading content
            pass

        async def content_exists(self, content_packet: StorytellerContentPacket) -> bool:
            # Implementation for checking if content exists
            pass
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class StorytellerStorageBase(ABC):
    """
    Abstract base class for all storage classes in the Storyteller application.

    This class provides the interface that all storage classes should follow. It includes
    methods for saving, loading, checking existence, and managing storage content.
    """

    def __init__(self, storage_path: Path) -> None:
        """
        Initialize the StorytellerStorageBase with a storage path.

        Args:
            storage_path (Path): The path where the storage content will be managed.
        """
        self.storage_path = storage_path

    @abstractmethod
    async def save_content(self, content_packet: Any) -> None:
        """
        Save content to the storage.

        Args:
            content_packet (Any): The content packet to be saved.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """

    @abstractmethod
    async def load_content(self, content_packet: Any) -> Any:
        """
        Load content from the storage.

        Args:
            content_packet (Any): The content packet to be loaded.

        Returns:
            Any: The loaded content packet.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """

    @abstractmethod
    async def content_exists(self, content_packet: Any) -> bool:
        """
        Check if specific content exists in the storage.

        Args:
            content_packet (Any): The content packet to check.

        Returns:
            bool: True if the content exists, False otherwise.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """

    async def remove_content(self, content_packet: Any) -> None:
        """
        Remove specific content from the storage.

        Args:
            content_packet (Any): The content packet to be removed.

        Raises:
            NotImplementedError: If the storage does not support content removal.
        """
        raise NotImplementedError("Content removal is not supported in this storage type.")

    async def clear_storage(self) -> None:
        """
        Clear all content from the storage.

        This method is optional and can be overridden by subclasses if necessary.
        """
        raise NotImplementedError("Clearing storage is not supported in this storage type.")

    async def list_content(self, stage_name: Optional[str] = None, phase_name: Optional[str] = None) -> Any:
        """
        List content in the storage, optionally filtered by stage and phase.

        Args:
            stage_name (Optional[str]): Optional filter for stage name.
            phase_name (Optional[str]): Optional filter for phase name.

        Returns:
            Any: A list of content items.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("Listing content is not supported in this storage type.")
