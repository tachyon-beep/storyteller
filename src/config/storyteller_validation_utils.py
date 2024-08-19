"""
validation_utils.py

This module provides utility functions for validating configuration values in the
storytelling pipeline. These functions are used by the StorytellerConfigurationValidator
to ensure that configuration values meet specific criteria.

Usage:
    from validation_utils import is_non_empty_string, is_positive_int

    if is_non_empty_string(some_value):
        print("Value is a non-empty string")
    
    if is_positive_int(some_number):
        print("Value is a positive integer")

Note:
    These functions raise ValueError if the validation fails, allowing for detailed
    error messages to be propagated up the call stack.
"""

from typing import Any


def is_non_empty_string(value: Any) -> bool:
    """
    Validate that a value is a non-empty string.

    Args:
        value: The value to validate.

    Returns:
        True if the value is a non-empty string.

    Raises:
        ValueError: If the value is not a string or is empty.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")
    if not value:
        raise ValueError("String must not be empty")
    return True


def is_non_negative_int(value: Any) -> bool:
    """
    Validate that a value is a non-negative integer.

    Args:
        value: The value to validate.

    Returns:
        True if the value is a non-negative integer.

    Raises:
        ValueError: If the value is not an integer or is negative.
    """
    if not isinstance(value, int):
        raise ValueError(f"Expected integer, got {type(value).__name__}")
    if value < 0:
        raise ValueError("Integer must be non-negative")
    return True


def is_positive_int(value: Any) -> bool:
    """
    Validate that a value is a positive integer.

    Args:
        value: The value to validate.

    Returns:
        True if the value is a positive integer.

    Raises:
        ValueError: If the value is not an integer or is not positive.
    """
    if not isinstance(value, int):
        raise ValueError(f"Expected integer, got {type(value).__name__}")
    if value <= 0:
        raise ValueError("Integer must be positive")
    return True


def is_valid_float_range(value: Any) -> bool:
    """
    Validate that a value is a float between 0 and 2, inclusive.

    Args:
        value: The value to validate.

    Returns:
        True if the value is a float between 0 and 2, inclusive.

    Raises:
        ValueError: If the value is not a float or is out of range.
    """
    if not isinstance(value, float):
        raise ValueError(f"Expected float, got {type(value).__name__}")
    if not 0 <= value <= 2:
        raise ValueError("Float must be between 0 and 2, inclusive")
    return True


def is_optional_string(value: Any) -> bool:
    """
    Validate that a value is either None or a non-empty string.

    Args:
        value: The value to validate.

    Returns:
        True if the value is None or a non-empty string.

    Raises:
        ValueError: If the value is neither None nor a non-empty string.
    """
    if value is None:
        return True
    return is_non_empty_string(value)
