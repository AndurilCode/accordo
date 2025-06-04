# Cursor MCP Configuration Examples

This directory contains example MCP configurations for Cursor IDE. These configurations show how to set up Workflow Commander with different feature sets and options.

## Configuration Files

### 1. Basic Setup (`basic-setup.json`)

**Purpose**: Minimal configuration for getting started with Workflow Commander in Cursor.

**Features**:
- Standard uvx-based installation from GitHub
- No additional command line arguments
- Uses default settings

### 2. Advanced Setup (`advanced-setup.json`)

**Purpose**: Configuration with additional command line options.

**Features**:
- Local state file synchronization enabled (`--enable-local-state-file`)
- JSON format for state files (`--local-state-file-format JSON`)
- Custom session retention period (`--session-retention-hours 72`)

**Command Line Arguments Explained**:

#### `--enable-local-state-file`
- **Purpose**: Automatically saves workflow state to local files in `.workflow-commander/sessions/`
- **Benefit**: Persistent state across sessions, better debugging

#### `--local-state-file-format`
- **Options**: `MD` (markdown) or `JSON` (structured JSON)
- **Default**: `MD`
- **Purpose**: Choose the format for local state files

#### `--session-retention-hours`
- **Default**: `168` (7 days)
- **Purpose**: Hours to keep completed sessions before cleanup
- **Example**: `72` keeps sessions for 3 days

#### `--repository-path`
- **Purpose**: Specify the repository root where `.workflow-commander` folder should be located
- **Default**: Current directory
- **Example**: `--repository-path /path/to/my/project`

#### `--disable-session-archiving`
- **Purpose**: Disable archiving of session files before cleanup
- **Default**: Sessions are archived with completion timestamp

## Configuration Location

**Configuration File Paths**:
- **Windows**: `%APPDATA%\Cursor\User\mcp.json`
- **macOS**: `~/Library/Application Support/Cursor/User/mcp.json`
- **Linux**: `~/.config/Cursor/User/mcp.json`
- **Project-specific**: `.cursor/mcp.json` in project root

## Setup Instructions

1. **Create Configuration File**:
   ```bash
   # Windows (PowerShell)
   New-Item -Path "$env:APPDATA\Cursor\User" -Name "mcp.json" -ItemType "file" -Force
   
   # macOS/Linux
   mkdir -p ~/.config/Cursor/User
   touch ~/.config/Cursor/User/mcp.json
   ```

2. **Copy Configuration**: Copy the contents of your chosen setup file to `mcp.json`

3. **Restart Cursor**: Close and reopen Cursor for the configuration to take effect

4. **Verify Installation**:
   ```
   workflow_discovery(task_description="Test: setup verification")
   ```

## Project-Specific Configuration

Create `.cursor/mcp.json` in your project root for project-specific settings:

```json
{
  "mcpServers": {
    "workflow-commander": {
      "command": "uvx",
      "args": [
        "--from", 
        "git+https://github.com/AndurilCode/workflow-commander@main", 
        "dev-workflow-mcp",
        "--enable-local-state-file",
        "--repository-path", "."
      ]
    }
  }
}
```

## Troubleshooting

### Common Issues

#### 1. Server Not Starting
**Symptoms**: MCP server doesn't appear in Cursor  
**Solutions**:
```bash
# Verify uvx is installed
uvx --version

# Test the server manually
uvx --from git+https://github.com/AndurilCode/workflow-commander@main dev-workflow-mcp --help
```

#### 2. Configuration Not Loading
**Symptoms**: Changes to mcp.json don't take effect  
**Solutions**:
1. **Restart Cursor completely** (close all windows)
2. **Check JSON syntax** - validate your JSON formatting
3. **Check file location** - ensure mcp.json is in the correct directory

## Getting Help

If you encounter issues:

1. **Check Configuration**: Validate JSON syntax and file locations
2. **Test Manually**: Try running the server command manually  
3. **Report Issues**: Use GitHub issues for bugs and feature requests

## Next Steps

Once Cursor is configured:

2. **[Basic Workflow Examples](../../workflows/basic/)** - Explore example workflows 