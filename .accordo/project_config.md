# Project Configuration

## Project Structure
- `src/accordo-mcp/` - Main package source code
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
python -m src.accordo-mcp.server
```

## Documentation Maintenance Plan

### README.md Maintenance Responsibilities
- **Primary Maintainer**: Project lead responsible for major structural updates
- **Feature Owners**: Developers implementing new features must update relevant documentation sections
- **Release Manager**: Updates version-specific information and examples before releases

### Update Triggers
Documentation should be updated when:
1. **New Features**: Any new workflow capabilities, tools, or auto-progression enhancements
2. **API Changes**: Changes to workflow_guidance, workflow_state, or discovery tools
3. **Workflow Updates**: New YAML workflows or changes to existing workflow definitions
4. **Configuration Changes**: Environment variables, MCP setup, or installation procedures
5. **Breaking Changes**: Any changes that affect existing user workflows or configurations

### Maintenance Process
1. **Feature Development**: Developer updates documentation as part of feature implementation
2. **Review Process**: Documentation changes reviewed alongside code changes in PRs
3. **Testing**: Validate all code examples and installation instructions work correctly
4. **Release Updates**: Update changelog and version-specific information before releases

### Key Sections Requiring Regular Updates
- **Available Workflows**: Keep workflow descriptions current with actual YAML files
- **Code Examples**: Ensure all examples work with current implementation
- **Auto-Progression Features**: Update as auto-progression capabilities evolve
- **Installation Instructions**: Verify setup procedures work across platforms
- **Troubleshooting**: Add new issues and solutions as they're discovered

### Quality Assurance
- **Quarterly Reviews**: Comprehensive documentation review every quarter
- **Link Validation**: Regular checks that all links and references are current
- **Example Testing**: Periodic testing of all code examples in clean environments
- **User Feedback**: Incorporate feedback from documentation users and community

### Documentation Architecture Notes
- **Modular Structure**: Each major feature has dedicated sections for easy updates
- **Auto-Progression Focus**: Prominently features the key differentiating capability
- **Discovery-First Approach**: Emphasizes the modern workflow discovery process
- **YAML-Driven System**: Reflects the current pure YAML architecture without legacy references

## Changelog
- [2025-06-11] **ENHANCEMENT**: Enhanced workflow state tools to provide comprehensive audit trail with complete progression data: removed problematic ImportError fallback from export_session_to_markdown() function and replaced with direct session.to_markdown() integration, enhanced DynamicWorkflowState.to_markdown() method to display detailed acceptance criteria evidence with full text preservation (no truncation), improved node completion history formatting with emojis and structured evidence display, ensuring workflow tools now show complete workflow progression including all node outputs and criteria satisfaction evidence for better debugging and audit capabilities
- [2025-06-11] **MAJOR CLEANUP**: Completely removed execution settings from entire codebase for simplified architecture: eliminated ExecutionConfig class and execution field from WorkflowDefinition model, removed default_max_depth and allow_backtracking from WorkflowConfiguration service, updated template generator to stop creating execution blocks in YAML generation, cleaned all 10 workflow files (.accordo/workflows/*.yaml, docs/workflows/*.yaml, examples/workflows/*.yaml) to remove execution sections, updated discovery prompts and template files to exclude execution configuration guidance, removed execution-related test assertions and mock objects from test suite, maintained full backward compatibility as execution settings were configuration artifacts not used in runtime logic, achieved zero regression impact with all 618 tests passing and zero linting errors, resulting in cleaner codebase with simplified YAML workflow structure
- [2025-06-09] Added GitHub Actions workflow for pull request quality checks: created .github/workflows/pull-request.yml that triggers on PR events (opened, reopened, synchronize), runs linting checks (ruff check .), executes test suite (pytest tests/ --tb=short), and fails workflow on any errors. Includes comments for future enabling of code formatting and type checking once codebase violations are resolved. Added mypy to dev dependencies for future use.
- [2025-01-10] Refactored session manager input handling to be fully dynamic: replaced hardcoded input key checks (task_description, bug_severity, reproduction_steps) with dynamic iteration over workflow_def.inputs, created _prepare_dynamic_inputs() function with smart task mapping and type-based defaults, maintaining backward compatibility while supporting any workflow input structure defined in YAML
- [2025-06-04] Optimized session file structure and enhanced node completion tracking: deprecated unused plan field in YAML workflows, enhanced complete_current_node() to always populate node_outputs with acceptance criteria evidence, added validation helpers has_node_completion_evidence() and get_node_completion_summary(), improved logging for criteria satisfaction, and maintained backward compatibility while eliminating empty node_outputs in session files
- [2025-06-04] Implemented unique session file management system to prevent overrides: added timestamp-based unique filenames (client_timestamp_counter.ext), session archiving with completion timestamps, configurable retention policies (--session-retention-hours), and comprehensive test suite ensuring concurrent sessions no longer overwrite each other's files
- [2025-01-09] Added WORKFLOW_AUTO_PROGRESSION_ENABLED environment variable to control automatic workflow progression, allowing users to disable auto-progression and require manual confirmation for all transitions when set to "false" (default: "false")
- [2025-06-03] Completely rewrote README to reflect modern dynamic YAML workflow system, removing all legacy references and highlighting auto-progression feature with comprehensive usage examples and troubleshooting guide
- [2025-06-03] Implemented automatic workflow progression for linear paths, enabling workflows to automatically advance through single-path nodes while preserving manual control for decision points and terminal nodes
- [2025-06-02] Fixed missing WorkflowLoadError class and updated discovery_prompts.py to work with pure discovery system by removing hardcoded scoring methods and enabling agent-driven workflow selection without automated scoring algorithms
- [2025-06-02] Enhanced documentation.yaml and debugging.yaml workflows with highly authoritative guidance following same pattern as default-coding workflow, including mandatory progress logging in create_docs and develop_fix phases for comprehensive tracking and validation
- [2025-06-02] Enhanced default-coding.yaml workflow with highly authoritative and specific execution guidance, including mandatory progress logging in construct phase requiring workflow_state tool calls after every major step to ensure proper tracking and validation
- [2025-06-02] Updated bootstrap-execute-tasks.sh to deploy guidelines for the new dynamic workflow system, replacing hardcoded workflow instructions with schema-driven discovery and agent-controlled workflow selection documentation
- [2025-06-02] Transformed hardcoded YAML workflow system into truly dynamic schema-driven architecture by eliminating all hardcoded routing logic, implementing pure schema analysis, and enabling agent-driven workflow selection while preserving legacy fallback compatibility
- [2025-05-30] Implemented standardized task_description parameter format validation with "Action: Brief description" pattern across all 6 phase prompt tools, including comprehensive Field documentation and helpful error messages for non-conforming formats
- [2025-06-04] Refactored configuration system to use CLI arguments instead of environment variables: removed WORKFLOW_AUTO_APPROVE_PLANS (no longer needed with YAML workflows), converted local state file settings to --enable-local-state-file and --local-state-file-format CLI flags with automatic session persistence to .accordo/sessions/
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