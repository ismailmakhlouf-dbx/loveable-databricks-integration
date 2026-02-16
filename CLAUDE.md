# Instructions for Claude Code

## Project Context

This is the **Lovable Bridge MCP Server** - converting Lovable projects to Databricks Apps.

**CRITICAL:** Always read `PROGRESS.md` first to understand current state!

## Git Workflow with Milestones

### When to Push to Git

After completing these milestones, **ALWAYS commit AND push**:

1. ✅ **Milestone 1: Transformer Completion** (PENDING)
   - Commit transformer files
   - Push to remote
   - Message: "feat: Add LLM and type conversion transformers"

2. 🎯 **Milestone 2: Generator Foundation** (NEXT)
   - Complete FastAPIGenerator skeleton
   - Complete first template (endpoint template)
   - Create templates directory structure
   - Push to remote
   - Message: "feat: Add FastAPI generator foundation and templates"

3. 🎯 **Milestone 3: Generator Core**
   - Complete all generators (FastAPI, Model, Config)
   - Push to remote
   - Message: "feat: Complete code generation layer"

4. 🎯 **Milestone 4: Integration**
   - Update mcp_tools.py with real implementations
   - Push to remote
   - Message: "feat: Integrate generators into MCP tools"

5. 🎯 **Milestone 5: Deployer Foundation**
   - Complete deployer modules
   - Push to remote
   - Message: "feat: Add Databricks deployment layer"

6. 🎯 **Milestone 6: Validator**
   - Complete validator modules
   - Push to remote
   - Message: "feat: Add validation layer"

7. 🎯 **Milestone 7: Tests**
   - Add test suite
   - Push to remote
   - Message: "test: Add comprehensive test coverage"

8. 🎯 **Milestone 8: Documentation**
   - Complete all documentation
   - Push to remote
   - Message: "docs: Complete project documentation"

### Push Command Pattern

```bash
# After committing milestone work
git push origin master

# Verify push succeeded
git log origin/master -1
```

### Commit Message Format

Use conventional commits:
```
<type>(<scope>): <description>

<optional body>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

Types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance

## Current Priorities

1. **URGENT:** Commit and push transformer files
2. Create templates directory structure
3. Build FastAPIGenerator (Phase 3)
4. Build remaining generators
5. Build deployers (Phase 4)
6. Build validators (Phase 5)

## Key Principles

1. **Read PROGRESS.md first** - Always check current state
2. **Commit frequently** - After each logical unit of work
3. **Push at milestones** - After completing major features
4. **Test before pushing** - Run tests when available
5. **Update PROGRESS.md** - Keep it current after each milestone

## Data Flow Reference

```
GitHub URL
  ↓
ProjectScanner (analyzer/project_scanner.py)
  ↓
BackendAnalyzer (analyzer/backend_analyzer.py)
DatabaseAnalyzer (analyzer/database_analyzer.py)
FrontendAnalyzer (analyzer/frontend_analyzer.py)
  ↓
TypeConverter (transformer/type_converter.py)
LLMConverter (transformer/llm_converter.py)
  ↓
FastAPIGenerator (generator/fastapi_generator.py) ← BUILD THIS NEXT
ModelGenerator (generator/model_generator.py)
ConfigGenerator (generator/config_generator.py)
  ↓
Validator modules
  ↓
Deployer modules
  ↓
Databricks App URL
```

## Error Recovery

If session crashes:
1. Read PROGRESS.md to see what was completed
2. Check git status for uncommitted work
3. Check git log to see last commit
4. Resume from last documented state

## Quick Commands

```bash
# Check project state
git status
git log -5 --oneline

# Current work
ls -la src/*/

# Line counts (see implementation progress)
wc -l src/**/*.py | sort -n

# Commit and push milestone
git add .
git commit -m "feat: <description>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
git push origin master
```

## Testing Strategy

When tests are available:
```bash
# Always run before pushing
pytest --cov=src --cov-report=term-missing

# If tests fail, do NOT push
# Fix issues first, then commit and push
```

## Documentation Updates

After each milestone, update:
1. **PROGRESS.md** - Mark phases complete, update percentage
2. **README.md** - Update features list if needed
3. **This file** - Update milestone status

## Remote Repository

Make sure remote is configured:
```bash
# Check remote
git remote -v

# If not set, should point to GitHub repo
# origin  https://github.com/your-org/lovable-bridge-mcp.git
```

## Collaboration Notes

This project can be worked on by:
- Claude Code (this tool)
- Cursor AI (use .cursorrules)
- Cline (use .clinerules)
- Human developers (use README.md)

All tools have access to same context via:
- PROGRESS.md - Current state
- PLAN.md - Detailed plan
- CLAUDE.md - This file
- .cursorrules - Cursor-specific
- .clinerules - Cline-specific

## Remember

- **Push after milestones** - Don't let work sit unpushed
- **Small commits, frequent pushes** - Better than large batches
- **Always include Co-Authored-By** - Give credit
- **Keep PROGRESS.md current** - It's the source of truth
- **Test before push** - When tests exist, run them

## Success Criteria

Project is successful when:
- All 5 phases complete
- Tests passing
- Documentation complete
- Can import real Lovable project end-to-end
- Deploys to Databricks successfully
- All work committed and pushed to remote
