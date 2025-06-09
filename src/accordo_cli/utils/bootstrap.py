"""Bootstrap utilities for deploying workflow guidelines to AI assistants."""

from pathlib import Path

import typer


class BootstrapManager:
    """Manages deployment of workflow guidelines to AI assistant configuration files."""

    # Target file paths for each assistant
    CURSOR_TARGET = ".cursor/rules/execute-tasks.mdc"
    COPILOT_TARGET = ".github/copilot-instructions.md"
    CLAUDE_TARGET = "CLAUDE.md"

    # Content with YAML frontmatter for Cursor
    CURSOR_CONTENT = """---
description: 
globs: 
alwaysApply: true
---
## Task Execution Guidelines

### 🚨 MANDATORY WORKFLOW COMPLIANCE 🚨
**Before starting ANY task, evaluate it using these criteria:**

#### Use Workflow Tools When:
- Task involves multiple steps or phases
- Task requires coordination across multiple files
- Task involves creating, modifying, or analyzing code structures
- Task requires planning, analysis, or systematic approach
- Task involves debugging, testing, or validation
- Task creates new features, components, or systems
- **When in doubt, ALWAYS use workflows**

#### Only Skip Workflows For:
- Single mathematical calculations
- One-line explanations or definitions
- Direct copy/paste operations
- Immediate answers to factual questions

### 🔄 MANDATORY WORKFLOW ENTRY PROCESS
**⚠️ NON-NEGOTIABLE:** For ALL qualifying tasks, you MUST follow this exact sequence:

#### STEP 1: DISCOVER (REQUIRED FIRST STEP)
```
workflow_discovery(task_description="[Exact user request]")
```
**Purpose:** View all available YAML workflows and their capabilities
**Result:** List of workflows with descriptions and suitability assessment

#### STEP 2: CHOOSE AND START (REQUIRED SECOND STEP)
```
workflow_guidance(action="start", context="workflow: [Selected Workflow Name]")
```
**Purpose:** Initialize the selected workflow session
**Result:** Workflow begins with first phase instructions

#### STEP 3: FOLLOW SCHEMA (ONGOING) 
```
workflow_guidance(action="next", context='{"choose": "[option]", "criteria_evidence": {"criterion": "detailed evidence"}}')
```
**Purpose:** Navigate through workflow phases using YAML-defined transitions with detailed evidence
**Result:** Structured progression through the complete workflow with work tracking

### 🎯 Decision Framework
**Use this exact decision tree for EVERY user request:**

1. **Is this a single, immediate action?** 
   - YES: Proceed directly (rare cases only)
   - NO: Go to Step 2

2. **Does the task involve ANY of these?**
   - Multiple files or components? → USE WORKFLOW
   - Planning or analysis phase? → USE WORKFLOW  
   - Code creation or modification? → USE WORKFLOW
   - Testing or validation? → USE WORKFLOW
   - Debugging or troubleshooting? → USE WORKFLOW
   - Documentation or explanation? → USE WORKFLOW

3. **Still uncertain?** → USE WORKFLOW (default choice)

### 🏗️ Dynamic Workflow System Architecture
The workflow system operates on these principles:

1. **Schema-Driven Navigation**: All workflow behavior defined by YAML schemas
2. **Agent-Driven Selection**: You choose workflows based on task requirements  
3. **Dynamic Discovery**: System discovers available workflows automatically
4. **Context Parameters**: Control execution with JSON format: `context='{"choose": "node_name", "criteria_evidence": {...}}'`
5. **No Hardcoded Routes**: All transitions defined in YAML `next_allowed_nodes`

### 📋 Available Workflow Tools
- `workflow_discovery` - **START HERE ALWAYS** - Discover available YAML workflows
- `workflow_guidance` - Main execution engine for dynamic workflows
- `workflow_state` - Check and update current workflow state
- `workflow_creation_guidance` - Create custom workflows when existing ones don't fit

### 📚 Supporting Tools
- Context7: Real-time documentation lookup
- GitHub: Repository file access
- Standard coding tools: file operations, terminal, search, etc.

### ⚡ Enforcement Rules
1. **NEVER skip workflow discovery** for multi-step tasks
2. **ALWAYS start with `workflow_discovery()`** before other workflow tools
3. **NEVER use legacy approaches** when workflow tools are available
4. **ALWAYS follow YAML schema transitions** rather than making ad-hoc decisions
5. **WHEN UNCERTAIN → USE WORKFLOWS** (fail-safe principle)

### 🆔 SESSION ID MANAGEMENT (NEW)
**All workflows auto-generate unique session IDs for multi-session support:**

#### Session ID Usage Patterns:
```
# Start workflow - returns session_id in response
workflow_discovery(task_description="Your task")
workflow_guidance(action="start", context="workflow: Selected Workflow")

# Continue with session_id for targeted operations
workflow_guidance(session_id="abc-123", action="next", context='{"choose": "option"}')
workflow_state(session_id="abc-123", operation="get")
```

#### Multi-Session Benefits:
- **Parallel Workflows**: Run multiple workflows simultaneously
- **Session Continuity**: Resume specific workflows after interruption  
- **Session Isolation**: Keep different tasks completely separate
- **Session Tracking**: Monitor progress of individual workflows

#### Best Practices:
- **ALWAYS save session_id** from workflow start responses
- **ALWAYS include session_id** in subsequent workflow calls
- **Use session_id** when managing multiple concurrent workflows
- **Fallback handling**: System supports backward compatibility without session_id"""

    # Core content without YAML frontmatter for other assistants
    CORE_CONTENT = """## Task Execution Guidelines

### 🚨 MANDATORY WORKFLOW COMPLIANCE 🚨
**Before starting ANY task, evaluate it using these criteria:**

#### Use Workflow Tools When:
- Task involves multiple steps or phases
- Task requires coordination across multiple files
- Task involves creating, modifying, or analyzing code structures
- Task requires planning, analysis, or systematic approach
- Task involves debugging, testing, or validation
- Task creates new features, components, or systems
- **When in doubt, ALWAYS use workflows**

#### Only Skip Workflows For:
- Single mathematical calculations
- One-line explanations or definitions
- Direct copy/paste operations
- Immediate answers to factual questions

### 🔄 MANDATORY WORKFLOW ENTRY PROCESS
**⚠️ NON-NEGOTIABLE:** For ALL qualifying tasks, you MUST follow this exact sequence:

#### STEP 1: DISCOVER (REQUIRED FIRST STEP)
```
workflow_discovery(task_description="[Exact user request]")
```
**Purpose:** View all available YAML workflows and their capabilities
**Result:** List of workflows with descriptions and suitability assessment

#### STEP 2: CHOOSE AND START (REQUIRED SECOND STEP)
```
workflow_guidance(action="start", context="workflow: [Selected Workflow Name]")
```
**Purpose:** Initialize the selected workflow session
**Result:** Workflow begins with first phase instructions

#### STEP 3: FOLLOW SCHEMA (ONGOING) 
```
workflow_guidance(action="next", context='{"choose": "[option]", "criteria_evidence": {"criterion": "detailed evidence"}}')
```
**Purpose:** Navigate through workflow phases using YAML-defined transitions with detailed evidence
**Result:** Structured progression through the complete workflow with work tracking

### 🎯 Decision Framework
**Use this exact decision tree for EVERY user request:**

1. **Is this a single, immediate action?** 
   - YES: Proceed directly (rare cases only)
   - NO: Go to Step 2

2. **Does the task involve ANY of these?**
   - Multiple files or components? → USE WORKFLOW
   - Planning or analysis phase? → USE WORKFLOW  
   - Code creation or modification? → USE WORKFLOW
   - Testing or validation? → USE WORKFLOW
   - Debugging or troubleshooting? → USE WORKFLOW
   - Documentation or explanation? → USE WORKFLOW

3. **Still uncertain?** → USE WORKFLOW (default choice)

### 🏗️ Dynamic Workflow System Architecture
The workflow system operates on these principles:

1. **Schema-Driven Navigation**: All workflow behavior defined by YAML schemas
2. **Agent-Driven Selection**: You choose workflows based on task requirements  
3. **Dynamic Discovery**: System discovers available workflows automatically
4. **Context Parameters**: Control execution with JSON format: `context='{"choose": "node_name", "criteria_evidence": {...}}'`
5. **No Hardcoded Routes**: All transitions defined in YAML `next_allowed_nodes`

### 📋 Available Workflow Tools
- `workflow_discovery` - **START HERE ALWAYS** - Discover available YAML workflows
- `workflow_guidance` - Main execution engine for dynamic workflows
- `workflow_state` - Check and update current workflow state
- `workflow_creation_guidance` - Create custom workflows when existing ones don't fit

### 📚 Supporting Tools
- Context7: Real-time documentation lookup
- GitHub: Repository file access
- Standard coding tools: file operations, terminal, search, etc.

### ⚡ Enforcement Rules
1. **NEVER skip workflow discovery** for multi-step tasks
2. **ALWAYS start with `workflow_discovery()`** before other workflow tools
3. **NEVER use legacy approaches** when workflow tools are available
4. **ALWAYS follow YAML schema transitions** rather than making ad-hoc decisions
5. **WHEN UNCERTAIN → USE WORKFLOWS** (fail-safe principle)

### 🆔 SESSION ID MANAGEMENT (NEW)
**All workflows auto-generate unique session IDs for multi-session support:**

#### Session ID Usage Patterns:
```
# Start workflow - returns session_id in response
workflow_discovery(task_description="Your task")
workflow_guidance(action="start", context="workflow: Selected Workflow")

# Continue with session_id for targeted operations
workflow_guidance(session_id="abc-123", action="next", context='{"choose": "option"}')
workflow_state(session_id="abc-123", operation="get")
```

#### Multi-Session Benefits:
- **Parallel Workflows**: Run multiple workflows simultaneously
- **Session Continuity**: Resume specific workflows after interruption  
- **Session Isolation**: Keep different tasks completely separate
- **Session Tracking**: Monitor progress of individual workflows

#### Best Practices:
- **ALWAYS save session_id** from workflow start responses
- **ALWAYS include session_id** in subsequent workflow calls
- **Use session_id** when managing multiple concurrent workflows
- **Fallback handling**: System supports backward compatibility without session_id"""

    def _log_info(self, message: str) -> None:
        """Log info message with colored output."""
        typer.secho(f"[INFO] {message}", fg=typer.colors.BLUE)

    def _log_success(self, message: str) -> None:
        """Log success message with colored output."""
        typer.secho(f"[SUCCESS] {message}", fg=typer.colors.GREEN)

    def _log_warning(self, message: str) -> None:
        """Log warning message with colored output."""
        typer.secho(f"[WARNING] {message}", fg=typer.colors.YELLOW)

    def _log_error(self, message: str) -> None:
        """Log error message with colored output."""
        typer.secho(f"[ERROR] {message}", fg=typer.colors.RED)

    def _check_content_exists(self, target_file: Path) -> bool:
        """Check if workflow guidelines content already exists in target file."""
        if not target_file.exists():
            return False

        try:
            content = target_file.read_text(encoding="utf-8")
            # Check for key phrases that indicate execute-tasks content exists
            return (
                "Task Execution Guidelines" in content
                and "MANDATORY WORKFLOW COMPLIANCE" in content
            )
        except Exception:
            return False

    def _ensure_directory(self, target_file: Path) -> bool:
        """Ensure directory exists for target file."""
        target_dir = target_file.parent

        if not target_dir.exists():
            self._log_info(f"Creating directory: {target_dir}")
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                self._log_success(f"Directory created: {target_dir}")
                return True
            except Exception as e:
                self._log_error(f"Failed to create directory: {target_dir} - {e}")
                return False

        return True

    def deploy_to_cursor(self, force: bool = False) -> bool:
        """Deploy content to Cursor."""
        self._log_info("Deploying to Cursor...")

        target_file = Path(self.CURSOR_TARGET)

        if not self._ensure_directory(target_file):
            return False

        if not force and self._check_content_exists(target_file):
            self._log_warning(
                f"Execute-tasks content already exists in {target_file}, skipping"
            )
            return True

        try:
            if target_file.exists() and not force:
                # File exists, append the content with separator
                content_to_add = (
                    f"\n\n# Execute-Tasks Guidelines\n\n{self.CURSOR_CONTENT}"
                )
                with target_file.open("a", encoding="utf-8") as f:
                    f.write(content_to_add)
                self._log_success(
                    f"Execute-tasks content appended to existing {target_file}"
                )
            else:
                # File doesn't exist or force mode, create/overwrite with the content
                target_file.write_text(self.CURSOR_CONTENT, encoding="utf-8")
                action = "overwritten" if force and target_file.exists() else "created"
                self._log_success(
                    f"Execute-tasks content deployed to {action} {target_file}"
                )

            return True

        except Exception as e:
            self._log_error(f"Failed to deploy to Cursor: {e}")
            return False

    def deploy_to_copilot(self, force: bool = False) -> bool:
        """Deploy content to GitHub Copilot."""
        self._log_info("Deploying to GitHub Copilot...")

        target_file = Path(self.COPILOT_TARGET)

        if not self._ensure_directory(target_file):
            return False

        if not force and self._check_content_exists(target_file):
            self._log_warning(
                f"Execute-tasks content already exists in {target_file}, skipping"
            )
            return True

        try:
            if target_file.exists() and not force:
                # File exists, append the content with separator
                content_to_add = (
                    f"\n\n# Execute-Tasks Guidelines\n\n{self.CORE_CONTENT}"
                )
                with target_file.open("a", encoding="utf-8") as f:
                    f.write(content_to_add)
                self._log_success(
                    f"Execute-tasks content appended to existing {target_file}"
                )
            else:
                # File doesn't exist or force mode, create/overwrite
                if force or not target_file.exists():
                    header = "# GitHub Copilot Instructions\n\n"
                    content = f"{header}{self.CORE_CONTENT}"
                    target_file.write_text(content, encoding="utf-8")
                    action = (
                        "overwritten" if force and target_file.exists() else "created"
                    )
                    self._log_success(
                        f"Execute-tasks content deployed to {action} {target_file}"
                    )

            return True

        except Exception as e:
            self._log_error(f"Failed to deploy to GitHub Copilot: {e}")
            return False

    def deploy_to_claude(self, force: bool = False) -> bool:
        """Deploy content to Claude."""
        self._log_info("Deploying to Claude...")

        target_file = Path(self.CLAUDE_TARGET)

        if not self._ensure_directory(target_file):
            return False

        if not force and self._check_content_exists(target_file):
            self._log_warning(
                f"Execute-tasks content already exists in {target_file}, skipping"
            )
            return True

        try:
            if target_file.exists() and not force:
                # File exists, append the content with separator
                content_to_add = (
                    f"\n\n# Execute-Tasks Guidelines\n\n{self.CORE_CONTENT}"
                )
                with target_file.open("a", encoding="utf-8") as f:
                    f.write(content_to_add)
                self._log_success(
                    f"Execute-tasks content appended to existing {target_file}"
                )
            else:
                # File doesn't exist or force mode, create/overwrite
                if force or not target_file.exists():
                    header = "# Claude AI Instructions\n\n"
                    content = f"{header}{self.CORE_CONTENT}"
                    target_file.write_text(content, encoding="utf-8")
                    action = (
                        "overwritten" if force and target_file.exists() else "created"
                    )
                    self._log_success(
                        f"Execute-tasks content deployed to {action} {target_file}"
                    )

            return True

        except Exception as e:
            self._log_error(f"Failed to deploy to Claude: {e}")
            return False

    def deploy_to_assistant(self, assistant: str, force: bool = False) -> bool:
        """Deploy content to a specific assistant."""
        if assistant == "cursor":
            return self.deploy_to_cursor(force)
        elif assistant == "copilot":
            return self.deploy_to_copilot(force)
        elif assistant == "claude":
            return self.deploy_to_claude(force)
        else:
            self._log_error(f"Unknown assistant type: {assistant}")
            return False

    def deploy_all(self, force: bool = False) -> dict[str, bool]:
        """Deploy content to all assistants."""
        results = {}
        results["cursor"] = self.deploy_to_cursor(force)
        results["copilot"] = self.deploy_to_copilot(force)
        results["claude"] = self.deploy_to_claude(force)
        return results
