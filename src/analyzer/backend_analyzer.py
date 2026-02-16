"""
Backend Analyzer for Supabase Edge Functions.

Analyzes TypeScript/Deno Edge Functions to extract:
- Function signatures and parameters
- Database operations (CRUD patterns)
- Authentication requirements
- External API calls
- LLM API usage
"""

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EdgeFunctionInfo:
    """Represents an Edge Function's metadata."""

    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.has_handler = False
        self.http_methods: list[str] = []
        self.database_operations: list[dict[str, Any]] = []
        self.auth_required = False
        self.external_apis: list[str] = []
        self.llm_apis: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "path": str(self.path),
            "has_handler": self.has_handler,
            "http_methods": self.http_methods,
            "database_operations": self.database_operations,
            "auth_required": self.auth_required,
            "external_apis": self.external_apis,
            "llm_apis": self.llm_apis,
        }


class BackendAnalyzer:
    """Analyzes Supabase Edge Functions."""

    def __init__(self, functions_path: Path):
        """
        Initialize backend analyzer.

        Args:
            functions_path: Path to supabase/functions directory
        """
        self.functions_path = functions_path
        self.functions: dict[str, EdgeFunctionInfo] = {}

    def analyze(self) -> dict[str, Any]:
        """
        Analyze all Edge Functions.

        Returns:
            Backend metadata dictionary
        """
        logger.info(f"Analyzing Edge Functions: {self.functions_path}")

        if not self.functions_path.exists():
            logger.warning(f"Functions path does not exist: {self.functions_path}")
            return {
                "functions": {},
                "function_count": 0,
            }

        # Find all function directories
        for func_dir in self.functions_path.iterdir():
            if func_dir.is_dir() and not func_dir.name.startswith("_"):
                self._analyze_function(func_dir)

        metadata = {
            "functions": {name: func.to_dict() for name, func in self.functions.items()},
            "function_count": len(self.functions),
            "total_db_operations": sum(
                len(func.database_operations) for func in self.functions.values()
            ),
            "functions_with_auth": sum(1 for func in self.functions.values() if func.auth_required),
            "llm_usage_detected": any(func.llm_apis for func in self.functions.values()),
        }

        logger.info(f"Backend analysis complete: {len(self.functions)} functions found")
        return metadata

    def _analyze_function(self, func_dir: Path) -> None:
        """Analyze a single Edge Function."""
        func_name = func_dir.name
        logger.debug(f"Analyzing function: {func_name}")

        # Look for index.ts or index.js
        index_path = func_dir / "index.ts"
        if not index_path.exists():
            index_path = func_dir / "index.js"

        if not index_path.exists():
            logger.warning(f"No index file found for function: {func_name}")
            return

        func_info = EdgeFunctionInfo(func_name, index_path)

        try:
            with open(index_path) as f:
                code = f.read()

            # Analyze the code
            self._analyze_code(code, func_info)

            self.functions[func_name] = func_info

        except Exception as e:
            logger.error(f"Failed to analyze function {func_name}: {e}")

    def _analyze_code(self, code: str, func_info: EdgeFunctionInfo) -> None:
        """Analyze Edge Function code."""
        # Check for handler function
        if "export" in code and ("handler" in code or "serve(" in code):
            func_info.has_handler = True

        # Detect HTTP methods
        func_info.http_methods = self._detect_http_methods(code)

        # Detect database operations
        func_info.database_operations = self._detect_database_operations(code)

        # Detect authentication
        func_info.auth_required = self._detect_auth(code)

        # Detect external APIs
        func_info.external_apis = self._detect_external_apis(code)

        # Detect LLM APIs
        func_info.llm_apis = self._detect_llm_apis(code)

    def _detect_http_methods(self, code: str) -> list[str]:
        """Detect HTTP methods used."""
        methods = []

        # Check for method checks in code
        if re.search(r'method\s*===?\s*["\']GET["\']', code, re.IGNORECASE):
            methods.append("GET")
        if re.search(r'method\s*===?\s*["\']POST["\']', code, re.IGNORECASE):
            methods.append("POST")
        if re.search(r'method\s*===?\s*["\']PUT["\']', code, re.IGNORECASE):
            methods.append("PUT")
        if re.search(r'method\s*===?\s*["\']DELETE["\']', code, re.IGNORECASE):
            methods.append("DELETE")
        if re.search(r'method\s*===?\s*["\']PATCH["\']', code, re.IGNORECASE):
            methods.append("PATCH")

        # If no explicit method checks, assume POST (common for Edge Functions)
        if not methods:
            methods = ["POST"]

        return methods

    def _detect_database_operations(self, code: str) -> list[dict[str, Any]]:
        """Detect Supabase database operations."""
        operations = []

        # Pattern: supabase.from('table').select(...)
        select_pattern = r"supabase\.from\(['\"](\w+)['\"]\)\.select\("
        for match in re.finditer(select_pattern, code):
            operations.append(
                {
                    "type": "SELECT",
                    "table": match.group(1),
                }
            )

        # Pattern: supabase.from('table').insert(...)
        insert_pattern = r"supabase\.from\(['\"](\w+)['\"]\)\.insert\("
        for match in re.finditer(insert_pattern, code):
            operations.append(
                {
                    "type": "INSERT",
                    "table": match.group(1),
                }
            )

        # Pattern: supabase.from('table').update(...)
        update_pattern = r"supabase\.from\(['\"](\w+)['\"]\)\.update\("
        for match in re.finditer(update_pattern, code):
            operations.append(
                {
                    "type": "UPDATE",
                    "table": match.group(1),
                }
            )

        # Pattern: supabase.from('table').delete(...)
        delete_pattern = r"supabase\.from\(['\"](\w+)['\"]\)\.delete\("
        for match in re.finditer(delete_pattern, code):
            operations.append(
                {
                    "type": "DELETE",
                    "table": match.group(1),
                }
            )

        # Pattern: supabase.from('table').upsert(...)
        upsert_pattern = r"supabase\.from\(['\"](\w+)['\"]\)\.upsert\("
        for match in re.finditer(upsert_pattern, code):
            operations.append(
                {
                    "type": "UPSERT",
                    "table": match.group(1),
                }
            )

        return operations

    def _detect_auth(self, code: str) -> bool:
        """Detect authentication usage."""
        auth_patterns = [
            r"supabase\.auth\.getUser\(",
            r"supabase\.auth\.getSession\(",
            r"req\.headers\.get\(['\"]authorization['\"]\)",
            r"Authorization",
        ]

        for pattern in auth_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True

        return False

    def _detect_external_apis(self, code: str) -> list[str]:
        """Detect external API calls."""
        apis = []

        # Look for fetch calls
        fetch_pattern = r"fetch\(['\"]([^'\"]+)['\"]\)"
        for match in re.finditer(fetch_pattern, code):
            url = match.group(1)
            if url.startswith("http"):
                # Extract domain
                domain_match = re.search(r"https?://([^/]+)", url)
                if domain_match:
                    apis.append(domain_match.group(1))

        return list(set(apis))  # Remove duplicates

    def _detect_llm_apis(self, code: str) -> list[dict[str, Any]]:
        """Detect LLM API usage (OpenAI, Anthropic, etc.)."""
        llm_apis = []

        # OpenAI
        if "openai" in code.lower():
            # Extract model name
            model_pattern = r'model:\s*["\']([^"\']+)["\']'
            models = re.findall(model_pattern, code)

            llm_apis.append(
                {
                    "provider": "OpenAI",
                    "models": models if models else ["gpt-4"],  # Default assumption
                    "endpoints": self._extract_openai_endpoints(code),
                }
            )

        # Anthropic
        if "anthropic" in code.lower() or "claude" in code.lower():
            model_pattern = r'model:\s*["\']([^"\']+)["\']'
            models = re.findall(model_pattern, code)

            llm_apis.append(
                {
                    "provider": "Anthropic",
                    "models": models if models else ["claude-3-sonnet"],  # Default
                    "endpoints": ["messages"],
                }
            )

        # Generic LLM API detection
        if re.search(r'(completion|chat|generate)', code, re.IGNORECASE):
            if not llm_apis:  # Only add if not already detected
                llm_apis.append(
                    {
                        "provider": "Unknown",
                        "models": [],
                        "endpoints": ["completion"],
                    }
                )

        return llm_apis

    def _extract_openai_endpoints(self, code: str) -> list[str]:
        """Extract OpenAI endpoint types."""
        endpoints = []

        if "chat.completions" in code:
            endpoints.append("chat.completions")
        if "completions" in code:
            endpoints.append("completions")
        if "embeddings" in code:
            endpoints.append("embeddings")

        return endpoints if endpoints else ["chat.completions"]
