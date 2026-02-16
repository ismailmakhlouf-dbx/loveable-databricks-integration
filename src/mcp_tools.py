"""
MCP Tool Implementations for Lovable Bridge.

This module contains the actual implementation of the MCP tools:
- lovable_import: Import and analyze Lovable projects
- lovable_convert: Convert to APX format
- lovable_deploy: Deploy to Databricks
- lovable_status: Check deployment status
"""

import json
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Any

from mcp.types import TextContent

from .analyzer.backend_analyzer import BackendAnalyzer
from .analyzer.database_analyzer import DatabaseAnalyzer
from .analyzer.frontend_analyzer import FrontendAnalyzer
from .analyzer.project_scanner import ProjectScanner
from .deployer.database_deployer import DatabaseDeployer
from .deployer.databricks_deployer import DatabricksDeployer
from .generator.config_generator import ConfigGenerator
from .generator.fastapi_generator import FastAPIGenerator
from .generator.model_generator import ModelGenerator
from .transformer.llm_converter import LLMConverter
from .transformer.type_converter import TypeConverter
from .validator.compatibility_validator import CompatibilityValidator
from .validator.deployment_validator import DeploymentValidator

logger = logging.getLogger(__name__)

# In-memory storage for project data (in production, use a database)
PROJECT_STORE: dict[str, dict[str, Any]] = {}
DEPLOYMENT_STORE: dict[str, dict[str, Any]] = {}


class LovableError(Exception):
    """Base exception for Lovable Bridge errors."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_mcp_response(self) -> TextContent:
        """Convert error to MCP TextContent response."""
        return TextContent(
            type="text",
            text=json.dumps(
                {
                    "error": {
                        "code": self.code,
                        "message": self.message,
                        "details": self.details,
                    }
                }
            ),
        )


async def lovable_import(url: str, name: str | None = None) -> dict[str, Any]:
    """
    Import and analyze a Lovable project from GitHub or ZIP URL.

    Args:
        url: GitHub repository URL or ZIP download URL
        name: Optional project name (auto-detected if not provided)

    Returns:
        Project metadata including ID, components, endpoints, tables

    Raises:
        LovableError: If import fails
    """
    try:
        logger.info(f"Importing Lovable project from: {url}")

        # Generate unique project ID
        project_id = f"proj_{uuid.uuid4().hex[:12]}"

        # Import project using ProjectScanner
        scanner = await ProjectScanner.from_url(url, name)
        project_path = scanner.project_path
        project_name = name or scanner.project_name

        logger.info(f"Project downloaded to: {project_path}")

        # Run all analyzers
        backend_metadata = {}
        database_metadata = {}
        frontend_metadata = {}

        # Analyze backend (Supabase Edge Functions)
        functions_path = project_path / "supabase" / "functions"
        if functions_path.exists():
            backend_analyzer = BackendAnalyzer(functions_path)
            backend_metadata = backend_analyzer.analyze()
            logger.info(
                f"Backend analysis: {backend_metadata.get('function_count', 0)} functions"
            )

        # Analyze database (migrations)
        migrations_path = project_path / "supabase" / "migrations"
        if migrations_path.exists():
            database_analyzer = DatabaseAnalyzer(migrations_path)
            database_metadata = database_analyzer.analyze()
            logger.info(
                f"Database analysis: {database_metadata.get('table_count', 0)} tables"
            )

        # Analyze frontend
        src_path = project_path / "src"
        if src_path.exists():
            frontend_analyzer = FrontendAnalyzer(src_path)
            frontend_metadata = frontend_analyzer.analyze()
            logger.info(
                f"Frontend analysis: {frontend_metadata.get('component_count', 0)} components"
            )

        # Detect technologies
        technologies = {
            "frontend": ["React", "TypeScript"],
            "backend": [],
            "database": [],
            "llm_apis": [],
        }

        if backend_metadata.get("function_count", 0) > 0:
            technologies["backend"].append("Supabase Edge Functions")

        if database_metadata.get("table_count", 0) > 0:
            technologies["database"].append("PostgreSQL")

        # Detect LLM APIs
        functions = backend_metadata.get("functions", {})
        for func_info in functions.values():
            llm_apis = func_info.get("llm_apis", [])
            for llm_api in llm_apis:
                provider = llm_api.get("provider")
                if provider not in technologies["llm_apis"]:
                    technologies["llm_apis"].append(provider)

        # Compile project data
        project_data = {
            "project_id": project_id,
            "name": project_name,
            "url": url,
            "project_path": str(project_path),
            "status": "imported",
            "backend": backend_metadata,
            "database": database_metadata,
            "frontend": frontend_metadata,
            "technologies": technologies,
            "analysis": {
                "components": frontend_metadata.get("component_count", 0),
                "api_endpoints": backend_metadata.get("function_count", 0),
                "database_tables": database_metadata.get("table_count", 0),
                "edge_functions": backend_metadata.get("function_count", 0),
                "pages": frontend_metadata.get("page_count", 0),
            },
        }

        # Store project data
        PROJECT_STORE[project_id] = project_data

        logger.info(f"Project imported successfully: {project_id}")
        return project_data

    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise LovableError(
            "IMPORT_FAILED",
            f"Failed to import project: {str(e)}",
            {"url": url, "error": str(e)},
        ) from e


async def lovable_convert(
    project_id: str,
    catalog: str = "main",
    schema: str = "lovable_app",
) -> dict[str, Any]:
    """
    Convert imported Lovable project to APX format.

    Args:
        project_id: Project ID from lovable_import
        catalog: Unity Catalog name (default: "main")
        schema: Database schema name (default: "lovable_app")

    Returns:
        Conversion summary with generated files and compatibility report

    Raises:
        LovableError: If conversion fails
    """
    try:
        logger.info(f"Converting project {project_id} to APX format")

        # Load project data
        if project_id not in PROJECT_STORE:
            raise LovableError(
                "PROJECT_NOT_FOUND",
                f"Project {project_id} not found",
                {"project_id": project_id},
            )

        project_data = PROJECT_STORE[project_id]
        project_name = project_data["name"]

        # Initialize converters
        type_converter = TypeConverter()
        llm_converter = LLMConverter()

        # Run compatibility validation
        compatibility_validator = CompatibilityValidator()
        compatibility_results = compatibility_validator.validate(project_data)

        if not compatibility_results["compatible"]:
            logger.warning("Project has compatibility issues")
            # Continue but include issues in response

        # Create output directory
        output_dir = Path(tempfile.mkdtemp(prefix=f"lovable_{project_id}_"))
        logger.info(f"Output directory: {output_dir}")

        # Initialize generators
        fastapi_gen = FastAPIGenerator(
            backend_metadata=project_data.get("backend", {}),
            type_converter=type_converter,
            llm_converter=llm_converter,
            output_dir=output_dir,
        )

        model_gen = ModelGenerator(
            database_metadata=project_data.get("database", {}),
            type_converter=type_converter,
            output_dir=output_dir,
        )

        config_gen = ConfigGenerator(
            project_metadata=project_data,
            output_dir=output_dir,
        )

        # Generate code
        logger.info("Generating FastAPI application...")
        fastapi_files = fastapi_gen.generate(
            project_name=project_name,
            project_description=f"Databricks App for {project_name}",
        )

        logger.info("Generating models...")
        model_files = model_gen.generate()

        logger.info("Generating configuration...")
        config_files = config_gen.generate(
            project_name=project_name,
            catalog=catalog,
            schema=schema,
        )

        # Combine all generated files
        all_files = {}
        all_files.update(fastapi_files)
        all_files.update(model_files)
        all_files.update(config_files)

        # Write files to disk
        fastapi_gen.write_files(fastapi_files)
        model_gen.write_files(model_files)
        config_gen.write_files(config_files)

        # Get LLM conversion summary
        llm_summary = llm_converter.get_conversion_summary()

        # Update project data
        project_data["status"] = "converted"
        project_data["output_dir"] = str(output_dir)
        project_data["catalog"] = catalog
        project_data["schema"] = schema
        project_data["generated_files"] = list(all_files.keys())

        conversion_summary = {
            "project_id": project_id,
            "project_name": project_name,
            "status": "converted",
            "output_dir": str(output_dir),
            "generated_files": {
                "total": len(all_files),
                "fastapi": len(fastapi_files),
                "models": len(model_files),
                "config": len(config_files),
            },
            "llm_conversions": llm_summary,
            "compatibility": compatibility_results,
            "catalog": catalog,
            "schema": schema,
        }

        logger.info(f"Conversion complete: {len(all_files)} files generated")
        return conversion_summary

    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        raise LovableError(
            "CONVERSION_FAILED",
            f"Failed to convert project: {str(e)}",
            {"project_id": project_id, "error": str(e)},
        ) from e


async def lovable_deploy(
    project_id: str,
    app_name: str,
    target: str = "dev",
) -> dict[str, Any]:
    """
    Deploy converted project to Databricks.

    Args:
        project_id: Project ID from lovable_convert
        app_name: Databricks App name
        target: Deployment target - "dev" or "prod" (default: "dev")

    Returns:
        Deployment info with app URL and status

    Raises:
        LovableError: If deployment fails
    """
    try:
        logger.info(f"Deploying project {project_id} to Databricks ({target})")

        # Load project data
        if project_id not in PROJECT_STORE:
            raise LovableError(
                "PROJECT_NOT_FOUND",
                f"Project {project_id} not found",
                {"project_id": project_id},
            )

        project_data = PROJECT_STORE[project_id]

        if project_data.get("status") != "converted":
            raise LovableError(
                "PROJECT_NOT_CONVERTED",
                "Project must be converted before deployment",
                {"project_id": project_id, "status": project_data.get("status")},
            )

        output_dir = Path(project_data["output_dir"])
        catalog = project_data.get("catalog", "main")
        schema = project_data.get("schema", "lovable_app")

        # Run deployment validation
        deployment_validator = DeploymentValidator()
        validation_results = deployment_validator.validate(
            app_path=output_dir,
            catalog=catalog,
            schema=schema,
        )

        if not validation_results["valid"]:
            raise LovableError(
                "DEPLOYMENT_VALIDATION_FAILED",
                "Deployment validation failed",
                {"errors": validation_results["errors"]},
            )

        # Deploy database
        logger.info("Deploying database schema...")
        database_deployer = DatabaseDeployer()

        # Load migration files
        migrations = []
        migrations_path = Path(project_data["project_path"]) / "supabase" / "migrations"
        if migrations_path.exists():
            for migration_file in sorted(migrations_path.glob("*.sql")):
                with open(migration_file) as f:
                    migrations.append(f.read())

        db_deployment = await database_deployer.deploy(
            catalog=catalog,
            schema=schema,
            migrations=migrations,
        )

        # Deploy app
        logger.info("Deploying Databricks App...")
        databricks_deployer = DatabricksDeployer()

        app_deployment = await databricks_deployer.deploy(
            app_name=app_name,
            app_path=output_dir,
            config={
                "target": target,
                "catalog": catalog,
                "schema": schema,
                "description": f"Databricks App for {project_data['name']}",
            },
        )

        # Generate deployment ID
        deployment_id = f"deploy_{uuid.uuid4().hex[:12]}"

        # Store deployment info
        deployment_info = {
            "deployment_id": deployment_id,
            "project_id": project_id,
            "app_name": app_name,
            "target": target,
            "app_url": app_deployment["app_url"],
            "status": "deployed",
            "database": db_deployment,
            "app": app_deployment,
        }

        DEPLOYMENT_STORE[deployment_id] = deployment_info

        # Update project data
        project_data["status"] = "deployed"
        project_data["deployment_id"] = deployment_id

        logger.info(f"Deployment complete: {app_deployment['app_url']}")
        return deployment_info

    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        raise LovableError(
            "DEPLOYMENT_FAILED",
            f"Failed to deploy project: {str(e)}",
            {"project_id": project_id, "error": str(e)},
        ) from e


async def lovable_status(deployment_id: str) -> dict[str, Any]:
    """
    Check deployment status and get app details.

    Args:
        deployment_id: Deployment ID from lovable_deploy

    Returns:
        Current status, app URL, and provisioned services

    Raises:
        LovableError: If deployment not found
    """
    try:
        logger.info(f"Checking status for deployment {deployment_id}")

        # Load deployment info
        if deployment_id not in DEPLOYMENT_STORE:
            raise LovableError(
                "DEPLOYMENT_NOT_FOUND",
                f"Deployment {deployment_id} not found",
                {"deployment_id": deployment_id},
            )

        deployment_info = DEPLOYMENT_STORE[deployment_id]

        # Get current status from Databricks
        databricks_deployer = DatabricksDeployer()
        app_status = databricks_deployer.get_deployment_status(
            deployment_info["app"]["deployment_id"]
        )

        # Update deployment info
        deployment_info["app"]["status"] = app_status["state"]

        status_info = {
            "deployment_id": deployment_id,
            "project_id": deployment_info["project_id"],
            "app_name": deployment_info["app_name"],
            "status": app_status["state"],
            "app_url": deployment_info["app_url"],
            "services": {
                "app": app_status,
                "database": deployment_info["database"],
            },
        }

        logger.info(f"Deployment status: {app_status['state']}")
        return status_info

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise LovableError(
            "STATUS_CHECK_FAILED",
            f"Failed to check deployment status: {str(e)}",
            {"deployment_id": deployment_id, "error": str(e)},
        ) from e
