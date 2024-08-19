"""
Storyteller Batch Manager Module

This module provides the BatchManager class which is responsible for managing batch execution
in the storyteller pipeline. It handles the initialization and management of batch IDs and batch names,
and provides logging for batch start and end operations.

Usage:
    batch_manager = BatchManager(starting_batch_id=0, batch_name="storyteller_batch")
    batch_manager.start_batch()
    # Perform batch operations
    batch_manager.end_batch()
"""

import logging

logger = logging.getLogger(__name__)


class BatchManager:
    """
    Manages the batch execution in the storyteller pipeline.

    Attributes:
        current_batch_id (int): The ID of the current batch.
        batch_name (str): The name of the current batch.
    """

    def __init__(self, batch_name: str, starting_batch_id: int) -> None:
        """
        Initializes the BatchManager with the starting batch ID and batch name.

        Args:
            batch_name (str): The name of the batch.
            starting_batch_id (int): The starting batch ID.
        """
        self.batch_name: str = batch_name
        self.current_batch_id: int = starting_batch_id

    def start_batch(self) -> None:
        """
        Starts a new batch by incrementing the batch ID and logging the start of the batch.

        Raises:
            ValueError: If the batch ID is negative.
        """
        if self.current_batch_id < 0:
            raise ValueError("Batch ID cannot be negative.")
        self.current_batch_id += 1
        logger.info("Starting batch ID: %d", self.current_batch_id)

    def end_batch(self) -> None:
        """
        Ends the current batch by logging the end of the batch.
        """
        logger.info("Ending batch ID: %d", self.current_batch_id)

    def get_current_batch_id(self) -> int:
        """
        Gets the current batch ID.

        Returns:
            int: The current batch ID.
        """
        return self.current_batch_id

    def get_batch_name(self) -> str:
        """
        Gets the name of the current batch.

        Returns:
            str: The name of the batch.
        """
        return self.batch_name

    def set_batch_name(self, new_batch_name: str) -> None:
        """
        Sets a new name for the batch.

        Args:
            new_batch_name (str): The new name for the batch.
        """
        self.batch_name = new_batch_name
        logger.info("Batch name set to: %s", self.batch_name)
