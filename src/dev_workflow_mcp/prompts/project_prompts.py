"""Project setup and configuration prompts."""

from fastmcp import Context, FastMCP


def register_project_prompts(mcp: FastMCP):
    """Register all project-related prompts."""

    @mcp.tool()
    def check_project_config_guidance(ctx: Context) -> str:
        """Guide agent to verify and validate project_config.md with mandatory execution steps."""
        return """🔍 CHECKING & VALIDATING PROJECT CONFIGURATION

**📋 REQUIRED ACTIONS:**
1. Check if .workflow-commander/project_config.md exists in the current directory

2. If it exists, verify it contains these sections:
   - ## Project Info
   - ## Dependencies  
   - ## Test Commands
   - ## Changelog

3. Verify that the file is readable and properly formatted

4. Check that test commands are valid for the current project

5. If missing sections or issues found, note what needs to be added/fixed

6. If file doesn't exist, create a basic template

**✅ IF PROJECT_CONFIG.MD IS READY:**
Continue with your current workflow step

**❌ IF PROJECT_CONFIG.MD NEEDS SETUP:**
Call: `create_project_config_guidance`

**❌ IF CONFIG NEEDS FIXES:**
Call appropriate prompts to fix missing sections

🎯 **Project configuration verification and validation complete!**
"""

    @mcp.tool()
    def create_project_config_guidance(ctx: Context) -> str:
        """Guide agent to create a basic project_config.md template with mandatory execution steps."""
        return """📄 CREATING PROJECT CONFIG FILE

**📋 REQUIRED ACTIONS:**
1. Create .workflow-commander/project_config.md with this basic structure:

```markdown
# Project Configuration

## Project Info
<!-- Describe the project name, version, and description -->

## Dependencies
<!-- List key dependencies and their versions -->

## Test Commands
<!-- Commands to run tests and linters -->
```bash
# Example commands:
# npm test
# python -m pytest
# ruff check .
```

## Build Commands
<!-- Commands to build/compile the project -->

## Changelog
<!-- Project changelog entries -->
```

2. Fill in the sections based on the current project structure

3. Save the file in the .workflow-commander directory

**✅ WHEN PROJECT_CONFIG.MD IS CREATED:**
Return to your previous workflow step

🎯 **Project configuration file created successfully!**
""" 