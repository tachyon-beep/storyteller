# Storyteller Project TODO List

## LLM Integration
1. Complete OpenAI and AzureOpenAI plugins.
2. Extract plugins from main code base and store in plugins folder as user extensible.
3. Finish 'agent mode':
   - Implement system for dynamically creating agents on specified LLMs, with specified configuration settings and system instructions via configuration.
   - Allow users to specify which agent to execute a given phase on.
   - Finish implementation of full parameter set (e.g. Top P and Top A).
4. Enhance JSON schema support for LLMs:
   - Improve enforcement of schema compliance.
   - More testing and evaluation.

## Batches and Parallelization
1. Separate batch configuration from system configuration.
2. Additional system parameters to constrain batches (i.e. max stages, max running time, max tokens).
3. Automated and configurable batch verification and validation.
4. Allow concurrent batches to be run.
5. Allow batches to be created, monitored and downloaded from a HTTP interface.

## Architecture Improvements
1. Further decoupling and migration to a message bus:
   - Redesign architecture to improve modularity.

## Documentation and Demonstration
1. Build a demonstrator to showcase capability.
2. Write documentation.

## Content Plugin System
Implement a system for complex, code and LLM-mediated behaviors attachable to stages:
1. Optimise Outputs:
   - Query multiple LLMs or agents (with various system prompts).
   - Use a mediator LLM to select the best outcome based on defined criteria.
2. Consensus and Collaboration:
   - Query multiple LLMs or agents with diverse prompts.
   - Use a mediator LLM to facilitate consensus-building.
   - Implement multiple modes: round-robin, debate, voting.
3. Guard:
   - Use an LLM to review stage output.
   - Implement logic to halt execution or force reruns based on conditions.

## Testing and Quality Assurance
1. Develop literally any unit and integration tests.

## Security
1. Implement restricted python for all plugins.

## Monitoring and Logging
1. Implement structured logging for improved analysis.
2. Add performance metrics tracking.
3. A monitoring dashboard for creating and executing batches, and monitoring system health and performance during batch runs.

## Containerization
1. Create Dockerfiles for the main application and services.
2. Develop a docker-compose file for local deployment and testing.
