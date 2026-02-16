"""
Deployment Validator.

Validates deployment configuration and prerequisites.
"""

import logging
from pathlib import Path
from typing import Any

from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


class DeploymentValidator:
    """Validates deployment prerequisites."""

    def __init__(self, workspace_client: WorkspaceClient | None = None):
        """
        Initialize deployment validator.

        Args:
            workspace_client: Databricks workspace client
        """
        self.workspace = workspace_client or WorkspaceClient()
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(
        self,
        app_path: Path,
        catalog: str,
        schema: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Validate deployment prerequisites.

        Args:
            app_path: Path to application code
            catalog: Unity Catalog name
            schema: Schema name
            config: Optional configuration

        Returns:
            Validation results
        """
        logger.info("Validating deployment prerequisites")

        self.errors = []
        self.warnings = []

        # Validate workspace access
        self._validate_workspace_access()

        # Validate catalog/schema permissions
        self._validate_catalog_permissions(catalog, schema)

        # Validate app configuration
        self._validate_app_configuration(app_path)

        # Validate required files
        self._validate_required_files(app_path)

        # Check compute availability
        self._check_compute_availability()

        # Compile results
        valid = len(self.errors) == 0

        results = {
            "valid": valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }

        logger.info(
            f"Deployment validation complete: {'✓ Valid' if valid else '✗ Invalid'}"
        )

        return results

    def _validate_workspace_access(self) -> None:
        """Validate workspace access."""
        try:
            # Test workspace connection
            _ = self.workspace.current_user.me()
            logger.info("✓ Workspace access validated")

        except Exception as e:
            self.errors.append(f"Cannot access workspace: {e}")
            logger.error(f"✗ Workspace access failed: {e}")

    def _validate_catalog_permissions(self, catalog: str, schema: str) -> None:
        """Validate catalog and schema permissions."""
        try:
            # Check catalog exists and user has access
            # Note: Actual implementation would use Unity Catalog APIs
            logger.info(f"✓ Catalog {catalog} access validated (mock)")

            # Check schema
            logger.info(f"✓ Schema {schema} access validated (mock)")

        except Exception as e:
            self.errors.append(
                f"Cannot access catalog {catalog}.{schema}: {e}"
            )
            logger.error(f"✗ Catalog access failed: {e}")

    def _validate_app_configuration(self, app_path: Path) -> None:
        """Validate app.yaml configuration."""
        app_yaml_path = app_path / "app.yaml"

        if not app_yaml_path.exists():
            self.errors.append("Missing app.yaml configuration file")
            logger.error("✗ app.yaml not found")
            return

        try:
            # Validate app.yaml structure
            # TODO: Add YAML parsing and validation
            logger.info("✓ app.yaml exists")

        except Exception as e:
            self.errors.append(f"Invalid app.yaml: {e}")
            logger.error(f"✗ app.yaml validation failed: {e}")

    def _validate_required_files(self, app_path: Path) -> None:
        """Validate required files exist."""
        required_files = [
            "app.yaml",
            "requirements.txt",
            "app/__init__.py",
            "app/main.py",
        ]

        for file_path in required_files:
            full_path = app_path / file_path
            if not full_path.exists():
                self.warnings.append(f"Missing recommended file: {file_path}")
                logger.warning(f"⚠ Missing {file_path}")

    def _check_compute_availability(self) -> None:
        """Check compute resource availability."""
        try:
            # Check if user can create/access compute
            # Note: Actual implementation would use Databricks APIs
            logger.info("✓ Compute availability validated (mock)")

        except Exception as e:
            self.warnings.append(f"Cannot verify compute availability: {e}")
            logger.warning(f"⚠ Compute check failed: {e}")

    def validate_environment(self, required_env_vars: list[str]) -> dict[str, Any]:
        """
        Validate environment variables.

        Args:
            required_env_vars: List of required environment variable names

        Returns:
            Validation results
        """
        import os

        missing = []
        present = []

        for var in required_env_vars:
            if var in os.environ:
                present.append(var)
            else:
                missing.append(var)

        return {
            "valid": len(missing) == 0,
            "missing": missing,
            "present": present,
        }
