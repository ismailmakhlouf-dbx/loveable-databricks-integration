"""
Project Scanner for Lovable projects.

Scans and analyzes the structure of Lovable projects from GitHub or ZIP files.
"""

import json
import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import httpx
from git import Repo

logger = logging.getLogger(__name__)


class ProjectScanner:
    """Scans and analyzes Lovable project structure."""

    def __init__(self, project_path: Path):
        """
        Initialize project scanner.

        Args:
            project_path: Path to the Lovable project directory
        """
        self.project_path = project_path
        self.project_name = project_path.name

    @classmethod
    async def from_url(cls, url: str, name: str | None = None) -> "ProjectScanner":
        """
        Create scanner from GitHub or ZIP URL.

        Args:
            url: GitHub repository URL or ZIP download URL
            name: Optional project name

        Returns:
            ProjectScanner instance

        Raises:
            ValueError: If URL is invalid or fetch fails
        """
        if "github.com" in url:
            return await cls._from_github(url, name)
        elif url.endswith(".zip"):
            return await cls._from_zip(url, name)
        else:
            raise ValueError(f"Unsupported URL format: {url}")

    @classmethod
    async def _from_github(cls, url: str, name: str | None = None) -> "ProjectScanner":
        """Clone from GitHub repository."""
        logger.info(f"Cloning from GitHub: {url}")

        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix="lovable_"))

        try:
            # Clone repository
            Repo.clone_from(url, temp_dir)
            logger.info(f"Repository cloned to: {temp_dir}")

            # Determine project name
            if name is None:
                name = url.rstrip("/").split("/")[-1].replace(".git", "")

            return cls(temp_dir)

        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            raise ValueError(f"Failed to clone repository: {e}") from e

    @classmethod
    async def _from_zip(cls, url: str, name: str | None = None) -> "ProjectScanner":
        """Download and extract ZIP file."""
        logger.info(f"Downloading ZIP from: {url}")

        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix="lovable_"))

        try:
            # Download ZIP file
            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

            # Save and extract ZIP
            zip_path = temp_dir / "project.zip"
            zip_path.write_bytes(response.content)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find the project root (usually in a subdirectory)
            subdirs = [d for d in temp_dir.iterdir() if d.is_dir()]
            project_root = subdirs[0] if len(subdirs) == 1 else temp_dir

            logger.info(f"ZIP extracted to: {project_root}")

            if name is None:
                name = project_root.name

            return cls(project_root)

        except Exception as e:
            logger.error(f"Failed to download/extract ZIP: {e}")
            raise ValueError(f"Failed to download/extract ZIP: {e}") from e

    def scan(self) -> dict[str, Any]:
        """
        Scan the project and extract metadata.

        Returns:
            Project metadata dictionary
        """
        logger.info(f"Scanning project: {self.project_path}")

        metadata = {
            "name": self.project_name,
            "path": str(self.project_path),
            "structure": self._analyze_structure(),
            "package_json": self._parse_package_json(),
            "frontend": self._scan_frontend(),
            "backend": self._scan_backend(),
            "database": self._scan_database(),
            "config": self._scan_config(),
        }

        logger.info(f"Project scan complete: {self.project_name}")
        return metadata

    def _analyze_structure(self) -> dict[str, Any]:
        """Analyze project directory structure."""
        structure = {
            "has_src": (self.project_path / "src").exists(),
            "has_components": (self.project_path / "src" / "components").exists(),
            "has_pages": (self.project_path / "src" / "pages").exists(),
            "has_supabase": (self.project_path / "supabase").exists(),
            "has_package_json": (self.project_path / "package.json").exists(),
        }

        logger.debug(f"Project structure: {structure}")
        return structure

    def _parse_package_json(self) -> dict[str, Any]:
        """Parse package.json for dependencies."""
        package_json_path = self.project_path / "package.json"

        if not package_json_path.exists():
            logger.warning("package.json not found")
            return {}

        try:
            with open(package_json_path) as f:
                data = json.load(f)

            dependencies = data.get("dependencies", {})
            dev_dependencies = data.get("devDependencies", {})

            return {
                "name": data.get("name"),
                "version": data.get("version"),
                "dependencies": dependencies,
                "devDependencies": dev_dependencies,
                "scripts": data.get("scripts", {}),
            }

        except Exception as e:
            logger.error(f"Failed to parse package.json: {e}")
            return {}

    def _scan_frontend(self) -> dict[str, Any]:
        """Scan frontend components and pages."""
        frontend_data: dict[str, Any] = {
            "components": [],
            "pages": [],
            "hooks": [],
            "utils": [],
        }

        # Scan components
        components_dir = self.project_path / "src" / "components"
        if components_dir.exists():
            frontend_data["components"] = self._find_files(components_dir, ["*.tsx", "*.jsx"])

        # Scan pages
        pages_dir = self.project_path / "src" / "pages"
        if pages_dir.exists():
            frontend_data["pages"] = self._find_files(pages_dir, ["*.tsx", "*.jsx"])

        # Scan hooks
        hooks_dir = self.project_path / "src" / "hooks"
        if hooks_dir.exists():
            frontend_data["hooks"] = self._find_files(hooks_dir, ["*.ts", "*.tsx"])

        return frontend_data

    def _scan_backend(self) -> dict[str, Any]:
        """Scan Supabase Edge Functions."""
        backend_data = {
            "edge_functions": [],
            "has_supabase_client": False,
        }

        # Scan edge functions
        functions_dir = self.project_path / "supabase" / "functions"
        if functions_dir.exists():
            backend_data["edge_functions"] = [
                str(f.relative_to(self.project_path))
                for f in functions_dir.iterdir()
                if f.is_dir() and not f.name.startswith("_")
            ]

        # Check for Supabase client usage
        integrations_dir = self.project_path / "src" / "integrations" / "supabase"
        if integrations_dir.exists():
            backend_data["has_supabase_client"] = True

        return backend_data

    def _scan_database(self) -> dict[str, Any]:
        """Scan database migrations and schema."""
        database_data = {
            "migrations": [],
            "has_seed_data": False,
        }

        # Scan migrations
        migrations_dir = self.project_path / "supabase" / "migrations"
        if migrations_dir.exists():
            database_data["migrations"] = self._find_files(migrations_dir, ["*.sql"])

        # Check for seed data
        seed_path = self.project_path / "supabase" / "seed.sql"
        if seed_path.exists():
            database_data["has_seed_data"] = True

        return database_data

    def _scan_config(self) -> dict[str, Any]:
        """Scan configuration files."""
        config_data = {
            "has_env_example": (self.project_path / ".env.example").exists(),
            "has_vite_config": (self.project_path / "vite.config.ts").exists(),
            "has_tailwind_config": (self.project_path / "tailwind.config.ts").exists(),
            "has_typescript_config": (self.project_path / "tsconfig.json").exists(),
        }

        return config_data

    def _find_files(self, directory: Path, patterns: list[str]) -> list[str]:
        """
        Find files matching patterns in directory.

        Args:
            directory: Directory to search
            patterns: List of glob patterns

        Returns:
            List of file paths relative to project root
        """
        files = []
        for pattern in patterns:
            for file_path in directory.rglob(pattern):
                if file_path.is_file():
                    files.append(str(file_path.relative_to(self.project_path)))

        return sorted(files)
