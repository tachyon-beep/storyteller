"""
storyteller_configuration_validator.py

This module provides a configuration validation system for the storytelling pipeline.
It defines a set of validation functions and a main validator class that uses these
functions to validate configuration data against predefined schemas.

The module utilizes the `schema` library for defining and enforcing schemas.

Usage:
    from storyteller_configuration_validator import StorytellerConfigurationValidator
    
    validator = StorytellerConfigurationValidator()
    schema = validator.create_base_schema()
    
    try:
        validated_config = validator.validate_config(config_data, schema)
    except StorytellerConfigurationError as e:
        print(f"Configuration validation failed: {e}")

Note:
    This module requires the `schema` library to be installed.
"""

import logging
from typing import Any, Dict, List

from schema import Schema, SchemaError, Optional as SchemaOptional

from config.storyteller_configuration_types import StorytellerConfig
from config.storyteller_validation_utils import (
    is_non_empty_string,
    is_non_negative_int,
    is_positive_int,
    is_valid_float_range,
    is_optional_string
)

logger = logging.getLogger(__name__)


class StorytellerConfigurationError(Exception):
    """Custom exception for configuration-related errors."""


class StorytellerConfigurationValidator:
    """
    Validates configuration data against predefined schemas.

    This class provides methods to create schemas and validate configuration data
    against those schemas. It includes a set of validation functions for specific
    data types and structures used in the storytelling pipeline configuration.
    """

    def create_common_string_schema(self, keys: List[str]) -> Schema:
        """
        Create a schema for a dictionary with specific keys as non-empty strings.

        Args:
            keys: List of keys that should be non-empty strings.

        Returns:
            A schema that enforces non-empty string values for the provided keys.
        """
        return Schema({key: is_non_empty_string for key in keys})

    def create_paths_schema(self) -> Schema:
        """
        Create the schema for the 'paths' section of the configuration.

        Returns:
            The schema for the 'paths' section.
        """
        return self.create_common_string_schema([
            'root', 'config', 'src', 'plugins', 'prompts', 'schemas',
            'data', 'batch_storage', 'ephemeral_storage', 'output_folder'
        ])

    def create_batch_schema(self) -> Schema:
        """
        Create the schema for the 'batch' section of the configuration.

        Returns:
            The schema for the 'batch' section.
        """
        return Schema({
            'size': is_positive_int,
            'name': is_non_empty_string,
            'starting_id': is_non_negative_int,
        })

    def create_content_processing_schema(self) -> Schema:
        """
        Create the schema for the 'content_processing' section of the configuration.

        Returns:
            The schema for the 'content_processing' section.
        """
        return Schema({
            'default_max_retries': is_positive_int,
        })

    def create_guidance_schema(self) -> Schema:
        """
        Create the schema for the 'guidance' section of the configuration.

        Returns:
            The schema for the 'guidance' section.
        """
        return Schema({
            'folder': is_non_empty_string,
            str: {
                'tag': is_non_empty_string,
                'path': is_non_empty_string
            }
        })

    def create_llm_schema(self) -> Schema:
        """
        Create the schema for the 'llm' section of the configuration.

        Returns:
            The schema for the 'llm' section.
        """
        return Schema({
            'type': is_non_empty_string,
            'default_temperature': is_valid_float_range,
            SchemaOptional('pass_schema'): bool,  # Optional field to specify whether to pass a schema
            'max_output_tokens': is_positive_int,
            SchemaOptional('autocontinue'): bool,  # Optional field
            SchemaOptional('max_continues'): is_positive_int,  # Optional field
            SchemaOptional('max_retries'): is_positive_int,  # Optional field
            'config': self.create_common_string_schema(['project_id', 'location', 'model']),
        })

    def create_plugins_schema(self) -> Schema:
        """
        Create the schema for the 'plugins' section of the configuration.

        Returns:
            The schema for the 'plugins' section.
        """
        return Schema({
            str: {
                'enabled': bool,
                SchemaOptional('debug'): bool,
                'file': is_non_empty_string,
                'class_name': is_non_empty_string,
                SchemaOptional('tag'): is_optional_string,
                SchemaOptional('guidance'): is_optional_string,
                'repair': bool,
                SchemaOptional('retry'): bool,
                SchemaOptional('default_schema'): is_non_empty_string,
                SchemaOptional('repair_prompt'): is_optional_string,
            },
        })

    def create_stages_schema(self) -> Schema:
        """
        Create the schema for the 'stages' section of the configuration.

        Returns:
            The schema for the 'stages' section.
        """
        return Schema([
            {
                'name': is_non_empty_string,
                'display_name': is_non_empty_string,
                'description': is_non_empty_string,
                'order': is_positive_int,
                'enabled': bool,
                'guidance': is_non_empty_string,
                'phases': [
                    {
                        'name': is_non_empty_string,
                        'prompt_file': is_non_empty_string,
                        'plugin': is_non_empty_string,
                        SchemaOptional('temperature'): is_valid_float_range,
                        SchemaOptional('schema'): is_non_empty_string,
                    }
                ]
            }
        ])

    def create_placeholders_schema(self) -> Schema:
        """
        Create the schema for the 'placeholders' section of the configuration.

        Returns:
            The schema for the 'placeholders' section.
        """
        return Schema({
            str: {
                'tag': is_non_empty_string,
                'source': is_non_empty_string,
                'allow_duplicates': bool,
                'count': is_positive_int,
            }
        })

    def create_cache_schema(self) -> Schema:
        """
        Create the schema for the 'cache' section of the configuration.

        Returns:
            The schema for the 'cache' section.
        """
        return Schema({
            'enabled': bool,
            'max_size': is_positive_int,
            'ttl': is_positive_int,
        })

    def create_base_schema(self) -> Schema:
        """
        Create the base schema for configuration validation.

        This method combines all sub-schemas into a complete configuration schema.

        Returns:
            The complete base schema for configuration validation.
        """
        return Schema({
            'paths': self.create_paths_schema(),
            'batch': self.create_batch_schema(),
            'content_processing': self.create_content_processing_schema(),
            'guidance': self.create_guidance_schema(),
            'llm': self.create_llm_schema(),
            'plugins': self.create_plugins_schema(),
            'stages': self.create_stages_schema(),
            'placeholders': self.create_placeholders_schema(),
            'cache': self.create_cache_schema(),
        })

    def validate_config(self, config: Dict[str, Any], schema: Schema) -> StorytellerConfig:
        """
        Validate the configuration against the provided schema.

        This method attempts to validate the given configuration against the provided schema.
        It logs the results of the validation and raises an exception if validation fails.

        Args:
            config: The configuration to validate.
            schema: The schema to validate against.

        Returns:
            The validated configuration.

        Raises:
            StorytellerConfigurationError: If the configuration is invalid.
        """
        try:
            validated_config = schema.validate(config)
            logger.info("Configuration successfully validated")
            for section in validated_config:
                logger.debug("Section '%s' validated successfully", section)
            return validated_config
        except SchemaError as e:
            logger.error("Configuration validation failed: %s", str(e))
            raise StorytellerConfigurationError(f"Invalid configuration: {str(e)}") from e
