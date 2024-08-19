"""
Storyteller Output Storage Module

This module provides the StorytellerOutputStorage class for managing output storage
operations in the Storyteller application. It handles saving, loading, and managing
content across different stages and phases of the storytelling process.

The StorytellerOutputStorage class inherits from StorytellerStorageBase, ensuring
a consistent interface with other storage systems in the application.

Usage:
    from storyteller_output_storage import StorytellerOutputStorage
    from pathlib import Path
    from storyteller_storage_types import StorytellerContentPacket

    storage = StorytellerOutputStorage(Path("/path/to/output"))
    await storage.create_output_folder("session_01")
    
    content_packet = StorytellerContentPacket(...)
    await storage.save_content(content_packet)
    
    loaded_packet = await storage.load_content(content_packet)
    
    exists = await storage.content_exists(content_packet)
    
    file_list = await storage.list_content()
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncGenerator

import aiofiles

from storage.storyteller_storage_base import StorytellerStorageBase
from storage.storyteller_storage_types import (
    StorytellerStorageError,
    StorytellerStorageNotFoundError,
    StorytellerAtomicFileWriter
)

from common.storyteller_types import StorytellerContentPacket

logger = logging.getLogger(__name__)

NO_OUTPUT_FOLDER = "Output folder not created. Call 'create_output_folder' first."


class StorytellerOutputStorage(StorytellerStorageBase):
    """
    Manages output storage operations for the Storyteller application.

    This class provides methods for creating output folders, saving and loading content,
    checking for file existence, and listing all files within the current output folder.
    It inherits from StorytellerStorageBase to ensure a consistent interface with other
    storage systems in the application.

    Attributes:
        storage_path (Path): The root path where output storage will be managed.
        current_output_folder (Optional[Path]): The path to the current output folder.
        _lock (asyncio.Lock): A lock to ensure thread-safe operations on the storage.
    """

    def __init__(self, output_storage_path: Path) -> None:
        """
        Initialize the StorytellerOutputStorage with the given storage path.

        Args:
            output_storage_path (Path): The root path where output will be stored.
        """
        super().__init__(output_storage_path)
        self.current_output_folder: Optional[Path] = None
        self._lock: asyncio.Lock = asyncio.Lock()

    async def create_output_folder(self, folder_name: str) -> None:
        """
        Create a new output folder for storing content.

        Args:
            folder_name (str): The name of the folder to create.

        Raises:
            StorytellerStorageError: If there's an error creating the folder.
        """
        async with self._lock:
            try:
                self.current_output_folder = self.storage_path / folder_name
                await asyncio.to_thread(self.current_output_folder.mkdir, parents=True, exist_ok=True)
                logger.info("Created output folder: %s", self.current_output_folder)
            except OSError as e:
                logger.error("Failed to create output folder: %s", str(e))
                raise StorytellerStorageError(f"Failed to create output folder: {str(e)}") from e

    async def save_content(self, content_packet: StorytellerContentPacket) -> None:
        """
        Save content to the current output folder.

        Args:
            content_packet (StorytellerContentPacket): The packet containing the content and metadata to be saved.

        Raises:
            ValueError: If the output folder has not been created.
            StorytellerStorageError: If there's an error saving the content.
        """
        if self.current_output_folder is None:
            raise ValueError(NO_OUTPUT_FOLDER)

        async with self._lock:
            try:
                file_path = self.get_file_path(content_packet)
                async with StorytellerAtomicFileWriter(file_path) as f:
                    await f.write(content_packet.content)
                logger.info("Saved to output storage: %s", file_path)
            except OSError as e:
                logger.error("Failed to save to output storage: %s. Error: %s", content_packet.file_name, str(e))
                raise StorytellerStorageError(f"Failed to save output content: {str(e)}") from e

    async def load_content(self, content_packet: StorytellerContentPacket) -> StorytellerContentPacket:
        """
        Load content from the current output folder.

        Args:
            content_packet (StorytellerContentPacket): The packet containing the metadata to locate the content.

        Returns:
            StorytellerContentPacket: A new packet containing the loaded content and metadata.

        Raises:
            ValueError: If the output folder has not been created.
            StorytellerStorageNotFoundError: If the content file does not exist.
            StorytellerStorageError: If there's an error loading the content.
        """
        if self.current_output_folder is None:
            raise ValueError(NO_OUTPUT_FOLDER)

        async with self._lock:
            file_path = None
            try:
                file_path = self.get_file_path(content_packet)
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                content_packet.content = content
                return content_packet
            except FileNotFoundError as exc:
                logger.error("File not found in output storage: %s", file_path)
                raise StorytellerStorageNotFoundError(f"Content not found: {content_packet.file_name}") from exc
            except OSError as exc:
                logger.error("Failed to load from output storage: %s. Error: %s", content_packet.file_name, str(exc))
                raise StorytellerStorageError(f"Failed to load output content: {str(exc)}") from exc

    def get_file_path(self, content_packet: StorytellerContentPacket) -> Path:
        """
        Get the full file path for a given content packet in the current output folder.

        Args:
            content_packet (StorytellerContentPacket): The content packet containing the file metadata.

        Returns:
            Path: The full file path.

        Raises:
            ValueError: If the output folder has not been created.
        """
        if self.current_output_folder is None:
            raise ValueError(NO_OUTPUT_FOLDER)
        return self.current_output_folder / f"{content_packet.stage_name}_{content_packet.phase_name}_{content_packet.file_name}"

    async def content_exists(self, content_packet: StorytellerContentPacket) -> bool:
        """
        Check if a file exists in the current output folder.

        Args:
            content_packet (StorytellerContentPacket): The content packet containing the file metadata.

        Returns:
            bool: True if the file exists, False otherwise.

        Raises:
            ValueError: If the output folder has not been created.
        """
        if self.current_output_folder is None:
            raise ValueError(NO_OUTPUT_FOLDER)
        file_path = self.get_file_path(content_packet)
        return await asyncio.to_thread(file_path.exists)

    async def list_content(self, stage_name: Optional[str] = None, phase_name: Optional[str] = None) -> List[StorytellerContentPacket]:
        """
        List all files in the current output folder, optionally filtered by stage and phase.

        Args:
            stage_name (Optional[str]): Filter for stage name.
            phase_name (Optional[str]): Filter for phase name.

        Returns:
            List[StorytellerContentPacket]: A list of content packets representing the content in the folder.

        Raises:
            ValueError: If the output folder has not been created.
        """
        if self.current_output_folder is None:
            raise ValueError(NO_OUTPUT_FOLDER)
        content_list = []
        async for item in self._aiter_directory(self.current_output_folder):
            if item.is_file():
                parts = item.stem.split('_')
                if len(parts) >= 3:
                    item_stage, item_phase = parts[:2]
                    item_filename = '_'.join(parts[2:])
                    if (stage_name is None or item_stage == stage_name) and (phase_name is None or item_phase == phase_name):
                        content_list.append(
                            StorytellerContentPacket(
                                content="",  # Content not loaded in list operation
                                file_name=item_filename,
                                file_extension=item.suffix[1:],
                                stage_name=item_stage,
                                phase_name=item_phase,
                            )
                        )
        return content_list

    async def remove_content(self, content_packet: StorytellerContentPacket) -> None:
        """
        Remove specific content from the current output folder.

        Args:
            content_packet (StorytellerContentPacket): The content packet containing the file metadata.

        Raises:
            ValueError: If the output folder has not been created.
            StorytellerStorageNotFoundError: If the specified file does not exist.
            StorytellerStorageError: If there's an error removing the file.
        """
        if self.current_output_folder is None:
            raise ValueError(NO_OUTPUT_FOLDER)
        file_path = self.get_file_path(content_packet)
        if not await asyncio.to_thread(file_path.exists):
            raise StorytellerStorageNotFoundError(f"File not found: {file_path}")
        try:
            await asyncio.to_thread(file_path.unlink)
            logger.info("Removed content: %s", file_path)
        except OSError as e:
            logger.error("Failed to remove content: %s. Error: %s", file_path, str(e))
            raise StorytellerStorageError(f"Failed to remove content: {str(e)}") from e

    async def update_metadata(self, content_packet: StorytellerContentPacket, new_metadata: Dict[str, Any]) -> None:
        """
        Update the metadata of a specific content file.

        Args:
            content_packet (StorytellerContentPacket): The content packet to update.
            new_metadata (Dict[str, Any]): The new metadata to merge with existing metadata.

        Raises:
            ValueError: If the output folder has not been created.
            StorytellerStorageNotFoundError: If the specified file does not exist.
            StorytellerStorageError: If there's an error updating the metadata.
        """
        if self.current_output_folder is None:
            raise ValueError(NO_OUTPUT_FOLDER)
        if not await self.content_exists(content_packet):
            raise StorytellerStorageNotFoundError(f"Content not found: {content_packet.file_name}")
        content_packet.metadata.update(new_metadata)
        await self.save_content(content_packet)

    async def _aiter_directory(self, path: Path) -> AsyncGenerator[Path, None]:
        """
        Asynchronous generator to iterate over items in a directory.

        Args:
            path (Path): The directory path to iterate over.

        Yields:
            Path: Each item in the directory.
        """
        for item in await asyncio.to_thread(list, path.iterdir()):
            yield item
