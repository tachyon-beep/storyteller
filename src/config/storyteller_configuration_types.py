"""
storyteller_configuration_types.py

This module defines the structure of the configuration for the storytelling system using TypedDict.
It provides type hints for the configuration, ensuring consistency and type safety across the entire
configuration managment subsystem. The configuration is divided into various sections, each represented
by a TypedDict class.

Usage:
    from config.storyteller_configuration_types import StorytellerConfig, PathsConfig, LLMConfig

    def process_config(config: StorytellerConfig) -> None:
        root_path = config['paths']['root']
        llm_type = config['llm']['type']
        # Process the configuration...

This module helps ensure that configurations are correctly structured, reducing errors and improving maintainability.
"""

from typing import TypedDict, List, Union, Optional, Literal, Any, Dict


class PathsConfig(TypedDict):
    """
    Configuration for various paths used in the storytelling system.

    Attributes:
        root (str): The root path of the project.
        config (str): The directory for configuration files.
        plugins (str): The directory for plugins.
        prompts (str): The directory for prompt files.
        schemas (str): The directory for schema files.
        data (str): The directory for data files.
        batch_storage (str): The directory for batch storage.
        ephemeral_storage (str): The directory for ephemeral storage.
        output_folder (str): The directory for output files.
    """

    root: str
    config: str
    plugins: str
    prompts: str
    schemas: str
    data: str
    batch_storage: str
    ephemeral_storage: str
    output_folder: str


class BatchConfig(TypedDict):
    """
    Configuration for batch processing.

    Attributes:
        size (int): The size of the batch.
        batch_name (str): The name of the batch.
        starting_id (int): The starting ID for batch processing.
    """

    size: int
    batch_name: str
    starting_id: int


class ContentProcessingConfig(TypedDict):
    """
    Configuration for content processing.

    Attributes:
        default_max_retries (int): The default maximum number of retries for content processing.
    """

    default_max_retries: int


class GuidanceConfig(TypedDict):
    """
    Configuration for the guidance system.

    Attributes:
        folder (str): The directory containing guidance files.
        generic_guidance (str): The path to the generic guidance file.
    """

    folder: str
    tag: str


class LLMConfig(TypedDict):
    """
    Configuration for the Language Model (LLM).

    Attributes:
        type (str): The type of the language model.
        default_temperature (float): The default temperature for the language model.
        config (Dict[str, str]): Additional configuration details for the language model.
    """

    type: str
    default_temperature: float
    config: Dict[str, str]
    pass_schema: bool  # Optional, but we'll handle defaulting outside of TypedDict
    autocontinue: bool  # Optional, handle default value outside of TypedDict
    max_continues: int  # Optional, handle default value outside of TypedDict
    max_retries: int  # Optional, handle default value outside of TypedDict
    max_output_tokens: int


class PluginConfig(TypedDict, total=False):
    """
    Configuration for a single plugin.

    This configuration is used both in the overall configuration structure
    and when initializing individual plugin instances.

    Attributes:
        enabled (bool): Whether the plugin is enabled.
        file (str): The file path of the plugin.
        class_name (str): The class name of the plugin.
        tag (Optional[str]): An optional tag for the plugin.
        guidance (Optional[str]): Optional guidance related to the plugin.
        repair (bool): Whether the plugin supports repair.
        retry (Optional[bool]): Whether the plugin should retry on failure.
        default_schema (Optional[str]): The default schema associated with the plugin.
        repair_prompt (Optional[str]): The prompt used for repair operations.
    """

    enabled: bool
    file: str
    class_name: str
    tag: Optional[str]
    guidance: Optional[str]
    repair: bool
    retry: Optional[bool]
    default_schema: Optional[str]
    repair_prompt: Optional[str]


class PhaseConfig(TypedDict):
    """
    Configuration for a single phase in a stage of the storytelling process.

    Attributes:
        name (str): The name of the phase.
        prompt_file (str): The file path of the prompt used in this phase.
        plugin (str): The name of the plugin used in this phase.
        temperature (Optional[float]): The temperature setting for the phase (if applicable).
        schema (Optional[str]): The schema associated with this phase.
    """

    name: str
    prompt_file: str
    plugin: str
    temperature: Optional[float]
    schema: Optional[str]


class StageConfig(TypedDict):
    """
    Configuration for a single stage in the storytelling process.

    Attributes:
        name (str): The name of the stage.
        display_name (str): The display name of the stage.
        description (str): A description of the stage.
        order (int): The order in which the stage should be executed.
        enabled (bool): Whether the stage is enabled.
        guidance (str): The guidance file path associated with the stage.
        phases (List[PhaseConfig]): The list of phases within this stage.
    """

    name: str
    display_name: str
    description: str
    order: int
    enabled: bool
    guidance: str
    phases: List[PhaseConfig]


class PlaceholderConfig(TypedDict):
    """
    Configuration for a placeholder.

    Attributes:
        tag (str): The tag identifying the placeholder.
        source (str): The source of the placeholder data.
        allow_duplicates (bool): Whether duplicates are allowed.
        count (int): The number of placeholders.
    """

    tag: str
    source: str
    allow_duplicates: bool
    count: int
    values: List[str]


class CacheConfig(TypedDict):
    """
    Configuration for caching within the storytelling system.

    Attributes:
        enabled (bool): Whether caching is enabled.
        max_size (int): The maximum size of the cache.
        ttl (int): The time-to-live for cached items, in seconds.
    """

    enabled: bool
    max_size: int
    ttl: int


class StorytellerConfig(TypedDict):
    """
    Main configuration type for the storytelling system.

    This TypedDict represents the complete configuration structure for the storytelling system,
    including all subsections and their respective configurations.

    Attributes:
        paths (PathsConfig): Configuration for various paths used in the system.
        batch (BatchConfig): Configuration for batch processing.
        content_processing (ContentProcessingConfig): Configuration for content processing.
        guidance (GuidanceConfig): Configuration for the guidance system.
        llm (LLMConfig): Configuration for the Language Model.
        plugins (Dict[str, PluginConfig]): Configuration for plugins used in the system.
        stages (List[StageConfig]): Configuration for the stages in the storytelling process.
        placeholders (Dict[str, PlaceholderConfig]): Configuration for placeholders.
        cache (CacheConfig): Configuration for caching.
    """

    paths: PathsConfig
    batch: BatchConfig
    content_processing: ContentProcessingConfig
    guidance: GuidanceConfig
    llm: LLMConfig
    plugins: Dict[str, PluginConfig]
    stages: List[StageConfig]
    placeholders: Dict[str, PlaceholderConfig]
    cache: CacheConfig


# Environment types
EnvironmentType = Literal['development', 'staging', 'production']

# Generic configuration value types
ConfigValue = Union[str, int, float, bool, Dict[str, Any], List[Any]]
NestedConfig = Dict[str, Union[ConfigValue, 'NestedConfig']]
