"""
Storyteller Exceptions

This module defines custom exceptions for the Storyteller system.
These exceptions provide more specific error handling and reporting
for various components of the system.
"""

from typing import Optional


class StorytellerError(Exception):
    """
    Base exception for errors in the Storyteller system.
    This exception serves as a parent class for more specific exceptions.
    It can be used to catch any Storyteller-related exception.

    Attributes:
        message (str): Description of the error.
        component (Optional[str]): Component where the error occurred.
        operation (Optional[str]): Operation being performed when the error occurred.
    """

    def __init__(self, message: str, component: Optional[str] = None, operation: Optional[str] = None) -> None:
        super().__init__(message)
        self.component = component
        self.operation = operation

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.component and self.operation:
            return f"{base_msg} (Component: {self.component}, Operation: {self.operation})"
        elif self.component:
            return f"{base_msg} (Component: {self.component})"
        elif self.operation:
            return f"{base_msg} (Operation: {self.operation})"
        return base_msg


class StorytellerContentProcessingError(StorytellerError):
    """
    Exception raised when there's an error processing content in the Storyteller system.

    This could include errors in parsing, transformation, or validation of content.
    """


class StorytellerConfigurationError(StorytellerError):
    """
    Exception raised when there's an error in the configuration of the Storyteller system.

    This could include missing or invalid configuration settings.
    """


class StorytellerFileNotFoundError(StorytellerError):
    """
    Exception raised when a required file is not found in the Storyteller system.

    This could include missing prompt templates, guidance files, or other necessary resources.
    Use this instead of the built-in FileNotFoundError when you want to catch Storyteller-specific file issues.
    """


class StorytellerInvalidContentTypeError(StorytellerError):
    """
    Exception raised when an invalid content type is specified or encountered.

    This could occur when processing or categorizing content in the system.
    """


class StorytellerInvalidGuidanceTypeError(StorytellerError):
    """
    Exception raised when an invalid guidance type is specified or encountered.

    This could occur when loading or processing guidance for the storytelling process.
    """


class StorytellerMissingAttributeError(StorytellerError):
    """
    Exception raised when a required attribute is missing from a ContentPacket or similar structure.

    Attributes:
        attribute (str): The name of the missing attribute.
    """

    def __init__(self, attribute: str, message: Optional[str] = None):
        super().__init__(message or f"Missing required attribute: {attribute}")
        self.attribute = attribute
