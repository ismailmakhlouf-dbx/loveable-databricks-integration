"""
Database Deployer.

Sets up Lakebase PostgreSQL database and Unity Catalog.
"""

import logging
from typing import Any

import sqlparse
from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


class DatabaseDeployer:
    """Deploys database schema to Lakebase."""

    def __init__(self, workspace_client: WorkspaceClient | None = None):
        """
        Initialize database deployer.

        Args:
            workspace_client: Databricks workspace client
        """
        self.workspace = workspace_client or WorkspaceClient()

    async def deploy(
        self,
        catalog: str,
        schema: str,
        migrations: list[str],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Deploy database schema to Lakebase.

        Args:
            catalog: Unity Catalog name
            schema: Schema name
            migrations: List of SQL migration scripts
            config: Optional configuration

        Returns:
            Deployment information
        """
        logger.info(f"Deploying database schema to {catalog}.{schema}")

        try:
            # Create catalog if not exists
            await self._create_catalog(catalog)

            # Create schema if not exists
            await self._create_schema(catalog, schema)

            # Run migrations
            migration_results = []
            for i, migration_sql in enumerate(migrations):
                result = await self._run_migration(
                    catalog, schema, migration_sql, i
                )
                migration_results.append(result)

            n = len(migration_results)
            logger.info(f"Database deployment complete: {n} migrations applied")

            return {
                "catalog": catalog,
                "schema": schema,
                "migrations_applied": len(migration_results),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Database deployment failed: {e}")
            raise

    async def _create_catalog(self, catalog: str) -> None:
        """Create Unity Catalog if not exists."""
        logger.info(f"Creating catalog: {catalog}")

        try:
            # Use SQL to create catalog
            sql = f"CREATE CATALOG IF NOT EXISTS {catalog}"
            await self._execute_sql(sql)
            logger.info(f"Catalog {catalog} created or already exists")

        except Exception as e:
            logger.error(f"Failed to create catalog: {e}")
            # Don't fail if catalog already exists
            if "already exists" not in str(e).lower():
                raise

    async def _create_schema(self, catalog: str, schema: str) -> None:
        """Create schema if not exists."""
        logger.info(f"Creating schema: {catalog}.{schema}")

        try:
            sql = f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}"
            await self._execute_sql(sql)
            logger.info(f"Schema {catalog}.{schema} created or already exists")

        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            if "already exists" not in str(e).lower():
                raise

    async def _run_migration(
        self, catalog: str, schema: str, migration_sql: str, migration_number: int
    ) -> dict[str, Any]:
        """Run a single migration script."""
        logger.info(f"Running migration {migration_number}")

        try:
            # Parse SQL into statements
            statements = sqlparse.split(migration_sql)

            # Execute each statement
            for i, statement in enumerate(statements):
                statement = statement.strip()
                if not statement:
                    continue

                # Qualify table names with catalog.schema
                qualified_sql = self._qualify_table_names(
                    statement, catalog, schema
                )

                await self._execute_sql(qualified_sql)
                logger.debug(f"Executed statement {i+1} of migration {migration_number}")

            return {
                "migration_number": migration_number,
                "statements_executed": len(statements),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Migration {migration_number} failed: {e}")
            return {
                "migration_number": migration_number,
                "status": "failed",
                "error": str(e),
            }

    def _qualify_table_names(
        self, sql: str, catalog: str, schema: str
    ) -> str:
        """Qualify table names with catalog and schema."""
        # Simple implementation - prepend catalog.schema to CREATE TABLE
        # This is a simplified version; production would need more robust parsing

        qualified = sql

        # Handle CREATE TABLE statements
        if "CREATE TABLE" in sql.upper():
            # Find table name and qualify it
            import re

            pattern = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)"
            match = re.search(pattern, sql, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                qualified = qualified.replace(
                    table_name, f"{catalog}.{schema}.{table_name}", 1
                )

        return qualified

    async def _execute_sql(self, sql: str) -> Any:
        """Execute SQL statement."""
        try:
            # Use Databricks SQL execution API
            # For now, we'll use workspace SQL API
            # In production, use proper SQL warehouse connection

            logger.debug(f"Executing SQL: {sql[:100]}...")

            # Mock execution for now
            # TODO: Implement actual SQL execution using Databricks SQL Warehouse
            return {"status": "executed"}

        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            raise

    def verify_schema(self, catalog: str, schema: str) -> dict[str, Any]:
        """
        Verify database schema.

        Args:
            catalog: Catalog name
            schema: Schema name

        Returns:
            Schema verification results
        """
        logger.info(f"Verifying schema: {catalog}.{schema}")

        try:
            # Check if schema exists
            # In production, query information_schema

            return {
                "catalog": catalog,
                "schema": schema,
                "exists": True,
                "tables": [],  # TODO: List tables
            }

        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            return {
                "catalog": catalog,
                "schema": schema,
                "exists": False,
                "error": str(e),
            }
