"""
Storyteller Library Module

This module provides tools and utilities for managing dynamic and random data sets in Storyteller orchestration.
This data is generally used by the prompt manager to generate dynamic prompts for LLM execution.

The module uses the `StorytellerConfigManager` to load and manage storytelling elements from JSON files,
allowing for easy updates and modifications without changing the core codebase.

Key Components:
- StorytellerLibrary: A class representing dynamic data decisions based on configuration.
- generate_data_decisions: Function to generate a randomized data set based on the configuration.
- generate_system_prompt: Function to generate system prompts for LLM execution.

Usage:
    from storyteller_library import generate_data_decisions, generate_system_prompt
    from config.storyteller_configuration_manager import storyteller_config

    # Generate data decisions
    decisions = generate_data_decisions()

    # Generate a system prompt
    prompt = generate_system_prompt()

Note:
    This module requires the `StorytellerConfigManager` to be properly initialized
    with the necessary JSON files for various storytelling elements.
"""

import logging
import random
from typing import Any, Dict, List, Optional

from config.storyteller_configuration_manager import storyteller_config

logger = logging.getLogger(__name__)


class StorytellerLibrary:
    """
    Represents dynamic data decisions for use in an orchestrated LLM job.

    This class uses a dictionary to store attributes, allowing for flexible
    configuration-driven attribute definition and validation.

    Attributes:
        config_manager (StorytellerConfigManager): The configuration manager instance.
        data (Dict[str, Any]): A dictionary to store the dynamic attributes.
    """

    def __init__(self) -> None:
        """
        Initializes the StorytellerLibrary instance.

        This constructor initializes the StorytellerLibrary by setting up the configuration
        manager and populating the data dictionary based on the configuration.

        Raises:
            KeyError: If a required setting is missing from the placeholder configuration.
            ValueError: If data validation fails for any placeholder.
            OSError: If there's an error reading a configuration file.
        """
        self.config_manager = storyteller_config
        self.data: Dict[str, Any] = {}
        self._initialize_from_config()

    def _initialize_from_config(self) -> None:
        """
        Initializes the data dictionary from the configuration.

        This method fetches placeholder configurations from the config manager,
        retrieves and validates the corresponding values, and populates the
        data dictionary.

        Raises:
            KeyError: If a required setting is missing from the placeholder configuration.
            ValueError: If data validation fails for any placeholder.
            OSError: If there's an error reading a configuration file.
        """
        if self.config_manager is None:
            raise ValueError("Configuration manager is not initialized")

        placeholders = self.config_manager.get_all_placeholder_configs()
        for key, settings in placeholders.items():
            try:
                values = self._load_values(key)
                tag = settings["tag"]
                count = settings["count"]
                allow_duplicates = settings.get("allow_duplicates", False)

                self._validate_values(key, values, count)

                self.data[key] = {
                    "tag": tag,
                    "count": count,
                    "allow_duplicates": allow_duplicates,
                    "values": values,
                }
            except (KeyError, ValueError, OSError) as error:
                logger.error("Error processing placeholder %s: %s", key, str(error))
                raise

    def _get_values(self, key: str) -> List[str]:
        """
        Retrieves values from the specified placeholder key based on the configuration rules.

        Args:
            key (str): The placeholder key to retrieve values for.

        Returns:
            List[str]: A list of retrieved string values.

        Raises:
            ValueError: If no data is found for the specified key or the configuration is missing.
        """
        key_data = self.data.get(key)

        if not key_data:
            raise ValueError(f"No configuration found for placeholder: {key}")

        values = key_data.get('values', [])
        count = key_data.get('count', 0)
        allow_duplicates = key_data.get('allow_duplicates', False)

        if not values:
            raise ValueError(f"No data found for key: {key}")

        if not all(isinstance(value, str) for value in values):
            raise ValueError(f"All values in {key} must be strings")

        if count > len(values) and not allow_duplicates:
            logger.warning(
                "Requested count %d is greater than available unique values %d for key %s. Returning all available values.",
                count, len(values), key)
            return values

        if allow_duplicates:
            return random.choices(values, k=count)
        else:
            return random.sample(values, k=min(count, len(values)))

    def _load_values(self, key: str) -> List[str]:
        """
        Loads values from the configuration manager for the specified placeholder key.

        Args:
            key (str): The placeholder key to retrieve values for.

        Returns:
            List[str]: A list of retrieved string values.

        Raises:
            ValueError: If no data is found for the specified source or the configuration is missing.
            OSError: If there's an error reading the JSON file.
        """
        if self.config_manager.path_manager is None:
            raise ValueError("Path manager is not initialized")
        if self.config_manager.config_loader is None:
            raise ValueError("Config loader is not initialized")

        placeholder_config = self.config_manager.get_all_placeholder_configs()
        if not placeholder_config:
            raise ValueError("No configuration found for placeholders")

        keys = placeholder_config.get(key)
        if not keys:
            raise ValueError(f"No configuration found for placeholder: {key}")

        source = keys.get('source', '')
        if not source:
            raise ValueError(f"Source not defined for placeholder: {key}")

        json_file_path = self.config_manager.path_manager.get_data_path(source)

        if not json_file_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")

        placeholder_data = self.config_manager.config_loader.load_json(str(json_file_path))

        all_values = placeholder_data.get('values', [])

        if not all_values:
            raise ValueError(f"No data found for source: {source}")

        if not all(isinstance(value, str) for value in all_values):
            raise ValueError(f"All values in {source} must be strings")

        return all_values

    def _validate_values(self, key: str, values: List[Any], expected_count: int) -> None:
        """
        Validates the retrieved values for a placeholder.

        Args:
            key (str): The placeholder key.
            values (List[Any]): The retrieved values.
            expected_count (int): The expected number of values.

        Raises:
            ValueError: If validation fails due to insufficient values or invalid data.
        """
        if len(values) < expected_count:
            raise ValueError(f"Not enough values for {key}. Expected {expected_count}, got {len(values)}")

        if any(value is None or (isinstance(value, str) and not value.strip()) for value in values):
            raise ValueError(f"Invalid empty or None value found in {key}")

    def get_tag(self, key: str) -> str:
        """
        Retrieves the tag for a specific key.

        Args:
            key (str): The key to retrieve the tag for.

        Returns:
            str: The tag associated with the key.

        Raises:
            KeyError: If the key is not found in the data.
        """
        if key not in self.data:
            raise KeyError(f"Key '{key}' not found in the data.")
        return self.data[key]["tag"]

    def get_value(self, key: str) -> List[str]:
        """
        Retrieves the value for a specific key.

        Args:
            key (str): The key to retrieve the value for.

        Returns:
            List[str]: The randomly selected values associated with the key.

        Raises:
            KeyError: If the key is not found in the data.
        """
        if key not in self.data:
            raise KeyError(f"Key '{key}' not found in the data.")
        return self._get_values(key)

    def to_dict(self) -> Dict[str, List[str]]:
        """
        Converts the StorytellerLibrary instance to a dictionary.

        Returns:
            Dict[str, List[str]]: A dictionary representation of the instance with randomly selected values.
        """
        return {key: self.get_value(key) for key in self.data}

    def refresh_data(self, key: Optional[str] = None) -> None:
        """
        Refreshes the data for a specific key or all keys if no key is provided.

        Args:
            key (Optional[str]): The key to refresh. If None, refreshes all keys.

        Raises:
            KeyError: If the specified key doesn't exist.
        """
        if key is None:
            self._initialize_from_config()
        elif key in self.data:
            self.data[key]['values'] = self._load_values(key)
        else:
            raise KeyError(f"Key '{key}' not found in the data.")

    def has_key(self, key: str) -> bool:
        """
        Checks if a key exists in the data.

        Args:
            key (str): The key to check.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        return key in self.data

    def get_keys(self) -> List[str]:
        """
        Returns a list of all keys in the data.

        Returns:
            List[str]: A list of all keys.
        """
        return list(self.data.keys())


def generate_data_decisions() -> StorytellerLibrary:
    """
    Generates a StorytellerLibrary instance with populated fields based on the configuration.

    Returns:
        StorytellerLibrary: An instance with generated and validated data decisions.

    Raises:
        ValueError: If required attributes are missing or if data validation fails.
        OSError: If there's an error reading a configuration file.
    """
    try:
        return StorytellerLibrary()
    except (ValueError, OSError) as error:
        logger.error("Error generating data decisions: %s", str(error))
        raise


def generate_system_prompt(custom_skills: Optional[List[str]] = None) -> str:
    """
    Generates the system prompt for the generative model.

    Args:
        custom_skills (Optional[List[str]]): List of custom skills to include in the prompt.

    Returns:
        str: A string containing the system prompt.

    Raises:
        ValueError: If the system configuration is not a dictionary or is None.
        OSError: If there's an error reading the system configuration file.
    """
    assert storyteller_config is not None, "Storyteller configuration manager is not initialized"
    assert storyteller_config.config_loader is not None, "Config loader is not initialized"
    assert storyteller_config.path_manager is not None, "Path manager is not initialized"

    try:
        system_config = storyteller_config.config_loader.load_json(
            storyteller_config.path_manager.get_data_path("system_config"),
            dict
        )

        if not isinstance(system_config, dict):
            raise ValueError("system_config is not a dictionary or is None")

        default_skills: List[Dict[str, str]] = system_config.get("default_skills", [])
        if not isinstance(default_skills, list):
            default_skills = []

        skills_to_use = custom_skills if custom_skills is not None else [skill["name"] for skill in default_skills]

        prompt_template = system_config.get("prompt_template")
        if not prompt_template:
            raise ValueError("prompt_template is missing in system_config")

        filtered_skills = [skill for skill in default_skills if skill["name"] in skills_to_use]
        formatted_skills = "\n\n".join(f"{skill['name']}: {skill['description']}" for skill in filtered_skills)

        return prompt_template.format(skills=formatted_skills)
    except (ValueError, OSError) as error:
        logger.error("Error generating system prompt: %s", str(error))
        raise
