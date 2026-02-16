"""Pytest configuration and fixtures."""

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_project_dir():
    """Create temporary project directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_project_metadata():
    """Sample project metadata."""
    return {
        "project_id": "proj_test123",
        "name": "test-project",
        "url": "https://github.com/test/project",
        "status": "imported",
        "backend": {
            "functions": {
                "get-users": {
                    "name": "get-users",
                    "http_methods": ["GET"],
                    "database_operations": [
                        {"type": "SELECT", "table": "users"}
                    ],
                    "auth_required": True,
                    "llm_apis": [],
                }
            },
            "function_count": 1,
        },
        "database": {
            "tables": {
                "users": {
                    "name": "users",
                    "columns": [
                        {
                            "name": "id",
                            "type": "UUID",
                            "primary_key": True,
                            "not_null": True,
                            "default": "gen_random_uuid()",
                        },
                        {
                            "name": "email",
                            "type": "TEXT",
                            "not_null": True,
                            "unique": True,
                        },
                    ],
                }
            },
            "table_count": 1,
        },
        "frontend": {
            "components": {},
            "component_count": 0,
        },
    }
