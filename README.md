# Workflow Commander MCP Server

A powerful MCP (Model Context Protocol) server that provides **dynamic YAML-driven workflow guidance** for AI coding agents. Features structured development workflows with progression control and decision points.

## What This Does

This server guides AI agents through structured, schema-driven development workflows:
- **📋 Dynamic YAML Workflows**: Custom workflows defined in YAML with schema-driven execution
- **🔍 Discovery-First**: Automatically discovers and selects appropriate workflows based on task
- **⚡ Real-time State**: Live workflow state tracking with comprehensive session management
- **🎯 Mandatory Guidance**: Authoritative phase-by-phase instructions agents must follow
- **🤖 Agent-Generated Workflows**: Unique capability for agents to create custom YAML workflows on-the-fly

### Two Workflow Approaches

### Built-in Workflow Discovery Process

1. **Automatic Discovery** - System scans `.workflow-commander/workflows/` for available YAML workflows
2. **Intelligent Matching** - Analyzes task description against workflow capabilities and goals
3. **Workflow Selection** - Agent chooses the most appropriate workflow from discovered options
4. **Immediate Execution** - Selected workflow starts with full state management and progression control

This provides **instant access** to proven workflows for common development patterns - coding, documentation, debugging, and more!

### Agent Workflow Generation Process

1. **Analyze Task Requirements** - Agent understands specific needs
2. **Get Creation Guidance** - Comprehensive templates and best practices provided
3. **Generate Custom YAML** - Agent creates workflow tailored to exact requirements
4. **Start Execution** - Custom workflow runs with full state management

This enables agents to create workflows for **any domain** - web development, data science, DevOps, research, documentation, testing, and more!

## Quick Start

### Prerequisites

Install [uv](https://docs.astral.sh/uv/) for Python package management

Configure your MCP client:

**For Cursor** (`.cursor/mcp.json`):
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

## Getting Help

### 📚 Documentation
- **[Complete Documentation](docs/)** - Comprehensive guides and references
- **[Installation Prerequisites](docs/installation/prerequisites.md)** - Detailed setup requirements

### 🎯 Examples
- **[Workflow Examples](examples/workflows/)** - Ready-to-use workflow YAML files
- **[Configuration Examples](examples/configurations/)** - MCP client setup examples

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.