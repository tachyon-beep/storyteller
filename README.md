# Storyteller: General-Purpose LLM Orchestration and Batch Processing System

Storyteller is an advanced, modular system designed for orchestrating Large Language Models (LLMs) in batch processes. While it originated as a tool for generating synthetic narrative data, it has evolved into a flexible and powerful framework for managing complex LLM-driven workflows across various domains and use cases.

**Note:** Storyteller is currently in alpha and may be difficult to get running. Parts of it are non-functional or not fully tested. 

**Warning:** This system can consume a significant number of tokens if not used carefully, monitor usage carefully if you are using a paid LLM.

## Features

- **Versatile LLM Orchestration**: Coordinate and manage multiple LLM interactions within a single workflow.
- **Batch Processing**: Efficiently handle large-scale data processing tasks using LLMs.
- **Modular Architecture**: Easily extendable with plugins for various content types and processing needs.
- **Multi-Stage Pipeline**: Configurable stages for different aspects of your LLM workflow.
- **LLM Integration**: Supports multiple LLM backends, including OpenAI's GPT and Google's Vertex AI Gemini.
- **Efficient Storage Management**: Handles ephemeral, batch, and output storage for different content lifecycles.
- **Dynamic Configuration**: YAML-based configuration with validation for easy setup and modification.
- **Progress Tracking**: Built-in progress tracking and resumability for long-running processes.
- **Flexible Content Processing**: Support for JSON, lists, plain text, and custom formats.
- **Error Handling and Repair**: LLM-enabled error handling with limited repair capabilities.

## Use Cases

Storyteller can be applied to a wide range of LLM-driven tasks, including but not limited to:

- Large-scale text analysis and processing
- Automated content generation for various industries
- Data augmentation and synthetic data generation
- Complex decision-making systems
- Multi-step reasoning and problem-solving workflows

## System Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt` 

## Quick Start

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/storyteller.git
   cd storyteller
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure the system by editing `config/pipeline.development.yaml`.

4. Define your stages, phases, prompts, schemas and guidance as described below.

5. Run the orchestrator:
   ```
   set PYTHONPATH=./src:./plugins
   python storyteller.py
   ```

## Configuration

The system is configured using YAML files located in the `config/` directory. The main configuration file is `pipeline.development.yaml`, which includes settings for:

- Paths
- Batch processing
- LLM settings
- Plugin configurations
- Pipeline stages and phases
- Content processing parameters

### Creating New Stages

1. Define the new stage in `pipeline.development.yaml` under the `stages` section.
2. Create corresponding prompt files in the `prompts/` directory.
3. If required, create a schemas and place it in the `schemas/` directory.
4. Update the general and stage level guidance in the `guidance/` directory as required.

## Architecture

Storyteller is built with a modular architecture:

- `storyteller.py`: Main entry point
- `storyteller_orchestrator.py`: Manages the overall pipeline execution
- `storyteller_stage_manager.py`: Handles individual stages and progress tracking
- `storyteller_plugin_manager.py`: Manages content processing plugins
- `storyteller_storage_manager.py`: Coordinates different storage types
- `storyteller_llm_factory.py`: Creates and manages LLM instances
- `storyteller_content_processor.py`: Processes generated content
- `storyteller_prompt_manager.py`: Manages prompt preparation and handling

## Extending Storyteller

### Adding New Plugins

1. Create a new plugin file in the `plugins/` directory.
2. Implement the plugin class, extending `StorytellerOutputPlugin`.
3. Add the plugin configuration to `pipeline.development.yaml`.
4. Develop appropriate guidance on output formats for inclusion in generated prompts.

## Project Roadmap

The roadmap includes:

1. Enhancing LLM integration (OpenAI, AzureOpenAI plugins, agent mode)
2. Improving batch processing and parallelization
3. Architectural improvements for better modularity
4. Expanding the content plugin system
5. Implementing testing and quality assurance measures
6. Enhancing security, monitoring, and logging capabilities
7. Containerization for easier deployment

For a detailed list of planned features and improvements, please see our [TODO list](TODO.md).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the [MIT License](LICENSE).
