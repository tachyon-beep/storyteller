"""
Storyteller Content Processor Module

This module provides the StorytellerContentProcessor class and associated strategies
for processing content in the Storyteller application. It handles content validation,
processing, and error handling using a strategy pattern for flexibility in processing logic.

Usage:
    from storyteller_content_processor import StorytellerContentProcessor, DefaultContentProcessingStrategy

    processor = StorytellerContentProcessor(
        plugin_manager,
        stage_manager,
        llm_instance,
        progress_tracker,
        batch_storage,
        ephemeral_storage,
        DefaultContentProcessingStrategy()
    )
    processed_content, success = await processor.process_content(content_packet)
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple, Callable
import asyncio
import logging

from config.storyteller_configuration_manager import storyteller_config
from orchestration.storyteller_stage_manager import StorytellerStageManager, StorytellerProgressTracker
from llm.storyteller_llm_interface import StorytellerLLMInterface
from storage.storyteller_batch_storage import StorytellerBatchStorage
from storage.storyteller_ephemeral_storage import StorytellerEphemeralStorage
from storage.storyteller_storage_types import StorytellerStorageError
from common.storyteller_types import StorytellerContentPacket
from common.storyteller_exceptions import StorytellerContentProcessingError
from plugins.storyteller_plugin_manager import StorytellerPluginManager
from plugins.storyteller_output_plugin import StorytellerOutputPlugin

logger = logging.getLogger(__name__)

ERROR_PROCESSING_CONTENT = "Error processing content: %s"


class ContentProcessingStrategy(ABC):
    """
    Abstract base class for content processing strategies.

    This class defines the interface for content processing strategies used by
    the StorytellerContentProcessor.
    """

    @abstractmethod
    async def process(self, content_packet: StorytellerContentPacket,
                      processor: 'StorytellerContentProcessor') -> Tuple[StorytellerContentPacket, bool]:
        """
        Process the given content packet.

        Args:
            content_packet: The content packet to process.
            processor: The content processor instance.

        Returns:
            A tuple containing the processed content packet and a boolean indicating success.

        Raises:
            StorytellerContentProcessingError: If content processing fails.
        """


class DefaultContentProcessingStrategy(ContentProcessingStrategy):
    """
    Default implementation of the content processing strategy.

    This strategy implements the standard content processing logic, including
    validation, repair attempts, and retries.
    """

    async def process(self, content_packet: StorytellerContentPacket,
                      processor: 'StorytellerContentProcessor') -> Tuple[StorytellerContentPacket, bool]:
        """
        Process the given content packet using the default strategy.

        Args:
            content_packet: The content packet to process.
            processor: The content processor instance.

        Returns:
            A tuple containing the processed content packet and a boolean indicating success.

        Raises:
            StorytellerContentProcessingError: If content processing fails.
        """
        plugin_name = content_packet.plugin_name
        stage_name = content_packet.stage_name
        phase_name = content_packet.phase_name
        plugin = processor.plugin_manager.get_plugin(plugin_name)

        try:
            schema = processor.get_schema(plugin_name, stage_name, phase_name)
            processed_content = await plugin.process_wrapper(content_packet.content, stage_name=stage_name, phase_name=phase_name)
            content_packet.content = processed_content
            if schema and not await plugin.validate(processed_content, stage_name, phase_name):
                content_packet, success = await processor.handle_invalid_content(
                    content_packet, plugin, stage_name, phase_name
                )
                return content_packet, success
            await processor.ephemeral_storage.save_content(content_packet)
            return content_packet, True
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            error_message = f"Error processing {plugin_name} content for {stage_name}_{phase_name}: {str(e)}"
            logger.error(ERROR_PROCESSING_CONTENT, error_message)
            processor.handle_processing_error(error_message, stage_name, phase_name)
            return content_packet, False


class StorytellerContentProcessor:
    """
    Processes content through various stages and phases using plugins.

    This class handles content processing by integrating with plugins that provide processing,
    validation, and repair functionality. It also manages retries and error handling,
    utilizing an LLM for content repair if necessary.
    """

    def __init__(
        self,
        plugin_manager: StorytellerPluginManager,
        stage_manager: StorytellerStageManager,
        llm_instance: StorytellerLLMInterface,
        progress_tracker: StorytellerProgressTracker,
        batch_storage: StorytellerBatchStorage,
        ephemeral_storage: StorytellerEphemeralStorage,
        processing_strategy: ContentProcessingStrategy = DefaultContentProcessingStrategy()
    ) -> None:
        """
        Initialize the StorytellerContentProcessor with the given components.

        Args:
            plugin_manager: Manages plugins for processing and validation.
            stage_manager: Manages the stages and phases of content processing.
            llm_instance: Instance of the LLM used for content generation and repair.
            progress_tracker: Tracks the progress and updates statuses.
            batch_storage: Handles long-term storage of processed content.
            ephemeral_storage: Handles temporary storage of content during processing.
            processing_strategy: The strategy used for content processing.
                Defaults to DefaultContentProcessingStrategy.
        """
        self.plugin_manager = plugin_manager
        self.stage_manager = stage_manager
        self.llm_instance = llm_instance
        self.progress_tracker = progress_tracker
        self.batch_storage = batch_storage
        self.ephemeral_storage = ephemeral_storage
        self.processing_strategy = processing_strategy
        self.max_retries: int = storyteller_config.get_nested_config_value("content_processing.default_max_retries")

    def get_schema(self, plugin_name: str, stage_name: str, phase_name: str) -> Optional[str]:
        """
        Retrieves the schema for a specific plugin, stage, and phase.

        Args:
            plugin_name: Name of the plugin.
            stage_name: Name of the stage.
            phase_name: Name of the phase.

        Returns:
            The schema to be used for validation, or None if no schema is found.
        """
        phase_schema, schema = self.stage_manager.get_phase_schema(stage_name, phase_name)

        if phase_schema:
            logger.debug("Type of phase schema: %s", type(schema))
            return schema
        return self.plugin_manager.get_plugin_schema(plugin_name)

    async def process_content(self, content_packet: StorytellerContentPacket) -> Tuple[StorytellerContentPacket, bool]:
        """
        Processes content through a specified plugin and validates it against a schema.

        This method delegates the processing to the current processing strategy.

        Args:
            content_packet: The content packet to be processed.

        Returns:
            A tuple containing the processed content packet and a boolean indicating success.

        Raises:
            StorytellerContentProcessingError: If the content cannot be processed or validated after all retries.
            ValueError: If the provided arguments are of incorrect types.
        """
        if not isinstance(content_packet, StorytellerContentPacket):
            raise ValueError("content_packet must be an instance of StorytellerContentPacket")

        return await self.processing_strategy.process(content_packet, self)

    async def handle_invalid_content(
        self,
        content_packet: StorytellerContentPacket,
        plugin: StorytellerOutputPlugin,
        stage_name: str,
        phase_name: str
    ) -> Tuple[StorytellerContentPacket, bool]:
        """
        Handles invalid content by attempting repair or retrying content generation.

        Args:
            content_packet: The content packet that failed validation.
            plugin: The plugin used for processing.
            stage_name: The name of the stage in the content processing pipeline.
            phase_name: The name of the phase in the content processing pipeline.

        Returns:
            A tuple containing the repaired or newly generated content packet and a boolean indicating success.

        Raises:
            StorytellerContentProcessingError: If content repair or retries fail to produce valid content.
        """
        if self.plugin_manager.get_plugin_repair_setting(plugin.get_format()):
            try:
                repaired_content = await self.attempt_repair(content_packet, plugin, stage_name, phase_name)
                if await plugin.validate(repaired_content, stage_name, phase_name):
                    logger.info("Content successfully repaired for %s_%s", stage_name, phase_name)
                    content_packet.content = repaired_content
                    return content_packet, True
            except ValueError as e:
                logger.warning("Repair failed for %s_%s: %s", stage_name, phase_name, str(e))

        if self.plugin_manager.get_plugin_retry_setting(plugin.get_format()):
            return await self.retry_content_generation(content_packet, plugin, stage_name, phase_name)

        raise StorytellerContentProcessingError(f"Failed to process content for {stage_name}_{phase_name}")

    async def attempt_repair(
        self,
        content_packet: StorytellerContentPacket,
        plugin: StorytellerOutputPlugin,
        stage_name: str,
        phase_name: str
    ) -> str:
        """
        Attempts to repair invalid content using an LLM.

        Args:
            content_packet: The content packet that failed validation.
            plugin: The plugin used for processing.
            stage_name: The name of the stage in the content processing pipeline.
            phase_name: The name of the phase in the content processing pipeline.

        Returns:
            The repaired content generated by the LLM.

        Raises:
            ValueError: If the LLM fails to generate repaired content.
        """
        repair_prompt = self.generate_repair_prompt(content_packet.content, plugin, stage_name, phase_name)
        repaired_content = await self.llm_instance.generate_content(repair_prompt, temperature=0.2)
        if not repaired_content:
            raise ValueError("LLM failed to generate repaired content")
        return repaired_content

    async def retry_content_generation(
        self,
        content_packet: StorytellerContentPacket,
        plugin: StorytellerOutputPlugin,
        stage_name: str,
        phase_name: str
    ) -> Tuple[StorytellerContentPacket, bool]:
        """
        Retries content generation using the original prompt and validates the generated content.

        Args:
            content_packet: The original content packet.
            plugin: The plugin used for processing.
            stage_name: The name of the stage in the content processing pipeline.
            phase_name: The name of the phase in the content processing pipeline.

        Returns:
            A tuple containing the valid content packet generated after retries and
            a boolean indicating success.

        Raises:
            StorytellerContentProcessingError: If all retry attempts fail to produce valid content.
        """
        for retry_count in range(self.max_retries):
            logger.info("Retry attempt %d for %s_%s", retry_count + 1, stage_name, phase_name)
            try:
                stage_index = self.stage_manager.get_stage_index_by_name(stage_name)
                phase_index = self.stage_manager.get_phase_index_by_name(stage_name, phase_name)
                temperature = self.stage_manager.get_phase_temperature(stage_index, phase_index)
                retry_content = await self.llm_instance.generate_content(content_packet.content, temperature=temperature)
                processed_content = await plugin.process(retry_content)
                if await plugin.validate(processed_content, stage_name, phase_name):
                    logger.info(
                        "Content successfully generated on retry %d for %s_%s",
                        retry_count + 1, stage_name, phase_name
                    )
                    content_packet.content = processed_content
                    return content_packet, True
            except (ValueError, TypeError, AttributeError, KeyError) as e:
                logger.error(
                    "Error during retry %d for %s_%s: %s",
                    retry_count + 1, stage_name, phase_name, str(e)
                )

        raise StorytellerContentProcessingError(
            f"Failed to generate valid content for {stage_name}_{phase_name} after {self.max_retries} retries"
        )

    def generate_repair_prompt(
        self,
        content: str,
        plugin: StorytellerOutputPlugin,
        stage_name: str,
        phase_name: str
    ) -> str:
        """
        Generates a prompt for the LLM to repair invalid content.

        Args:
            content: The invalid content.
            plugin: The plugin used for processing.
            stage_name: The name of the stage in the content processing pipeline.
            phase_name: The name of the phase in the content processing pipeline.

        Returns:
            A prompt to be used by the LLM for content repair.
        """
        return (
            f"Repair content for stage '{stage_name}', phase '{phase_name}'. "
            f"Plugin '{plugin.get_name()}'. Content: {content}"
        )

    def handle_processing_error(self, error_message: str, stage_name: str, phase_name: str) -> None:
        """
        Handles errors that occur during content processing.

        This method logs the error and updates the progress tracker with the error status.

        Args:
            error_message: The error message to be logged and tracked.
            stage_name: The name of the stage in the content processing pipeline.
            phase_name: The name of the phase in the content processing pipeline.

        Raises:
            StorytellerContentProcessingError: Raises this exception after logging and tracking the error.
        """
        error_context = f"Error in stage '{stage_name}', phase '{phase_name}': {error_message}"
        logger.error(ERROR_PROCESSING_CONTENT, error_context)
        raise StorytellerContentProcessingError(f"Halted due to content processing error: {error_context}")

    async def retry_operation(self, operation: Callable, *args: Any, max_retries: int = 3, **kwargs: Any) -> Any:
        """
        Retries an operation with exponential backoff.

        Args:
            operation: The operation to retry.
            *args: Positional arguments to pass to the operation.
            max_retries: The maximum number of retry attempts.
            **kwargs: Keyword arguments to pass to the operation.

        Returns:
            The result of the successful operation.

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
                    attempt + 1, max_retries, str(e)
                )
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def load_from_batch_storage(self, content_packet: StorytellerContentPacket) -> StorytellerContentPacket:
        """
        Loads the content packet from batch storage with retry mechanism.

        Args:
            content_packet: The content packet to be loaded.

        Returns:
            The loaded content packet.

        Raises:
            StorytellerStorageError: If loading from batch storage fails after all retries.
        """
        return await self.retry_operation(self.batch_storage.load_content, content_packet=content_packet)

    def set_processing_strategy(self, strategy: ContentProcessingStrategy) -> None:
        """
        Sets a new processing strategy for the content processor.

        Args:
            strategy: The new processing strategy to be used.
        """
        self.processing_strategy = strategy

    async def process_content_batch(
        self,
        content_packets: List[StorytellerContentPacket]
    ) -> List[Tuple[StorytellerContentPacket, bool]]:
        """
        Processes a batch of content packets concurrently.

        Args:
            content_packets: A list of content packets to be processed.

        Returns:
            A list of tuples, each containing a processed content packet
            and a boolean indicating success.
        """
        return await asyncio.gather(*(self.process_content(packet) for packet in content_packets))


class RepairOnlyContentProcessingStrategy(ContentProcessingStrategy):
    """
    A content processing strategy that only attempts to repair invalid content without retries.
    """

    async def process(self, content_packet: StorytellerContentPacket,
                      processor: 'StorytellerContentProcessor') -> Tuple[StorytellerContentPacket, bool]:
        """
        Process the given content packet using a repair-only strategy.

        Args:
            content_packet: The content packet to process.
            processor: The content processor instance.

        Returns:
            A tuple containing the processed content packet and a boolean indicating success.

        Raises:
            StorytellerContentProcessingError: If content processing fails.
        """
        plugin_name = content_packet.plugin_name
        stage_name = content_packet.stage_name
        phase_name = content_packet.phase_name
        plugin = processor.plugin_manager.get_plugin(plugin_name)

        try:
            schema = processor.get_schema(plugin_name, stage_name, phase_name)

            processed_content = await plugin.process(content_packet.content)

            content_packet.content = processed_content

            if schema and not await plugin.validate(processed_content, stage_name, phase_name):
                repaired_content = await processor.attempt_repair(content_packet, plugin, stage_name, phase_name)
                if await plugin.validate(repaired_content, stage_name, phase_name):
                    logger.info("Content successfully repaired for %s_%s", stage_name, phase_name)
                    content_packet.content = repaired_content
                    await processor.ephemeral_storage.save_content(content_packet)
                    return content_packet, True
                else:
                    logger.warning("Repair failed for %s_%s", stage_name, phase_name)
                    return content_packet, False

            await processor.ephemeral_storage.save_content(content_packet)
            return content_packet, True
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            error_message = f"Error processing {plugin_name} content for {stage_name}_{phase_name}: {str(e)}"
            logger.error(ERROR_PROCESSING_CONTENT, error_message)
            processor.handle_processing_error(error_message, stage_name, phase_name)
            return content_packet, False
