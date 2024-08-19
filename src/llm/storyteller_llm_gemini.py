"""
Storyteller Gemini Generator Module

This module provides an implementation of the StorytellerLLMInterface for Google's Vertex AI Gemini models.
It handles initialization, content generation, and error management for Vertex AI API interactions.

The StorytellerGeminiGenerator class encapsulates the logic for interacting with Gemini models,
including managing safety settings, generation configuration, and processing responses.

Usage:
    generator = StorytellerGeminiGenerator()
    await generator.initialize(config)
    response = await generator.generate_content("Tell me a story about a brave knight.")

Note:
This implementation requires the `google-cloud-aiplatform` package and appropriate
Google Cloud credentials to be set up in the environment.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, AsyncIterable, Callable, Awaitable
import json

import vertexai
from vertexai.generative_models._generative_models import (
    ResponseValidationError, FinishReason, GenerativeModel, GenerationConfig,
    GenerationResponse, ChatSession, SafetySetting
)
from google.api_core.exceptions import ResourceExhausted, GoogleAPICallError

from llm.storyteller_llm_interface import StorytellerLLMInterface

logger = logging.getLogger(__name__)

# Constants
RETRY_MESSAGE = "Waiting %d seconds before retrying..."
MAX_RETRIES_MESSAGE = "Max retries reached. Unable to generate content."
CONTINUATION_CONTEXT_LENGTH = 500

# Mapping FinishReason enums to human-friendly messages
FINISH_REASON_MESSAGES = {
    FinishReason.FINISH_REASON_UNSPECIFIED: "Unspecified reason.",
    FinishReason.STOP: "Natural stopping point or stop sequence reached.",
    FinishReason.MAX_TOKENS: "Maximum output tokens reached.",
    FinishReason.SAFETY: "Content blocked due to potential safety violations.",
    FinishReason.RECITATION: "Potential copyright violations detected.",
    FinishReason.OTHER: "Generation stopped for an unspecified reason.",
    FinishReason.BLOCKLIST: "Content contains forbidden terms.",
    FinishReason.PROHIBITED_CONTENT: "Content potentially contains prohibited material.",
    FinishReason.SPII: "Content potentially contains sensitive personal information (SPII).",
    FinishReason.MALFORMED_FUNCTION_CALL: "Generated function call is invalid."
}


class MaxTokensReachedError(Exception):
    """Custom exception raised when the maximum token limit is reached."""


class AutoContinuationLimitExceeded(Exception):
    """Custom exception raised when the auto-continuation limit is exceeded."""


class UnexpectedFinishReason(Exception):
    """Custom exception raised when an unexpected finish reason is encountered."""


class StorytellerGeminiGenerator(StorytellerLLMInterface):
    """
    A class to generate content using Google's Vertex AI Gemini models.

    This class implements the StorytellerLLMInterface and provides methods
    for initializing the Vertex AI client and generating content
    using the specified Gemini model.

    Attributes:
        project_id (str): The Google Cloud project ID.
        location (str): The location of the Vertex AI service.
        model (Optional[GenerativeModel]): The Gemini model instance.
        chat_session (Optional[ChatSession]): The chat session for managing conversation history.
        model_name (str): The name of the Gemini model.
        safety_settings (List[SafetySetting]): Safety settings for content generation.
        generation_config (Dict[str, Any]): Configuration for content generation.
        default_temperature (float): Default temperature for content generation.
        max_retries (int): Maximum number of retries for errors.
        retry_delay (int): Delay in seconds between retries.
        auto_continue (bool): Whether to automatically continue generating content.
        max_continues (int): Maximum number of auto-continuations.
        chat_history (List[Dict[str, str]]): List of chat messages.
        pass_schema (bool): Whether to pass schema information to the model.
        current_schema (Optional[str]): The current schema for content generation.
    """

    def __init__(self) -> None:
        """Initialize the StorytellerGeminiGenerator with default settings."""
        super().__init__()
        self.project_id: str = ""
        self.location: str = ""
        self.model: Optional[GenerativeModel] = None
        self.chat_session: Optional[ChatSession] = None
        self.model_name: str = ""
        self.safety_settings: List[SafetySetting] = []
        self.generation_config: Dict[str, Any] = {}
        self.default_temperature: float = 1.0
        self.max_retries: int = 3
        self.retry_delay: int = 30
        self.auto_continue: bool = False
        self.max_continues: int = 0
        self.chat_history: List[Dict[str, str]] = []
        self._initialization_lock = asyncio.Lock()
        self.pass_schema: bool = False
        self.current_schema: Optional[str] = None
        logger.debug("Initialized StorytellerGeminiGenerator")

    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the Vertex AI client and load the Gemini model.

        Args:
            config: Configuration parameters for the Gemini model.

        Raises:
            ValueError: If the model name is not provided in the configuration.
            RuntimeError: If there's an error initializing the Vertex AI client or loading the model.
        """
        async with self._initialization_lock:
            llm_config = config["config"]
            self.project_id = llm_config["project_id"]
            self.location = llm_config["location"]
            self.model_name = llm_config["model"]
            self.default_temperature = config.get("default_temperature", 1.0)
            self.max_retries = config.get("max_retries", 3)
            self.retry_delay = config.get("retry_delay", 30)
            self.auto_continue = config.get("autocontinue", False)
            self.max_continues = config.get("max_continues", 0)
            self.pass_schema = config.get("pass_schema", False)

            logger.debug("Initialization parameters: auto_continue=%s, max_continues=%d, pass_schema=%s",
                         self.auto_continue, self.max_continues, self.pass_schema)

            self.generation_config = {
                "temperature": self.default_temperature,
                "top_p": config.get("top_p", 0.95),
                "top_k": config.get("top_k", 40),
            }

            self.safety_settings = [
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH
                ),
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH
                ),
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH
                ),
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH
                ),
            ]

            if not self.model_name:
                logger.error("Gemini configuration has no model name")
                raise ValueError("Gemini configuration has no model name")

            logger.info("Initializing Vertex AI and Gemini Model: %s", self.model_name)
            try:
                vertexai.init(project=self.project_id, location=self.location)
                self.model = GenerativeModel(self.model_name)
                self.chat_session = self.model.start_chat(response_validation=False)
                logger.info("Gemini model and chat session initialized successfully")
            except (ValueError, RuntimeError, GoogleAPICallError) as exc:
                logger.error("Failed to initialize Vertex AI or load Gemini model: %s", str(exc))
                raise RuntimeError(f"Initialization failed: {str(exc)}") from exc

    def _prepare_generation_config(self, temperature: Optional[float]) -> GenerationConfig:
        """
        Prepare the generation configuration.

        Args:
            temperature: The temperature to use for generation.

        Returns:
            A GenerationConfig object with the appropriate settings.
        """
        temp = temperature if temperature is not None else self.default_temperature
        config = {
            "temperature": temp,
            "top_p": self.generation_config.get("top_p", 0.95),
            "top_k": self.generation_config.get("top_k", 40),
        }

        if self.current_schema and self.pass_schema:
            config["candidate_count"] = 1
            config["stop_sequences"] = ["}"]
            config["response_mime_type"] = "application/json"
            config["response_schema"] = json.loads(self.current_schema)

        logger.debug("Generation config prepared: %s", config)
        return GenerationConfig(**config)

    async def generate_content(self, prompt: str, temperature: Optional[float] = None) -> str:
        """
        Generate content using the Vertex AI Gemini API.

        Args:
            prompt: The input prompt for content generation.
            temperature: The sampling temperature to use. If None, uses the default.

        Returns:
            The generated content as a string.

        Raises:
            ValueError: If the Gemini model has not been initialized.
            RuntimeError: If content generation fails after maximum retries.
        """
        if self.chat_session is None or not self.generation_config:
            logger.error("Gemini model not initialized. Call initialize() first.")
            raise ValueError("Gemini model not initialized. Call initialize() first.")

        async def retryable_generate() -> str:
            if self.chat_session is None:
                raise ValueError("Chat session is not initialized")

            generation_config = self._prepare_generation_config(temperature)
            try:
                logger.debug("Sending message with prompt: %s", prompt[:100] + "..." if len(prompt) > 100 else prompt)
                response = await self.chat_session.send_message_async(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=self.safety_settings,
                    stream=True
                )
            except (ResourceExhausted, ResponseValidationError, GoogleAPICallError) as exc:
                logger.error("Exception during send_message_async: %s", str(exc))
                raise

            try:
                generated_content, finish_reason = await self._process_response(response)
                logger.debug("Initial generation finished. Finish reason: %s", FINISH_REASON_MESSAGES.get(finish_reason, "Unknown"))
            except MaxTokensReachedError as exc:
                logger.info("Max tokens reached. Partial response: %s", str(exc)[:100] + "..." if len(str(exc)) > 100 else str(exc))
                generated_content = str(exc)
                if self.auto_continue:
                    logger.info("Auto-continue is enabled. Attempting auto-continuation...")
                    try:
                        generated_content = await self._auto_continue(generated_content)
                        logger.debug("Auto-continuation completed. Final content length: %d", len(generated_content))
                    except (AutoContinuationLimitExceeded, UnexpectedFinishReason) as auto_continue_error:
                        logger.error("Auto-continuation failed: %s", str(auto_continue_error))
                        raise RuntimeError(f"Auto-continuation failed: {str(auto_continue_error)}") from auto_continue_error
                else:
                    logger.info("Auto-continue is disabled. Returning partial response.")
                finish_reason = FinishReason.MAX_TOKENS

            if not generated_content.strip():
                logger.warning("Gemini model returned empty content")
                raise RuntimeError("Gemini model returned empty content")

            logger.info(
                "Generation completed. Finish reason: %s",
                FINISH_REASON_MESSAGES.get(finish_reason, "Unknown finish reason")
            )

            return generated_content

        generated_content = await self._retry_with_backoff(retryable_generate)

        # Update chat history after successful generation
        self.chat_history.append({"role": "user", "content": prompt})
        self.chat_history.append({"role": "model", "content": generated_content})
        logger.debug("Chat history updated. Current history length: %d", len(self.chat_history))

        return generated_content

    async def _auto_continue(self, content: str) -> str:
        """
        Automatically continue generating content if needed.

        Args:
            content: The initial generated content.

        Returns:
            The full generated content, including any auto-continuations.

        Raises:
            AutoContinuationLimitExceeded: If the maximum number of continuations is reached.
            UnexpectedFinishReason: If an unexpected finish reason is encountered.
        """
        content_chunks: List[str] = [content]
        continuations = 0

        logger.debug("Starting auto-continuation process. Initial content length: %d", len(content))

        while continuations < self.max_continues:
            continuations += 1
            logger.info("Auto-continuing content generation (attempt %d of %d)", continuations, self.max_continues)

            try:
                continuation, finish_reason = await self._generate_continuation_with_context(content_chunks)
                content_chunks.append(continuation)

                total_length = sum(len(chunk) for chunk in content_chunks)
                logger.info("Continuation %d completed. Current total length: %d", continuations, total_length)

                if finish_reason == FinishReason.STOP:
                    logger.info("Natural stop point reached. Stopping auto-continuation.")
                    break
                elif finish_reason != FinishReason.MAX_TOKENS:
                    raise UnexpectedFinishReason(f"Unexpected finish reason: {finish_reason}")

            except (ValueError, RuntimeError, GoogleAPICallError) as exc:
                error_message = f"Error during auto-continuation attempt {continuations}: {str(exc)}"
                logger.error(error_message)
                raise RuntimeError(error_message) from exc

        if continuations >= self.max_continues:
            raise AutoContinuationLimitExceeded(f"Reached maximum continuations ({self.max_continues})")

        full_content = "".join(content_chunks)
        logger.debug("Auto-continuation process completed. Final content length: %d", len(full_content))
        return full_content

    async def _generate_continuation_with_context(self, content_chunks: List[str]) -> Tuple[str, FinishReason]:
        """
        Generate a continuation of the content with context from previous chunks.

        Args:
            content_chunks: List of previous content chunks.

        Returns:
            A tuple containing the generated continuation and the finish reason.

        Raises:
            ValueError: If the chat session is not initialized.
            RuntimeError: If there's an unexpected error during continuation generation.
        """
        context = content_chunks[-1][-CONTINUATION_CONTEXT_LENGTH:]
        continuation_prompt = f"Continue from here: {context}"
        logger.debug("Continuation prompt: %s", continuation_prompt)
        return await self._generate_continuation(continuation_prompt)

    async def _generate_continuation(self, continuation_prompt: str) -> Tuple[str, FinishReason]:
        """
        Generate a continuation of the content.

        Args:
            continuation_prompt: The prompt to use for generating the continuation.

        Returns:
            A tuple containing the generated continuation and the finish reason.

        Raises:
            ValueError: If the chat session is not initialized.
            RuntimeError: If there's an unexpected error during continuation generation.
        """
        if self.chat_session is None:
            raise ValueError("Chat session is not initialized")

        logger.debug("Generating continuation with prompt: %s",
                     continuation_prompt[:100] + "..." if len(continuation_prompt) > 100 else continuation_prompt)

        try:
            response = await self.chat_session.send_message_async(
                continuation_prompt,
                generation_config=self._prepare_generation_config(None),
                safety_settings=self.safety_settings,
                stream=True
            )
        except (ResourceExhausted, ResponseValidationError, GoogleAPICallError) as exc:
            logger.error("Exception during continuation generation: %s", str(exc))
            raise
        except Exception as exc:
            logger.error("Unhandled exception during continuation generation: %s", str(exc))
            raise RuntimeError(f"Unexpected error: {str(exc)}") from exc

        continuation, finish_reason = await self._process_response(response)
        logger.debug("Continuation generated. Length: %d, Finish reason: %s",
                     len(continuation), FINISH_REASON_MESSAGES.get(finish_reason, "Unknown"))

        return continuation, finish_reason

    async def _process_response(self, response: GenerationResponse | AsyncIterable[GenerationResponse]) -> Tuple[str, FinishReason]:
        """
        Process the response from the Gemini model, handling both streaming and non-streaming responses.

        Args:
            response: The response from the Gemini model.

        Returns:
            A tuple containing the processed text content from the response and the finish reason.

        Raises:
            MaxTokensReachedError: If the response ends due to reaching the maximum token limit.
            ResponseValidationError: If the response fails validation checks.
        """
        full_response: List[str] = []
        finish_reason = FinishReason.FINISH_REASON_UNSPECIFIED
        chunk_count = 0
        total_length = 0

        try:
            if isinstance(response, GenerationResponse):
                logger.debug("Received non-streaming response")
                full_response.append(response.text)
                finish_reason = response.candidates[0].finish_reason
            else:
                logger.debug("Processing streaming response")
                async for chunk in response:
                    chunk_count += 1
                    total_length += len(chunk.text)
                    full_response.append(chunk.text)
                    if chunk.candidates:
                        finish_reason = chunk.candidates[0].finish_reason

                    logger.debug("Chunk %d content: %s", chunk_count, chunk.text[:100] + "..." if len(chunk.text) > 100 else chunk.text)

                    # Log every 10 chunks or when finish reason changes
                    if chunk_count % 10 == 0 or finish_reason != FinishReason.FINISH_REASON_UNSPECIFIED:
                        logger.debug("Processed %d chunks. Total length: %d. Current finish reason: %s",
                                     chunk_count, total_length, FINISH_REASON_MESSAGES.get(finish_reason, "Unknown"))

        except ResponseValidationError as exc:
            logger.error("Response validation error: %s", str(exc))
            safety_ratings = getattr(exc, 'safety_ratings', None)
            if safety_ratings:
                logger.debug("Safety ratings: %s", safety_ratings)
            raise

        except Exception as exc:
            logger.error("Unexpected exception during response processing: %s", str(exc))
            raise

        complete_response = "".join(full_response)
        human_readable_finish_reason = FINISH_REASON_MESSAGES.get(finish_reason, f"Unknown finish reason: {finish_reason}")
        logger.debug("Response processing completed. Total chunks: %d, Total length: %d", chunk_count, len(complete_response))
        logger.info("Final finish reason: %s", human_readable_finish_reason)

        if finish_reason == FinishReason.MAX_TOKENS:
            logger.warning("Maximum token limit reached during response processing.")
            raise MaxTokensReachedError(
                f"Maximum token limit reached during response processing. Partial response: {complete_response[:100]}...")

        return complete_response, finish_reason

    async def _retry_with_backoff(self, retry_func: Callable[[], Awaitable[str]]) -> str:
        """
        Helper method to handle retry logic with backoff.

        Args:
            retry_func: The asynchronous function to retry.

        Returns:
            The result of the function if successful.

        Raises:
            RuntimeError: If the maximum number of retries is exceeded.
        """
        retries = 0
        while retries < self.max_retries:
            try:
                return await retry_func()
            except ResourceExhausted:
                logger.warning("Resource exhausted. Retrying...")
            except ResponseValidationError as exc:
                logger.warning("Response validation error: %s", self._extract_safety_info(str(exc)))
            except GoogleAPICallError as exc:
                logger.warning("Google API call error: %s", str(exc))
            except RuntimeError as exc:
                logger.warning("Runtime error: %s", str(exc))

            retries += 1
            if retries < self.max_retries:
                logger.info(RETRY_MESSAGE, self.retry_delay)
                await asyncio.sleep(self.retry_delay)
            else:
                logger.error(MAX_RETRIES_MESSAGE)
                raise RuntimeError("Failed to generate content after retries.")

    def _extract_safety_info(self, error_message: str) -> str:
        """
        Extract relevant safety information from the error message.

        Args:
            error_message: The full error message from ResponseValidationError.

        Returns:
            A string containing relevant safety information.
        """
        safety_info = [
            line.strip() for line in error_message.split('\n')
            if any(key in line.lower() for key in ('category:', 'probability:', 'severity:'))
        ]
        logger.debug("Extracted safety information: %s", safety_info)
        return '; '.join(safety_info)

    def _extract_detailed_validation_info(self, response: Dict[Any, Any]) -> str:
        """
        Extract detailed validation information from the model response.

        Args:
            response: The JSON response from the model.

        Returns:
            A detailed message explaining the block reason and any safety ratings.
        """
        feedback = response.get("promptFeedback", {})
        block_reason = feedback.get("blockReason", "BLOCK_REASON_UNSPECIFIED")
        safety_ratings = feedback.get("safetyRatings", [])

        block_reason_message = {
            "BLOCK_REASON_UNSPECIFIED": "The block reason is unspecified.",
            "SAFETY": "The prompt was blocked due to safety reasons.",
            "OTHER": "The prompt was blocked due to unknown reasons.",
            "BLOCKLIST": "The prompt was blocked due to terminology blocklist violations.",
            "PROHIBITED_CONTENT": "The prompt was blocked due to prohibited content."
        }.get(block_reason, "Unknown block reason.")

        safety_info = [
            f"Category: {rating.get('category', 'Unknown category')}, "
            f"Probability: {rating.get('probability', 'Unknown probability')}, "
            f"Severity: {rating.get('severity', 'Unknown severity')}"
            for rating in safety_ratings
        ]

        safety_info_message = "; ".join(safety_info) if safety_info else "No safety ratings provided."
        logger.debug("Extracted validation information: %s", safety_info_message)
        return f"{block_reason_message} Safety Info: {safety_info_message}"

    def _handle_response_validation_error(self, response: Dict[Any, Any]) -> str:
        """
        Handle the response validation error by extracting detailed block reasons.

        Args:
            response: The JSON response from the model.

        Returns:
            A message detailing the block reason and safety concerns, if any.
        """
        try:
            return self._extract_detailed_validation_info(response)
        except KeyError as exc:
            logger.error("Key error while extracting validation information: %s", str(exc))
        except TypeError as exc:
            logger.error("Type error while processing response: %s", str(exc))
        except ValueError as exc:
            logger.error("Value error during response validation: %s", str(exc))
        return "An error occurred while extracting validation information."

    def set_schema(self, schema: Optional[str]) -> None:
        """
        Set the schema for content generation.

        Args:
            schema: The schema to be used for content generation, or None to clear the schema.

        Raises:
            ValueError: If an invalid JSON schema is provided.
        """
        if schema:
            try:
                json.loads(schema)  # Validate JSON
                self.current_schema = schema
                logger.debug("Schema set successfully")
            except json.JSONDecodeError as exc:
                logger.error("Invalid JSON schema provided: %s", str(exc))
                raise ValueError("Invalid JSON schema provided") from exc
        else:
            self.current_schema = None
            logger.debug("Schema cleared")
