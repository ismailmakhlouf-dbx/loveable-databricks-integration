"""
Type Converter for TypeScript to Python type mapping.

Maps TypeScript primitives and complex types to Python type hints.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class TypeConverter:
    """Converts TypeScript types to Python type hints."""

    # Basic type mappings
    TYPE_MAPPING = {
        "string": "str",
        "number": "int | float",
        "boolean": "bool",
        "any": "Any",
        "void": "None",
        "null": "None",
        "undefined": "None",
        "Date": "datetime",
        "Promise": "Awaitable",
        "object": "dict[str, Any]",
    }

    # SQL type mappings for SQLModel
    SQL_TYPE_MAPPING = {
        "UUID": "UUID",
        "TEXT": "str",
        "VARCHAR": "str",
        "CHAR": "str",
        "INTEGER": "int",
        "INT": "int",
        "BIGINT": "int",
        "SMALLINT": "int",
        "SERIAL": "int",
        "BIGSERIAL": "int",
        "BOOLEAN": "bool",
        "BOOL": "bool",
        "TIMESTAMP": "datetime",
        "TIMESTAMPTZ": "datetime",
        "DATE": "date",
        "TIME": "time",
        "FLOAT": "float",
        "DOUBLE": "float",
        "REAL": "float",
        "NUMERIC": "Decimal",
        "DECIMAL": "Decimal",
        "JSON": "dict[str, Any]",
        "JSONB": "dict[str, Any]",
        "ARRAY": "list",
        "BYTEA": "bytes",
    }

    def __init__(self) -> None:
        """Initialize type converter."""
        self.custom_types: dict[str, str] = {}

    def convert_typescript_type(self, ts_type: str) -> str:
        """
        Convert TypeScript type to Python type hint.

        Args:
            ts_type: TypeScript type string

        Returns:
            Python type hint string
        """
        # Clean up the type
        ts_type = ts_type.strip()

        # Handle basic types
        if ts_type in self.TYPE_MAPPING:
            return self.TYPE_MAPPING[ts_type]

        # Handle array types: T[] -> list[T]
        if ts_type.endswith("[]"):
            inner_type = ts_type[:-2]
            converted_inner = self.convert_typescript_type(inner_type)
            return f"list[{converted_inner}]"

        # Handle Array<T> -> list[T]
        array_match = re.match(r"Array<(.+)>", ts_type)
        if array_match:
            inner_type = array_match.group(1)
            converted_inner = self.convert_typescript_type(inner_type)
            return f"list[{converted_inner}]"

        # Handle Promise<T> -> Awaitable[T]
        promise_match = re.match(r"Promise<(.+)>", ts_type)
        if promise_match:
            inner_type = promise_match.group(1)
            converted_inner = self.convert_typescript_type(inner_type)
            return f"Awaitable[{converted_inner}]"

        # Handle Record<K, V> -> dict[K, V]
        record_match = re.match(r"Record<(.+),\s*(.+)>", ts_type)
        if record_match:
            key_type = record_match.group(1)
            value_type = record_match.group(2)
            converted_key = self.convert_typescript_type(key_type)
            converted_value = self.convert_typescript_type(value_type)
            return f"dict[{converted_key}, {converted_value}]"

        # Handle union types: A | B -> A | B
        if "|" in ts_type:
            types = [t.strip() for t in ts_type.split("|")]
            converted = [self.convert_typescript_type(t) for t in types]
            return " | ".join(converted)

        # Handle optional types: T? -> T | None
        if ts_type.endswith("?"):
            inner_type = ts_type[:-1]
            converted_inner = self.convert_typescript_type(inner_type)
            return f"{converted_inner} | None"

        # If it's a custom type, return as-is (assuming it's a class/model name)
        return ts_type

    def convert_sql_type(self, sql_type: str) -> tuple[str, dict[str, Any]]:
        """
        Convert SQL type to Python type with SQLModel field options.

        Args:
            sql_type: SQL type string (e.g., "VARCHAR(255)", "TIMESTAMP")

        Returns:
            Tuple of (python_type, field_options)
        """
        # Extract base type and parameters
        match = re.match(r"(\w+)(?:\(([^)]+)\))?", sql_type.upper())
        if not match:
            return "str", {}

        base_type = match.group(1)
        params = match.group(2)

        # Get Python type
        python_type = self.SQL_TYPE_MAPPING.get(base_type, "str")

        # Field options for SQLModel
        field_options: dict[str, Any] = {}

        # Handle VARCHAR/CHAR length
        if base_type in ("VARCHAR", "CHAR") and params:
            try:
                max_length = int(params)
                field_options["max_length"] = max_length
            except ValueError:
                pass

        # Handle NUMERIC/DECIMAL precision
        if base_type in ("NUMERIC", "DECIMAL") and params:
            # NUMERIC(10,2) -> precision=10, scale=2
            precision_parts = params.split(",")
            if len(precision_parts) == 2:
                field_options["max_digits"] = int(precision_parts[0].strip())
                field_options["decimal_places"] = int(precision_parts[1].strip())

        return python_type, field_options

    def typescript_interface_to_pydantic(
        self, interface_code: str, class_name: str | None = None
    ) -> str:
        """
        Convert TypeScript interface to Pydantic model.

        Args:
            interface_code: TypeScript interface code
            class_name: Optional class name override

        Returns:
            Python Pydantic model code
        """
        lines = interface_code.strip().split("\n")

        # Extract interface name if not provided
        if class_name is None:
            for line in lines:
                if "interface" in line:
                    match = re.search(r"interface\s+(\w+)", line)
                    if match:
                        class_name = match.group(1)
                        break

        if class_name is None:
            class_name = "Model"

        # Generate Pydantic model
        model_lines = [
            f"class {class_name}(BaseModel):",
            '    """Auto-generated Pydantic model."""',
            "",
        ]

        # Parse fields
        for line in lines:
            line = line.strip()
            if not line or line.startswith("//") or line.startswith("/*"):
                continue

            # Match field: name: type or name?: type
            field_match = re.match(r"(\w+)(\?)?:\s*(.+?)[;,]?$", line)
            if field_match:
                field_name = field_match.group(1)
                is_optional = field_match.group(2) == "?"
                field_type = field_match.group(3)

                # Convert type
                python_type = self.convert_typescript_type(field_type)

                # Add optional
                if is_optional:
                    python_type = f"{python_type} | None"
                    model_lines.append(f"    {field_name}: {python_type} = None")
                else:
                    model_lines.append(f"    {field_name}: {python_type}")

        return "\n".join(model_lines)

    def sql_table_to_sqlmodel(
        self, table_name: str, columns: list[dict[str, Any]]
    ) -> str:
        """
        Convert SQL table definition to SQLModel class.

        Args:
            table_name: Name of the table
            columns: List of column definitions

        Returns:
            Python SQLModel class code
        """
        # Generate class name (PascalCase)
        class_name = "".join(word.capitalize() for word in table_name.split("_"))

        model_lines = [
            f"class {class_name}(SQLModel, table=True):",
            f'    """SQLModel for {table_name} table."""',
            f'    __tablename__ = "{table_name}"',
            "",
        ]

        # Generate fields
        for col in columns:
            field_name = col["name"]
            col_type = col["type"]

            # Convert SQL type
            python_type, field_options = self.convert_sql_type(col_type)

            # Build Field() options
            field_args = []

            if col.get("primary_key"):
                field_args.append("primary_key=True")
            if col.get("unique"):
                field_args.append("unique=True")
            if col.get("not_null") and not col.get("primary_key"):
                # Primary keys are already not null
                pass
            if col.get("default"):
                default_value = col["default"]
                if default_value == "gen_random_uuid()":
                    field_args.append("default_factory=uuid4")
                    python_type = "UUID"
                elif default_value == "NOW()":
                    field_args.append("default_factory=datetime.utcnow")
                elif default_value.isdigit():
                    field_args.append(f"default={default_value}")
                else:
                    field_args.append(f"default={repr(default_value)}")

            # Add field options
            for key, value in field_options.items():
                field_args.append(f"{key}={value}")

            # Optional fields
            if not col.get("not_null") and not col.get("primary_key"):
                python_type = f"{python_type} | None"
                if "default" not in " ".join(field_args):
                    field_args.append("default=None")

            # Generate field line
            if field_args:
                field_def = f"Field({', '.join(field_args)})"
                model_lines.append(f"    {field_name}: {python_type} = {field_def}")
            else:
                model_lines.append(f"    {field_name}: {python_type}")

        return "\n".join(model_lines)

    def add_custom_type(self, ts_type: str, py_type: str) -> None:
        """
        Register a custom type mapping.

        Args:
            ts_type: TypeScript type name
            py_type: Python type name
        """
        self.custom_types[ts_type] = py_type
        logger.debug(f"Registered custom type mapping: {ts_type} -> {py_type}")
