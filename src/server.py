"""
FastAPI MCP Server for Lovable Bridge.

This server implements the Model Context Protocol (MCP) to enable
AI agents and users to import Lovable projects into Databricks.
"""

import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from databricks.sdk import WorkspaceClient
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool

from .mcp_tools import (
    LovableError,
    lovable_convert,
    lovable_deploy,
    lovable_import,
    lovable_status,
)

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

# SSE transport (single instance, shared across connections)
sse_transport = SseServerTransport("/mcp/messages/")

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
        "mcp_sse_endpoint": "/mcp/sse",
        "mcp_messages_endpoint": "/mcp/messages/",
    }


@app.get("/health")
async def health() -> dict[str, str | bool]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "databricks_connected": workspace_client is not None,
    }


@mcp_server.list_tools()  # type: ignore[untyped-decorator, no-untyped-call]
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
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


@mcp_server.call_tool()  # type: ignore[untyped-decorator, no-untyped-call]
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """Route MCP tool calls to their implementations."""
    args = arguments or {}
    try:
        match name:
            case "lovable_import":
                result = await lovable_import(**args)
            case "lovable_convert":
                result = await lovable_convert(**args)
            case "lovable_deploy":
                result = await lovable_deploy(**args)
            case "lovable_status":
                result = await lovable_status(**args)
            case _:
                raise ValueError(f"Unknown tool: {name}")
        return [TextContent(type="text", text=json.dumps(result))]
    except LovableError as e:
        return [TextContent(type="text", text=json.dumps({
            "error": {"code": e.code, "message": e.message, "details": e.details}
        }))]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}", exc_info=True)
        return [TextContent(type="text", text=json.dumps({
            "error": {"code": "TOOL_ERROR", "message": str(e)}
        }))]


@app.get("/mcp/sse")
async def mcp_sse_endpoint(request: Request) -> None:
    """
    SSE endpoint for MCP protocol.

    MCP clients connect here to establish a persistent SSE stream.
    After connecting, clients send tool calls to /mcp/messages/.
    """
    logger.info("MCP SSE client connected")
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options(),
        )


@app.post("/mcp/messages/")
async def mcp_messages_endpoint(request: Request) -> None:
    """
    Message endpoint for MCP protocol.

    MCP clients POST tool call requests here after connecting via SSE.
    """
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
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
