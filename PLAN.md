# Lovable Bridge MCP Server - Implementation Plan

## Vision

Create an MCP server that enables non-technical users to seamlessly import Lovable projects into Databricks infrastructure with zero manual configuration.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Lovable Bridge MCP Server                 │
│                                                               │
│  Input: GitHub URL or ZIP                                    │
│     ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 1. ANALYZER: Scan & understand project structure        ││
│  │    - Frontend (React components, routes, hooks)         ││
│  │    - Backend (Edge Functions, API patterns)             ││
│  │    - Database (schemas, migrations, RLS)                ││
│  │    - LLM APIs (OpenAI, Anthropic detection)            ││
│  └─────────────────────────────────────────────────────────┘│
│     ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 2. TRANSFORMER: Convert types and APIs                  ││
│  │    - TypeScript → Python type hints                     ││
│  │    - Interfaces → Pydantic models                       ││
│  │    - SQL types → SQLModel fields                        ││
│  │    - OpenAI/Anthropic → Databricks Foundation Models    ││
│  └─────────────────────────────────────────────────────────┘│
│     ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 3. GENERATOR: Create APX project files                  ││
│  │    - FastAPI app with endpoints                         ││
│  │    - SQLModel models                                    ││
│  │    - Databricks configs (app.yaml, databricks.yml)     ││
│  │    - Tests and documentation                            ││
│  └─────────────────────────────────────────────────────────┘│
│     ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 4. VALIDATOR: Check compatibility and config            ││
│  │    - Feature support validation                         ││
│  │    - Configuration validation                           ││
│  │    - Pre-deployment checks                              ││
│  └─────────────────────────────────────────────────────────┘│
│     ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 5. DEPLOYER: Deploy to Databricks                       ││
│  │    - Create Databricks App                              ││
│  │    - Setup Lakebase database                            ││
│  │    - Configure OAuth                                    ││
│  │    - Provision Volumes                                  ││
│  └─────────────────────────────────────────────────────────┘│
│     ↓                                                         │
│  Output: Running Databricks App URL                          │
└─────────────────────────────────────────────────────────────┘
```

## Phase 3: Generator Module (NEXT PRIORITY)

### 3.1 FastAPI Generator

**File:** `src/generator/fastapi_generator.py`

**Purpose:** Convert Supabase Edge Functions to FastAPI endpoints

**Key Classes:**
```python
class FastAPIGenerator:
    def __init__(self, backend_metadata: dict, type_converter: TypeConverter, llm_converter: LLMConverter)

    def generate_app(self) -> str:
        """Generate main FastAPI app.py"""

    def generate_endpoint(self, function_info: EdgeFunctionInfo) -> str:
        """Generate single endpoint from Edge Function"""

    def generate_router(self, functions: list[EdgeFunctionInfo]) -> str:
        """Generate APIRouter for grouped endpoints"""

    def generate_dependencies(self, function_info: EdgeFunctionInfo) -> str:
        """Generate FastAPI dependencies (auth, db)"""
```

**Tasks:**
1. Create template structure for FastAPI apps
2. Map HTTP methods from Edge Functions to FastAPI route decorators
3. Convert Edge Function parameters to FastAPI path/query/body params
4. Generate dependency injection for database connections
5. Generate dependency injection for authentication
6. Handle CORS configuration
7. Convert database operations (supabase.from()) to SQLAlchemy queries
8. Convert LLM API calls using llm_converter
9. Generate error handling and logging

**Templates Needed:**
- `templates/fastapi/app.py.jinja2` - Main app structure
- `templates/fastapi/endpoint.py.jinja2` - Single endpoint
- `templates/fastapi/router.py.jinja2` - Router file
- `templates/fastapi/dependencies.py.jinja2` - Auth/DB dependencies

### 3.2 Model Generator

**File:** `src/generator/model_generator.py`

**Purpose:** Generate SQLModel and Pydantic models

**Key Classes:**
```python
class ModelGenerator:
    def __init__(self, database_metadata: dict, type_converter: TypeConverter)

    def generate_sqlmodels(self) -> dict[str, str]:
        """Generate SQLModel classes from database schemas"""

    def generate_pydantic_models(self) -> dict[str, str]:
        """Generate Pydantic models for API schemas"""

    def generate_relationships(self) -> str:
        """Generate SQLModel relationships from foreign keys"""
```

**Tasks:**
1. Convert TableSchema objects to SQLModel classes
2. Map SQL types to SQLModel field types using type_converter
3. Generate field validators for constraints
4. Generate relationships from foreign keys
5. Create separate Pydantic models for API requests/responses
6. Handle optional fields and defaults
7. Generate model documentation

**Templates Needed:**
- `templates/models/sqlmodel.py.jinja2` - SQLModel class
- `templates/models/pydantic.py.jinja2` - Pydantic model
- `templates/models/__init__.py.jinja2` - Models package

### 3.3 Config Generator

**File:** `src/generator/config_generator.py`

**Purpose:** Generate Databricks configuration files

**Key Classes:**
```python
class ConfigGenerator:
    def __init__(self, project_metadata: dict)

    def generate_app_yaml(self) -> str:
        """Generate app.yaml for Databricks Apps"""

    def generate_databricks_yml(self) -> str:
        """Generate databricks.yml asset bundle"""

    def generate_env_config(self) -> str:
        """Generate .env configuration"""

    def generate_catalog_config(self) -> str:
        """Generate Unity Catalog registration SQL"""
```

**Tasks:**
1. Generate app.yaml with:
   - App name, description
   - Compute resources (based on project size)
   - Environment variables
   - Network configuration
2. Generate databricks.yml asset bundle with:
   - Resources (apps, jobs, volumes)
   - Targets (dev, staging, prod)
   - Sync patterns
3. Generate .env.example with required variables
4. Generate Unity Catalog setup SQL
5. Generate deployment scripts

**Templates Needed:**
- `templates/config/app.yaml.jinja2`
- `templates/config/databricks.yml.jinja2`
- `templates/config/.env.example.jinja2`
- `templates/config/catalog_setup.sql.jinja2`

### 3.4 Test Generator

**File:** `src/generator/test_generator.py`

**Purpose:** Generate pytest test files

**Key Classes:**
```python
class TestGenerator:
    def __init__(self, metadata: dict)

    def generate_endpoint_tests(self) -> dict[str, str]:
        """Generate tests for API endpoints"""

    def generate_model_tests(self) -> dict[str, str]:
        """Generate tests for SQLModel models"""

    def generate_fixtures(self) -> str:
        """Generate pytest fixtures"""
```

**Tasks:**
1. Generate test files for each endpoint
2. Generate fixtures for database and auth
3. Generate mock data based on schemas
4. Create integration tests
5. Generate conftest.py

## Phase 4: Deployment Module

### 4.1 Databricks Deployer

**File:** `src/deployer/databricks_deployer.py`

**Tasks:**
1. Use Databricks SDK to create app
2. Upload generated code
3. Configure compute resources
4. Set environment variables
5. Start the app
6. Return app URL

### 4.2 Database Deployer

**File:** `src/deployer/database_deployer.py`

**Tasks:**
1. Connect to Lakebase PostgreSQL
2. Create Unity Catalog schema
3. Run migrations
4. Set up tables
5. Import seed data if needed

### 4.3 Auth Deployer

**File:** `src/deployer/auth_deployer.py`

**Tasks:**
1. Configure OAuth app
2. Set up service principals
3. Configure RBAC permissions
4. Generate API keys

### 4.4 Storage Deployer

**File:** `src/deployer/storage_deployer.py`

**Tasks:**
1. Create Databricks Volume
2. Configure access policies
3. Migrate files from Supabase Storage (if needed)

## Phase 5: Validation Module

### 5.1 Compatibility Validator

**File:** `src/validator/compatibility_validator.py`

**Tasks:**
1. Check for unsupported Supabase features
2. Warn about Realtime (needs manual setup)
3. Check for complex stored procedures
4. Identify Edge Runtime limitations

### 5.2 Deployment Validator

**File:** `src/validator/deployment_validator.py`

**Tasks:**
1. Validate Databricks workspace access
2. Check catalog/schema permissions
3. Verify compute availability
4. Validate configuration files

### 5.3 Runtime Validator

**File:** `src/validator/runtime_validator.py`

**Tasks:**
1. Health check endpoints
2. Test database connectivity
3. Verify LLM model access
4. Test authentication flow

## Integration Steps

### Update MCP Tools

**File:** `src/mcp_tools.py`

Replace mock implementations with real ones:

```python
async def lovable_import(url: str, name: str | None = None):
    # 1. Use ProjectScanner.from_url()
    scanner = await ProjectScanner.from_url(url, name)

    # 2. Run all analyzers
    backend_analyzer = BackendAnalyzer(scanner.project_path / "supabase/functions")
    backend_metadata = backend_analyzer.analyze()

    database_analyzer = DatabaseAnalyzer(scanner.project_path / "supabase/migrations")
    database_metadata = database_analyzer.analyze()

    frontend_analyzer = FrontendAnalyzer(scanner.project_path / "src")
    frontend_metadata = frontend_analyzer.analyze()

    # 3. Store metadata
    # 4. Return real analysis

async def lovable_convert(project_id: str, catalog: str, schema: str):
    # 1. Load project metadata
    # 2. Initialize generators
    fastapi_gen = FastAPIGenerator(...)
    model_gen = ModelGenerator(...)
    config_gen = ConfigGenerator(...)

    # 3. Generate all code
    # 4. Store generated code
    # 5. Return conversion summary

async def lovable_deploy(project_id: str, app_name: str, target: str):
    # 1. Load generated code
    # 2. Run validators
    # 3. Deploy using deployers
    # 4. Return deployment info
```

## Development Guidelines

### Code Style
- Use type hints everywhere
- Use Pydantic models for configuration
- Use logging extensively
- Handle errors gracefully with custom exceptions
- Write docstrings for all classes and functions

### Testing Strategy
- Unit tests for each module
- Integration tests for full workflow
- Mock external APIs (GitHub, Databricks)
- Use pytest fixtures for common setup

### Error Handling
- Create custom exception hierarchy
- Always provide helpful error messages
- Include suggestions for fixing issues
- Log errors with context

### Documentation
- Update README.md with usage examples
- Document all MCP tool parameters
- Create troubleshooting guide
- Add architecture diagrams

## Success Metrics

1. **Accuracy:** 90%+ of Lovable projects convert successfully
2. **Speed:** Complete import → deploy in < 5 minutes
3. **Compatibility:** Support all major Lovable patterns
4. **User Experience:** Zero configuration required for standard projects
5. **Reliability:** Proper error handling and recovery

## Future Enhancements

1. **Incremental Updates:** Support re-deploying after code changes
2. **Environment Sync:** Sync env vars from Supabase
3. **Data Migration:** Migrate production data from Supabase
4. **Monitoring:** Add observability to deployed apps
5. **Rollback:** Support rolling back deployments
6. **Multi-Region:** Deploy to multiple Databricks regions
7. **CI/CD Integration:** GitHub Actions workflow generation
