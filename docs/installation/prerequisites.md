# Prerequisites

Before installing Workflow Commander MCP Server, ensure your system meets the requirements and has the necessary dependencies installed.

## Required Dependencies

### Python Package Manager: uv

**uv** is the recommended and required Python package manager for Workflow Commander. It provides fast, reliable package management and is essential for the MCP server installation.

#### Why uv?
- **Performance**: Up to 100x faster than pip for package resolution
- **Reliability**: Better dependency resolution and lock file management
- **Simplicity**: Single tool for package management and virtual environments
- **Modern**: Built for modern Python development workflows

#### Installation

For complete installation instructions, see the official uv documentation:
**📖 [uv Installation Guide](https://docs.astral.sh/uv/getting-started/installation/)**

#### Verification

After installation, verify uv is working correctly:

```bash
uv --version
```

You should see output similar to:
```
uv 0.1.0 (or newer)
```

### Configuration File Locations

Different MCP clients store configuration in different locations:

**📖 [Cursor MCP Configuration](https://docs.cursor.com/advanced/mcp)**
**📖 [Claude Desktop MCP Setup](https://modelcontextprotocol.io/quickstart/user)**

## Project Structure

### Workflow Storage

Workflow Commander automatically creates and uses a specific directory structure in your project:

```
your-project/
├── .workflow-commander/
│   ├── workflows/          # Store your YAML workflow files here
│   │   ├── custom-workflow.yaml
│   │   ├── my-project-workflow.yaml
│   │   └── ...
│   ├── sessions/           # Workflow state files (auto-created)
│   └── project_config.md   # Project-specific guidance (auto-created)
├── src/
├── docs/
└── ... (your project files)
```

**Key directories:**
- **`.workflow-commander/workflows/`** - Place your custom YAML workflow files here
- **`.workflow-commander/sessions/`** - Automatic workflow state storage (if enabled)
- **`.workflow-commander/project_config.md`** - **Project-specific guidance for workflows**

### Project Configuration (`project_config.md`)

The `project_config.md` file provides **essential project context** that workflows use to understand your specific setup:

**Purpose:** 
- Guides AI agents on **how to work with your specific project**
- Contains project-specific commands, conventions, and procedures
- **Automatically referenced by workflows** for intelligent task execution

**Typical content includes:**
- **Test Commands**: `npm test`, `pytest`, `cargo test`, etc.
- **Linting**: `eslint .`, `ruff check`, `clippy`, etc.  
- **Build Processes**: `npm run build`, `cargo build`, `make`, etc.
- **Development Setup**: Virtual environment activation, dependency installation
- **Project Conventions**: Code style, file organization, naming patterns
- **Deployment Instructions**: How to deploy or publish the project

**Example structure:**
```markdown
# Project Configuration

## Development Setup
- **Install Dependencies**: `uv sync`
- **Activate Environment**: `source .venv/bin/activate`

## Quality Assurance  
- **Run Tests**: `uv run pytest tests/`
- **Lint Code**: `uv run ruff check src/`
- **Format Code**: `uv run ruff format src/`

## Build & Deploy
- **Build Package**: `uv build`
- **Publish**: `uv publish`
```

**Workflow Integration:**
- Workflows automatically read this file for project-specific guidance
- Enables **intelligent automation** of testing, linting, and deployment
- **Customizes workflow behavior** based on your project's specific needs

### File System Access

**Workflow Commander requires:**
- **Read/write access** to the project directory
- **Automatic creation** of `.workflow-commander/` folder structure
- **No access required** outside the project directory

## Next Steps

Once prerequisites are installed:

1. **[Configuration Examples](../../examples/configurations/)** - MCP client setup examples