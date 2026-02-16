"""
Project Generator.

Generates complete APX project structure from conversion results.
"""

import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ProjectGenerator:
    """Generates APX project structure."""

    def __init__(self, output_path: Path):
        """
        Initialize project generator.

        Args:
            output_path: Path where APX project will be generated
        """
        self.output_path = output_path
        self.generated_files: list[Path] = []

    def generate_project(
        self,
        project_name: str,
        original_project_path: Path,
        conversion_results: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate complete APX project.

        Args:
            project_name: Name of the project
            original_project_path: Path to original Lovable project
            conversion_results: Results from all converters

        Returns:
            Generation summary
        """
        logger.info(f"Generating APX project: {project_name}")

        # Create project structure
        self._create_directory_structure()

        # Generate backend files
        self._generate_backend(conversion_results)

        # Copy and adapt frontend files
        self._copy_frontend(original_project_path)

        # Generate configuration files
        self._generate_config(project_name, conversion_results)

        # Generate migrations
        self._generate_migrations(conversion_results)

        summary = {
            "project_name": project_name,
            "output_path": str(self.output_path),
            "generated_files": len(self.generated_files),
            "structure": self._get_structure_summary(),
        }

        logger.info(f"Project generation complete: {len(self.generated_files)} files created")
        return summary

    def _create_directory_structure(self) -> None:
        """Create APX directory structure."""
        directories = [
            "src/backend",
            "src/ui/src/components",
            "src/ui/src/pages",
            "src/ui/src/lib",
            "src/ui/public",
            "migrations",
            "tests",
            ".databricks",
        ]

        for directory in directories:
            dir_path = self.output_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {dir_path}")

    def _generate_backend(self, conversion_results: dict[str, Any]) -> None:
        """Generate backend Python files."""
        backend_path = self.output_path / "src" / "backend"

        # Generate app.py
        app_code = self._generate_app_py(conversion_results)
        self._write_file(backend_path / "app.py", app_code)

        # Generate models.py
        models_code = conversion_results.get("models_code", "")
        if models_code:
            self._write_file(backend_path / "models.py", models_code)

        # Generate router.py
        router_code = self._generate_router_py(conversion_results)
        self._write_file(backend_path / "router.py", router_code)

        # Generate database.py
        database_code = self._generate_database_py()
        self._write_file(backend_path / "database.py", database_code)

        # Generate auth.py
        auth_code = conversion_results.get("auth_code", "")
        if auth_code:
            self._write_file(backend_path / "auth.py", auth_code)

        # Generate config.py
        config_code = self._generate_config_py()
        self._write_file(backend_path / "config.py", config_code)

    def _generate_app_py(self, conversion_results: dict[str, Any]) -> str:
        """Generate FastAPI app.py."""
        return '''
"""
FastAPI Application Entry Point.

Auto-generated from Lovable project.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .router import router
from .database import create_db_and_tables

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Lovable APX Backend",
    description="Auto-generated FastAPI backend from Lovable project",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Starting application...")
    create_db_and_tables()
    logger.info("Database initialized")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Lovable APX Backend",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

    def _generate_router_py(self, conversion_results: dict[str, Any]) -> str:
        """Generate router.py with all converted routes."""
        routes = conversion_results.get("fastapi_routes", [])

        router_code = [
            "from fastapi import APIRouter",
            "",
            "router = APIRouter()",
            "",
            "# Auto-generated routes from Edge Functions",
            "",
        ]

        for route in routes:
            router_code.append(route.get("code", ""))
            router_code.append("")

        return "\n".join(router_code)

    def _generate_database_py(self) -> str:
        """Generate database.py."""
        return '''
"""
Database Configuration.

Lakebase PostgreSQL connection management.
"""

from sqlmodel import create_engine, Session, SQLModel
from typing import Generator
import os

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/dbname"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
)


def create_db_and_tables():
    """Create database tables."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """
    Get database session.

    Yields:
        Database session
    """
    with Session(engine) as session:
        yield session
'''

    def _generate_config_py(self) -> str:
        """Generate config.py."""
        return '''
"""
Application Configuration.

Manages environment variables and settings.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/dbname"

    # Databricks
    databricks_host: Optional[str] = None
    databricks_token: Optional[str] = None

    # App settings
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
'''

    def _copy_frontend(self, original_project_path: Path) -> None:
        """Copy and adapt frontend files."""
        src_path = original_project_path / "src"
        if not src_path.exists():
            logger.warning("Original src directory not found")
            return

        ui_src_path = self.output_path / "src" / "ui" / "src"

        # Copy components
        components_src = src_path / "components"
        if components_src.exists():
            components_dst = ui_src_path / "components"
            shutil.copytree(components_src, components_dst, dirs_exist_ok=True)
            logger.info("Copied components")

        # Copy pages
        pages_src = src_path / "pages"
        if pages_src.exists():
            pages_dst = ui_src_path / "pages"
            shutil.copytree(pages_src, pages_dst, dirs_exist_ok=True)
            logger.info("Copied pages")

        # Copy other frontend files
        for item in src_path.iterdir():
            if item.is_file():
                shutil.copy2(item, ui_src_path / item.name)

    def _generate_config(
        self, project_name: str, conversion_results: dict[str, Any]
    ) -> None:
        """Generate configuration files."""
        # Generate pyproject.toml
        pyproject = self._generate_pyproject_toml(project_name)
        self._write_file(self.output_path / "pyproject.toml", pyproject)

        # Generate databricks.yml
        databricks_yml = self._generate_databricks_yml(project_name)
        self._write_file(self.output_path / "databricks.yml", databricks_yml)

        # Generate app.yaml
        app_yaml = self._generate_app_yaml()
        self._write_file(self.output_path / "app.yaml", app_yaml)

    def _generate_pyproject_toml(self, project_name: str) -> str:
        """Generate pyproject.toml."""
        return f'''
[project]
name = "{project_name}"
version = "1.0.0"
description = "APX project converted from Lovable"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sqlmodel>=0.0.16",
    "alembic>=1.13.0",
    "databricks-sdk>=0.23.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
'''

    def _generate_databricks_yml(self, project_name: str) -> str:
        """Generate databricks.yml."""
        return f'''
bundle:
  name: {project_name}

resources:
  apps:
    {project_name}:
      name: {project_name}
      description: "Converted from Lovable project"
'''

    def _generate_app_yaml(self) -> str:
        """Generate app.yaml."""
        return '''
command:
  - "uvicorn"
  - "src.backend.app:app"
  - "--host"
  - "0.0.0.0"
  - "--port"
  - "8000"
'''

    def _generate_migrations(self, conversion_results: dict[str, Any]) -> None:
        """Generate Alembic migrations."""
        migrations_path = self.output_path / "migrations"

        # Generate initial migration
        migration_code = conversion_results.get("migration_code", "")
        if migration_code:
            migration_file = migrations_path / "001_initial.py"
            self._write_file(migration_file, migration_code)

    def _write_file(self, file_path: Path, content: str) -> None:
        """Write content to file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        self.generated_files.append(file_path)
        logger.debug(f"Generated file: {file_path}")

    def _get_structure_summary(self) -> dict[str, int]:
        """Get summary of generated structure."""
        return {
            "backend_files": len(
                [f for f in self.generated_files if "backend" in str(f)]
            ),
            "frontend_files": len([f for f in self.generated_files if "ui" in str(f)]),
            "config_files": len(
                [
                    f
                    for f in self.generated_files
                    if f.suffix in [".toml", ".yml", ".yaml"]
                ]
            ),
            "migration_files": len(
                [f for f in self.generated_files if "migrations" in str(f)]
            ),
        }
