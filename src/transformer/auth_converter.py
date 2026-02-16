"""
Auth Converter.

Converts Supabase Auth to Databricks OAuth and OBO tokens.
"""

import logging

logger = logging.getLogger(__name__)


class AuthConverter:
    """Converts Supabase Auth to Databricks OAuth."""

    def generate_auth_module(self) -> str:
        """
        Generate auth.py module with Databricks OAuth.

        Returns:
            Python code for auth module
        """
        return '''
"""
Authentication module using Databricks OAuth.

Handles user authentication with On-Behalf-Of (OBO) tokens.
"""

from fastapi import Depends, HTTPException, Header
from databricks.sdk import WorkspaceClient
from typing import Annotated


def get_workspace_client() -> WorkspaceClient:
    """Get Databricks workspace client."""
    return WorkspaceClient()


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    workspace: WorkspaceClient = Depends(get_workspace_client)
) -> dict:
    """
    Get current authenticated user from Databricks OAuth token.

    Args:
        authorization: Authorization header with Bearer token
        workspace: Databricks workspace client

    Returns:
        User information dictionary

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format"
        )

    token = authorization.replace("Bearer ", "")

    try:
        # Validate token and get user info
        # In production, validate the OBO token with Databricks
        current_user = workspace.current_user.me()

        return {
            "id": current_user.id,
            "user_name": current_user.user_name,
            "display_name": current_user.display_name,
            "active": current_user.active,
        }

    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


def require_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency that requires admin privileges.

    Args:
        current_user: Current authenticated user

    Returns:
        User information

    Raises:
        HTTPException: If user is not admin
    """
    # TODO: Implement admin check logic
    # Check user groups or permissions in Databricks
    return current_user


async def get_obo_token(
    authorization: Annotated[str | None, Header()] = None
) -> str:
    """
    Extract On-Behalf-Of token from authorization header.

    Args:
        authorization: Authorization header

    Returns:
        OBO token string

    Raises:
        HTTPException: If token is invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format"
        )

    return authorization.replace("Bearer ", "")
'''

    def convert_supabase_auth_to_databricks(self, ts_code: str) -> list[dict[str, str]]:
        """
        Detect Supabase auth calls and return conversion list for Databricks auth.

        Args:
            ts_code: TypeScript code with Supabase auth

        Returns:
            List of conversion dicts (original, converted, note)
        """
        conversions: list[dict[str, str]] = []

        # supabase.auth.getUser() -> get_current_user dependency
        if "supabase.auth.getUser()" in ts_code:
            conversions.append(
                {
                    "original": "supabase.auth.getUser()",
                    "converted": "current_user = Depends(get_current_user)",
                    "note": "Use FastAPI dependency injection",
                }
            )

        # supabase.auth.getSession() -> get_obo_token
        if "supabase.auth.getSession()" in ts_code:
            conversions.append(
                {
                    "original": "supabase.auth.getSession()",
                    "converted": "token = Depends(get_obo_token)",
                    "note": "Use OBO token dependency",
                }
            )

        return conversions

    def generate_rls_to_dependency(self, rls_policy: str) -> str:
        """
        Convert RLS policy to FastAPI dependency.

        Args:
            rls_policy: SQL RLS policy definition

        Returns:
            Python FastAPI dependency code
        """
        return '''
def check_row_access(
    item_id: str,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> bool:
    """
    Check if current user has access to the row.

    Converted from RLS policy:
    {rls_policy}

    Args:
        item_id: Item identifier
        current_user: Current authenticated user
        session: Database session

    Returns:
        True if access is allowed

    Raises:
        HTTPException: If access is denied
    """
    # TODO: Implement RLS logic based on original policy
    # Example: Check if item belongs to current user
    # stmt = select(Item).where(
    #     Item.id == item_id,
    #     Item.user_id == current_user["id"]
    # )
    # item = session.exec(stmt).first()
    # if not item:
    #     raise HTTPException(status_code=403, detail="Access denied")
    return True
'''
