# Deployment Guide

Complete guide for deploying the Lovable Bridge MCP Server to Databricks.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Deploying to Databricks](#deploying-to-databricks)
4. [Configuration](#configuration)
5. [Testing the Deployment](#testing-the-deployment)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required

- **Python 3.11 or higher**
- **Databricks workspace** with admin or workspace creator permissions
- **Databricks CLI** installed and configured
- **Git** for version control

### Optional but Recommended

- **GitHub Personal Access Token** (for private repository imports)
- **Unity Catalog** access (for database features)
- **Foundation Model Serving** access (for LLM features)

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/ismailmakhlouf-dbx/loveable-databricks-integration.git
cd loveable-databricks-integration
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -e ".[dev]"
```

### 4. Configure Environment

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Databricks Configuration
DATABRICKS_HOST=https://your-workspace.databricks.com
DATABRICKS_TOKEN=dapi...

# MCP Server Configuration
MCP_SERVER_NAME=lovable-bridge
LOG_LEVEL=info

# Optional: GitHub Access
GITHUB_TOKEN=ghp_...
```

### 5. Run Locally

```bash
uvicorn src.server:app --reload --port 8000
```

Test the server:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "databricks_connected": true
}
```

## Deploying to Databricks

### Method 1: Using Databricks CLI (Recommended)

#### Step 1: Validate Bundle

```bash
databricks bundle validate
```

This checks:
- `databricks.yml` syntax
- Required fields
- Permission configuration

#### Step 2: Deploy to Development

```bash
databricks bundle deploy --target dev
```

This will:
1. Upload source code to your workspace
2. Create the Databricks App
3. Configure permissions
4. Start the MCP server

#### Step 3: Get App Endpoint

```bash
databricks apps get lovable-bridge-mcp-dev
```

Copy the app URL (e.g., `https://your-workspace.databricks.com/apps/lovable-bridge-mcp-dev`)

#### Step 4: Deploy to Production

```bash
databricks bundle deploy --target prod
```

### Method 2: Manual Deployment

#### Step 1: Upload Files

```bash
# Create workspace directory
databricks workspace mkdirs /Workspace/apps/lovable-bridge-mcp

# Upload source code
databricks workspace import-dir \
  src/ \
  /Workspace/apps/lovable-bridge-mcp/src/ \
  --overwrite
```

#### Step 2: Create App

Create `app.yaml` in your workspace:

```yaml
command:
  - "uvicorn"
  - "src.server:app"
  - "--host"
  - "0.0.0.0"
  - "--port"
  - "8000"

resources:
  cpu: "1"
  memory: "2Gi"

env:
  - name: "MCP_SERVER_NAME"
    value: "lovable-bridge"
  - name: "LOG_LEVEL"
    value: "info"
```

#### Step 3: Deploy App

```bash
databricks apps create \
  --name lovable-bridge-mcp \
  --source-code-path /Workspace/apps/lovable-bridge-mcp
```

## Configuration

### Unity Catalog Setup

Configure default catalog and schema for converted projects:

```yaml
# databricks.yml
resources:
  catalogs:
    lovable:
      name: lovable_apps
      comment: "Catalog for Lovable-converted applications"

  schemas:
    default:
      catalog_name: lovable_apps
      name: default
      comment: "Default schema for Lovable apps"
```

### Lakebase Configuration

Lakebase PostgreSQL is provisioned automatically. Configure connection pooling:

```yaml
# app.yaml
env:
  - name: "DATABASE_POOL_SIZE"
    value: "5"
  - name: "DATABASE_POOL_TIMEOUT"
    value: "30"
```

### Foundation Model Serving

Ensure you have access to Foundation Model endpoints:

```bash
databricks serving-endpoints list
```

Required endpoints:
- `databricks-dbrx-instruct`
- `databricks-meta-llama-3-70b-instruct`
- `databricks-meta-llama-3-8b-instruct`

### Secrets Management

Store sensitive credentials in Databricks Secrets:

```bash
# Create secret scope
databricks secrets create-scope lovable-bridge

# Add GitHub token
databricks secrets put-secret \
  lovable-bridge \
  github-token \
  --string-value "ghp_..."
```

Reference in `app.yaml`:

```yaml
env:
  - name: "GITHUB_TOKEN"
    valueFrom:
      secretKeyRef:
        scope: lovable-bridge
        key: github-token
```

## Testing the Deployment

### 1. Health Check

```bash
curl https://your-workspace.databricks.com/apps/lovable-bridge-mcp/health
```

Expected response:

```json
{
  "status": "healthy",
  "databricks_connected": true
}
```

### 2. MCP Protocol Test

```bash
curl https://your-workspace.databricks.com/apps/lovable-bridge-mcp/mcp \
  -H "Content-Type: application/json"
```

### 3. Test Import Function

Using Python:

```python
import httpx

mcp_url = "https://your-workspace.databricks.com/apps/lovable-bridge-mcp"

response = httpx.post(
    f"{mcp_url}/tools/lovable_import",
    json={"url": "https://github.com/example/lovable-test-project"}
)

print(response.json())
```

### 4. Integration with AI Playground

1. Open Databricks AI Playground
2. Go to Settings → MCP Servers
3. Add new server:
   - **Name**: Lovable Bridge
   - **URL**: `https://your-workspace.databricks.com/apps/lovable-bridge-mcp/mcp`
   - **Auth**: Use workspace authentication
4. Test with prompt:

```
Import my Lovable project from https://github.com/myuser/my-app
and deploy it as 'test-app'
```

## Troubleshooting

### App Won't Start

**Check logs:**

```bash
databricks apps logs lovable-bridge-mcp --tail 50
```

**Common issues:**
- Missing dependencies → Re-deploy with `--force`
- Invalid credentials → Check `.env` and secrets
- Port already in use → Change port in `app.yaml`

### Import Fails

**Error**: "Failed to clone repository"

**Solutions:**
- Check GitHub token is valid
- Verify repository is accessible
- Try with a public repository first

### Conversion Errors

**Error**: "Failed to convert Edge Function"

**Solutions:**
- Check Edge Function syntax
- Review conversion logs
- File an issue with the project structure

### Deployment Timeout

**Error**: "Deployment did not complete in time"

**Solutions:**
- Increase timeout in configuration
- Check Databricks workspace capacity
- Deploy during off-peak hours

## Monitoring

### Application Metrics

View metrics in Databricks:

```bash
databricks apps metrics lovable-bridge-mcp
```

### Logging

Configure log aggregation:

```yaml
# app.yaml
env:
  - name: "LOG_DESTINATION"
    value: "/dbfs/logs/lovable-bridge/"
  - name: "LOG_ROTATION"
    value: "daily"
```

### Alerts

Set up alerts for:
- App health failures
- Deployment errors
- High error rates
- Resource usage

## Updating the Deployment

### Incremental Update

```bash
databricks bundle deploy --target prod
```

### Zero-Downtime Update

1. Deploy to new version:

```bash
databricks apps create \
  --name lovable-bridge-mcp-v2 \
  --source-code-path /Workspace/apps/lovable-bridge-mcp
```

2. Test new version
3. Update traffic routing
4. Decommission old version

## Backup and Recovery

### Backup Configuration

```bash
# Backup workspace directory
databricks workspace export-dir \
  /Workspace/apps/lovable-bridge-mcp \
  ./backup-$(date +%Y%m%d)
```

### Recovery

```bash
# Restore from backup
databricks workspace import-dir \
  ./backup-20240115 \
  /Workspace/apps/lovable-bridge-mcp \
  --overwrite
```

## Security Best Practices

1. **Use HTTPS** for all communications
2. **Enable workspace authentication** for MCP endpoint
3. **Rotate tokens** regularly
4. **Audit access logs** monthly
5. **Use separate environments** for dev/prod
6. **Implement rate limiting** for public endpoints
7. **Regular security updates** of dependencies

## Performance Tuning

### Scaling

Increase resources for high load:

```yaml
# app.yaml
resources:
  cpu: "2"
  memory: "4Gi"
  replicas: 3  # For high availability
```

### Caching

Enable caching for frequent operations:

```yaml
env:
  - name: "ENABLE_CACHE"
    value: "true"
  - name: "CACHE_TTL"
    value: "3600"
```

### Connection Pooling

Optimize database connections:

```python
# config.py
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
)
```

## Next Steps

After successful deployment:

1. ✅ Configure Unity Catalog integration
2. ✅ Set up monitoring and alerts
3. ✅ Train team on using the MCP server
4. ✅ Create example Lovable projects
5. ✅ Document common workflows
6. ✅ Establish support processes

## Support

For issues or questions:
- GitHub Issues: [Repository Issues](https://github.com/ismailmakhlouf-dbx/loveable-databricks-integration/issues)
- Documentation: [README.md](README.md)
- Examples: [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)
