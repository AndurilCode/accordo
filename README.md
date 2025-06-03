# Workflow Commander MCP Server

A powerful MCP (Model Context Protocol) server that provides **dynamic YAML-driven workflow guidance** for AI coding agents. Features structured development workflows with progression control and decision points.

## What This Does

This server guides AI agents through structured, schema-driven development workflows:
- **📋 Dynamic YAML Workflows**: Custom workflows defined in YAML with schema-driven execution
- **🔍 Discovery-First**: Automatically discovers and selects appropriate workflows based on task
- **⚡ Real-time State**: Live workflow state tracking with comprehensive session management
- **🎯 Mandatory Guidance**: Authoritative phase-by-phase instructions agents must follow

## Key Features

- **📋 YAML-Driven**: Fully customizable workflows defined in YAML with schema validation
- **🔍 Smart Discovery**: Automatic workflow discovery and selection based on task requirements  
- **🎯 Guided Execution**: Phase-by-phase mandatory guidance with acceptance criteria
- **📊 Real-time Tracking**: Live workflow state with detailed progress logging
- **🛡️ Error Recovery**: Built-in error handling and validation at each phase
- **📝 Session Management**: Persistent workflow sessions with automatic state synchronization

## Prerequisites

### Required: uv (Python Package Manager)

Install [uv](https://docs.astral.sh/uv/) for fast Python package management:

**On macOS and Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**On Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative methods:**
```bash
# With pip
pip install uv

# With pipx  
pipx install uv

# With Homebrew (macOS)
brew install uv
```

Verify installation:
```bash
uv --version
```

## Quick Start

### 1. Configure Your MCP Client

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

### 2. Discover and Start Workflows

**Discovery-First Approach:**
```
# 1. Discover available workflows
workflow_discovery(task_description="Add: user authentication to my API")

# 2. Start selected workflow (agent chooses appropriate workflow)
workflow_guidance(action="start", context="workflow: Default Coding Workflow\nyaml: <discovered_yaml_content>")

# 3. Execute workflows step-by-step with control!
```

### 3. Workflow Progression

The workflow automatically flows through linear paths:
```
Start → Auto-progress through single-path nodes → Stop at decision point → Manual choice → Auto-progress to completion
```

**Example Progression Flow:**
```
analyze ──🤖──→ blueprint ──🤖──→ construct ──🤖──→ validate ──🤖──→ complete
          auto      auto        auto         auto
```

**Decision Point Example:**
```
decision_point ──👤──→ option_a ──🤖──→ final
               │  manual
               └──👤──→ option_b ──🤖──→ final
                  manual    auto
```

## Dynamic YAML Workflow System

### Overview

The workflow system is **purely YAML-driven** with the following architecture:

- **🔍 Discovery-First**: Agent must discover workflows before starting
- **📋 Schema-Driven**: All behavior determined by YAML workflow definitions
- **🎯 Agent-Controlled**: Agent selects workflows based on task requirements
- **📊 Dynamic State**: Real-time session management with persistent state

### Auto-Progression Feature

**How Auto-Progression Works:**

1. **All Transitions**: Every workflow transition requires explicit manual choice
2. **Decision Points**: Nodes with multiple `next_allowed_nodes` offer choice selection
3. **Linear Paths**: Even single-path nodes require manual confirmation to proceed
4. **Terminal Nodes**: Nodes with no `next_allowed_nodes` end the workflow

**Manual Progression Rules:**
```yaml
# All nodes require manual choice
single_path_node:
  next_allowed_nodes: [next_step]  # Manual: choose: next_step

# Multiple options require manual choice  
decision_node:
  next_allowed_nodes: [option_a, option_b, option_c]  # Manual: choose: option_a

# 🏁 Workflow completion (no paths)
terminal_node:
  next_allowed_nodes: []  # Workflow complete
```

**Manual Progression Usage:**
```
**🎯 Available Next Steps:**
   • next_step: Continue to implementation phase

**📋 To Proceed:** Call workflow_guidance with context="choose: <option_name>"
**Example:** workflow_guidance(action="next", context="choose: next_step")
```

### Available Workflows

The system includes several pre-built workflows:

#### 1. **Default Coding Workflow** (`default-coding.yaml`)
- **Flow**: analyze → blueprint → construct → validate → complete
- **Auto-Progression**: ✅ All phases auto-progress (linear workflow)
- **Use Case**: Standard development tasks, feature implementation, bug fixes

#### 2. **Documentation Workflow** (`documentation.yaml`)  
- **Flow**: analyze_docs → plan_docs → create_docs → review_docs → finalize_docs
- **Auto-Progression**: ✅ All phases auto-progress (linear workflow)
- **Use Case**: Documentation creation, README updates, API documentation

#### 3. **Debugging Workflow** (`debugging.yaml`)
- **Flow**: investigate → analyze_root_cause → develop_fix → test_fix → validate_solution → finalize_bugfix  
- **Auto-Progression**: ✅ All phases auto-progress (linear workflow)
- **Use Case**: Bug investigation, issue resolution, troubleshooting

### Workflow Discovery Process

**1. Discover Available Workflows:**
```python
workflow_discovery(task_description="Add: user authentication system")
```

**2. Agent Examines Options:**
The system shows available workflows with their capabilities and suitability for the task.

**3. Start Selected Workflow:**
```python
workflow_guidance(
    action="start", 
    context="workflow: Default Coding Workflow\nyaml: <complete_yaml_content>"
)
```

**4. Progression Begins:**
The workflow automatically flows through linear paths.

### Creating Custom Workflows

#### Basic YAML Structure

```yaml
name: My Custom Workflow
description: Workflow description

inputs:
  task_description:
    type: string
    description: Task provided by the user
    required: true

execution:
  max_depth: 10
  allow_backtracking: true

workflow:
  goal: Overall workflow objective
  root: start_node
  
  tree:
    start_node:
      goal: |
        What this node accomplishes.
        Use ${{ inputs.task_description }} for dynamic content.
      acceptance_criteria:
        completion_check: "What constitutes completion"
      next_allowed_nodes: [next_node]  # Auto-progresses
    
    decision_node:
      goal: "Make a choice between options"
      next_allowed_nodes: [option_a, option_b]  # Requires manual choice
      
    terminal_node:
      goal: "Final step"
      next_allowed_nodes: []  # Workflow ends
```

#### Auto-Progression Design Guidelines

**For Linear Workflows:**
```yaml
# Each node has exactly one next_allowed_node
phase1: { next_allowed_nodes: [phase2] }
phase2: { next_allowed_nodes: [phase3] } 
phase3: { next_allowed_nodes: [complete] }
complete: { next_allowed_nodes: [] }
```

**For Decision Workflows:**
```yaml
# Mix linear and decision nodes
start: { next_allowed_nodes: [analyze] }      # Auto-progresses
analyze: { next_allowed_nodes: [decision] }   # Auto-progresses  
decision: { next_allowed_nodes: [a, b, c] }   # Manual choice required
option_a: { next_allowed_nodes: [final] }     # Auto-progresses
final: { next_allowed_nodes: [] }             # Terminal
```

**Best Practices:**
- Use single `next_allowed_node` for automatic progression
- Use multiple `next_allowed_nodes` only for genuine decision points
- Keep decision points focused and clearly documented
- Test auto-progression flows with the test workflow

### Workflow Directory Structure

```
.workflow-commander/
├── workflows/                    # YAML workflow definitions
│   ├── default-coding.yaml      # Standard coding workflow  
│   ├── documentation.yaml       # Documentation workflow
│   ├── debugging.yaml           # Debugging workflow
│   ├── auto-progression-test.yaml # Auto-progression testing
│   └── your-custom.yaml         # Your custom workflows
├── workflow_state.json          # Current session state (auto-managed)
└── project_config.md            # Project configuration
```

## Usage Guide

### Core Tools

The server provides two primary tools:

#### **workflow_guidance** - Main Workflow Control
```python
# Start workflow (discovery-first required)
workflow_guidance(action="start", task_description="Add: feature name")

# Navigate workflow (when at decision points)  
workflow_guidance(action="next", context="choose: option_name")

# Auto-progression (no context needed for linear paths)
workflow_guidance(action="next")  # Automatically progresses if possible
```

#### **workflow_state** - State Management
```python
# Get current state
workflow_state(operation="get")

# Update state with log entries
workflow_state(operation="update", updates='{"log_entry": "Progress update"}')

# Reset workflow
workflow_state(operation="reset")
```

### Workflow Process

**1. Discovery Phase:**
```
workflow_discovery(task_description="Add: user authentication")
→ Shows available workflows and their capabilities
```

**2. Initialization:**
```
workflow_guidance(action="start", context="workflow: Name\nyaml: <content>")  
→ Starts workflow and auto-progresses through initial linear nodes
```

**3. Auto-Progression:**
```
workflow_guidance(action="next")
→ Automatically advances through single-path nodes
→ Stops at decision points requiring manual choice
```

**4. Decision Points:**
```
workflow_guidance(action="next", context="choose: option_name")
→ Makes manual choice at decision points
→ Resumes auto-progression after choice
```

**5. Completion:**
```
→ Workflow automatically reaches terminal node
→ Shows completion status and summary
```

### Auto-Progression Examples

**Linear Workflow (All Auto-Progress):**
```
User: workflow_guidance(action="start", ...)
→ 🤖 Auto-progressed: analyze → blueprint → construct → validate → complete
→ ✅ Workflow completed automatically
```

**Decision Workflow (Mixed Auto/Manual):**
```
User: workflow_guidance(action="start", ...)  
→ 🤖 Auto-progressed: start → linear1 → linear2 → decision_point
→ ⏸️ Stopped at decision point (choose: option_a or option_b)

User: workflow_guidance(action="next", context="choose: option_a")
→ 🤖 Auto-progressed: option_a → final  
→ ✅ Workflow completed
```

## Advanced Configuration

### Environment Variables

#### **WORKFLOW_AUTO_APPROVE_PLANS** (default: `false`)
Controls automatic plan approval in workflows:

```bash
# Enable automatic plan approval  
export WORKFLOW_AUTO_APPROVE_PLANS=true
```

**MCP Configuration:**
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



#### **WORKFLOW_LOCAL_STATE_FILE** (default: `false`)
Enables local state file synchronization:

```bash
# Enable local state file backup
export WORKFLOW_LOCAL_STATE_FILE=true
export WORKFLOW_LOCAL_STATE_FILE_FORMAT=MD  # or JSON
```

### MCP Client Configuration Details

#### Cursor Configuration
- **Windows**: `%APPDATA%\Cursor\User\mcp.json`
- **macOS**: `~/Library/Application Support/Cursor/User/mcp.json`
- **Linux**: `~/.config/Cursor/User/mcp.json`
- **Project**: `.cursor/mcp.json` in project directory

#### Claude Desktop Configuration  
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

## Installation Options

### Option 1: MCP Client Configuration (Recommended)
Use the uvx-based configuration shown in Quick Start. Automatically handles dependencies and updates.

### Option 2: Local Development
```bash
# Clone and install
git clone <repository-url>
cd workflow-commander
uv sync
```

### Option 3: Direct Installation
```bash
uvx --from git+https://github.com/AndurilCode/workflow-commander@main dev-workflow-mcp
```

## Technical Details

### How Progression Works

**Schema Analysis:**
- The system analyzes each workflow node's `next_allowed_nodes`
 
- Terminal nodes (0 next nodes) → Workflow completion

**Transition Engine:**
- Validates all transitions against workflow schema
- Executes automatic transitions for single-path nodes
- Maintains comprehensive transition logs
- Prevents infinite loops with depth limits

**Session Management:**
- Real-time workflow state tracking
- Automatic state synchronization  
- Persistent session management across MCP calls
- Dynamic workflow definition caching

### Workflow State Structure

**Dynamic Session State:**
```json
{
  "workflow_name": "Default Coding Workflow",
  "current_node": "construct", 
  "status": "RUNNING",
  "node_history": ["analyze", "blueprint"],
  "execution_context": {},
  "log_entries": ["🔄 Transitioned: analyze → blueprint"]
}
```

**Progression Logging:**
```
[11:07:13] 🔄 Transitioned: analyze → blueprint
[11:07:13] 🔄 Transitioned: blueprint → construct  
[11:07:13] 📍 Current: construct (manual choice required)
```

### Required Project Files

#### project_config.md
Single configuration file containing:
- Project structure and organization
- Dependencies and build information  
- Test commands and quality processes
- Project changelog and version history

*All workflow state is managed automatically through MCP server sessions*

## Bootstrap Configuration (Optional)

Deploy AI assistant guidelines:

```bash
# Deploy workflow guidelines to AI assistants
curl -s https://raw.githubusercontent.com/AndurilCode/workflow-commander/refs/heads/main/bootstrap-execute-tasks.sh | bash
```

Creates configuration files for:
- **Cursor**: `.cursor/rules/execute-tasks.mdc`
- **GitHub Copilot**: `.github/copilot-instructions.md`  
- **Claude**: `./CLAUDE.md`

## Examples

### Complete Workflow Example

**1. Start with Discovery:**
```
workflow_discovery(task_description="Add: OAuth authentication")
→ Recommends Default Coding Workflow for implementation tasks
```

**2. Initialize Workflow:**
```  
workflow_guidance(action="start", context="workflow: Default Coding Workflow\nyaml: <yaml_content>")
→ 🤖 Auto-progressed to: CONSTRUCT
→ Started at analyze, automatically progressed through blueprint to construct
```

**3. Continue Through Auto-Progression:**
```
workflow_guidance(action="next")
→ 🤖 Auto-progressed to: VALIDATE  
→ Implementation complete, moved to validation phase
```

**4. Final Completion:**
```
workflow_guidance(action="next")
→ 🤖 Auto-progressed to: COMPLETE
→ ✅ Workflow completed successfully
```

### Custom Decision Workflow Example

**YAML Definition:**
```yaml
name: Feature Development Workflow
workflow:
  root: analyze
  tree:
    analyze: { next_allowed_nodes: [design] }      # Auto-progresses
    design: { next_allowed_nodes: [complexity] }   # Auto-progresses  
    complexity:                                     # Decision point
      next_allowed_nodes: [simple_impl, complex_impl]
    simple_impl: { next_allowed_nodes: [test] }    # Auto-progresses
    complex_impl: { next_allowed_nodes: [review] } # Auto-progresses
    test: { next_allowed_nodes: [deploy] }         # Auto-progresses
    review: { next_allowed_nodes: [test] }         # Auto-progresses
    deploy: { next_allowed_nodes: [] }             # Terminal
```

**Execution Flow:**
```
analyze ──🤖──→ design ──🤖──→ complexity ──👤──→ simple_impl ──🤖──→ test ──🤖──→ deploy
                                     │                                    
                                     └──👤──→ complex_impl ──🤖──→ review ──🤖──┘
```

## Troubleshooting

### Common Issues

**1. Discovery Required Error:**
```
❌ Workflow Discovery Required
→ Solution: Start with workflow_discovery() before using workflow_guidance
```

**2. Missing YAML Content:**
```  
❌ Workflow YAML Required
→ Solution: Include complete YAML content in context when starting workflows
```

**3. Invalid Choice Error:**
```
❌ Invalid choice: wrong_option
→ Solution: Use exact option names from available next steps
```

### Progression Issues

**Choice Not Working:**
- Verify context uses correct format: `context="choose: <option_name>"`
- Check that option name exactly matches available transitions
- Ensure workflow definition is valid
- Confirm node allows the specified transition

**Invalid Choice Error:**
```
❌ Invalid choice: wrong_option
→ Solution: Use exact option names from available next steps
→ Format: workflow_guidance(action="next", context="choose: <exact_option_name>")
```

**Stuck at Node:**
- Verify workflow YAML structure
- Check `next_allowed_nodes` configuration  
- Ensure available transitions are properly defined

### Getting Help

1. **Check Workflow State**: Use `workflow_state(operation="get")` for current status
2. **Validate Workflow**: Test workflow functionality with manual progression
3. **Review Logs**: Check transition logs for debugging
4. **Test Discovery**: Ensure workflow discovery process works correctly

## Acknowledgments

This project was inspired by workflow concepts from [@kleosr/cursorkleosr](https://github.com/kleosr/cursorkleosr). We've evolved these ideas into a dynamic, YAML-driven MCP server with structured workflow guidance and manual progression control.