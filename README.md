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

### Option 1: MCP Client Configuration (Recommended)

For use with MCP clients like Cursor, add this configuration to your `mcp.json` file:

```json
{
  "mcpServers": {
    "workflow-commander": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/AndurilCode/workflow-commander@main", "dev-workflow-mcp"]
    }
  }
}
````

#### Cursor Configuration

**Location of mcp.json:**
- **Windows**: `%APPDATA%\Cursor\User\mcp.json`
- **macOS**: `~/Library/Application Support/Cursor/User/mcp.json` 
- **Linux**: `~/.config/Cursor/User/mcp.json`

**Setup Steps:**
1. Create the configuration file at the appropriate location for your OS
2. Add the JSON configuration above
3. Restart Cursor to load the server
4. Access MCP settings: `Cmd/Ctrl + Shift + J` → Navigate to "MCP" tab
5. Verify the workflow-commander server appears and shows a green status

**Alternative Configuration Methods:**
- **Project-specific**: Create `.cursor/mcp.json` in your project directory
- **Global**: Use `~/.cursor/mcp.json` for access across all projects

#### Claude Desktop Configuration

**Location of claude_desktop_config.json:**
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**Setup Steps:**
1. Ensure you have [Claude Desktop](https://claude.ai/download) installed
2. Create or edit the configuration file at the appropriate location
3. Add the workflow-commander server configuration:

```json
{
  "mcpServers": {
    "workflow-commander": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/AndurilCode/workflow-commander@main", "dev-workflow-mcp"],
      "env": {}
    }
  }
}
```

4. Restart Claude Desktop
5. Test the connection by asking Claude: "What workflow guidance tools are available?"

**Prerequisites for both clients:**
- Node.js installed for running MCP servers
- `uvx` available in your PATH (install with `pip install uvx` if needed)

After adding the configuration, restart your MCP client to load the server.

### Option 2: Local Development Installation

```bash
# Clone the repository
git clone <repository-url>
cd dev-workflow-mcp

# Install dependencies
uv sync

# Or with pip
pip install -e .
```

### Option 3: Direct Installation

```bash
# Install directly from GitHub
uvx --from git+https://github.com/AndurilCode/workflow-commander@main dev-workflow-mcp
```

## Usage

### Running the Server (Local Development)

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

✅ STATE UPDATED AUTOMATICALLY:
- Phase → ANALYZE
- Status → RUNNING
- Analysis phase initiated

📋 CURRENT WORKFLOW STATE:
[Shows the complete updated workflow state]

📊 REQUIRED ACTIONS:
1. Read and understand project_config.md
2. Read relevant existing code  
3. Write clear requirements summary
4. Log findings as you discover them