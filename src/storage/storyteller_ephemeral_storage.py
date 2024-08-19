"""
Storyteller Ephemeral Storage Module

This module provides the StorytellerEphemeralStorage class for managing ephemeral (temporary)
storage operations in the Storyteller application. It handles saving, loading, and managing
temporary content with features such as TTL (Time To Live) for automatic content expiration.

The StorytellerEphemeralStorage class inherits from StorytellerStorageBase, ensuring
a consistent interface with other storage systems in the Storyteller application.

Usage:
    from storyteller_ephemeral_storage import StorytellerEphemeralStorage
    from pathlib import Path

    storage = StorytellerEphemeralStorage(Path("/path/to/ephemeral/storage"))
    await storage.save_content(content_packet)
    content = await storage.load_content(content_packet)
    await storage.clear_storage()
"""

from typing import Optional, Dict, List, Any, Callable
from pathlib import Path
import asyncio
import gzip
import logging
import time
import os
import shutil
import aiofiles
from storage.storyteller_storage_base import StorytellerStorageBase
from storage.storyteller_storage_types import (
    StorytellerStorageError,
    StorytellerStorageNotFoundError,
    StorytellerStorageValidationError,
    StorytellerStorageMetadataError,
    StorytellerAtomicFileWriter
)

from common.storyteller_types import StorytellerContentPacket

logger = logging.getLogger(__name__)


class StorytellerEphemeralStorage(StorytellerStorageBase):
    """
    Manage ephemeral (temporary) storage for the Storyteller application.

    This class provides methods for saving and loading temporary content,
    as well as managing the storage lifecycle including TTL-based expiration.

    Attributes:
        storage_path (Path): The directory path where ephemeral content is stored.
        _lock (asyncio.Lock): A lock to ensure thread-safe access to the storage.
    """

    def __init__(self, storage_path: Path) -> None:
        """
        Initialize the StorytellerEphemeralStorage with the given storage path.

        Args:
            storage_path (Path): The directory path where ephemeral content will be stored.
        """
        super().__init__(storage_path)
        self._lock = asyncio.Lock()

    def get_file_path(self, content_packet: StorytellerContentPacket) -> Path:
        """
        Construct the full file path for a given content packet.

        Args:
            content_packet (StorytellerContentPacket): The content packet containing metadata.

        Returns:
            Path: The constructed file path.
        """
        return self.storage_path / content_packet.file_name

    async def save_content(self, content_packet: StorytellerContentPacket) -> None:
        """
        Asynchronously save content to the ephemeral storage.

        Args:
            content_packet (StorytellerContentPacket): The content packet to save.

        Raises:
            StorytellerStorageValidationError: If the content fails validation.
            StorytellerStorageError: If there's an error writing to the file.
        """
        await self.validate_content_packet(content_packet)
        file_path = self.get_file_path(content_packet)

        async with self._lock:
            try:
                await asyncio.to_thread(file_path.parent.mkdir, parents=True, exist_ok=True)
                async with StorytellerAtomicFileWriter(file_path) as f:
                    await f.write(content_packet.content)
                logger.info("Saved to ephemeral storage: %s", file_path)
            except OSError as e:
                logger.error("Failed to save to ephemeral storage: %s. Error: %s", file_path, str(e))
                raise StorytellerStorageError(f"Failed to save content: {str(e)}") from e

    async def load_content(self, content_packet: StorytellerContentPacket) -> StorytellerContentPacket:
        """
        Asynchronously load content from the ephemeral storage.

        Args:
            content_packet (StorytellerContentPacket): The content packet with metadata.

        Returns:
            StorytellerContentPacket: The content packet with loaded content.

        Raises:
            StorytellerStorageNotFoundError: If the specified file does not exist.
            StorytellerStorageError: If there's an error reading the file.
        """
        file_path = self.get_file_path(content_packet)

        async with self._lock:
            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content_packet.content = await f.read()
                logger.info("Loaded from ephemeral storage: %s", file_path)
                return content_packet
            except FileNotFoundError as exc:
                logger.error("File not found in ephemeral storage: %s", file_path)
                raise StorytellerStorageNotFoundError(f"Content not found: {content_packet.file_name}") from exc
            except OSError as e:
                logger.error("Failed to load from ephemeral storage: %s. Error: %s", file_path, str(e))
                raise StorytellerStorageError(f"Failed to load content: {str(e)}") from e

    async def clear_storage(self) -> None:
        """
        Asynchronously clear all files in the ephemeral storage directory.

        Raises:
            StorytellerStorageError: If there's an error deleting the files.
        """
        async with self._lock:
            try:
                for item in self.storage_path.iterdir():
                    if item.is_file():
                        await asyncio.to_thread(item.unlink)
                    elif item.is_dir():
                        await asyncio.to_thread(shutil.rmtree, item)
                logger.info("Cleared contents of ephemeral storage: %s", self.storage_path)
            except OSError as e:
                logger.error("Failed to clear ephemeral storage: %s", str(e))
                raise StorytellerStorageError(f"Failed to clear storage: {str(e)}") from e

    async def content_exists(self, content_packet: StorytellerContentPacket) -> bool:
        """
        Check if specific content exists in the ephemeral storage.

        Args:
            content_packet (StorytellerContentPacket): The content packet with metadata.

        Returns:
            bool: True if the content exists, False otherwise.
        """
        file_path = self.get_file_path(content_packet)
        return await asyncio.to_thread(file_path.exists)

    async def remove_content(self, content_packet: StorytellerContentPacket) -> None:
        """
        Remove specific content from the ephemeral storage.

        Args:
            content_packet (StorytellerContentPacket): The content packet with metadata.

        Raises:
            StorytellerStorageNotFoundError: If the specified file does not exist.
            StorytellerStorageError: If there's an error removing the file.
        """
        file_path = self.get_file_path(content_packet)
        if not await asyncio.to_thread(file_path.exists):
            raise StorytellerStorageNotFoundError(f"File not found: {file_path}")

        try:
            await asyncio.to_thread(os.remove, file_path)
            logger.info("Removed content: %s", file_path)
        except OSError as e:
            logger.error("Failed to remove content: %s. Error: %s", file_path, str(e))
            raise StorytellerStorageError(f"Failed to remove content: {str(e)}") from e

    async def list_content(
        self, stage_name: Optional[str] = None, phase_name: Optional[str] = None
    ) -> List[StorytellerContentPacket]:
        """
        List content in the ephemeral storage, optionally filtered by stage and phase.

        Args:
            stage_name (Optional[str]): Filter for stage name.
            phase_name (Optional[str]): Filter for phase name.

        Returns:
            List[StorytellerContentPacket]: A list of content packets containing information about each content item.
        """
        content_list = []
        async with self._lock:
            items = await asyncio.to_thread(list, self.storage_path.iterdir())
            for item in items:
                if await asyncio.to_thread(item.is_file):
                    parts = item.name.split('_')
                    if len(parts) >= 3:
                        item_stage, item_phase = parts[:2]
                        item_filename = '_'.join(parts[2:])
                        if (stage_name is None or item_stage == stage_name) and (phase_name is None or item_phase == phase_name):
                            content_list.append(
                                StorytellerContentPacket(
                                    content="",  # Content not loaded in list operation
                                    file_name=item_filename,
                                    stage_name=item_stage,
                                    phase_name=item_phase,
                                )
                            )
        return content_list

    async def get_storage_size(self) -> int:
        """
        Get the total size of all files in the ephemeral storage.

        Returns:
            int: Total size in bytes.
        """
        total_size = 0
        async with self._lock:
            items = await asyncio.to_thread(list, self.storage_path.iterdir())
            for item in items:
                if await asyncio.to_thread(item.is_file):
                    total_size += (await asyncio.to_thread(os.stat, item)).st_size
        return total_size

    async def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about the current state of ephemeral storage.

        Returns:
            Dict[str, Any]: A dictionary containing information about the storage state,
            including total size and list of files.
        """
        async with self._lock:
            total_size = await self.get_storage_size()
            items = await asyncio.to_thread(list, self.storage_path.iterdir())
            file_list = [item.name for item in items if await asyncio.to_thread(item.is_file)]
        return {
            "total_size_bytes": total_size,
            "file_count": len(file_list),
            "files": file_list
        }

    async def set_content_ttl(self, content_packet: StorytellerContentPacket, ttl: int) -> None:
        """
        Set a Time To Live (TTL) for a specific content file.

        Args:
            content_packet (StorytellerContentPacket): The content packet with metadata.
            ttl (int): Time To Live in seconds.

        Raises:
            StorytellerStorageNotFoundError: If the specified file does not exist.
            StorytellerStorageError: If there's an error setting the file's modification time.
        """
        file_path = self.get_file_path(content_packet)
        if not await asyncio.to_thread(file_path.exists):
            raise StorytellerStorageNotFoundError(f"File not found: {file_path}")

        expiration_time = int(time.time()) + ttl
        try:
            os.utime(str(file_path), (expiration_time, expiration_time))
        except OSError as e:
            logger.error("Failed to set TTL for content: %s. Error: %s", file_path, str(e))
            raise StorytellerStorageError(f"Failed to set content TTL: {str(e)}") from e

    async def clear_expired_content(self) -> None:
        """
        Remove all expired content from the ephemeral storage.

        This method checks the modification time of each file and removes it
        if it has expired based on its TTL.
        """
        current_time = time.time()
        async with self._lock:
            items = await asyncio.to_thread(list, self.storage_path.iterdir())
            for item in items:
                if await asyncio.to_thread(item.is_file):
                    stat_result = await asyncio.to_thread(item.stat)
                    mtime = stat_result.st_mtime
                    if mtime < current_time:
                        try:
                            await asyncio.to_thread(os.remove, item)
                            logger.info("Removed expired content: %s", item)
                        except OSError as e:
                            logger.error("Failed to remove expired content: %s. Error: %s", item, str(e))

    async def update_metadata(self, content_packet: StorytellerContentPacket, new_metadata: Dict[str, Any]) -> None:
        """
        Update the metadata of a specific content file.

        Args:
            content_packet (StorytellerContentPacket): The content packet to update.
            new_metadata (Dict[str, Any]): The new metadata to apply.

        Raises:
            StorytellerStorageNotFoundError: If the specified file does not exist.
            StorytellerStorageMetadataError: If there's an error updating the metadata.
        """
        file_path = self.get_file_path(content_packet)
        if not await asyncio.to_thread(file_path.exists):
            raise StorytellerStorageNotFoundError(f"Content not found: {content_packet.file_name}")

        try:
            content_packet.metadata.update(new_metadata)
            await self.save_content(content_packet)
        except (OSError, IOError, StorytellerStorageError) as e:
            logger.error("Failed to update metadata for: %s. Error: %s", content_packet.file_name, str(e))
            raise StorytellerStorageMetadataError(f"Failed to update metadata: {str(e)}") from e

    async def query_by_metadata(self, query: Dict[str, Any]) -> List[StorytellerContentPacket]:
        """
        Query content based on metadata.

        Args:
            query (Dict[str, Any]): The metadata query to match against.

        Returns:
            List[StorytellerContentPacket]: A list of content packets that match the query.
        """
        all_content = await self.list_content()
        return [cp for cp in all_content if all(cp.metadata.get(k) == v for k, v in query.items())]

    async def retry_operation(self, operation: Callable[..., Any], *args: Any, max_retries: int = 3, **kwargs: Any) -> Any:
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
            except (StorytellerStorageError, OSError) as e:
                if attempt == max_retries - 1:
                    raise StorytellerStorageError(f"Operation failed after {max_retries} attempts: {str(e)}") from e
                logger.warning("Operation failed, retrying (%d/%d): %s", attempt + 1, max_retries, str(e))
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def validate_content_packet(self, content_packet: StorytellerContentPacket) -> None:
        """
        Validate the content of a ContentPacket.

        This method performs validation checks on the content packet before saving it to storage.

        Args:
            content_packet (StorytellerContentPacket): The content packet to validate.

        Raises:
            StorytellerStorageValidationError: If the content fails validation.
        """
        if not content_packet.content:
            raise StorytellerStorageValidationError(f"Content validation failed for {content_packet.file_name}: Content is empty")

        required_fields = ['file_name', 'file_extension', 'plugin_name', 'stage_name', 'phase_name']
        for field in required_fields:
            if getattr(content_packet, field, None) is None:
                raise StorytellerStorageValidationError(
                    f"Content validation failed for {content_packet.file_name}: Missing required field '{field}'")

    async def compress_storage(self) -> None:
        """
        Compress the ephemeral storage to save space.

        This method compresses all files in the ephemeral storage directory to reduce disk usage.

        Raises:
            StorytellerStorageError: If there's an error compressing the files.
        """
        async with self._lock:
            try:
                for item in self.storage_path.iterdir():
                    if item.is_file() and not item.name.endswith('.gz'):
                        compressed_path = item.with_suffix(item.suffix + '.gz')
                        with item.open('rb') as f_in:
                            with gzip.open(compressed_path, 'wb') as f_out:
                                await asyncio.to_thread(shutil.copyfileobj, f_in, f_out)
                        await asyncio.to_thread(item.unlink)
                logger.info("Compressed ephemeral storage: %s", self.storage_path)
            except OSError as e:
                logger.error("Failed to compress ephemeral storage: %s", str(e))
                raise StorytellerStorageError(f"Failed to compress storage: {str(e)}") from e

    async def decompress_file(self, content_packet: StorytellerContentPacket) -> None:
        """
        Decompress a specific file in the ephemeral storage.

        This method decompresses a gzip-compressed file in the ephemeral storage.

        Args:
            content_packet (StorytellerContentPacket): The content packet identifying the file to decompress.

        Raises:
            StorytellerStorageNotFoundError: If the specified compressed file does not exist.
            StorytellerStorageError: If there's an error decompressing the file.
        """
        file_path = self.get_file_path(content_packet)
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')

        if not await asyncio.to_thread(compressed_path.exists):
            raise StorytellerStorageNotFoundError(f"Compressed file not found: {compressed_path}")

        try:
            with gzip.open(compressed_path, 'rb') as f_in:
                with file_path.open('wb') as f_out:
                    await asyncio.to_thread(shutil.copyfileobj, f_in, f_out)
            await asyncio.to_thread(compressed_path.unlink)
            logger.info("Decompressed file: %s", file_path)
        except OSError as e:
            logger.error("Failed to decompress file: %s. Error: %s", compressed_path, str(e))
            raise StorytellerStorageError(f"Failed to decompress file: {str(e)}") from e

    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get detailed statistics about the ephemeral storage.

        This method provides more detailed information about the storage state,
        including file count by type, total size, and average file size.

        Returns:
            Dict[str, Any]: A dictionary containing detailed storage statistics.
        """
        stats = {
            "total_size_bytes": 0,
            "file_count": 0,
            "file_types": {},
            "average_file_size": 0
        }

        async with self._lock:
            items = await asyncio.to_thread(list, self.storage_path.iterdir())
            for item in items:
                if await asyncio.to_thread(item.is_file):
                    file_size = (await asyncio.to_thread(os.stat, item)).st_size
                    stats["total_size_bytes"] += file_size
                    stats["file_count"] += 1

                    file_type = item.suffix
                    if file_type in stats["file_types"]:
                        stats["file_types"][file_type] += 1
                    else:
                        stats["file_types"][file_type] = 1

        if stats["file_count"] > 0:
            stats["average_file_size"] = stats["total_size_bytes"] / stats["file_count"]

        return stats

    async def move_content(self, source_packet: StorytellerContentPacket, destination_packet: StorytellerContentPacket) -> None:
        """
        Move content from one location to another within the ephemeral storage.

        This method moves a file from one location to another within the ephemeral storage.

        Args:
            source_packet (StorytellerContentPacket): The content packet identifying the source file.
            destination_packet (StorytellerContentPacket): The content packet identifying the destination.

        Raises:
            StorytellerStorageNotFoundError: If the source file does not exist.
            StorytellerStorageError: If there's an error moving the file.
        """
        source_path = self.get_file_path(source_packet)
        destination_path = self.get_file_path(destination_packet)

        if not await asyncio.to_thread(source_path.exists):
            raise StorytellerStorageNotFoundError(f"Source file not found: {source_path}")

        try:
            await asyncio.to_thread(shutil.move, str(source_path), str(destination_path))
            logger.info("Moved content from %s to %s", source_path, destination_path)
        except OSError as e:
            logger.error("Failed to move content from %s to %s. Error: %s", source_path, destination_path, str(e))
            raise StorytellerStorageError(f"Failed to move content: {str(e)}") from e

    async def copy_content(self, source_packet: StorytellerContentPacket, destination_packet: StorytellerContentPacket) -> None:
        """
        Copy content from one location to another within the ephemeral storage.

        This method copies a file from one location to another within the ephemeral storage.

        Args:
            source_packet (StorytellerContentPacket): The content packet identifying the source file.
            destination_packet (StorytellerContentPacket): The content packet identifying the destination.

        Raises:
            StorytellerStorageNotFoundError: If the source file does not exist.
            StorytellerStorageError: If there's an error copying the file.
        """
        source_path = self.get_file_path(source_packet)
        destination_path = self.get_file_path(destination_packet)

        if not await asyncio.to_thread(source_path.exists):
            raise StorytellerStorageNotFoundError(f"Source file not found: {source_path}")

        try:
            await asyncio.to_thread(shutil.copy2, str(source_path), str(destination_path))
            logger.info("Copied content from %s to %s", source_path, destination_path)
        except OSError as e:
            logger.error("Failed to copy content from %s to %s. Error: %s", source_path, destination_path, str(e))
            raise StorytellerStorageError(f"Failed to copy content: {str(e)}") from e
