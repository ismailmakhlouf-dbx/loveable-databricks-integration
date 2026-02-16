"""
Model Generator.

Generates SQLModel and Pydantic models from database schemas.
"""

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from ..transformer.type_converter import TypeConverter

logger = logging.getLogger(__name__)


class ModelGenerator:
    """Generates SQLModel and Pydantic models."""

    def __init__(
        self,
        database_metadata: dict[str, Any],
        type_converter: TypeConverter,
        output_dir: Path,
    ):
        """
        Initialize model generator.

        Args:
            database_metadata: Database analysis metadata
            type_converter: Type converter instance
            output_dir: Output directory for generated code
        """
        self.database_metadata = database_metadata
        self.type_converter = type_converter
        self.output_dir = output_dir

        # Load templates
        template_dir = Path(__file__).parent.parent.parent / "templates"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> dict[str, str]:
        """
        Generate all models.

        Returns:
            Dictionary mapping file paths to generated code
        """
        logger.info("Generating SQLModel and Pydantic models")

        generated_files: dict[str, str] = {}

        tables = self.database_metadata.get("tables", {})

        if not tables:
            logger.warning("No tables found in database metadata")
            return generated_files

        # Generate models __init__.py
        model_imports = []

        for table_name, table_schema in tables.items():
            # Generate SQLModel
            sqlmodel_code = self._generate_sqlmodel(table_name, table_schema)
            model_name = self._table_name_to_model_name(table_name)
            generated_files[f"app/models/{table_name}.py"] = sqlmodel_code
            model_imports.append(f"from .{table_name} import {model_name}")

            # Generate Pydantic schemas
            pydantic_code = self._generate_pydantic_schemas(
                table_name, table_schema
            )
            generated_files[f"app/schemas/{table_name}.py"] = pydantic_code

        # Generate __init__.py for models
        generated_files["app/models/__init__.py"] = "\n".join(model_imports) + "\n"
        generated_files["app/schemas/__init__.py"] = ""

        logger.info(f"Generated {len(generated_files)} model files")
        return generated_files

    def _generate_sqlmodel(
        self, table_name: str, table_schema: dict[str, Any]
    ) -> str:
        """Generate SQLModel class from table schema."""
        template = self.env.get_template("models/sqlmodel.py.jinja2")

        model_name = self._table_name_to_model_name(table_name)
        columns = table_schema.get("columns", [])

        # Convert columns to fields
        fields = []
        has_relationships = False
        has_list_fields = False
        has_decimal = False

        for col in columns:
            field_info = self._convert_column_to_field(col)
            fields.append(field_info)

            if "Decimal" in field_info["type"]:
                has_decimal = True
            if "List[" in field_info["type"]:
                has_list_fields = True

        # TODO: Extract relationships from foreign keys
        relationships: list[dict[str, Any]] = []

        return template.render(
            model_name=model_name,
            table_name=table_name,
            model_description=f"SQLModel for {table_name} table",
            fields=fields,
            relationships=relationships,
            has_relationships=has_relationships,
            has_list_fields=has_list_fields,
            has_decimal=has_decimal,
        )

    def _generate_pydantic_schemas(
        self, table_name: str, table_schema: dict[str, Any]
    ) -> str:
        """Generate Pydantic schemas for API."""
        template = self.env.get_template("models/pydantic.py.jinja2")

        model_name = self._table_name_to_model_name(table_name)
        columns = table_schema.get("columns", [])

        # Separate fields into categories
        base_fields = []
        read_only_fields = []
        update_fields = []
        has_list_fields = False
        has_decimal = False
        has_validators = False

        for col in columns:
            field_info = self._convert_column_to_field(col)

            # Read-only fields (auto-generated)
            if col.get("primary_key") or col.get("default") in [
                "gen_random_uuid()",
                "NOW()",
            ]:
                read_only_fields.append(field_info)
            else:
                base_fields.append(field_info)
                update_fields.append(field_info)

            if "Decimal" in field_info["type"]:
                has_decimal = True
            if "List[" in field_info["type"]:
                has_list_fields = True

        return template.render(
            model_name=model_name,
            base_fields=base_fields,
            read_only_fields=read_only_fields,
            update_fields=update_fields,
            has_list_fields=has_list_fields,
            has_decimal=has_decimal,
            has_validators=has_validators,
        )

    def _convert_column_to_field(self, col: dict[str, Any]) -> dict[str, Any]:
        """Convert database column to model field."""
        field_name = col["name"]
        col_type = col["type"]

        # Convert SQL type to Python type
        python_type, field_options = self.type_converter.convert_sql_type(col_type)

        # Build Field() arguments
        field_args = []

        if col.get("primary_key"):
            field_args.append("primary_key=True")

        if col.get("unique"):
            field_args.append("unique=True")

        if col.get("default"):
            default_value = col["default"]
            if default_value == "gen_random_uuid()":
                field_args.append("default_factory=uuid4")
                python_type = "UUID"
            elif default_value == "NOW()":
                field_args.append("default_factory=datetime.utcnow")
            elif default_value.replace(".", "").replace("-", "").isdigit():
                field_args.append(f"default={default_value}")
            else:
                field_args.append(f'default="{default_value}"')

        # Add field options from type converter
        for key, value in field_options.items():
            field_args.append(f"{key}={value}")

        # Handle nullable
        if not col.get("not_null") and not col.get("primary_key"):
            python_type = f"Optional[{python_type}]"
            if "default" not in " ".join(field_args):
                field_args.append("default=None")

        return {
            "name": field_name,
            "type": python_type,
            "field_args": ", ".join(field_args) if field_args else None,
            "default": None,
        }

    def _table_name_to_model_name(self, table_name: str) -> str:
        """Convert table name to model name (PascalCase)."""
        return "".join(word.capitalize() for word in table_name.split("_"))

    def write_files(self, generated_files: dict[str, str]) -> None:
        """
        Write generated files to disk.

        Args:
            generated_files: Dictionary mapping file paths to content
        """
        for file_path, content in generated_files.items():
            full_path = self.output_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "w") as f:
                f.write(content)

            logger.info(f"Wrote {file_path}")
