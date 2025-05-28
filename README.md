# Development Workflow MCP Server

An MCP (Model Context Protocol) server that provides structured workflow guidance to guide coding agents through a disciplined development process. This server helps prevent hallucinations and ensures consistent, methodical development by providing step-by-step **mandatory execution guidance** through defined phases.

## Features

- **Structured Workflow**: Guides agents through ANALYZE → BLUEPRINT → CONSTRUCT → VALIDATE phases
- **State Management**: Maintains workflow state in `workflow_state.md` file
- **Mandatory Guidance**: Each tool provides authoritative instructions that agents must execute exactly
- **Prompt Chaining**: Each guidance tool explicitly specifies the next tool to call
- **Error Recovery**: Built-in error handling and recovery guidance
- **Multi-Item Processing**: Supports iterating through multiple workflow items
- **Changelog Integration**: Automatically updates project changelog

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd dev-workflow-mcp

# Install dependencies
uv sync

# Or with pip
pip install -e .
```

## Usage

### Running the Server

```bash
# Run the MCP server
python -m src.dev_workflow_mcp.server

# Or using the main function
python src/dev_workflow_mcp/server.py
```

### Available Guidance Tools

The server provides the following workflow guidance tools that provide **mandatory execution instructions**:

#### Phase Guidance
- `init_workflow_guidance` - Initialize a new workflow with mandatory steps
- `analyze_phase_guidance` - Guide through requirements analysis with mandatory steps
- `blueprint_phase_guidance` - Guide through planning and design with mandatory steps
- `construct_phase_guidance` - Guide through implementation with mandatory steps
- `validate_phase_guidance` - Guide through testing and validation with mandatory steps
- `revise_blueprint_guidance` - Revise plans based on feedback with mandatory steps

#### Management Guidance
- `complete_workflow_guidance` - Complete current workflow item with mandatory steps
- `iterate_next_item_guidance` - Move to next workflow item with mandatory steps
- `finalize_workflow_guidance` - Finalize entire workflow with mandatory steps
- `error_recovery_guidance` - Handle errors and recovery with mandatory steps
- `fix_validation_issues_guidance` - Fix validation problems with mandatory steps
- `escalate_to_user_guidance` - Escalate critical issues with mandatory steps
- `changelog_update_guidance` - Update project changelog with mandatory steps

#### Transition Guidance
- `update_workflow_state_guidance` - Update workflow state file with mandatory steps
- `create_workflow_state_file_guidance` - Create initial state file with mandatory steps
- `check_project_config_guidance` - Verify project configuration with mandatory steps
- `create_project_config_guidance` - Create project config template with mandatory steps
- `validate_workflow_files_guidance` - Validate workflow files with mandatory steps

### Workflow Process

1. **Initialize**: Start with `init_workflow_guidance(task_description="Your task")`
2. **Analyze**: Agent analyzes requirements without coding
3. **Blueprint**: Agent creates detailed implementation plan
4. **Construct**: Agent implements following the approved plan
5. **Validate**: Agent tests and validates the implementation
6. **Complete**: Agent finalizes and moves to next item (if any)

### Required Files

The workflow requires two files in your project root:

#### workflow_state.md
Tracks the current workflow state, progress, and logs. Created automatically by the `init_workflow_guidance`.

#### project_config.md
Contains project configuration including:
- Project structure
- Dependencies
- Test commands
- Build commands
- Changelog

## Example Usage

```python
# In your MCP client (e.g., Cursor)

# 1. Start a new workflow
# Call guidance: init_workflow_guidance
# Parameters: task_description="Add user authentication to the API"

# 2. The agent will be guided through each phase:
# - analyze_phase_guidance: Understand requirements
# - blueprint_phase_guidance: Create implementation plan
# - construct_phase_guidance: Implement the changes
# - validate_phase_guidance: Test and validate
# - complete_workflow_guidance: Finalize and update changelog

# 3. If there are more items, the workflow continues automatically
```

## Mandatory Execution Guidance

Each guidance tool provides authoritative instructions that agents must execute exactly:

```
✅ WHEN COMPLETE:
Call prompt: 'blueprint_phase_guidance'
Parameters: task_description="Add user authentication", requirements_summary="..."
```

This ensures the agent follows the exact workflow without deviation and prevents hallucinations.

## Error Handling

The workflow includes comprehensive error handling:

- **Simple Errors**: Fixed and workflow continues
- **Complex Issues**: Return to BLUEPRINT phase
- **Critical Errors**: Escalated to user with detailed context

## State Management

The workflow maintains state in `workflow_state.md`:

```markdown
## State
Phase: CONSTRUCT
Status: RUNNING
CurrentItem: Add user authentication to the API

## Items
| id | description | status |
|----|-------------|--------|
| 1 | Add user authentication to the API | pending |
| 2 | Implement rate limiting | pending |

## Log
[14:30:15] Started CONSTRUCT phase
[14:32:22] Created auth middleware
[14:35:10] Added JWT token validation
```

## Development

### Project Structure

```
src/dev_workflow_mcp/
├── server.py              # Main MCP server
├── models/                # Pydantic models
│   ├── workflow_state.py  # Workflow state models
│   └── responses.py       # Response models
├── prompts/               # Workflow guidance tools
│   ├── phase_prompts.py   # Phase-specific guidance
│   ├── management_prompts.py # Management guidance
│   └── transition_prompts.py # State transition guidance
├── utils/                 # Utilities
│   ├── state_manager.py   # State file operations
│   └── validators.py      # File validation
└── templates/             # File templates
    ├── workflow_state_template.md
    └── project_config_template.md
```

### Testing

```bash
# Run tests
python -m pytest

# Run linter
ruff check .

# Format code
ruff format .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linting and tests
6. Submit a pull request

## License

MIT License - see LICENSE file for details. 