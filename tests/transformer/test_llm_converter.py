"""Tests for LLMConverter."""

import pytest
from src.transformer.llm_converter import LLMConverter


def test_select_databricks_model():
    """Test model selection."""
    converter = LLMConverter()

    assert converter.select_databricks_model("gpt-4") == "databricks-dbrx-instruct"
    assert converter.select_databricks_model("gpt-3.5-turbo") == "databricks-meta-llama-3-70b-instruct"
    assert converter.select_databricks_model("claude-3-haiku") == "databricks-meta-llama-3-8b-instruct"
