"""
Storyteller Pipeline Script

This script serves as the main entry point for the storyteller pipeline. It configures
the environment, sets up logging, initializes the pipeline orchestrator, and executes
the storytelling process.

The script performs the following main tasks:
1. Configures logging for the application.
2. Prints configuration diagnostics to verify the setup.
3. Initializes and runs the PipelineOrchestrator to execute the storytelling pipeline.

Usage:
    python storyteller.py

Note:
    This script requires the storyteller configuration to be properly set up and
    all necessary dependencies to be installed.
"""

import asyncio
import logging
import os
import sys
from typing import Optional, Dict

from config.storyteller_configuration_manager import storyteller_config
from orchestration.storyteller_orchestrator import PipelineOrchestrator

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def print_config_diagnostics() -> None:
    """
    Print configuration diagnostics including loaded config path and configured paths.

    This function logs the path to the configuration file and the paths for various outputs.
    It helps in verifying that the configuration is loaded correctly and all required paths
    are properly set.
    """
    logger.info("Storyteller Config loaded")
    logger.info("Configured Paths:")

    # Print paths defined in the 'paths' section
    paths: Dict[str, Optional[str]] = storyteller_config.get_nested_config_value("paths")
    for key, _ in paths.items():
        logger.info("%s: %s", key.capitalize(), storyteller_config.get_path(key))

    # Print guidance folder separately
    guidance_folder: Optional[str] = storyteller_config.get_nested_config_value("guidance.folder")
    if guidance_folder is not None:
        guidance_path = storyteller_config.get_path("root") / guidance_folder
        logger.info("Guidance: %s", guidance_path)
    else:
        logger.warning("Guidance folder not configured")

    # Print other important configurations
    logger.info("LLM Type: %s", storyteller_config.get_nested_config_value("llm.type"))
    logger.info("Batch Size: %d", storyteller_config.get_nested_config_value("batch.size"))

    # Get enabled plugins
    plugin_config = storyteller_config.get_plugin_config()
    enabled_plugins = [name for name, config in plugin_config.items() if config.get('enabled', False)]
    logger.info("Enabled Plugins: %s", ", ".join(enabled_plugins))


async def run_orchestrator() -> None:
    """
    Run the pipeline orchestrator to execute the storytelling pipeline.

    This function initializes the PipelineOrchestrator, runs the batch process,
    and handles any exceptions that occur during the execution.

    Raises:
        ValueError: If there is a configuration error.
        RuntimeError: If there is a pipeline execution error.
    """
    try:
        orchestrator = PipelineOrchestrator()
        await orchestrator.initialize()
        await orchestrator.run_batch()
    except ValueError as ve:
        logger.error("Configuration error: %s", ve)
        raise
    except RuntimeError as re:
        logger.error("Pipeline execution error: %s", re)
        raise
    except Exception as e:
        logger.error("An unexpected error occurred during pipeline execution: %s", e, exc_info=True)
        raise
    except KeyboardInterrupt:
        logger.info("Pipeline execution interrupted by user.")
        raise


async def main() -> None:
    """
    Main entry point for the storyteller pipeline script.
    This function runs the configuration diagnostics and then executes the pipeline orchestrator.
    """
    print_config_diagnostics()  # TODO - Update the code so storyteller initialises all the components to deal with duplication of classes.
    orchestrator = PipelineOrchestrator()
    await orchestrator.initialize()
    await orchestrator.run_batch()
    logger.info("Storyteller pipeline completed successfully")

if __name__ == "__main__":
    asyncio.run(main())
