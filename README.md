# Development Workflow MCP Server

A fast, Rust-powered MCP (Model Context Protocol) server that provides structured workflow guidance for coding agents. This server helps prevent hallucinations and ensures consistent, methodical development by providing step-by-step **mandatory execution guidance** through defined phases.

## What This Does

This server guides AI coding agents through a disciplined development process:
- **ANALYZE** → **BLUEPRINT** → **CONSTRUCT** → **VALIDATE** phases
- **Mandatory guidance** with authoritative instructions agents must follow exactly
- **Error recovery** and built-in quality gates
- **Multi-item processing** for complex projects

## Prerequisites

Before using this workflow server, ensure you have the following installed:

### Required: uv (Python Package Manager)

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable Python package management. Install uv first:

**On macOS and Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**On Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative installation methods:**
```bash
# With pip
pip install uv

# With pipx  
pipx install uv

# With Homebrew (macOS)
brew install uv

# With Pacman (Arch Linux)
pacman -S uv
```

After installation, restart your terminal or add uv to your PATH:
```bash
# Add to ~/.bashrc, ~/.zshrc, etc.
export PATH="$HOME/.local/bin:$PATH"
```

Verify installation:
```bash
uv --version
```

### Optional: Node.js (for some MCP clients)

Some MCP clients may require Node.js. Install from [nodejs.org](https://nodejs.org/) if needed.

## Quick Start

**Get productive in 3 steps:**

### 1. Configure Your MCP Client

Add this to your MCP client configuration file:

**For Cursor** (`.cursor/mcp.json` or `%APPDATA%\Cursor\User\mcp.json`):
```json
{
  "mcpServers": {
    "workflow-commander": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/AndurilCode/workflow-commander@main", "dev-workflow-mcp"]
    }
  }
}
```

**For Claude Desktop** (`~/.config/Claude/claude_desktop_config.json`):
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

### 2. Configure AI Assistant Guidelines (Optional but Recommended)

Run this one-liner in any project directory to set up execute-tasks guidelines:

```bash
curl -s https://raw.githubusercontent.com/AndurilCode/workflow-commander/refs/heads/main/bootstrap-execute-tasks.sh | bash
```

This deploys configuration files that instruct AI assistants to:
- Use workflow guidance tools for complex tasks
- Follow mandatory execution instructions precisely  
- Maintain proper workflow state synchronization

### 3. Start Using

Restart your MCP client and start a workflow:

```
# In your AI assistant
init_workflow_guidance(task_description="Add user authentication to my API")
```

The workflow will guide you through each phase automatically!

## Features

- **🚀 Structured Workflow**: ANALYZE → BLUEPRINT → CONSTRUCT → VALIDATE phases
- **⚡ Mandatory Guidance**: Authoritative instructions that agents must execute exactly
- **🔗 Prompt Chaining**: Each guidance tool explicitly specifies the next tool to call
- **🛡️ Error Recovery**: Built-in error handling and recovery guidance
- **📝 Multi-Item Processing**: Supports iterating through multiple workflow items
- **📋 Changelog Integration**: Automatically updates project changelog
- **⚙️ Auto-Approval**: Optional automatic blueprint approval for streamlined workflows

## Advanced Configuration

### MCP Client Setup Details

#### Cursor Configuration Locations

- **Windows**: `%APPDATA%\Cursor\User\mcp.json`
- **macOS**: `~/Library/Application Support/Cursor/User/mcp.json` 
- **Linux**: `~/.config/Cursor/User/mcp.json`

**Alternative locations:**
- **Project-specific**: `.cursor/mcp.json` in your project directory
- **Global**: `~/.cursor/mcp.json` for access across all projects

**Setup Steps:**
1. Create the configuration file at the appropriate location for your OS
2. Add the JSON configuration above
3. Restart Cursor to load the server
4. Access MCP settings: `Cmd/Ctrl + Shift + J` → Navigate to "MCP" tab
5. Verify the workflow-commander server appears and shows a green status

#### Claude Desktop Configuration Locations

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**Setup Steps:**
1. Ensure you have [Claude Desktop](https://claude.ai/download) installed
2. Create or edit the configuration file at the appropriate location
3. Add the workflow-commander server configuration (see Quick Start section)
4. Restart Claude Desktop
5. Test the connection by asking Claude: "What workflow guidance tools are available?"

### Environment Variables

#### Auto-Approval Configuration

**For true Vibe Coders: WORKFLOW_AUTO_APPROVE_PLANS** (default: `false`)

Controls whether blueprint plans are automatically approved without user interaction:

- **`false`** (default): Blueprint plans require manual user approval before proceeding to implementation
- **`true`**: Blueprint plans are automatically approved and the workflow proceeds directly to the construction phase

**Usage:**
```bash
# Enable auto-approval for automated workflows
export WORKFLOW_AUTO_APPROVE_PLANS=true

# Or set when starting your MCP client
WORKFLOW_AUTO_APPROVE_PLANS=true cursor
```

**MCP Config:**
```json
{
  "mcpServers": {
    "workflow-commander": {
      "command": "uvx", 
      "args": ["--from", "git+https://github.com/AndurilCode/workflow-commander@main", "dev-workflow-mcp"],
      "env": {
        "WORKFLOW_AUTO_APPROVE_PLANS": "true"
      }
    }
  }
}
```

**When to use auto-approval:**
- ✅ Automated CI/CD workflows
- ✅ Batch processing multiple items
- ✅ Development environments with trusted input
- ❌ Production deployments requiring human oversight
- ❌ Complex or critical changes needing review

**Example with auto-approval enabled:**
```
🤖 BLUEPRINT AUTO-APPROVED - PROCEEDING TO CONSTRUCTION

✅ AUTO-APPROVAL ACTIVATED:
- Environment Variable: WORKFLOW_AUTO_APPROVE_PLANS=true
- Phase → CONSTRUCT (auto-transitioned)
- Plan automatically approved without user interaction

🔨 CONSTRUCT PHASE ACTIVE:
Continue with implementation - no user approval needed!
```

## Installation Options

### Option 1: MCP Client Configuration (Recommended)

Use the uvx-based configuration shown in the Quick Start section above. This method automatically handles dependencies and updates.

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

## Usage Guide

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

#### Project Setup Guidance
- `check_project_config_guidance` - Verify project configuration with mandatory steps
- `create_project_config_guidance` - Create project config template with mandatory steps

#### Transition Guidance
- `update_workflow_state_guidance` - Update workflow state with mandatory steps
- `get_workflow_state_markdown` - Get current workflow state for debugging/display

### Workflow Process

1. **Initialize**: Start with `init_workflow_guidance(task_description="Your task")`
2. **Analyze**: Agent analyzes requirements without coding
3. **Blueprint**: Agent creates detailed implementation plan
4. **Construct**: Agent implements following the approved plan
5. **Validate**: Agent tests and validates the implementation
6. **Complete**: Agent finalizes and moves to next item (if any)

### Example Workflow

```python
# In your MCP client (e.g., Cursor or Claude Desktop)

# 1. Start a new workflow
# Call: init_workflow_guidance
# Parameters: task_description="Add user authentication to the API"

# 2. The agent will be guided through each phase:
# - analyze_phase_guidance: Understand requirements
# - blueprint_phase_guidance: Create implementation plan  
# - construct_phase_guidance: Implement the changes
# - validate_phase_guidance: Test and validate
# - complete_workflow_guidance: Finalize and update changelog

# 3. Each step automatically updates and shows the current workflow state
# 4. If there are more items, the workflow continues automatically
```

### Bootstrap Configuration Details

The bootstrap script deploys execute-tasks configuration files for:
- **Cursor**: `.cursor/rules/execute-tasks.mdc` (with YAML frontmatter)
- **GitHub Copilot**: `.github/copilot-instructions.md`
- **Claude**: `./CLAUDE.md`

**Manual Options:**

```bash
# Deploy to specific assistants only
curl -s https://raw.githubusercontent.com/AndurilCode/workflow-commander/refs/heads/main/bootstrap-execute-tasks.sh | bash -s cursor
curl -s https://raw.githubusercontent.com/AndurilCode/workflow-commander/refs/heads/main/bootstrap-execute-tasks.sh | bash -s copilot
curl -s https://raw.githubusercontent.com/AndurilCode/workflow-commander/refs/heads/main/bootstrap-execute-tasks.sh | bash -s claude

# Deploy to multiple specific assistants
curl -s https://raw.githubusercontent.com/AndurilCode/workflow-commander/refs/heads/main/bootstrap-execute-tasks.sh | bash -s cursor copilot
```

The script will:
- Skip files that already contain execute-tasks content
- Create necessary directories automatically
- Deploy content with appropriate formatting for each assistant

## Technical Details

### How It Works

The workflow system uses **centralized session management** that automatically handles all state tracking:

- **No Manual File Editing**: All workflow state is managed automatically in-memory via MCP server sessions
- **Real-time State Updates**: Each guidance tool updates and returns the current state
- **Complete Visibility**: You always see the updated workflow state after each action
- **Automatic Logging**: All actions and transitions are logged with timestamps

### Required Files

The workflow requires one configuration file in your project root:

#### project_config.md
Contains project configuration including:
- Project structure and information
- Dependencies and versions
- Test commands and build processes
- Project changelog

*Note: Workflow state is now managed purely through the MCP server session system - no workflow files are created*

### Centralized State Management

Each guidance tool provides real-time state updates and clear next steps:

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → ANALYZE
- Status → RUNNING
- Analysis phase initiated

**📋 CURRENT WORKFLOW STATE:**
```markdown
# Workflow State
_Last updated: 2024-12-19_

## State
Phase: ANALYZE
Status: RUNNING
CurrentItem: Add user authentication to the API

## Plan
<!-- The AI fills this in during the BLUEPRINT phase -->

## Items
| id | description | status |
|----|-------------|--------|
| 1 | Add user authentication to the API | pending |

## Log
[2024-12-19 14:30:15] 🚀 WORKFLOW INITIALIZED: Add user authentication to the API
[2024-12-19 14:30:16] 📊 ANALYZE PHASE STARTED: Add user authentication to the API
```

**🔄 NEXT STEP:**
Call: `blueprint_phase_guidance`
Parameters: task_description="Add user authentication to the API", requirements_summary="..."

### Running the Server (Local Development)

```bash
# Run the MCP server
python -m src.dev_workflow_mcp.server

# Or using the main function
python src/dev_workflow_mcp/server.py
```

## Acknowledgments

This project was inspired by the workflow concepts from [@kleosr/cursorkleosr](https://github.com/kleosr/cursorkleosr). We've adapted and extended these ideas to create a more structured, MCP-based approach to development workflow guidance.