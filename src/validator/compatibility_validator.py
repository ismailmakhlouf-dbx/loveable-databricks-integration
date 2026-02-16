"""
Compatibility Validator.

Validates Lovable project compatibility with Databricks.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CompatibilityIssue:
    """Represents a compatibility issue."""

    SEVERITY_ERROR = "error"
    SEVERITY_WARNING = "warning"
    SEVERITY_INFO = "info"

    def __init__(
        self,
        severity: str,
        category: str,
        message: str,
        suggestion: str | None = None,
    ):
        self.severity = severity
        self.category = category
        self.message = message
        self.suggestion = suggestion

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
        }


class CompatibilityValidator:
    """Validates project compatibility with Databricks."""

    def __init__(self) -> None:
        """Initialize compatibility validator."""
        self.issues: list[CompatibilityIssue] = []

    def validate(self, project_metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Validate project compatibility.

        Args:
            project_metadata: Complete project metadata

        Returns:
            Validation results
        """
        logger.info("Validating project compatibility")

        self.issues = []

        # Validate backend
        backend_metadata = project_metadata.get("backend", {})
        self._validate_backend(backend_metadata)

        # Validate database
        database_metadata = project_metadata.get("database", {})
        self._validate_database(database_metadata)

        # Validate frontend
        frontend_metadata = project_metadata.get("frontend", {})
        self._validate_frontend(frontend_metadata)

        # Compile results
        errors = [i for i in self.issues if i.severity == CompatibilityIssue.SEVERITY_ERROR]
        warnings = [i for i in self.issues if i.severity == CompatibilityIssue.SEVERITY_WARNING]
        info = [i for i in self.issues if i.severity == CompatibilityIssue.SEVERITY_INFO]

        compatible = len(errors) == 0

        results = {
            "compatible": compatible,
            "issues": [i.to_dict() for i in self.issues],
            "summary": {
                "errors": len(errors),
                "warnings": len(warnings),
                "info": len(info),
            },
        }

        logger.info(
            f"Compatibility check complete: {'✓ Compatible' if compatible else '✗ Incompatible'}"
        )

        return results

    def _validate_backend(self, backend_metadata: dict[str, Any]) -> None:
        """Validate backend compatibility."""
        functions = backend_metadata.get("functions", {})

        for func_name, func_info in functions.items():
            # Check for unsupported features
            self._check_unsupported_features(func_name, func_info)

            # Check LLM APIs
            self._check_llm_apis(func_name, func_info)

            # Check external APIs
            self._check_external_apis(func_name, func_info)

    def _check_unsupported_features(
        self, func_name: str, func_info: dict[str, Any]
    ) -> None:
        """Check for unsupported Supabase features."""
        # Check for Realtime usage
        # Note: This would need to be detected during analysis
        # For now, just add a warning if function seems to use subscriptions

        if "realtime" in func_name.lower() or "subscribe" in func_name.lower():
            self.issues.append(
                CompatibilityIssue(
                    severity=CompatibilityIssue.SEVERITY_WARNING,
                    category="realtime",
                    message=f"Function '{func_name}' may use Supabase Realtime",
                    suggestion=(
                        "Supabase Realtime is not directly supported. "
                        "Consider polling with React Query or WebSocket."
                    ),
                )
            )

    def _check_llm_apis(self, func_name: str, func_info: dict[str, Any]) -> None:
        """Check LLM API compatibility."""
        llm_apis = func_info.get("llm_apis", [])

        for llm_api in llm_apis:
            provider = llm_api.get("provider")

            if provider == "OpenAI":
                self.issues.append(
                    CompatibilityIssue(
                        severity=CompatibilityIssue.SEVERITY_INFO,
                        category="llm",
                        message=(
                            f"Function '{func_name}' uses OpenAI API - "
                            "will be converted to Databricks Foundation Model Serving"
                        ),
                        suggestion="Ensure Databricks Foundation Model Serving is configured.",
                    )
                )

            elif provider == "Anthropic":
                self.issues.append(
                    CompatibilityIssue(
                        severity=CompatibilityIssue.SEVERITY_INFO,
                        category="llm",
                        message=(
                            f"Function '{func_name}' uses Anthropic API - "
                            "will be converted to Databricks Foundation Model Serving"
                        ),
                        suggestion="Ensure Databricks Foundation Model Serving is configured.",
                    )
                )

            elif provider == "Unknown":
                self.issues.append(
                    CompatibilityIssue(
                        severity=CompatibilityIssue.SEVERITY_WARNING,
                        category="llm",
                        message=f"Function '{func_name}' uses unknown LLM API",
                        suggestion="Manual review needed for LLM API conversion.",
                    )
                )

    def _check_external_apis(
        self, func_name: str, func_info: dict[str, Any]
    ) -> None:
        """Check external API compatibility."""
        external_apis = func_info.get("external_apis", [])

        if external_apis:
            self.issues.append(
                CompatibilityIssue(
                    severity=CompatibilityIssue.SEVERITY_INFO,
                    category="external_apis",
                    message=(
                        f"Function '{func_name}' calls external APIs: "
                        f"{', '.join(external_apis)}"
                    ),
                    suggestion=(
                        "Ensure network connectivity and API credentials "
                        "are configured in environment."
                    ),
                )
            )

    def _validate_database(self, database_metadata: dict[str, Any]) -> None:
        """Validate database compatibility."""
        tables = database_metadata.get("tables", {})

        for table_name, table_schema in tables.items():
            # Check for complex stored procedures
            # (Would need to be detected during analysis)

            # Check RLS policies
            rls_policies = table_schema.get("rls_policies", [])
            if rls_policies:
                self.issues.append(
                    CompatibilityIssue(
                        severity=CompatibilityIssue.SEVERITY_WARNING,
                        category="database",
                        message=f"Table '{table_name}' has {len(rls_policies)} RLS policies",
                        suggestion=(
                            "RLS policies will need to be reimplemented "
                            "as FastAPI dependencies for authorization."
                        ),
                    )
                )

    def _validate_frontend(self, frontend_metadata: dict[str, Any]) -> None:
        """Validate frontend compatibility."""
        components = frontend_metadata.get("components", {})

        for comp_name, comp_info in components.items():
            supabase_usage = comp_info.get("supabase_usage", [])

            # Check for realtime subscriptions
            if "realtime" in supabase_usage:
                self.issues.append(
                    CompatibilityIssue(
                        severity=CompatibilityIssue.SEVERITY_WARNING,
                        category="frontend",
                        message=f"Component '{comp_name}' uses Supabase Realtime",
                        suggestion=(
                            "Replace with React Query polling or "
                            "implement custom WebSocket endpoint."
                        ),
                    )
                )

            # Check for storage
            if "storage" in supabase_usage:
                self.issues.append(
                    CompatibilityIssue(
                        severity=CompatibilityIssue.SEVERITY_INFO,
                        category="frontend",
                        message=f"Component '{comp_name}' uses Supabase Storage",
                        suggestion=(
                            "Will be migrated to Databricks Volumes. "
                            "Update API calls accordingly."
                        ),
                    )
                )
