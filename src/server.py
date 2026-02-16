"""
FastAPI MCP Server for Lovable Bridge.

This server implements the Model Context Protocol (MCP) to enable
AI agents and users to import Lovable projects into Databricks.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from databricks.sdk import WorkspaceClient
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp_server = Server(os.getenv("MCP_SERVER_NAME", "lovable-bridge"))

# Global Databricks client (will be initialized on startup)
workspace_client: WorkspaceClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan context manager for startup and shutdown."""
    global workspace_client

    logger.info("Starting Lovable Bridge MCP Server...")

    # Initialize Databricks client
    try:
        workspace_client = WorkspaceClient()
        logger.info("Databricks client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Databricks client: {e}")
        workspace_client = None

    yield

    # Cleanup on shutdown
    logger.info("Shutting down Lovable Bridge MCP Server...")


# Initialize FastAPI app
app = FastAPI(
    title="Lovable Bridge MCP Server",
    description="MCP Server for importing Lovable projects into Databricks",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint - health check."""
    return {
        "name": "Lovable Bridge MCP Server",
        "version": "0.1.0",
        "status": "running",
        "mcp_endpoint": "/mcp",
    }


@app.get("/health")
async def health() -> dict[str, str | bool]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "databricks_connected": workspace_client is not None,
    }


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available MCP tools.

    These tools enable AI agents to import, convert, and deploy Lovable projects.
    """
    return [
        Tool(
            name="lovable_import",
            description="Import and analyze a Lovable project from GitHub or ZIP URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "GitHub repository URL or ZIP download URL",
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional project name (auto-detected if not provided)",
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="lovable_convert",
            description="Convert imported Lovable project to APX format",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Project ID from lovable_import",
                    },
                    "catalog": {
                        "type": "string",
                        "description": "Unity Catalog name",
                        "default": "main",
                    },
                    "schema": {
                        "type": "string",
                        "description": "Database schema name",
                        "default": "lovable_app",
                    },
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="lovable_deploy",
            description="Deploy converted project to Databricks",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Project ID from lovable_convert",
                    },
                    "app_name": {
                        "type": "string",
                        "description": "Databricks App name",
                    },
                    "target": {
                        "type": "string",
                        "description": "Deployment target (dev/prod)",
                        "default": "dev",
                        "enum": ["dev", "prod"],
                    },
                },
                "required": ["project_id", "app_name"],
            },
        ),
        Tool(
            name="lovable_status",
            description="Check deployment status and get app URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "deployment_id": {
                        "type": "string",
                        "description": "Deployment ID from lovable_deploy",
                    }
                },
                "required": ["deployment_id"],
            },
        ),
    ]


@app.post("/mcp")
async def handle_mcp(request: Request) -> JSONResponse:
    """
    MCP protocol endpoint.

    This endpoint handles MCP protocol communication using SSE transport.
    AI agents and clients connect to this endpoint to use the MCP tools.
    """
    # Create SSE transport for this connection
    transport = SseServerTransport("/mcp")

    # Handle the MCP protocol communication
    try:
        # The actual MCP protocol handling will be implemented in mcp_tools.py
        # For now, return a placeholder
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {
                        "tools": {
                            "listChanged": True,
                        }
                    },
                    "serverInfo": {
                        "name": "lovable-bridge",
                        "version": "0.1.0",
                    },
                },
            }
        )
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for the FastAPI app."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
