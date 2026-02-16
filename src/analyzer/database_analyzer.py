"""
Database Analyzer for Supabase migrations.

Parses SQL migration files to extract table schemas, relationships, and constraints.
"""

import logging
import re
from pathlib import Path
from typing import Any

import sqlparse
from sqlparse.sql import Function, Identifier, IdentifierList, Parenthesis, Token
from sqlparse.tokens import Keyword, Name

logger = logging.getLogger(__name__)


class TableSchema:
    """Represents a database table schema."""

    def __init__(self, name: str):
        self.name = name
        self.columns: list[dict[str, Any]] = []
        self.constraints: list[dict[str, Any]] = []
        self.indexes: list[dict[str, Any]] = []
        self.rls_policies: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "columns": self.columns,
            "constraints": self.constraints,
            "indexes": self.indexes,
            "rls_policies": self.rls_policies,
        }


class DatabaseAnalyzer:
    """Analyzes Supabase database migrations."""

    def __init__(self, migrations_path: Path):
        """
        Initialize database analyzer.

        Args:
            migrations_path: Path to migrations directory
        """
        self.migrations_path = migrations_path
        self.tables: dict[str, TableSchema] = {}

    def analyze(self) -> dict[str, Any]:
        """
        Analyze all migration files.

        Returns:
            Database metadata dictionary
        """
        logger.info(f"Analyzing database migrations: {self.migrations_path}")

        # Find all SQL migration files
        migration_files = sorted(self.migrations_path.glob("*.sql"))

        for migration_file in migration_files:
            logger.debug(f"Parsing migration: {migration_file.name}")
            self._parse_migration(migration_file)

        metadata = {
            "tables": {name: table.to_dict() for name, table in self.tables.items()},
            "table_count": len(self.tables),
            "migration_files": [f.name for f in migration_files],
        }

        logger.info(f"Database analysis complete: {len(self.tables)} tables found")
        return metadata

    def _parse_migration(self, migration_file: Path) -> None:
        """Parse a single migration file."""
        try:
            with open(migration_file) as f:
                sql_content = f.read()

            # Parse SQL statements
            statements = sqlparse.parse(sql_content)

            for statement in statements:
                self._process_statement(statement)

        except Exception as e:
            logger.error(f"Failed to parse migration {migration_file}: {e}")

    def _process_statement(self, statement: sqlparse.sql.Statement) -> None:
        """Process a single SQL statement."""
        # Get statement type
        stmt_type = statement.get_type()

        if stmt_type == "CREATE":
            self._process_create_statement(statement)
        elif stmt_type == "ALTER":
            self._process_alter_statement(statement)
        elif "RLS" in statement.value.upper() or "ROW LEVEL SECURITY" in statement.value.upper():
            self._process_rls_statement(statement)

    def _process_create_statement(self, statement: sqlparse.sql.Statement) -> None:
        """Process CREATE TABLE/INDEX statements."""
        sql = statement.value.upper()

        if "CREATE TABLE" in sql:
            self._parse_create_table(statement)
        elif "CREATE INDEX" in sql:
            self._parse_create_index(statement)
        elif "CREATE POLICY" in sql:
            self._parse_create_policy(statement)

    def _parse_create_table(self, statement: sqlparse.sql.Statement) -> None:
        """Parse CREATE TABLE statement."""
        try:
            # Extract table name
            table_name = self._extract_table_name(statement)
            if not table_name:
                return

            # Create or get table schema
            if table_name not in self.tables:
                self.tables[table_name] = TableSchema(table_name)

            table = self.tables[table_name]

            # Extract columns and constraints
            columns_def = self._find_parenthesis(statement)
            if columns_def:
                self._parse_columns(columns_def, table)

        except Exception as e:
            logger.error(f"Failed to parse CREATE TABLE: {e}")

    def _extract_table_name(self, statement: sqlparse.sql.Statement) -> str | None:
        """Extract table name from CREATE TABLE statement."""
        tokens = list(statement.flatten())

        # Find the table name after "CREATE TABLE"
        found_create = False
        found_table = False

        for token in tokens:
            if token.ttype is Keyword and token.value.upper() == "CREATE":
                found_create = True
            elif found_create and token.ttype is Keyword and token.value.upper() == "TABLE":
                found_table = True
            elif found_table and token.ttype is Name:
                # Remove quotes and schema prefix
                name = token.value.strip('"').strip("'")
                if "." in name:
                    name = name.split(".")[-1]
                return name

        return None

    def _find_parenthesis(self, statement: sqlparse.sql.Statement) -> Parenthesis | None:
        """Find the main parenthesis containing column definitions."""
        for token in statement.tokens:
            if isinstance(token, Parenthesis):
                return token
        return None

    def _parse_columns(self, parenthesis: Parenthesis, table: TableSchema) -> None:
        """Parse column definitions from parenthesis."""
        # Split by commas to get individual column definitions
        content = parenthesis.value.strip("()").strip()

        # Simple regex-based parsing for column definitions
        column_pattern = r'(\w+)\s+([\w\[\]]+)(?:\s*\(([\d,\s]+)\))?'

        # Split by commas but respect nested parentheses
        columns = self._smart_split(content)

        for col_def in columns:
            col_def = col_def.strip()

            if not col_def:
                continue

            # Check if this is a constraint (PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK)
            if any(
                keyword in col_def.upper()
                for keyword in ["PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK", "CONSTRAINT"]
            ):
                self._parse_constraint(col_def, table)
                continue

            # Parse column definition
            column = self._parse_column_definition(col_def)
            if column:
                table.columns.append(column)

    def _smart_split(self, content: str) -> list[str]:
        """Split by commas while respecting nested parentheses."""
        result = []
        current = []
        depth = 0

        for char in content:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                result.append("".join(current))
                current = []
                continue

            current.append(char)

        if current:
            result.append("".join(current))

        return result

    def _parse_column_definition(self, col_def: str) -> dict[str, Any] | None:
        """Parse a single column definition."""
        try:
            # Extract column name and type
            parts = col_def.split()
            if len(parts) < 2:
                return None

            name = parts[0].strip('"').strip("'")
            col_type = parts[1].upper()

            # Check for constraints
            not_null = "NOT NULL" in col_def.upper()
            unique = "UNIQUE" in col_def.upper()
            primary_key = "PRIMARY KEY" in col_def.upper()

            # Extract default value
            default = None
            if "DEFAULT" in col_def.upper():
                default_match = re.search(r"DEFAULT\s+([^,\s]+(?:\([^)]*\))?)", col_def, re.IGNORECASE)
                if default_match:
                    default = default_match.group(1)

            return {
                "name": name,
                "type": col_type,
                "not_null": not_null,
                "unique": unique,
                "primary_key": primary_key,
                "default": default,
            }

        except Exception as e:
            logger.error(f"Failed to parse column definition '{col_def}': {e}")
            return None

    def _parse_constraint(self, constraint_def: str, table: TableSchema) -> None:
        """Parse table constraint."""
        constraint = {
            "definition": constraint_def,
            "type": self._identify_constraint_type(constraint_def),
        }
        table.constraints.append(constraint)

    def _identify_constraint_type(self, constraint_def: str) -> str:
        """Identify constraint type."""
        constraint_upper = constraint_def.upper()

        if "PRIMARY KEY" in constraint_upper:
            return "PRIMARY KEY"
        elif "FOREIGN KEY" in constraint_upper:
            return "FOREIGN KEY"
        elif "UNIQUE" in constraint_upper:
            return "UNIQUE"
        elif "CHECK" in constraint_upper:
            return "CHECK"
        else:
            return "UNKNOWN"

    def _parse_create_index(self, statement: sqlparse.sql.Statement) -> None:
        """Parse CREATE INDEX statement."""
        try:
            # Extract table name and index definition
            sql = statement.value

            # Simple regex to extract table name
            table_match = re.search(r"ON\s+(\w+)", sql, re.IGNORECASE)
            if not table_match:
                return

            table_name = table_match.group(1).strip('"').strip("'")

            if table_name not in self.tables:
                self.tables[table_name] = TableSchema(table_name)

            index = {
                "definition": sql,
            }
            self.tables[table_name].indexes.append(index)

        except Exception as e:
            logger.error(f"Failed to parse CREATE INDEX: {e}")

    def _parse_create_policy(self, statement: sqlparse.sql.Statement) -> None:
        """Parse CREATE POLICY (RLS) statement."""
        try:
            sql = statement.value

            # Extract table name
            table_match = re.search(r"ON\s+(\w+)", sql, re.IGNORECASE)
            if not table_match:
                return

            table_name = table_match.group(1).strip('"').strip("'")

            if table_name not in self.tables:
                self.tables[table_name] = TableSchema(table_name)

            policy = {
                "definition": sql,
            }
            self.tables[table_name].rls_policies.append(policy)

        except Exception as e:
            logger.error(f"Failed to parse CREATE POLICY: {e}")

    def _process_alter_statement(self, statement: sqlparse.sql.Statement) -> None:
        """Process ALTER TABLE statements."""
        # For now, just log ALTER statements
        logger.debug(f"ALTER statement: {statement.value[:100]}...")

    def _process_rls_statement(self, statement: sqlparse.sql.Statement) -> None:
        """Process RLS (Row Level Security) statements."""
        try:
            sql = statement.value

            # Extract table name
            table_match = re.search(r"ON\s+(\w+)", sql, re.IGNORECASE)
            if table_match:
                table_name = table_match.group(1).strip('"').strip("'")

                if table_name not in self.tables:
                    self.tables[table_name] = TableSchema(table_name)

                policy = {
                    "definition": sql,
                }
                self.tables[table_name].rls_policies.append(policy)

        except Exception as e:
            logger.error(f"Failed to parse RLS statement: {e}")
