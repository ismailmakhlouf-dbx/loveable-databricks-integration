"""
FastAPI Generator.

Converts Supabase Edge Functions to FastAPI endpoints.
"""

import logging
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from ..transformer.type_converter import TypeConverter
from ..transformer.llm_converter import LLMConverter

logger = logging.getLogger(__name__)


class EndpointInfo:
    """Represents a FastAPI endpoint."""

    def __init__(self, function_name: str):
        self.function_name = function_name
        self.http_method = "POST"
        self.path = f"/{function_name}"
        self.parameters: list[dict[str, Any]] = []
        self.return_type = "dict[str, Any]"
        self.description = f"{function_name} endpoint"
        self.requires_session = False
        self.requires_auth = False
        self.body: str | None = None
        self.original_function = function_name


class FastAPIGenerator:
    """Generates FastAPI application from Edge Functions."""

    def __init__(
        self,
        backend_metadata: dict[str, Any],
        type_converter: TypeConverter,
        llm_converter: LLMConverter,
        output_dir: Path,
    ):
        """
        Initialize FastAPI generator.

        Args:
            backend_metadata: Backend analysis metadata
            type_converter: Type converter instance
            llm_converter: LLM converter instance
            output_dir: Output directory for generated code
        """
        self.backend_metadata = backend_metadata
        self.type_converter = type_converter
        self.llm_converter = llm_converter
        self.output_dir = output_dir

        # Load templates
        template_dir = Path(__file__).parent.parent.parent / "templates"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self, project_name: str, project_description: str = "") -> dict[str, str]:
        """
        Generate complete FastAPI application.

        Args:
            project_name: Name of the project
            project_description: Project description

        Returns:
            Dictionary mapping file paths to generated code
        """
        logger.info(f"Generating FastAPI application for {project_name}")

        generated_files = {}

        # Generate main app
        generated_files["app/main.py"] = self._generate_main_app(
            project_name, project_description
        )

        # Generate routers for each function
        functions = self.backend_metadata.get("functions", {})
        if functions:
            generated_files["app/routers/__init__.py"] = self._generate_routers_init(
                functions
            )

            for func_name, func_info in functions.items():
                router_code = self._generate_router(func_name, func_info)
                generated_files[f"app/routers/{func_name}.py"] = router_code

        # Generate dependencies
        generated_files["app/dependencies.py"] = self._generate_dependencies(
            project_name
        )

        # Generate database module
        generated_files["app/database.py"] = self._generate_database_module(
            project_name
        )

        # Generate __init__.py files
        generated_files["app/__init__.py"] = '"""Application package."""\n'

        logger.info(f"Generated {len(generated_files)} files")
        return generated_files

    def _generate_main_app(
        self, project_name: str, project_description: str
    ) -> str:
        """Generate main FastAPI app."""
        template = self.env.get_template("fastapi/app.py.jinja2")

        functions = self.backend_metadata.get("functions", {})
        routers = list(functions.keys())

        return template.render(
            project_name=project_name,
            project_description=project_description or f"{project_name} API",
            routers=routers,
        )

    def _generate_router(self, func_name: str, func_info: dict[str, Any]) -> str:
        """Generate router for a function."""
        template = self.env.get_template("fastapi/router.py.jinja2")

        # Convert function info to endpoint
        endpoint = self._convert_function_to_endpoint(func_name, func_info)

        # Determine required models
        models = self._extract_models_for_function(func_info)

        # Determine required dependencies
        dependencies = []
        if endpoint.requires_auth:
            dependencies.append("get_current_user_id")
        if endpoint.requires_session:
            dependencies.append("get_session")

        return template.render(
            router_name=func_name,
            endpoints=[endpoint],
            models=models,
            dependencies=dependencies,
        )

    def _generate_routers_init(self, functions: dict[str, Any]) -> str:
        """Generate routers __init__.py."""
        imports = [f"from . import {name}" for name in functions.keys()]
        return "\n".join(imports) + "\n"

    def _generate_dependencies(self, project_name: str) -> str:
        """Generate FastAPI dependencies."""
        template = self.env.get_template("fastapi/dependencies.py.jinja2")
        return template.render(project_name=project_name)

    def _generate_database_module(self, project_name: str) -> str:
        """Generate database module."""
        template = self.env.get_template("fastapi/database.py.jinja2")

        # Generate database URL from catalog/schema
        database_url = "postgresql://user:password@localhost:5432/dbname"  # Placeholder

        return template.render(
            project_name=project_name,
            database_url=database_url,
        )

    def _convert_function_to_endpoint(
        self, func_name: str, func_info: dict[str, Any]
    ) -> EndpointInfo:
        """Convert Edge Function info to FastAPI endpoint."""
        endpoint = EndpointInfo(func_name)

        # Set HTTP methods
        http_methods = func_info.get("http_methods", ["POST"])
        endpoint.http_method = http_methods[0]  # Use first method

        # Check if auth required
        endpoint.requires_auth = func_info.get("auth_required", False)

        # Check if database operations exist
        db_operations = func_info.get("database_operations", [])
        endpoint.requires_session = len(db_operations) > 0

        # Generate endpoint body if we have database operations
        if db_operations:
            endpoint.body = self._generate_endpoint_body(func_info)

        # Convert LLM APIs if present
        llm_apis = func_info.get("llm_apis", [])
        if llm_apis:
            # Add LLM conversion logic to body
            llm_body = self._generate_llm_endpoint_body(llm_apis)
            if endpoint.body:
                endpoint.body += "\n\n" + llm_body
            else:
                endpoint.body = llm_body

        return endpoint

    def _generate_endpoint_body(self, func_info: dict[str, Any]) -> str:
        """Generate endpoint body code for database operations."""
        db_operations = func_info.get("database_operations", [])

        body_lines = []
        body_lines.append("try:")

        for op in db_operations:
            op_type = op.get("type", "SELECT")
            table = op.get("table", "table")

            if op_type == "SELECT":
                body_lines.append(f"    # Query {table}")
                body_lines.append(
                    f"    statement = select({table.capitalize()})"
                )
                body_lines.append(
                    f"    results = session.exec(statement).all()"
                )
                body_lines.append(
                    f"    return {{'data': [r.dict() for r in results]}}"
                )
            elif op_type == "INSERT":
                body_lines.append(f"    # Insert into {table}")
                body_lines.append(
                    f"    new_item = {table.capitalize()}(**data.dict())"
                )
                body_lines.append(f"    session.add(new_item)")
                body_lines.append(f"    session.commit()")
                body_lines.append(f"    session.refresh(new_item)")
                body_lines.append(f"    return {{'data': new_item.dict()}}")

        body_lines.append("except Exception as e:")
        body_lines.append(
            "    raise HTTPException(status_code=500, detail=str(e))"
        )

        return "\n".join(body_lines)

    def _generate_llm_endpoint_body(self, llm_apis: list[dict[str, Any]]) -> str:
        """Generate endpoint body for LLM API calls."""
        body_lines = []
        body_lines.append("# LLM API integration")
        body_lines.append("from databricks.sdk import WorkspaceClient")
        body_lines.append("")
        body_lines.append("workspace = WorkspaceClient()")

        for llm_api in llm_apis:
            provider = llm_api.get("provider", "Unknown")
            models = llm_api.get("models", [])

            if provider in ["OpenAI", "Anthropic"]:
                # Use first model or default
                external_model = models[0] if models else "gpt-4"
                databricks_model = self.llm_converter.select_databricks_model(
                    external_model
                )

                body_lines.append("")
                body_lines.append(f"# Convert {provider} call to Databricks")
                body_lines.append(
                    f'response = workspace.serving_endpoints.query('
                )
                body_lines.append(f'    name="{databricks_model}",')
                body_lines.append(f"    inputs={{")
                body_lines.append(f'        "messages": messages,')
                body_lines.append(f'        "temperature": 0.7,')
                body_lines.append(f'        "max_tokens": 1000,')
                body_lines.append(f"    }}")
                body_lines.append(f")")
                body_lines.append(
                    'result = response.predictions[0]["candidates"][0]["text"]'
                )

        return "\n".join(body_lines)

    def _extract_models_for_function(
        self, func_info: dict[str, Any]
    ) -> list[str]:
        """Extract model names referenced by function."""
        models = []

        db_operations = func_info.get("database_operations", [])
        for op in db_operations:
            table = op.get("table", "")
            if table:
                # Convert table name to model name (PascalCase)
                model_name = "".join(
                    word.capitalize() for word in table.split("_")
                )
                if model_name not in models:
                    models.append(model_name)

        return models

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
