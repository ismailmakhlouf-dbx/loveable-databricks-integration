# Usage Examples

Practical examples for using the Lovable Bridge MCP Server.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Via AI Playground](#via-ai-playground)
3. [Via Python Client](#via-python-client)
4. [Via Databricks Notebooks](#via-databricks-notebooks)
5. [Common Workflows](#common-workflows)
6. [Advanced Usage](#advanced-usage)

## Quick Start

### Complete End-to-End Example

From Lovable project URL to deployed Databricks App in minutes:

```python
import httpx

mcp_url = "https://your-workspace.databricks.com/apps/lovable-bridge-mcp"

# 1. Import project
response = httpx.post(
    f"{mcp_url}/tools/lovable_import",
    json={"url": "https://github.com/user/my-lovable-app"}
)
project_id = response.json()["project_id"]
print(f"✅ Project imported: {project_id}")

# 2. Convert to APX
response = httpx.post(
    f"{mcp_url}/tools/lovable_convert",
    json={
        "project_id": project_id,
        "catalog": "main",
        "schema": "my_app"
    }
)
print("✅ Conversion complete")

# 3. Deploy to Databricks
response = httpx.post(
    f"{mcp_url}/tools/lovable_deploy",
    json={
        "project_id": project_id,
        "app_name": "my-customer-dashboard",
        "target": "dev"
    }
)
deployment_id = response.json()["deployment_id"]
app_url = response.json()["app_url"]
print(f"✅ Deployed: {app_url}")

# 4. Check status
response = httpx.post(
    f"{mcp_url}/tools/lovable_status",
    json={"deployment_id": deployment_id}
)
status = response.json()
print(f"Status: {status['status']}")
```

## Via AI Playground

### Example 1: Simple Import and Deploy

**User prompt:**

```
Import my Lovable project from https://github.com/acme/inventory-app
and deploy it as "acme-inventory" to the development environment.
```

**AI Response:**

```
I'll help you import and deploy your Lovable project.

[Calling lovable_import...]
✅ Project imported successfully!
   - Project ID: proj_abc123def456
   - Components: 12 React components
   - API Endpoints: 4 Edge Functions
   - Database Tables: 6 tables

[Calling lovable_convert...]
✅ Conversion complete!
   - Backend: 4 FastAPI routes generated
   - Database: 6 SQLModel models created
   - LLM APIs: Converted OpenAI to Databricks DBRX

[Calling lovable_deploy...]
✅ Deployment initiated!
   - App Name: acme-inventory
   - Target: dev
   - Deployment ID: deploy_xyz789abc

[Calling lovable_status...]
✅ Deployment complete!
   - Status: Running
   - App URL: https://workspace.databricks.com/apps/acme-inventory
   - Lakebase: Provisioned
   - Unity Catalog: Configured (main.inventory)

Your app is now live! 🎉
```

### Example 2: Convert with Custom Configuration

**User prompt:**

```
Import https://github.com/startup/crm-app
Convert it with catalog "production" and schema "crm_v2"
Then deploy to production as "crm-production"
```

**AI Actions:**

1. Import project
2. Convert with custom catalog/schema
3. Deploy to production target
4. Return production URL

### Example 3: Check Existing Deployment

**User prompt:**

```
What's the status of deployment deploy_xyz789abc?
```

**AI Response:**

```
[Calling lovable_status...]

Deployment Status:
- Deployment ID: deploy_xyz789abc
- App Name: acme-inventory
- Status: Running
- Health: Healthy
- App URL: https://workspace.databricks.com/apps/acme-inventory
- Services:
  ✅ Lakebase: Ready
  ✅ Unity Catalog: Ready
  ✅ Foundation Models: Ready
  ✅ Volumes: Ready
- Deployed: 2024-01-15 10:30 UTC
```

## Via Python Client

### Example 1: Batch Import Multiple Projects

```python
import asyncio
import httpx

mcp_url = "https://your-workspace.databricks.com/apps/lovable-bridge-mcp"

projects = [
    {
        "url": "https://github.com/acme/project1",
        "name": "Project 1",
        "app_name": "acme-project1"
    },
    {
        "url": "https://github.com/acme/project2",
        "name": "Project 2",
        "app_name": "acme-project2"
    },
]

async def deploy_project(project):
    async with httpx.AsyncClient() as client:
        # Import
        response = await client.post(
            f"{mcp_url}/tools/lovable_import",
            json={"url": project["url"], "name": project["name"]}
        )
        project_id = response.json()["project_id"]

        # Convert
        await client.post(
            f"{mcp_url}/tools/lovable_convert",
            json={"project_id": project_id}
        )

        # Deploy
        response = await client.post(
            f"{mcp_url}/tools/lovable_deploy",
            json={
                "project_id": project_id,
                "app_name": project["app_name"]
            }
        )

        return response.json()

# Deploy all projects in parallel
async def main():
    tasks = [deploy_project(p) for p in projects]
    results = await asyncio.gather(*tasks)
    for result in results:
        print(f"Deployed: {result['app_url']}")

asyncio.run(main())
```

### Example 2: Custom Conversion with Validation

```python
import httpx

mcp_url = "https://your-workspace.databricks.com/apps/lovable-bridge-mcp"

def deploy_with_validation(github_url: str, app_name: str):
    """Deploy with pre-deployment validation."""

    # Step 1: Import
    response = httpx.post(
        f"{mcp_url}/tools/lovable_import",
        json={"url": github_url},
        timeout=120.0
    )

    if "error" in response.json():
        raise Exception(f"Import failed: {response.json()['error']}")

    project_id = response.json()["project_id"]
    analysis = response.json()["analysis"]

    # Step 2: Validate project structure
    print(f"Analysis Results:")
    print(f"  - Components: {analysis['components']}")
    print(f"  - Endpoints: {analysis['api_endpoints']}")
    print(f"  - Tables: {analysis['database_tables']}")

    # Check for unsupported features
    if analysis.get("edge_functions", 0) > 10:
        print("⚠️ Warning: Large number of Edge Functions may take longer to convert")

    # Step 3: Convert
    response = httpx.post(
        f"{mcp_url}/tools/lovable_convert",
        json={
            "project_id": project_id,
            "catalog": "main",
            "schema": app_name.replace("-", "_")
        },
        timeout=300.0
    )

    conversion = response.json()
    print(f"Conversion Results:")
    print(f"  - Routes: {conversion['conversions']['edge_functions_to_fastapi']}")
    print(f"  - Models: {conversion['conversions']['typescript_types_to_pydantic']}")
    print(f"  - LLM APIs: {conversion['conversions']['llm_apis_converted']}")

    # Step 4: Deploy
    response = httpx.post(
        f"{mcp_url}/tools/lovable_deploy",
        json={
            "project_id": project_id,
            "app_name": app_name,
            "target": "dev"
        },
        timeout=600.0
    )

    deployment = response.json()
    print(f"✅ Deployed: {deployment['app_url']}")

    return deployment

# Usage
deployment = deploy_with_validation(
    "https://github.com/startup/saas-app",
    "startup-saas-dev"
)
```

## Via Databricks Notebooks

### Example 1: Interactive Deployment

```python
# Cell 1: Setup
%pip install httpx

import httpx
mcp_url = "https://your-workspace.databricks.com/apps/lovable-bridge-mcp"

# Cell 2: Import Project
response = httpx.post(
    f"{mcp_url}/tools/lovable_import",
    json={"url": dbutils.widgets.get("project_url")}
)
project_id = response.json()["project_id"]
displayHTML(f"<h3>✅ Project Imported: {project_id}</h3>")

# Cell 3: Display Analysis
analysis = response.json()["analysis"]
display(spark.createDataFrame([
    ("Components", analysis["components"]),
    ("API Endpoints", analysis["api_endpoints"]),
    ("Database Tables", analysis["database_tables"]),
]).toDF("Metric", "Count"))

# Cell 4: Convert
response = httpx.post(
    f"{mcp_url}/tools/lovable_convert",
    json={"project_id": project_id}
)
displayHTML("<h3>✅ Conversion Complete</h3>")

# Cell 5: Deploy
app_name = dbutils.widgets.get("app_name")
response = httpx.post(
    f"{mcp_url}/tools/lovable_deploy",
    json={"project_id": project_id, "app_name": app_name}
)
deployment_id = response.json()["deployment_id"]
displayHTML(f"<h3>✅ Deployment Started: {deployment_id}</h3>")

# Cell 6: Monitor Status
import time

while True:
    response = httpx.post(
        f"{mcp_url}/tools/lovable_status",
        json={"deployment_id": deployment_id}
    )
    status = response.json()
    displayHTML(f"<h4>Status: {status['status']}</h4>")

    if status["status"] == "running":
        displayHTML(f"<h2>🎉 App is Live!</h2><a href='{status['app_url']}' target='_blank'>{status['app_url']}</a>")
        break

    time.sleep(10)
```

### Example 2: Scheduled Deployment Pipeline

```python
# Databricks Job Notebook

from databricks import jobs
import httpx

def deploy_daily_updates():
    """Deploy Lovable projects on schedule."""

    mcp_url = "https://your-workspace.databricks.com/apps/lovable-bridge-mcp"

    # List of projects to deploy
    projects = spark.read.table("deployment_config.projects").collect()

    for project in projects:
        try:
            # Import
            response = httpx.post(
                f"{mcp_url}/tools/lovable_import",
                json={"url": project.github_url}
            )
            project_id = response.json()["project_id"]

            # Convert
            httpx.post(
                f"{mcp_url}/tools/lovable_convert",
                json={"project_id": project_id}
            )

            # Deploy
            response = httpx.post(
                f"{mcp_url}/tools/lovable_deploy",
                json={
                    "project_id": project_id,
                    "app_name": project.app_name,
                    "target": "prod"
                }
            )

            # Log success
            spark.sql(f"""
                INSERT INTO deployment_logs VALUES (
                    '{project.app_name}',
                    current_timestamp(),
                    'success',
                    '{response.json()["app_url"]}'
                )
            """)

        except Exception as e:
            # Log failure
            spark.sql(f"""
                INSERT INTO deployment_logs VALUES (
                    '{project.app_name}',
                    current_timestamp(),
                    'failed',
                    '{str(e)}'
                )
            """)

deploy_daily_updates()
```

## Common Workflows

### Workflow 1: Development to Production Pipeline

```python
def dev_to_prod_pipeline(github_url: str, app_name: str):
    """Complete pipeline from dev to prod."""

    # 1. Deploy to dev
    print("🔨 Deploying to development...")
    dev_deployment = deploy_app(github_url, f"{app_name}-dev", "dev")

    # 2. Run tests
    print("🧪 Running tests...")
    test_results = run_integration_tests(dev_deployment["app_url"])

    if not test_results["passed"]:
        raise Exception("Tests failed in dev")

    # 3. Deploy to staging
    print("📦 Deploying to staging...")
    staging_deployment = deploy_app(github_url, f"{app_name}-staging", "dev")

    # 4. Manual approval
    approval = input("Deploy to production? (yes/no): ")
    if approval.lower() != "yes":
        return

    # 5. Deploy to production
    print("🚀 Deploying to production...")
    prod_deployment = deploy_app(github_url, app_name, "prod")

    print(f"✅ Production deployment complete: {prod_deployment['app_url']}")

def deploy_app(url: str, name: str, target: str):
    """Helper to deploy app."""
    mcp_url = "https://your-workspace.databricks.com/apps/lovable-bridge-mcp"

    # Import
    response = httpx.post(
        f"{mcp_url}/tools/lovable_import",
        json={"url": url}
    )
    project_id = response.json()["project_id"]

    # Convert
    httpx.post(
        f"{mcp_url}/tools/lovable_convert",
        json={"project_id": project_id}
    )

    # Deploy
    response = httpx.post(
        f"{mcp_url}/tools/lovable_deploy",
        json={
            "project_id": project_id,
            "app_name": name,
            "target": target
        }
    )

    return response.json()
```

### Workflow 2: Multi-Environment Deployment

```python
def deploy_to_all_environments(github_url: str, app_base_name: str):
    """Deploy to all environments."""

    environments = {
        "dev": "dev",
        "staging": "dev",
        "prod": "prod"
    }

    deployments = {}

    for env_name, target in environments.items():
        print(f"Deploying to {env_name}...")

        app_name = f"{app_base_name}-{env_name}"
        deployment = deploy_app(github_url, app_name, target)

        deployments[env_name] = deployment
        print(f"✅ {env_name}: {deployment['app_url']}")

    return deployments

# Usage
deployments = deploy_to_all_environments(
    "https://github.com/company/app",
    "company-app"
)
```

## Advanced Usage

### Custom Transformation Hooks

```python
# Customize conversion behavior
def deploy_with_custom_transforms(github_url: str, app_name: str):
    """Deploy with custom transformation options."""

    # Import with custom analyzer settings
    response = httpx.post(
        f"{mcp_url}/tools/lovable_import",
        json={
            "url": github_url,
            "options": {
                "analyze_dependencies": True,
                "detect_unused_code": True
            }
        }
    )

    project_id = response.json()["project_id"]

    # Convert with custom mappings
    response = httpx.post(
        f"{mcp_url}/tools/lovable_convert",
        json={
            "project_id": project_id,
            "catalog": "custom_catalog",
            "schema": "custom_schema",
            "options": {
                "llm_model_mapping": {
                    "gpt-4": "custom-llm-endpoint"
                },
                "enable_caching": True,
                "optimize_queries": True
            }
        }
    )

    # Deploy with resource specifications
    response = httpx.post(
        f"{mcp_url}/tools/lovable_deploy",
        json={
            "project_id": project_id,
            "app_name": app_name,
            "target": "prod",
            "resources": {
                "cpu": "2",
                "memory": "4Gi",
                "replicas": 3
            }
        }
    )

    return response.json()
```

### Monitoring and Observability

```python
def monitor_deployment(deployment_id: str, duration_minutes: int = 60):
    """Monitor deployment health over time."""

    import time
    from datetime import datetime

    end_time = time.time() + (duration_minutes * 60)
    health_log = []

    while time.time() < end_time:
        response = httpx.post(
            f"{mcp_url}/tools/lovable_status",
            json={"deployment_id": deployment_id}
        )

        status = response.json()
        health_log.append({
            "timestamp": datetime.now(),
            "status": status["status"],
            "health": status["health"],
        })

        print(f"[{datetime.now()}] Status: {status['status']} | Health: {status['health']}")

        if status["status"] != "running":
            print(f"⚠️ App not running: {status['status']}")
            break

        time.sleep(60)  # Check every minute

    return health_log
```

## Next Steps

- Review [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- Contribute examples via GitHub pull requests
