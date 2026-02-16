"""
Database Converter.

Converts SQL migrations to SQLModel models and Alembic migrations.
"""

import logging
from typing import Any

from .type_converter import TypeConverter

logger = logging.getLogger(__name__)


class DatabaseConverter:
    """Converts SQL migrations to SQLModel and Alembic."""

    def __init__(self) -> None:
        """Initialize database converter."""
        self.type_converter = TypeConverter()
        self.models: dict[str, str] = {}
        self.alembic_migrations: list[str] = []

    def convert_migrations(self, tables: dict[str, Any]) -> dict[str, Any]:
        """
        Convert parsed SQL tables to SQLModel models.

        Args:
            tables: Dictionary of parsed table schemas

        Returns:
            Conversion result with models and migrations
        """
        logger.info(f"Converting {len(tables)} tables to SQLModel")

        # Generate SQLModel for each table
        for table_name, table_data in tables.items():
            sqlmodel_code = self.type_converter.sql_table_to_sqlmodel(
                table_name=table_name, columns=table_data.get("columns", [])
            )
            self.models[table_name] = sqlmodel_code

        # Generate Alembic migration
        alembic_migration = self._generate_alembic_migration(tables)
        self.alembic_migrations.append(alembic_migration)

        return {
            "models": self.models,
            "alembic_migrations": self.alembic_migrations,
            "table_count": len(tables),
        }

    def _generate_alembic_migration(self, tables: dict[str, Any]) -> str:
        """Generate Alembic migration from table schemas."""
        migration_code = [
            '"""Initial schema migration.',
            "",
            "Revision ID: 001_initial",
            "Revises:",
            "Create Date: 2024-01-15",
            "",
            '"""',
            "from alembic import op",
            "import sqlalchemy as sa",
            "import sqlmodel",
            "from uuid import uuid4",
            "",
            "# revision identifiers, used by Alembic.",
            'revision = "001_initial"',
            "down_revision = None",
            "branch_labels = None",
            "depends_on = None",
            "",
            "",
            "def upgrade() -> None:",
            '    """Upgrade database schema."""',
        ]

        # Generate CREATE TABLE statements for each table
        for table_name, table_data in tables.items():
            migration_code.append(f"    # Create {table_name} table")
            migration_code.append("    op.create_table(")
            migration_code.append(f"        '{table_name}',")

            # Add columns
            for col in table_data.get("columns", []):
                col_line = self._generate_alembic_column(col)
                migration_code.append(f"        {col_line},")

            migration_code.append("    )")
            migration_code.append("")

            # Add indexes
            for _idx in table_data.get("indexes", []):
                migration_code.append(f"    # Index for {table_name}")
                migration_code.append("    # TODO: Add index creation")
                migration_code.append("")

        migration_code.extend(
            [
                "",
                "def downgrade() -> None:",
                '    """Downgrade database schema."""',
            ]
        )

        # Generate DROP TABLE statements
        for table_name in reversed(list(tables.keys())):
            migration_code.append(f"    op.drop_table('{table_name}')")

        return "\n".join(migration_code)

    def _generate_alembic_column(self, col: dict[str, Any]) -> str:
        """Generate Alembic column definition."""
        col_name = col["name"]
        col_type_str = col["type"].upper()

        # Map SQL type to SQLAlchemy type
        sa_type_map = {
            "UUID": "sa.UUID()",
            "TEXT": "sa.Text()",
            "VARCHAR": "sa.String(255)",
            "INTEGER": "sa.Integer()",
            "BIGINT": "sa.BigInteger()",
            "BOOLEAN": "sa.Boolean()",
            "TIMESTAMP": "sa.DateTime()",
            "TIMESTAMPTZ": "sa.DateTime(timezone=True)",
            "DATE": "sa.Date()",
            "FLOAT": "sa.Float()",
            "NUMERIC": "sa.Numeric()",
            "JSON": "sa.JSON()",
            "JSONB": "sa.JSON()",
        }

        sa_type = sa_type_map.get(col_type_str, "sa.String()")

        # Build column definition
        parts = [f"sa.Column('{col_name}', {sa_type}"]

        if col.get("primary_key"):
            parts.append("primary_key=True")
        if col.get("unique"):
            parts.append("unique=True")
        if col.get("not_null"):
            parts.append("nullable=False")

        return ", ".join(parts) + ")"

    def convert_rls_policies(
        self, rls_policies: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Convert Row-Level Security policies to FastAPI dependencies.

        Args:
            rls_policies: List of RLS policy definitions

        Returns:
            List of FastAPI dependency functions
        """
        dependencies = []

        for policy in rls_policies:
            policy_def = policy.get("definition", "")

            # Parse policy to understand the rule
            # This is a simplified conversion
            dependency = {
                "name": self._extract_policy_name(policy_def),
                "description": "Auto-generated RLS policy",
                "code": self._generate_rls_dependency(policy_def),
            }
            dependencies.append(dependency)

        return dependencies

    def _extract_policy_name(self, policy_def: str) -> str:
        """Extract policy name from definition."""
        import re

        match = re.search(r"CREATE POLICY\s+(\w+)", policy_def, re.IGNORECASE)
        if match:
            return match.group(1)
        return "custom_policy"

    def _generate_rls_dependency(self, policy_def: str) -> str:
        """Generate FastAPI dependency from RLS policy."""
        return '''
def check_row_level_security(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> bool:
    """
    Row-level security check.

    TODO: Implement custom RLS logic based on original policy:
    {policy_def}
    """
    # Add your custom security logic here
    return True
'''

    def generate_models_file(self) -> str:
        """Generate complete models.py file with all SQLModel definitions."""
        imports = [
            "from datetime import date, datetime",
            "from decimal import Decimal",
            "from typing import Any",
            "from uuid import UUID, uuid4",
            "",
            "from sqlmodel import Field, SQLModel",
            "",
        ]

        models_code = "\n\n".join(self.models.values())

        return "\n".join(imports) + "\n" + models_code
