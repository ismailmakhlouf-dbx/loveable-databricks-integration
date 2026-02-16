"""Tests for TypeConverter."""

import pytest
from src.transformer.type_converter import TypeConverter


def test_convert_typescript_primitives():
    """Test converting TypeScript primitive types."""
    converter = TypeConverter()

    assert converter.convert_typescript_type("string") == "str"
    assert converter.convert_typescript_type("number") == "int | float"
    assert converter.convert_typescript_type("boolean") == "bool"


def test_convert_typescript_arrays():
    """Test converting TypeScript array types."""
    converter = TypeConverter()

    assert converter.convert_typescript_type("string[]") == "list[str]"
    assert converter.convert_typescript_type("Array<number>") == "list[int | float]"


def test_convert_sql_type():
    """Test converting SQL types."""
    converter = TypeConverter()

    python_type, options = converter.convert_sql_type("VARCHAR(255)")
    assert python_type == "str"
    assert options["max_length"] == 255
