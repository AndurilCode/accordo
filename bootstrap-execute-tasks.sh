#!/bin/bash

# Bootstrap Execute-Tasks Configuration Script
# Deploys dynamic workflow system guidelines to multiple AI assistants
# Usage: ./bootstrap-execute-tasks.sh [cursor|copilot|claude|all]

set -euo pipefail

# Constants
readonly CURSOR_TARGET=".cursor/rules/execute-tasks.mdc"
readonly COPILOT_TARGET=".github/copilot-instructions.md"
readonly CLAUDE_TARGET="./CLAUDE.md"

# Embedded content for Cursor (with YAML frontmatter)
read -r -d '' CURSOR_CONTENT << 'EOF' || true
---
description: 
globs: 
alwaysApply: true
---
## Task Execution Guidelines

### When to Use Workflow Tools
- **Simple tasks**: Handle directly without tools (e.g., basic calculations, straightforward code edits, simple explanations)
- **Complex tasks**: Always use `workflow_guidance` for multi-step problems, tasks requiring coordination across files, or when explicit planning would help

### Dynamic Workflow System
The workflow system is now fully dynamic and schema-driven:

1. **Workflow Discovery**: The system automatically discovers available workflows from `.workflow-commander/workflows/` directory
2. **Agent Choice**: You choose which workflow to use based on the task requirements - no automated scoring
3. **Schema-Driven Navigation**: Workflow transitions are determined by the YAML schema (`next_allowed_nodes` and `next_allowed_workflows`)
4. **Context Parameters**: Control workflow execution using context like `context="choose: node_name"` or `context="workflow: Workflow Name"`

### Workflow Execution Process
1. **Initialize**: When using `workflow_guidance`, the system will present available workflows for your selection
2. **Choose Workflow**: Select the most appropriate workflow based on task description and workflow goals
3. **Follow Schema**: Navigate through workflow nodes using the transitions defined in the YAML schema
4. **Agent Decisions**: Make routing decisions based on schema-presented options rather than hardcoded logic
5. **Stay Synchronized**: The workflow state file tracks your progress through the chosen workflow

### Available Tools
- `workflow_guidance`: Main tool for dynamic workflow execution with agent-driven workflow selection
- `workflow_state`: Tool for checking and updating workflow state
- Context7: Use for up-to-date documentation about technologies
- GitHub: Read files from other repositories when needed

### Key Principles
- **No hardcoded routing**: All workflow behavior is determined by YAML schema definitions
- **Agent-driven selection**: You choose workflows and transitions based on schema-presented options
- **Schema as source of truth**: Workflow definitions in YAML files drive all behavior
- **Legacy fallback preserved**: System falls back to legacy workflows when no YAML workflows are available
- If uncertain whether a task is "simple," err on the side of using the workflow tool
EOF

# Core content for other assistants (without YAML frontmatter)
read -r -d '' CORE_CONTENT << 'EOF' || true
## Task Execution Guidelines

### When to Use Workflow Tools
- **Simple tasks**: Handle directly without tools (e.g., basic calculations, straightforward code edits, simple explanations)
- **Complex tasks**: Always use `workflow_guidance` for multi-step problems, tasks requiring coordination across files, or when explicit planning would help

### Dynamic Workflow System
The workflow system is now fully dynamic and schema-driven:

1. **Workflow Discovery**: The system automatically discovers available workflows from `.workflow-commander/workflows/` directory
2. **Agent Choice**: You choose which workflow to use based on the task requirements - no automated scoring
3. **Schema-Driven Navigation**: Workflow transitions are determined by the YAML schema (`next_allowed_nodes` and `next_allowed_workflows`)
4. **Context Parameters**: Control workflow execution using context like `context="choose: node_name"` or `context="workflow: Workflow Name"`

### Workflow Execution Process
1. **Initialize**: When using `workflow_guidance`, the system will present available workflows for your selection
2. **Choose Workflow**: Select the most appropriate workflow based on task description and workflow goals
3. **Follow Schema**: Navigate through workflow nodes using the transitions defined in the YAML schema
4. **Agent Decisions**: Make routing decisions based on schema-presented options rather than hardcoded logic
5. **Stay Synchronized**: The workflow state file tracks your progress through the chosen workflow

### Available Tools
- `workflow_guidance`: Main tool for dynamic workflow execution with agent-driven workflow selection
- `workflow_state`: Tool for checking and updating workflow state
- Context7: Use for up-to-date documentation about technologies
- GitHub: Read files from other repositories when needed

### Key Principles
- **No hardcoded routing**: All workflow behavior is determined by YAML schema definitions
- **Agent-driven selection**: You choose workflows and transitions based on schema-presented options
- **Schema as source of truth**: Workflow definitions in YAML files drive all behavior
- **Legacy fallback preserved**: System falls back to legacy workflows when no YAML workflows are available
- If uncertain whether a task is "simple," err on the side of using the workflow tool
EOF

# Color output for better UX
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show usage information
show_help() {
    cat << EOF
Bootstrap Execute-Tasks Configuration Script

USAGE:
    $0 [OPTIONS] [ASSISTANT_TYPE]

ASSISTANT_TYPES:
    cursor      Deploy to Cursor (.cursor/rules/execute-tasks.mdc)
    copilot     Deploy to GitHub Copilot (.github/copilot-instructions.md)
    claude      Deploy to Claude (./CLAUDE.md)
    all         Deploy to all assistants (default)

OPTIONS:
    --help, -h  Show this help message

EXAMPLES:
    $0                    # Deploy to all assistants
    $0 all                # Deploy to all assistants
    $0 cursor             # Deploy only to Cursor
    $0 copilot claude     # Deploy to Copilot and Claude

DESCRIPTION:
    This script deploys dynamic workflow system guidelines (embedded in the script)
    to the appropriate configuration files for different AI code assistants.
    It checks if content already exists and only appends if the content is missing.
    
    The guidelines describe the new schema-driven workflow system where agents
    discover available workflows and make routing decisions based on YAML schemas.
    
    Cursor receives the full content including YAML frontmatter.
    GitHub Copilot and Claude receive only the core guidelines content.
EOF
}

# Check if content already exists in target file
check_content_exists() {
    local target_file="$1"
    
    if [[ ! -f "$target_file" ]]; then
        return 1  # File doesn't exist, content definitely doesn't exist
    fi
    
    # Check for key phrases that indicate execute-tasks content exists
    if grep -q "Task Execution Guidelines" "$target_file" && \
       grep -q "When to Use Workflow Tools" "$target_file"; then
        return 0  # Content exists
    else
        return 1  # Content doesn't exist
    fi
}

# Ensure directory exists for target file
ensure_directory() {
    local target_file="$1"
    local target_dir
    target_dir=$(dirname "$target_file")
    
    if [[ ! -d "$target_dir" ]]; then
        log_info "Creating directory: $target_dir"
        mkdir -p "$target_dir"
        if [[ $? -eq 0 ]]; then
            log_success "Directory created: $target_dir"
        else
            log_error "Failed to create directory: $target_dir"
            return 1
        fi
    fi
    
    return 0
}

# Deploy content to Cursor
deploy_cursor() {
    log_info "Deploying to Cursor..."
    
    if ! ensure_directory "$CURSOR_TARGET"; then
        return 1
    fi
    
    if check_content_exists "$CURSOR_TARGET"; then
        log_warning "Execute-tasks content already exists in $CURSOR_TARGET, skipping"
        return 0
    fi
    
    # Check if file exists to determine whether to append or create
    if [[ -f "$CURSOR_TARGET" ]]; then
        # File exists, append the content with separator
        {
            echo ""
            echo "# Execute-Tasks Guidelines"
            echo ""
            echo "$CURSOR_CONTENT"
        } >> "$CURSOR_TARGET"
        log_success "Execute-tasks content appended to existing $CURSOR_TARGET"
    else
        # File doesn't exist, create it with the content
        echo "$CURSOR_CONTENT" > "$CURSOR_TARGET"
        log_success "Execute-tasks content deployed to new $CURSOR_TARGET"
    fi
}

# Deploy content to GitHub Copilot
deploy_copilot() {
    log_info "Deploying to GitHub Copilot..."
    
    if ! ensure_directory "$COPILOT_TARGET"; then
        return 1
    fi
    
    if check_content_exists "$COPILOT_TARGET"; then
        log_warning "Execute-tasks content already exists in $COPILOT_TARGET, skipping"
        return 0
    fi
    
    # Check if file exists to determine whether to append or create
    if [[ -f "$COPILOT_TARGET" ]]; then
        # File exists, append the content with separator
        {
            echo ""
            echo "# Execute-Tasks Guidelines"
            echo ""
            echo "$CORE_CONTENT"
        } >> "$COPILOT_TARGET"
        log_success "Execute-tasks content appended to existing $COPILOT_TARGET"
    else
        # File doesn't exist, create it with header and core content
        {
            echo "# GitHub Copilot Instructions"
            echo ""
            echo "$CORE_CONTENT"
        } > "$COPILOT_TARGET"
        log_success "Execute-tasks content deployed to new $COPILOT_TARGET"
    fi
}

# Deploy content to Claude
deploy_claude() {
    log_info "Deploying to Claude..."
    
    if ! ensure_directory "$CLAUDE_TARGET"; then
        return 1
    fi
    
    if check_content_exists "$CLAUDE_TARGET"; then
        log_warning "Execute-tasks content already exists in $CLAUDE_TARGET, skipping"
        return 0
    fi
    
    # Check if file exists to determine whether to append or create
    if [[ -f "$CLAUDE_TARGET" ]]; then
        # File exists, append the content with separator
        {
            echo ""
            echo "# Execute-Tasks Guidelines"
            echo ""
            echo "$CORE_CONTENT"
        } >> "$CLAUDE_TARGET"
        log_success "Execute-tasks content appended to existing $CLAUDE_TARGET"
    else
        # File doesn't exist, create it with header and core content
        {
            echo "# Claude AI Instructions"
            echo ""
            echo "$CORE_CONTENT"
        } > "$CLAUDE_TARGET"
        log_success "Execute-tasks content deployed to new $CLAUDE_TARGET"
    fi
}

# Main execution logic
main() {
    local assistants=()
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            cursor|copilot|claude|all)
                assistants+=("$1")
                ;;
            *)
                log_error "Unknown argument: $1"
                echo ""
                show_help
                exit 1
                ;;
        esac
        shift
    done
    
    # Default to 'all' if no assistants specified
    if [[ ${#assistants[@]} -eq 0 ]]; then
        assistants=("all")
    fi
    
    # Track deployment results
    local success_count=0
    local total_count=0
    
    # Process each assistant type
    for assistant in "${assistants[@]}"; do
        case $assistant in
            cursor)
                total_count=$((total_count + 1))
                if deploy_cursor; then
                    success_count=$((success_count + 1))
                fi
                ;;
            copilot)
                total_count=$((total_count + 1))
                if deploy_copilot; then
                    success_count=$((success_count + 1))
                fi
                ;;
            claude)
                total_count=$((total_count + 1))
                if deploy_claude; then
                    success_count=$((success_count + 1))
                fi
                ;;
            all)
                total_count=$((total_count + 3))
                if deploy_cursor; then success_count=$((success_count + 1)); fi
                if deploy_copilot; then success_count=$((success_count + 1)); fi
                if deploy_claude; then success_count=$((success_count + 1)); fi
                ;;
        esac
    done
    
    # Summary
    echo ""
    log_info "Deployment Summary:"
    log_info "- Successful deployments: $success_count"
    log_info "- Total attempted: $total_count"
    
    if [[ $success_count -eq $total_count ]]; then
        log_success "All deployments completed successfully!"
        exit 0
    else
        log_warning "Some deployments encountered issues. Check logs above."
        exit 1
    fi
}

# Execute main function with all arguments
main "$@" 