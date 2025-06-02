# Project Configuration

## Project Structure
- `src/dev_workflow_mcp/` - Main package source code
  - `server.py` - Main MCP server implementation
  - `models/` - Pydantic models for workflow state and responses
  - `prompts/` - Workflow prompt definitions organized by category
  - `utils/` - Utility functions for state management and validation
  - `templates/` - Template files for workflow and project configuration
- `tests/` - Test files (to be added)
- `docs/` - Documentation files
- `pyproject.toml` - Project configuration and dependencies
- `README.md` - Project documentation

## Dependencies
- Python 3.12+
- FastMCP - MCP server framework
- Pydantic - Data validation and settings management
- uv - Package and dependency management

## Test Commands
```bash
# Run tests (when implemented)
source .venv/bin/activate && python -m pytest tests/ --tb=short
# Run linter
ruff check .

# Format code
ruff format .

# Type checking
mypy src/

# Check all quality tools
ruff check . && ruff format --check . && mypy src/
```

## Build Commands
```bash
# Install dependencies
source .venv/bin/activate && uv sync --extra dev

# Install in development mode
uv pip install -e .

# Build package
python -m build

# Run the MCP server
python -m src.dev_workflow_mcp.server
```

## Changelog
- [2025-06-02] Fixed missing WorkflowLoadError class and updated discovery_prompts.py to work with pure discovery system by removing hardcoded scoring methods and enabling agent-driven workflow selection without automated scoring algorithms
- [2025-06-02] Enhanced documentation.yaml and debugging.yaml workflows with highly authoritative guidance following same pattern as default-coding workflow, including mandatory progress logging in create_docs and develop_fix phases for comprehensive tracking and validation
- [2025-06-02] Enhanced default-coding.yaml workflow with highly authoritative and specific execution guidance, including mandatory progress logging in construct phase requiring workflow_state tool calls after every major step to ensure proper tracking and validation
- [2025-06-02] Updated bootstrap-execute-tasks.sh to deploy guidelines for the new dynamic workflow system, replacing hardcoded workflow instructions with schema-driven discovery and agent-controlled workflow selection documentation
- [2025-06-02] Transformed hardcoded YAML workflow system into truly dynamic schema-driven architecture by eliminating all hardcoded routing logic, implementing pure schema analysis, and enabling agent-driven workflow selection while preserving legacy fallback compatibility
- [2025-05-30] Implemented standardized task_description parameter format validation with "Action: Brief description" pattern across all 6 phase prompt tools, including comprehensive Field documentation and helpful error messages for non-conforming formats
- Added WORKFLOW_AUTO_APPROVE_PLANS environment variable to enable automatic blueprint approval, allowing workflows to bypass manual user approval and transition directly from blueprint to construction phase when set to "true"
- Enhanced all four core phase prompts (analyze, blueprint, construct, validate) with mandatory validation checklists, explicit anti-patterns, detailed examples, escalation triggers, and comprehensive verification procedures to provide clearer agent guidance and reduce workflow divergence
- Updated bootstrap-execute-tasks.sh to embed execute-tasks content directly instead of reading from external files, with Cursor receiving YAML frontmatter format while Copilot and Claude get clean content without YAML frontmatter
- Created bootstrap-execute-tasks.sh script that deploys execute-tasks guidelines to multiple AI assistants (Cursor, GitHub Copilot, Claude) with argument parsing, content checking, directory creation, and intelligent deployment logic
- Removed all utility tools (hello_workflow, get_session_statistics, health_check_sessions, export_client_session, cleanup_old_sessions) from MCP server to eliminate noise and provide a clean, focused tool interface for agents
- Fixed all 27 failing unit tests by adding Context parameters to test methods and updating test expectations for session-based state management
- Improved tool naming from `_prompt` to `_guidance` suffix to clearly indicate mandatory execution guidance that agents must follow exactly
- Implemented comprehensive unit test suite with 143 tests achieving 99% code coverage across all modules
- Implemented comprehensive workflow MCP server with phase-based prompts
- Added state management utilities and file templates
- Created prompt chaining system for guided workflow execution
- Added error recovery and validation prompts
- Implemented multi-item workflow processing capabilities 