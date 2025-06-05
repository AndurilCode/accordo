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

**Purpose**: Configuration with comprehensive command line options including cache features.

**Features**:
- Repository path specification (`--repository-path`)
- Local state file synchronization enabled (`--enable-local-state-file`)
- JSON format for state files (`--local-state-file-format JSON`)
- Custom session retention period (`--session-retention-hours 72`)
- **Cache mode enabled** (`--enable-cache-mode`)
- **Semantic embedding model** (`--cache-embedding-model all-MiniLM-L6-v2`)
- **Custom cache location** (`--cache-db-path .workflow-commander/cache`)
- **Search result limit** (`--cache-max-results 50`)

### 3. Cache-Enabled Setup (`cache-enabled-setup.json`)

**Purpose**: Focused configuration highlighting cache features for semantic workflow analysis.

**Features**:
- Essential cache configuration for semantic search
- Optimized for workflow state persistence and discovery
- Includes both local file storage and cache mode
- Performance-tuned embedding model selection

**Command Line Arguments Explained**:

#### Repository Configuration

##### `--repository-path`
- **Purpose**: Specify the repository root where `.workflow-commander` folder should be located
- **Default**: Current directory
- **Example**: `--repository-path /path/to/my/project`
- **Use Case**: Essential for project-specific workflow organization

#### State File Configuration

##### `--enable-local-state-file`
- **Purpose**: Automatically saves workflow state to local files in `.workflow-commander/sessions/`
- **Benefit**: Persistent state across sessions, better debugging
- **Use Case**: Development environments requiring state inspection

##### `--local-state-file-format`
- **Options**: `MD` (markdown) or `JSON` (structured JSON)
- **Default**: `MD`
- **Purpose**: Choose the format for local state files
- **Recommendation**: Use `JSON` for programmatic access, `MD` for human readability

#### Session Management

##### `--session-retention-hours`
- **Default**: `168` (7 days)
- **Purpose**: Hours to keep completed sessions before cleanup
- **Example**: `72` keeps sessions for 3 days
- **Use Case**: Adjust based on project activity and storage constraints

##### `--disable-session-archiving`
- **Purpose**: Disable archiving of session files before cleanup
- **Default**: Sessions are archived with completion timestamp
- **Use Case**: Reduce storage usage in high-volume environments

#### Cache Configuration (Semantic Search Features)

##### `--enable-cache-mode`
- **Purpose**: Enable ChromaDB-based caching for workflow state persistence and semantic search
- **Benefit**: 
  - Cross-session workflow state persistence after MCP server restarts
  - Semantic search of historical workflow patterns
  - Enhanced workflow discovery based on past work
- **Use Case**: Projects with complex workflows requiring historical context

##### `--cache-embedding-model`
- **Purpose**: Specify the sentence transformer model for semantic embeddings
- **Default**: `all-MiniLM-L6-v2`
- **Options**:
  - `all-MiniLM-L6-v2`: Fast, lightweight model (recommended for most use cases)
  - `all-mpnet-base-v2`: Higher quality, more resource-intensive
- **Performance**: MiniLM loads ~4x faster with good semantic quality
- **Use Case**: Balance between speed and semantic search accuracy

##### `--cache-db-path`
- **Purpose**: Specify the ChromaDB database directory location
- **Default**: `.workflow-commander/cache` (relative to repository path)
- **Example**: `--cache-db-path ./custom-cache` or `/absolute/path/to/cache`
- **Use Case**: Custom cache locations for shared team workflows or storage optimization

##### `--cache-collection-name`
- **Purpose**: Name of the ChromaDB collection for storing workflow states
- **Default**: `workflow_states`
- **Example**: `--cache-collection-name my_project_workflows`
- **Use Case**: Isolate workflow data by project or team when sharing cache storage

##### `--cache-max-results`
- **Purpose**: Maximum number of results returned from semantic search queries
- **Default**: `50`
- **Range**: 1-100 (practical limit for meaningful results)
- **Use Case**: Tune based on project size and search result relevance needs

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

### Basic Project Setup
```json
{
  "mcpServers": {
    "workflow-commander": {
      "command": "uvx",
      "args": [
        "--from", 
        "git+https://github.com/AndurilCode/workflow-commander@main", 
        "dev-workflow-mcp",
        "--repository-path", ".",
        "--enable-local-state-file"
      ]
    }
  }
}
```

### Project with Semantic Search (Recommended)
```json
{
  "mcpServers": {
    "workflow-commander": {
      "command": "uvx",
      "args": [
        "--from", 
        "git+https://github.com/AndurilCode/workflow-commander@main", 
        "dev-workflow-mcp",
        "--repository-path", ".",
        "--enable-local-state-file",
        "--local-state-file-format", "JSON",
        "--enable-cache-mode",
        "--cache-embedding-model", "all-MiniLM-L6-v2"
      ]
    }
  }
}
```

### Performance-Optimized Setup (Large Projects)
```json
{
  "mcpServers": {
    "workflow-commander": {
      "command": "uvx",
      "args": [
        "--from", 
        "git+https://github.com/AndurilCode/workflow-commander@main", 
        "dev-workflow-mcp",
        "--repository-path", ".",
        "--enable-local-state-file",
        "--local-state-file-format", "JSON",
        "--session-retention-hours", "48",
        "--enable-cache-mode",
        "--cache-embedding-model", "all-MiniLM-L6-v2",
        "--cache-db-path", "/fast-storage/.workflow-cache",
        "--cache-max-results", "25"
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

#### 3. Cache Mode Issues
**Symptoms**: Semantic search not working, cache-related errors  
**Solutions**:
```bash
# Verify cache dependencies are installed
pip install sentence-transformers chromadb

# Test cache initialization manually
uvx --from git+https://github.com/AndurilCode/workflow-commander@main dev-workflow-mcp \
  --enable-cache-mode --cache-embedding-model all-MiniLM-L6-v2 --help

# Check cache directory permissions
ls -la .workflow-commander/cache/
```

#### 4. Performance Issues
**Symptoms**: Slow startup, high memory usage  
**Solutions**:
1. **Use lightweight embedding model**: `--cache-embedding-model all-MiniLM-L6-v2`
2. **Reduce cache results**: `--cache-max-results 25`
3. **Optimize cache location**: Store on fast SSD storage
4. **Adjust session retention**: `--session-retention-hours 48`

## Getting Help

If you encounter issues:

1. **Check Configuration**: Validate JSON syntax and file locations
2. **Test Manually**: Try running the server command manually  
3. **Report Issues**: Use GitHub issues for bugs and feature requests

## Next Steps

Once Cursor is configured:

2. **[Basic Workflow Examples](../../workflows/basic/)** - Explore example workflows 