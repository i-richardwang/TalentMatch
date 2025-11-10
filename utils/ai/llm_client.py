"""
LLM client module

Provides unified management and usage interface for language models, 
supporting multiple providers.
"""

import os
from typing import Any, List, Optional, Type

from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..core.logging import get_project_logger
from ..core.exceptions import LLMError, ConfigurationError

# Configure logging
logger = get_project_logger(__name__)


def init_language_model(temperature: float = 0.0, model_name: Optional[str] = None, **kwargs: Any) -> ChatOpenAI:
    """
    Initialize language model.

    Args:
        temperature: Model output temperature, controls randomness. Defaults to 0.0.
        model_name: Model name
        **kwargs: Additional optional parameters passed to model initialization.

    Returns:
        Initialized language model instance.

    Raises:
        LLMError: Raised when invalid parameters or missing required configuration.
    """
    try:
        model_name = model_name or os.getenv("LLM_MODEL", "gpt-4")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_api_base = os.getenv("OPENAI_API_BASE")

        if not openai_api_key or not openai_api_base:
            raise LLMError(
                "Cannot find API key or base URL. Please check environment variable settings.",
                error_code="MISSING_API_CONFIG"
            )

        model_params = {
            "model": model_name,
            "openai_api_key": openai_api_key,
            "openai_api_base": openai_api_base,
            "temperature": temperature,
            "max_tokens": kwargs.get("max_tokens", 1024),
            **{k: v for k, v in kwargs.items() if k != "max_tokens"}
        }

        return ChatOpenAI(**model_params)
        
    except Exception as e:
        if isinstance(e, LLMError):
            raise
        logger.error(f"Failed to initialize LLM: {e}")
        raise LLMError(f"Failed to initialize LLM: {e}", error_code="LLM_INIT_ERROR")


class LanguageModelChain:
    """
    Language model chain for processing input and generating structured output.

    Attributes:
        model_cls: Pydantic model class defining the output structure.
        parser: JSON output parser.
        prompt_template: Chat prompt template.
        chain: Complete processing chain.
    """

    def __init__(
        self, model_cls: Type[BaseModel], sys_msg: str, user_msg: str, model: Any
    ):
        """
        Initialize LanguageModelChain instance.

        Args:
            model_cls: Pydantic model class defining the output structure.
            sys_msg: System message.
            user_msg: User message.
            model: Language model instance.

        Raises:
            LLMError: Raised when invalid parameters are provided.
        """
        # Runtime parameter type validation
        try:
            if not (isinstance(model_cls, type) and issubclass(model_cls, BaseModel)):
                raise LLMError("model_cls must be a subclass of Pydantic BaseModel", error_code="INVALID_MODEL_CLASS")
        except (TypeError, AttributeError):
            raise LLMError("model_cls must be a valid BaseModel class", error_code="INVALID_MODEL_CLASS")
        
        # String parameter validation
        if not (isinstance(sys_msg, str) and isinstance(user_msg, str)):
            raise LLMError("sys_msg and user_msg must be strings", error_code="INVALID_MESSAGE_TYPE")
        
        # Callable object validation
        if not callable(model):
            raise LLMError("model must be callable", error_code="INVALID_MODEL_OBJECT")

        self.model_cls = model_cls
        self.parser = JsonOutputParser(pydantic_object=model_cls)

        format_instructions = """
Output your answer as a JSON object that conforms to the following schema:
```json
{schema}
```

Important instructions:
1. Ensure your JSON is valid and properly formatted.
2. Do not include the schema definition in your answer.
3. Only output the data instance that matches the schema.
4. Do not include any explanations or comments within the JSON output.
        """

        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", sys_msg + format_instructions),
                ("human", user_msg),
            ]
        ).partial(schema=model_cls.model_json_schema())

        self.chain = self.prompt_template | model | self.parser

    def __call__(self) -> Any:
        """
        Invoke the processing chain.

        Returns:
            Output from the processing chain.
        """
        return self.chain
