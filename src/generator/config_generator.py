"""
Configuration Generator.

Generates Databricks configuration files (app.yaml, databricks.yml, .env).
"""

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class ConfigGenerator:
    """Generates Databricks configuration files."""

    def __init__(
        self,
        project_metadata: dict[str, Any],
        output_dir: Path,
    ):
        """
        Initialize config generator.

        Args:
            project_metadata: Complete project metadata
            output_dir: Output directory for generated config
        """
        self.project_metadata = project_metadata
        self.output_dir = output_dir

        # Load templates
        template_dir = Path(__file__).parent.parent.parent / "templates"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(
        self,
        project_name: str,
        catalog: str = "main",
        schema: str = "default",
        databricks_host: str = "",
    ) -> dict[str, str]:
        """
        Generate all configuration files.

        Args:
            project_name: Name of the project
            catalog: Unity Catalog name
            schema: Database schema name
            databricks_host: Databricks workspace host

        Returns:
            Dictionary mapping file paths to generated config
        """
        logger.info(f"Generating configuration files for {project_name}")

        generated_files = {}

        # Generate app.yaml
        generated_files["app.yaml"] = self._generate_app_yaml(
            project_name, catalog, schema, databricks_host
        )

        # Generate databricks.yml
        generated_files["databricks.yml"] = self._generate_databricks_yml(
            project_name, catalog, schema, databricks_host
        )

        # Generate .env.example
        generated_files[".env.example"] = self._generate_env_example(
            project_name, catalog, schema, databricks_host
        )

        # Generate requirements.txt
        generated_files["requirements.txt"] = self._generate_requirements()

        logger.info(f"Generated {len(generated_files)} configuration files")
        return generated_files

    def _generate_app_yaml(
        self,
        project_name: str,
        catalog: str,
        schema: str,
        databricks_host: str,
    ) -> str:
        """Generate app.yaml for Databricks Apps."""
        template = self.env.get_template("config/app.yaml.jinja2")

        # Determine resource requirements based on project size
        backend_metadata = self.project_metadata.get("backend", {})
        database_metadata = self.project_metadata.get("database", {})

        function_count = backend_metadata.get("function_count", 0)
        table_count = database_metadata.get("table_count", 0)

        # Scale resources based on complexity
        if function_count > 5 or table_count > 10:
            memory_request = "2Gi"
            memory_limit = "4Gi"
            cpu_request = "1000m"
            cpu_limit = "2000m"
        else:
            memory_request = "512Mi"
            memory_limit = "1Gi"
            cpu_request = "250m"
            cpu_limit = "500m"

        # Database URL
        database_url = f"postgresql://{{{{POSTGRES_USER}}}}:{{{{POSTGRES_PASSWORD}}}}@localhost:5432/{catalog}.{schema}"

        # Check if volumes needed
        volumes: list[dict[str, Any]] = []
        # TODO: Add volume configuration if storage detected

        # Additional env vars
        additional_env_vars = []
        llm_usage = backend_metadata.get("llm_usage_detected", False)
        if llm_usage:
            additional_env_vars.append(
                {"name": "DATABRICKS_LLM_ENABLED", "value": "true"}
            )

        return template.render(
            project_name=project_name,
            database_url=database_url,
            databricks_host=databricks_host or "${DATABRICKS_HOST}",
            memory_request=memory_request,
            memory_limit=memory_limit,
            cpu_request=cpu_request,
            cpu_limit=cpu_limit,
            volumes=volumes,
            additional_env_vars=additional_env_vars,
        )

    def _generate_databricks_yml(
        self,
        project_name: str,
        catalog: str,
        schema: str,
        databricks_host: str,
    ) -> str:
        """Generate databricks.yml asset bundle."""
        template = self.env.get_template("config/databricks.yml.jinja2")

        bundle_name = project_name.replace(" ", "-").lower()
        app_name = bundle_name

        # Detect if jobs needed (cron functions, etc.)
        jobs: list[dict[str, Any]] = []
        # TODO: Add job configuration if cron detected

        # Volume configuration
        volumes = [
            {
                "name": f"{bundle_name}-storage",
                "catalog": catalog,
                "schema": schema,
                "type": "MANAGED",
                "comment": f"Storage volume for {project_name}",
            }
        ]

        # Service principal
        service_principal = f"sp-{bundle_name}-prod"

        return template.render(
            bundle_name=bundle_name,
            workspace_host=databricks_host or "${DATABRICKS_HOST}",
            app_name=app_name,
            app_description=f"Databricks App for {project_name}",
            jobs=jobs,
            volumes=volumes,
            dev_workspace_host=databricks_host or "${DATABRICKS_HOST}",
            dev_catalog=f"{catalog}_dev",
            dev_schema=f"{schema}_dev",
            prod_workspace_host=databricks_host or "${DATABRICKS_HOST}",
            prod_catalog=catalog,
            prod_schema=schema,
            service_principal=service_principal,
        )

    def _generate_env_example(
        self,
        project_name: str,
        catalog: str,
        schema: str,
        databricks_host: str,
    ) -> str:
        """Generate .env.example file."""
        template = self.env.get_template("config/env.example.jinja2")

        # Database URL
        database_url = f"postgresql://user:password@localhost:5432/{catalog}.{schema}"

        # LLM endpoints
        backend_metadata = self.project_metadata.get("backend", {})
        functions = backend_metadata.get("functions", {})

        llm_endpoints = []
        for func_name, func_info in functions.items():
            llm_apis = func_info.get("llm_apis", [])
            for llm_api in llm_apis:
                provider = llm_api.get("provider")
                if provider in ["OpenAI", "Anthropic"]:
                    env_var = f"{func_name.upper()}_LLM_MODEL"
                    models = llm_api.get("models", [])
                    model_name = models[0] if models else "databricks-dbrx-instruct"
                    llm_endpoints.append(
                        {"env_var": env_var, "model_name": model_name}
                    )

        # Storage volumes
        storage_volumes = [
            {
                "env_var": "STORAGE_VOLUME_PATH",
                "path": f"/Volumes/{catalog}/{schema}/storage",
            }
        ]

        # External services (from external APIs detected)
        external_services: list[dict[str, str]] = []
        for _func_name, func_info in functions.items():
            external_apis = func_info.get("external_apis", [])
            for api in external_apis:
                # Extract service name from domain
                service_name = api.split(".")[0].upper()
                if service_name not in [s["name"] for s in external_services]:
                    external_services.append({"name": service_name})

        return template.render(
            project_name=project_name,
            databricks_host=databricks_host or "https://your-workspace.cloud.databricks.com",
            database_url=database_url,
            catalog_name=catalog,
            schema_name=schema,
            app_name=project_name.replace(" ", "-").lower(),
            app_env="development",
            llm_endpoints=llm_endpoints,
            storage_volumes=storage_volumes,
            external_services=external_services,
        )

    def _generate_requirements(self) -> str:
        """Generate requirements.txt."""
        requirements = [
            "# Python dependencies for Databricks App",
            "# Generated by Lovable Bridge MCP Server",
            "",
            "# Web framework",
            "fastapi>=0.109.0",
            "uvicorn[standard]>=0.27.0",
            "pydantic>=2.5.0",
            "",
            "# Database",
            "sqlmodel>=0.0.14",
            "psycopg2-binary>=2.9.9",
            "alembic>=1.13.0",
            "",
            "# Databricks",
            "databricks-sdk>=0.18.0",
            "",
            "# Utilities",
            "python-dotenv>=1.0.0",
            "httpx>=0.26.0",
            "",
        ]

        # Add testing dependencies
        requirements.extend(
            [
                "# Development dependencies (optional)",
                "pytest>=7.4.0",
                "pytest-asyncio>=0.23.0",
                "pytest-cov>=4.1.0",
                "black>=23.12.0",
                "ruff>=0.1.9",
                "mypy>=1.8.0",
            ]
        )

        return "\n".join(requirements)

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
