"""
Frontend Analyzer for React/TypeScript components.

Analyzes React components to extract:
- Component metadata (props, state, hooks)
- Supabase client usage patterns
- React Router routes
- API integration points
"""

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ComponentInfo:
    """Represents a React component's metadata."""

    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.is_page = False
        self.hooks: list[str] = []
        self.supabase_usage: list[str] = []
        self.api_calls: list[str] = []
        self.routes: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "path": str(self.path),
            "is_page": self.is_page,
            "hooks": self.hooks,
            "supabase_usage": self.supabase_usage,
            "api_calls": self.api_calls,
            "routes": self.routes,
        }


class FrontendAnalyzer:
    """Analyzes React/TypeScript frontend components."""

    def __init__(self, src_path: Path):
        """
        Initialize frontend analyzer.

        Args:
            src_path: Path to src directory
        """
        self.src_path = src_path
        self.components: dict[str, ComponentInfo] = {}
        self.pages: dict[str, ComponentInfo] = {}
        self.routes: list[dict[str, Any]] = []

    def analyze(self) -> dict[str, Any]:
        """
        Analyze all frontend components.

        Returns:
            Frontend metadata dictionary
        """
        logger.info(f"Analyzing frontend: {self.src_path}")

        if not self.src_path.exists():
            logger.warning(f"Source path does not exist: {self.src_path}")
            return {
                "components": {},
                "pages": {},
                "routes": [],
                "component_count": 0,
                "page_count": 0,
            }

        # Analyze components
        components_path = self.src_path / "components"
        if components_path.exists():
            self._analyze_directory(components_path, is_page=False)

        # Analyze pages
        pages_path = self.src_path / "pages"
        if pages_path.exists():
            self._analyze_directory(pages_path, is_page=True)

        # Analyze routes
        self._analyze_routes()

        metadata = {
            "components": {name: comp.to_dict() for name, comp in self.components.items()},
            "pages": {name: page.to_dict() for name, page in self.pages.items()},
            "routes": self.routes,
            "component_count": len(self.components),
            "page_count": len(self.pages),
            "total_supabase_usage": sum(
                len(comp.supabase_usage)
                for comp in list(self.components.values()) + list(self.pages.values())
            ),
        }

        logger.info(
            f"Frontend analysis complete: {len(self.components)} components, {len(self.pages)} pages"
        )
        return metadata

    def _analyze_directory(self, directory: Path, is_page: bool = False) -> None:
        """Recursively analyze components in a directory."""
        for file_path in directory.rglob("*.tsx"):
            if file_path.is_file():
                self._analyze_component(file_path, is_page)

        for file_path in directory.rglob("*.jsx"):
            if file_path.is_file():
                self._analyze_component(file_path, is_page)

    def _analyze_component(self, file_path: Path, is_page: bool = False) -> None:
        """Analyze a single component file."""
        component_name = file_path.stem
        logger.debug(f"Analyzing component: {component_name}")

        comp_info = ComponentInfo(component_name, file_path)
        comp_info.is_page = is_page

        try:
            with open(file_path) as f:
                code = f.read()

            # Analyze the code
            self._analyze_component_code(code, comp_info)

            # Store component
            if is_page:
                self.pages[component_name] = comp_info
            else:
                self.components[component_name] = comp_info

        except Exception as e:
            logger.error(f"Failed to analyze component {component_name}: {e}")

    def _analyze_component_code(self, code: str, comp_info: ComponentInfo) -> None:
        """Analyze component code."""
        # Detect React hooks
        comp_info.hooks = self._detect_hooks(code)

        # Detect Supabase usage
        comp_info.supabase_usage = self._detect_supabase_usage(code)

        # Detect API calls
        comp_info.api_calls = self._detect_api_calls(code)

        # Detect routes (for Route components)
        comp_info.routes = self._detect_routes(code)

    def _detect_hooks(self, code: str) -> list[str]:
        """Detect React hooks usage."""
        hooks = []

        # Common hooks
        hook_patterns = [
            r"useState",
            r"useEffect",
            r"useContext",
            r"useReducer",
            r"useCallback",
            r"useMemo",
            r"useRef",
            r"useQuery",
            r"useMutation",
            r"useNavigate",
            r"useParams",
            r"useSearchParams",
        ]

        for pattern in hook_patterns:
            if re.search(rf"\b{pattern}\s*\(", code):
                hooks.append(pattern)

        return hooks

    def _detect_supabase_usage(self, code: str) -> list[str]:
        """Detect Supabase client usage patterns."""
        usage = []

        # Supabase import
        if "from '@/integrations/supabase" in code or 'from "@/integrations/supabase' in code:
            usage.append("supabase_client_import")

        # Auth operations
        if re.search(r"supabase\.auth\.", code):
            usage.append("auth")

        # Database operations
        if re.search(r"supabase\.from\(", code):
            usage.append("database")

            # Specific operations
            if ".select(" in code:
                usage.append("select")
            if ".insert(" in code:
                usage.append("insert")
            if ".update(" in code:
                usage.append("update")
            if ".delete(" in code:
                usage.append("delete")

        # Realtime
        if re.search(r"supabase\.channel\(", code) or ".subscribe(" in code:
            usage.append("realtime")

        # Storage
        if re.search(r"supabase\.storage\.", code):
            usage.append("storage")

        return list(set(usage))  # Remove duplicates

    def _detect_api_calls(self, code: str) -> list[str]:
        """Detect API calls (fetch, axios, etc.)."""
        api_calls = []

        # fetch calls
        if re.search(r"\bfetch\s*\(", code):
            api_calls.append("fetch")

        # axios
        if "axios" in code:
            api_calls.append("axios")

        # React Query
        if "useQuery" in code or "useMutation" in code:
            api_calls.append("react-query")

        return api_calls

    def _detect_routes(self, code: str) -> list[str]:
        """Detect React Router routes."""
        routes = []

        # Pattern: <Route path="..." element={...} />
        route_pattern = r'<Route\s+path=["\'](.*?)["\']'
        for match in re.finditer(route_pattern, code):
            routes.append(match.group(1))

        return routes

    def _analyze_routes(self) -> None:
        """Analyze routing configuration."""
        # Look for App.tsx or main routing file
        app_files = ["App.tsx", "App.jsx", "main.tsx", "main.jsx"]

        for app_file in app_files:
            app_path = self.src_path / app_file
            if app_path.exists():
                try:
                    with open(app_path) as f:
                        code = f.read()

                    # Extract routes
                    route_pattern = r'<Route\s+path=["\'](.*?)["\']\s+element=\{<(\w+)'
                    for match in re.finditer(route_pattern, code):
                        path = match.group(1)
                        component = match.group(2)

                        self.routes.append(
                            {
                                "path": path,
                                "component": component,
                            }
                        )

                except Exception as e:
                    logger.error(f"Failed to analyze routes in {app_file}: {e}")
