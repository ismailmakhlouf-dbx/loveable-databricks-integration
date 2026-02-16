"""
Edge Function Converter.

Converts Supabase Edge Functions (TypeScript/Deno) to FastAPI routes (Python).
This is the most complex transformation in the system.
"""

import logging
import re
from typing import Any

from .llm_converter import LLMConverter
from .type_converter import TypeConverter

logger = logging.getLogger(__name__)


class EdgeFunctionConverter:
    """Converts Supabase Edge Functions to FastAPI routes."""

    def __init__(self) -> None:
        """Initialize converter."""
        self.type_converter = TypeConverter()
        self.llm_converter = LLMConverter()
        self.converted_functions: list[dict[str, Any]] = []

    def convert_function(
        self, func_name: str, ts_code: str, func_info: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Convert a single Edge Function to FastAPI route.

        Args:
            func_name: Name of the function
            ts_code: TypeScript source code
            func_info: Metadata from backend analyzer

        Returns:
            Dictionary with converted Python code and metadata
        """
        logger.info(f"Converting Edge Function: {func_name}")

        # Extract function signature and body (reserved for future use)
        _ = re.search(
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)|"
            r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
            ts_code,
            re.DOTALL,
        )

        # Detect HTTP methods
        http_methods = func_info.get("http_methods", ["POST"])

        # Detect database operations
        db_operations = func_info.get("database_operations", [])

        # Detect auth requirement
        needs_auth = func_info.get("auth_required", False)

        # Convert LLM calls
        converted_code, llm_conversions = self.llm_converter.detect_and_convert_llm_calls(
            ts_code
        )

        # Generate FastAPI route
        fastapi_code = self._generate_fastapi_route(
            func_name=func_name,
            http_methods=http_methods,
            db_operations=db_operations,
            needs_auth=needs_auth,
            ts_code=ts_code,
            llm_conversions=llm_conversions,
        )

        # Generate Pydantic models
        pydantic_models = self._extract_and_convert_types(ts_code)

        conversion_result = {
            "function_name": func_name,
            "fastapi_code": fastapi_code,
            "pydantic_models": pydantic_models,
            "http_methods": http_methods,
            "db_operations": db_operations,
            "needs_auth": needs_auth,
            "llm_conversions": llm_conversions,
        }

        self.converted_functions.append(conversion_result)
        return conversion_result

    def _generate_fastapi_route(
        self,
        func_name: str,
        http_methods: list[str],
        db_operations: list[dict[str, Any]],
        needs_auth: bool,
        ts_code: str,
        llm_conversions: list[dict[str, Any]],
    ) -> str:
        """Generate FastAPI route code."""
        # Convert function name to route path
        route_path = f"/{func_name.replace('_', '-')}"

        # Determine primary HTTP method
        primary_method = http_methods[0].lower() if http_methods else "post"

        # Generate imports
        imports = [
            "from fastapi import APIRouter, HTTPException, Depends",
            "from sqlmodel import Session, select",
            "from typing import Any",
            "",
        ]

        if needs_auth:
            imports.append("from ..auth import get_current_user")

        if db_operations:
            imports.append("from ..database import get_session")

        # Generate router
        router_code = [
            "",
            "router = APIRouter()",
            "",
        ]

        # Generate function signature
        func_signature = [f'@router.{primary_method}("{route_path}")']

        # Build function parameters
        params = []

        # Add request body parameter
        params.append("request_data: dict[str, Any]")

        # Add session dependency if DB operations exist
        if db_operations:
            params.append("session: Session = Depends(get_session)")

        # Add auth dependency if needed
        if needs_auth:
            params.append("current_user: dict = Depends(get_current_user)")

        # Generate function body
        func_body = self._generate_function_body(
            func_name=func_name,
            db_operations=db_operations,
            ts_code=ts_code,
            llm_conversions=llm_conversions,
        )

        # Assemble the route
        route_code = "\n".join(imports + router_code + func_signature)
        route_code += f"\nasync def {func_name}(\n"
        route_code += ",\n".join(f"    {param}" for param in params)
        route_code += "\n) -> dict[str, Any]:\n"
        route_code += f'    """\n    {func_name.replace("_", " ").title()}.\n\n'
        route_code += "    Auto-generated from Supabase Edge Function.\n"
        route_code += '    """\n'
        route_code += func_body

        return route_code

    def _generate_function_body(
        self,
        func_name: str,
        db_operations: list[dict[str, Any]],
        ts_code: str,
        llm_conversions: list[dict[str, Any]],
    ) -> str:
        """Generate the function body based on detected patterns."""
        body_lines = ["    try:"]

        # Extract request data
        body_lines.append("        # Extract request data")

        # Detect what fields are accessed from request
        field_pattern = r"(?:const|let|var)\s+\{([^}]+)\}\s*=\s*(?:await\s+)?req\.json\(\)"
        field_match = re.search(field_pattern, ts_code)

        if field_match:
            fields = [f.strip() for f in field_match.group(1).split(",")]
            for field in fields:
                body_lines.append(f'        {field} = request_data.get("{field}")')
        else:
            # Generic extraction
            body_lines.append("        # TODO: Extract specific fields from request_data")

        body_lines.append("")

        # Generate database operations
        if db_operations:
            body_lines.append("        # Database operations")
            for op in db_operations:
                op_type = op["type"]
                table_name = op["table"]
                model_name = "".join(word.capitalize() for word in table_name.split("_"))

                if op_type == "SELECT":
                    body_lines.append(f"        stmt = select({model_name})")
                    body_lines.append("        result = session.exec(stmt).all()")
                elif op_type == "INSERT":
                    body_lines.append(f"        new_item = {model_name}(**request_data)")
                    body_lines.append("        session.add(new_item)")
                    body_lines.append("        session.commit()")
                    body_lines.append("        session.refresh(new_item)")
                    body_lines.append("        result = new_item")
                elif op_type == "UPDATE":
                    body_lines.append(
                        f"        stmt = select({model_name}).where({model_name}.id == item_id)"
                    )
                    body_lines.append("        item = session.exec(stmt).first()")
                    body_lines.append("        if not item:")
                    body_lines.append(
                        '            raise HTTPException(status_code=404, detail="Item not found")'
                    )
                    body_lines.append("        for key, value in request_data.items():")
                    body_lines.append("            setattr(item, key, value)")
                    body_lines.append("        session.commit()")
                    body_lines.append("        session.refresh(item)")
                    body_lines.append("        result = item")
                elif op_type == "DELETE":
                    body_lines.append(
                        f"        stmt = select({model_name}).where({model_name}.id == item_id)"
                    )
                    body_lines.append("        item = session.exec(stmt).first()")
                    body_lines.append("        if not item:")
                    body_lines.append(
                        '            raise HTTPException(status_code=404, detail="Item not found")'
                    )
                    body_lines.append("        session.delete(item)")
                    body_lines.append("        session.commit()")
                    body_lines.append('        result = {"success": True}')

            body_lines.append("")

        # Generate LLM calls if detected
        if llm_conversions:
            body_lines.append("        # LLM API calls")
            body_lines.append("        # TODO: Implement LLM call logic")
            body_lines.append(
                "        # Use workspace.serving_endpoints.query() for Databricks models"
            )
            body_lines.append("")

        # Return response
        body_lines.append("        return {")
        body_lines.append('            "success": True,')
        if db_operations:
            body_lines.append('            "data": result,')
        body_lines.append("        }")

        # Error handling
        body_lines.append("    except Exception as e:")
        body_lines.append("        raise HTTPException(")
        body_lines.append("            status_code=500,")
        body_lines.append('            detail=f"Error in {func_name}: {str(e)}"')
        body_lines.append("        )")

        return "\n".join(body_lines)

    def _extract_and_convert_types(self, ts_code: str) -> list[str]:
        """Extract TypeScript interfaces and convert to Pydantic models."""
        models = []

        # Find interface definitions
        interface_pattern = r"interface\s+(\w+)\s*\{([^}]+)\}"
        for match in re.finditer(interface_pattern, ts_code, re.DOTALL):
            interface_name = match.group(1)
            interface_body = match.group(2)

            # Convert to Pydantic
            pydantic_code = self.type_converter.typescript_interface_to_pydantic(
                f"interface {interface_name} {{{interface_body}}}", interface_name
            )
            models.append(pydantic_code)

        # Find type aliases
        type_pattern = r"type\s+(\w+)\s*=\s*\{([^}]+)\}"
        for match in re.finditer(type_pattern, ts_code, re.DOTALL):
            type_name = match.group(1)
            type_body = match.group(2)

            # Convert to Pydantic (treat as interface)
            pydantic_code = self.type_converter.typescript_interface_to_pydantic(
                f"interface {type_name} {{{type_body}}}", type_name
            )
            models.append(pydantic_code)

        return models

    def convert_supabase_client_call(self, db_call: str) -> str:
        """
        Convert Supabase client call to SQLModel query.

        Args:
            db_call: Supabase client call (e.g., "supabase.from('users').select()")

        Returns:
            SQLModel query code
        """
        # Extract table name
        table_match = re.search(r"from\(['\"](\w+)['\"]\)", db_call)
        if not table_match:
            return "# TODO: Convert Supabase call"

        table_name = table_match.group(1)
        model_name = "".join(word.capitalize() for word in table_name.split("_"))

        # Determine operation
        if ".select(" in db_call:
            # Parse filters
            filters = []
            if ".eq(" in db_call:
                eq_match = re.search(r"\.eq\(['\"](\w+)['\"]\s*,\s*([^)]+)\)", db_call)
                if eq_match:
                    field = eq_match.group(1)
                    value = eq_match.group(2)
                    filters.append(f"{model_name}.{field} == {value}")

            if filters:
                where_clause = " and ".join(filters)
                return (
                    f"stmt = select({model_name}).where({where_clause})\n"
                    "result = session.exec(stmt)"
                )
            else:
                return f"stmt = select({model_name})\nresult = session.exec(stmt).all()"

        elif ".insert(" in db_call:
            return f"new_item = {model_name}(**data)\nsession.add(new_item)\nsession.commit()"

        elif ".update(" in db_call:
            return f"# Update {model_name}\n# TODO: Add update logic"

        elif ".delete(" in db_call:
            return f"# Delete {model_name}\n# TODO: Add delete logic"

        return "# TODO: Convert Supabase call"

    def get_conversion_summary(self) -> dict[str, Any]:
        """Get summary of all conversions."""
        return {
            "total_functions": len(self.converted_functions),
            "functions": [
                {
                    "name": f["function_name"],
                    "methods": f["http_methods"],
                    "db_ops": len(f["db_operations"]),
                    "needs_auth": f["needs_auth"],
                    "llm_calls": len(f["llm_conversions"]),
                }
                for f in self.converted_functions
            ],
        }
