"""Project setup and configuration prompts."""

from fastmcp import Context, FastMCP


def register_project_prompts(mcp: FastMCP):
    """Register all project-related prompts."""

    @mcp.tool()
    def check_project_config_guidance(ctx: Context) -> str:
        """Guide agent to verify project_config.md exists with mandatory execution steps."""
        return """🔍 CHECKING PROJECT CONFIGURATION

**📋 REQUIRED ACTIONS:**
1. Check if project_config.md exists in the current directory

2. If it exists, verify it contains these sections:
   - ## Project Info
   - ## Dependencies  
   - ## Test Commands
   - ## Changelog

3. If missing sections, note what needs to be added

4. If file doesn't exist, create a basic template

**✅ IF PROJECT_CONFIG.MD IS READY:**
Continue with your current workflow step

**❌ IF PROJECT_CONFIG.MD NEEDS SETUP:**
Call: `create_project_config_guidance`

🎯 **Project configuration verification complete!**
"""

    @mcp.tool()
    def create_project_config_guidance(ctx: Context) -> str:
        """Guide agent to create a basic project_config.md template with mandatory execution steps."""
        return """📄 CREATING PROJECT CONFIG FILE

**📋 REQUIRED ACTIONS:**
1. Create project_config.md with this basic structure:

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

3. Save the file

**✅ WHEN PROJECT_CONFIG.MD IS CREATED:**
Return to your previous workflow step

🎯 **Project configuration file created successfully!**
"""

    @mcp.tool()
    def validate_project_config_guidance(ctx: Context) -> str:
        """Guide agent to validate project configuration file with mandatory execution steps."""
        return """✅ VALIDATING PROJECT CONFIGURATION

**📋 REQUIRED ACTIONS:**
1. Check project_config.md exists and has required sections:
   - ## Project Info
   - ## Dependencies
   - ## Test Commands
   - ## Changelog

2. Verify that the file is readable and properly formatted

3. Check that test commands are valid for the current project

4. Report any missing files or sections

**✅ IF PROJECT CONFIG IS VALID:**
Continue with your current workflow step

**❌ IF CONFIG NEEDS FIXES:**
Call appropriate prompts to fix missing sections

🎯 **Project configuration validation complete!**
""" 