# Lovable Bridge MCP Server

A Model Context Protocol (MCP) server that enables seamless import and deployment of [Lovable](https://lovable.dev) projects into Databricks infrastructure.

## Overview

This MCP server allows non-technical users to:
1. Import Lovable projects (React + TypeScript + Supabase) from GitHub or ZIP
2. Automatically convert to Databricks Apps format (APX)
3. Deploy as production-ready Databricks Apps

### Automatic Conversions

- **Backend**: Supabase Edge Functions (TypeScript) → FastAPI (Python)
- **Database**: Supabase PostgreSQL → Lakebase PostgreSQL
- **AI/LLM**: External APIs (OpenAI, Anthropic) → Databricks Foundation Model Serving
- **Auth**: Supabase Auth → Databricks OAuth
- **Storage**: Supabase Storage → Databricks Volumes
- **Catalog**: Automatic Unity Catalog registration

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│         Databricks Workspace (User's Environment)           │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │    Databricks AI Playground / Notebooks / Apps         │  │
│  │    "Import my Lovable project from GitHub URL..."      │  │
│  └─────────────────────┬───────────────────────────────────┘  │
│                        ↓                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         Lovable Bridge MCP Server (This App)           │  │
│  │  MCP Tools:                                             │  │
│  │    • lovable_import   - Fetch & analyze project        │  │
│  │    • lovable_convert  - Transform to APX               │  │
│  │    • lovable_deploy   - Deploy to Databricks           │  │
│  │    • lovable_status   - Check deployment status        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.11+
- Databricks workspace access
- Databricks CLI configured

### Local Development

```bash
# Clone the repository
git clone https://github.com/your-org/lovable-bridge-mcp
cd lovable-bridge-mcp

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your Databricks credentials

# Run MCP server locally
uvicorn src.server:app --reload --port 8000

# Test MCP endpoint
curl http://localhost:8000/mcp
```

### Deploy to Databricks

```bash
# Validate bundle configuration
databricks bundle validate

# Deploy to development environment
databricks bundle deploy --target dev

# Get the app endpoint
databricks apps get lovable-bridge-mcp-dev

# Deploy to production
databricks bundle deploy --target prod
```

## Usage

### Via Databricks AI Playground

1. Open Databricks AI Playground
2. Ensure the "Lovable Bridge" MCP server is configured
3. Use natural language to import and deploy:

```
User: "Import my Lovable project from https://github.com/user/my-app and deploy it as 'customer-dashboard'"

AI Agent: ✅ Project imported successfully!
   - 15 React components detected
   - 3 API endpoints found
   - 5 database tables identified

✅ Conversion complete!
   - Generated FastAPI backend
   - Created SQLModel models

✅ Deployment complete!
   - App URL: https://workspace.databricks.com/apps/customer-dashboard
```

### Via Python/Notebooks

```python
import httpx

mcp_url = "https://your-workspace.databricks.com/apps/lovable-bridge-mcp"

# Import project
response = httpx.post(f"{mcp_url}/tools/lovable_import", json={
    "url": "https://github.com/user/my-app"
})
project_id = response.json()["project_id"]

# Convert to APX
httpx.post(f"{mcp_url}/tools/lovable_convert", json={
    "project_id": project_id,
    "catalog": "main",
    "schema": "my_app"
})

# Deploy
response = httpx.post(f"{mcp_url}/tools/lovable_deploy", json={
    "project_id": project_id,
    "app_name": "my-app",
    "target": "dev"
})

print(f"Deployed: {response.json()['app_url']}")
```

## MCP Tools

### lovable_import

Import and analyze a Lovable project from GitHub or ZIP URL.

**Parameters:**
- `url` (required): GitHub repository URL or ZIP download URL
- `name` (optional): Project name (auto-detected if not provided)

**Returns:**
- Project metadata, component count, API endpoints, database tables
- Project ID for subsequent operations

### lovable_convert

Convert imported Lovable project to APX format.

**Parameters:**
- `project_id` (required): Project ID from lovable_import
- `catalog` (optional): Unity Catalog name (default: "main")
- `schema` (optional): Database schema name (default: "lovable_app")

**Returns:**
- Conversion summary, generated files, compatibility report

### lovable_deploy

Deploy converted project to Databricks.

**Parameters:**
- `project_id` (required): Project ID from lovable_convert
- `app_name` (required): Databricks App name
- `target` (optional): Deployment target - "dev" or "prod" (default: "dev")

**Returns:**
- Deployment ID, app URL, status

### lovable_status

Check deployment status and get app details.

**Parameters:**
- `deployment_id` (required): Deployment ID from lovable_deploy

**Returns:**
- Current status, app URL, provisioned services

## Feature Support

### Fully Supported (Zero Configuration)

✅ React + TypeScript frontend
✅ Supabase Edge Functions → FastAPI
✅ PostgreSQL database → Lakebase
✅ Database migrations
✅ Row-Level Security → FastAPI dependencies
✅ Authentication → Databricks OAuth
✅ OpenAI/Anthropic APIs → Foundation Model Serving
✅ Unity Catalog registration
✅ File storage → Databricks Volumes

### Partially Supported (Manual Configuration Required)

⚠️ Supabase Realtime → React Query polling or WebSocket
⚠️ Cron jobs → Databricks Jobs
⚠️ Complex stored procedures → Python functions

### Not Supported

❌ Supabase-specific features without Databricks equivalents

## Development

### Project Structure

```
lovable-bridge-mcp/
├── src/
│   ├── server.py              # FastAPI MCP server
│   ├── mcp_tools.py           # MCP tool implementations
│   ├── analyzer/              # Project analysis
│   ├── transformer/           # Code conversion
│   ├── generator/             # APX generation
│   ├── deployer/              # Databricks deployment
│   └── validator/             # Validation
├── templates/                 # Jinja2 templates
├── tests/                     # Test suite
├── app.yaml                   # Databricks App config
├── databricks.yml             # Asset Bundle
└── pyproject.toml             # Python project config
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/analyzer/test_project_scanner.py
```

### Code Quality

```bash
# Format code
black src tests

# Lint
ruff check src tests

# Type check
mypy src
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run code quality checks
5. Submit a pull request

## License

[License details]

## Support

For issues and questions:
- GitHub Issues: [repository issues page]
- Documentation: [link to docs]

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Databricks SDK](https://docs.databricks.com/dev-tools/sdk-python.html)
