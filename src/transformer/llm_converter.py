"""
LLM API Converter.

Converts external LLM API calls (OpenAI, Anthropic) to Databricks Foundation Model Serving.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class LLMConverter:
    """Converts external LLM APIs to Databricks Foundation Model Serving."""

    # Model mapping with auto-selection
    MODEL_MAPPING = {
        # OpenAI models
        "gpt-4": "databricks-dbrx-instruct",
        "gpt-4-turbo": "databricks-dbrx-instruct",
        "gpt-4-turbo-preview": "databricks-dbrx-instruct",
        "gpt-4-32k": "databricks-dbrx-instruct",
        "gpt-3.5-turbo": "databricks-meta-llama-3-70b-instruct",
        "gpt-3.5-turbo-16k": "databricks-meta-llama-3-70b-instruct",
        "gpt-3.5": "databricks-meta-llama-3-8b-instruct",
        # Anthropic models
        "claude-3-5-sonnet": "databricks-dbrx-instruct",
        "claude-3-opus": "databricks-dbrx-instruct",
        "claude-3-sonnet": "databricks-meta-llama-3-70b-instruct",
        "claude-3-haiku": "databricks-meta-llama-3-8b-instruct",
        "claude-2.1": "databricks-dbrx-instruct",
        "claude-2": "databricks-dbrx-instruct",
        # Fallback
        "default": "databricks-dbrx-instruct",
    }

    def __init__(self):
        """Initialize LLM converter."""
        self.detected_models: list[dict[str, Any]] = []

    def select_databricks_model(self, external_model: str) -> str:
        """
        Auto-select the closest Databricks model.

        Args:
            external_model: External model name

        Returns:
            Databricks model endpoint name
        """
        # Normalize model name
        model_lower = external_model.lower()

        # Direct mapping
        if model_lower in self.MODEL_MAPPING:
            return self.MODEL_MAPPING[model_lower]

        # Fuzzy matching based on model characteristics
        if any(x in model_lower for x in ["gpt-4", "opus", "large", "advanced"]):
            return "databricks-dbrx-instruct"
        elif any(x in model_lower for x in ["gpt-3.5", "sonnet", "medium"]):
            return "databricks-meta-llama-3-70b-instruct"
        elif any(x in model_lower for x in ["haiku", "small", "fast"]):
            return "databricks-meta-llama-3-8b-instruct"

        # Default fallback
        logger.warning(f"Unknown model '{external_model}', using default")
        return self.MODEL_MAPPING["default"]

    def convert_openai_to_databricks(self, code: str) -> str:
        """
        Convert OpenAI API calls to Databricks Foundation Model Serving.

        Args:
            code: TypeScript/JavaScript code with OpenAI calls

        Returns:
            Python code with Databricks API calls
        """
        # Extract model name
        model_match = re.search(r'model:\s*["\']([^"\']+)["\']', code)
        external_model = model_match.group(1) if model_match else "gpt-4"

        # Select Databricks model
        databricks_model = self.select_databricks_model(external_model)

        # Track conversion
        self.detected_models.append(
            {
                "original_provider": "OpenAI",
                "original_model": external_model,
                "databricks_model": databricks_model,
            }
        )

        # Generate Python code
        python_code = f'''
from databricks.sdk import WorkspaceClient

workspace = WorkspaceClient()

# Convert OpenAI call to Databricks Foundation Model Serving
response = workspace.serving_endpoints.query(
    name="{databricks_model}",
    inputs={{
        "messages": messages,  # Use same message format
        "temperature": temperature or 0.7,
        "max_tokens": max_tokens or 1000,
    }}
)

# Extract response text
result = response.predictions[0]["candidates"][0]["text"]
'''
        return python_code.strip()

    def convert_anthropic_to_databricks(self, code: str) -> str:
        """
        Convert Anthropic API calls to Databricks Foundation Model Serving.

        Args:
            code: TypeScript/JavaScript code with Anthropic calls

        Returns:
            Python code with Databricks API calls
        """
        # Extract model name
        model_match = re.search(r'model:\s*["\']([^"\']+)["\']', code)
        external_model = model_match.group(1) if model_match else "claude-3-sonnet"

        # Select Databricks model
        databricks_model = self.select_databricks_model(external_model)

        # Track conversion
        self.detected_models.append(
            {
                "original_provider": "Anthropic",
                "original_model": external_model,
                "databricks_model": databricks_model,
            }
        )

        # Generate Python code
        python_code = f'''
from databricks.sdk import WorkspaceClient

workspace = WorkspaceClient()

# Convert Anthropic call to Databricks Foundation Model Serving
response = workspace.serving_endpoints.query(
    name="{databricks_model}",
    inputs={{
        "messages": messages,  # Use same message format
        "temperature": temperature or 0.7,
        "max_tokens": max_tokens or 1000,
    }}
)

# Extract response text
result = response.predictions[0]["candidates"][0]["text"]
'''
        return python_code.strip()

    def detect_and_convert_llm_calls(self, code: str) -> tuple[str, list[dict[str, Any]]]:
        """
        Detect and convert all LLM API calls in code.

        Args:
            code: Original code with LLM API calls

        Returns:
            Tuple of (converted_code, detected_models)
        """
        converted_code = code
        conversions = []

        # OpenAI detection patterns
        openai_patterns = [
            (
                r"openai\.chat\.completions\.create\([^)]+\)",
                self.convert_openai_to_databricks,
            ),
            (r"openai\.completions\.create\([^)]+\)", self.convert_openai_to_databricks),
        ]

        # Anthropic detection patterns
        anthropic_patterns = [
            (r"anthropic\.messages\.create\([^)]+\)", self.convert_anthropic_to_databricks),
        ]

        # Convert OpenAI calls
        for pattern, converter in openai_patterns:
            matches = re.finditer(pattern, code, re.DOTALL)
            for match in matches:
                original_call = match.group(0)
                converted_call = converter(original_call)
                converted_code = converted_code.replace(original_call, converted_call)
                conversions.append(
                    {
                        "type": "OpenAI",
                        "original": original_call[:100],
                        "converted": True,
                    }
                )

        # Convert Anthropic calls
        for pattern, converter in anthropic_patterns:
            matches = re.finditer(pattern, code, re.DOTALL)
            for match in matches:
                original_call = match.group(0)
                converted_call = converter(original_call)
                converted_code = converted_code.replace(original_call, converted_call)
                conversions.append(
                    {
                        "type": "Anthropic",
                        "original": original_call[:100],
                        "converted": True,
                    }
                )

        return converted_code, conversions

    def generate_llm_helper(self) -> str:
        """
        Generate helper function for LLM calls.

        Returns:
            Python helper function code
        """
        return '''
from databricks.sdk import WorkspaceClient
from typing import Any

def call_databricks_llm(
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> str:
    """
    Helper function to call Databricks Foundation Model Serving.

    Args:
        model: Databricks model endpoint name
        messages: List of messages in OpenAI format
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        Generated text response
    """
    workspace = WorkspaceClient()

    response = workspace.serving_endpoints.query(
        name=model,
        inputs={
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    )

    # Extract response text
    return response.predictions[0]["candidates"][0]["text"]
'''

    def get_conversion_summary(self) -> dict[str, Any]:
        """
        Get summary of all LLM conversions.

        Returns:
            Conversion summary dictionary
        """
        return {
            "total_conversions": len(self.detected_models),
            "models": self.detected_models,
            "databricks_endpoints_used": list(
                set(m["databricks_model"] for m in self.detected_models)
            ),
        }
