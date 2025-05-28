"""State manager for workflow state file operations."""

from datetime import UTC, datetime
from pathlib import Path


class StateManager:
    """Manages workflow state file operations."""

    def __init__(self, state_file: str = "workflow_state.md"):
        """Initialize state manager with state file path."""
        self.state_file = Path(state_file)

    def file_exists(self) -> bool:
        """Check if workflow state file exists."""
        return self.state_file.exists()

    def create_initial_state(self, task_description: str) -> None:
        """Create initial workflow state file."""
        template_path = (
            Path(__file__).parent.parent / "templates" / "workflow_state_template.md"
        )

        if template_path.exists():
            with open(template_path) as f:
                template = f.read()

            # Replace template variables
            content = template.format(
                timestamp=datetime.now(UTC).strftime("%Y-%m-%d"),
                task_description=task_description,
            )
        else:
            # Fallback if template doesn't exist
            content = self._get_fallback_template(task_description)

        with open(self.state_file, "w") as f:
            f.write(content)

    def read_state(self) -> str | None:
        """Read the current workflow state file content."""
        if not self.file_exists():
            return None

        with open(self.state_file) as f:
            return f.read()

    def update_state_section(
        self, phase: str, status: str, current_item: str | None = None
    ) -> bool:
        """Update the State section of the workflow file."""
        content = self.read_state()
        if not content:
            return False

        lines = content.split("\n")
        updated_lines = []
        in_state_section = False
        state_section_updated = False

        for line in lines:
            if line.strip() == "## State":
                in_state_section = True
                updated_lines.append(line)
                # Update timestamp
                if updated_lines and updated_lines[0].startswith("_Last updated:"):
                    updated_lines[0] = (
                        f"_Last updated: {datetime.now(UTC).strftime('%Y-%m-%d')}_"
                    )
                continue

            if in_state_section and line.startswith("## "):
                # End of state section
                in_state_section = False
                state_section_updated = True

            if in_state_section:
                if line.startswith("Phase:"):
                    updated_lines.append(f"Phase: {phase}")
                elif line.startswith("Status:"):
                    updated_lines.append(f"Status: {status}")
                elif line.startswith("CurrentItem:"):
                    updated_lines.append(f"CurrentItem: {current_item or 'null'}")
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        if state_section_updated:
            with open(self.state_file, "w") as f:
                f.write("\n".join(updated_lines))
            return True

        return False

    def append_to_log(self, entry: str) -> bool:
        """Append an entry to the Log section."""
        content = self.read_state()
        if not content:
            return False

        lines = content.split("\n")
        log_section_found = False

        # Find the Log section and append
        for i, line in enumerate(lines):
            if line.strip() == "## Log":
                log_section_found = True
                # Find the end of the log section
                j = i + 1
                while j < len(lines) and not lines[j].startswith("## "):
                    j += 1

                # Insert the new entry before the next section
                timestamp = datetime.now(UTC).strftime("%H:%M:%S")
                new_entry = f"[{timestamp}] {entry}"
                lines.insert(j, new_entry)
                break

        if log_section_found:
            with open(self.state_file, "w") as f:
                f.write("\n".join(lines))
            return True

        return False

    def _get_fallback_template(self, task_description: str) -> str:
        """Get fallback template if template file doesn't exist."""
        return f"""# workflow_state.md
_Last updated: {datetime.now(UTC).strftime("%Y-%m-%d")}_

## State
Phase: INIT  
Status: READY  
CurrentItem: {task_description}  

## Plan
<!-- The AI fills this in during the BLUEPRINT phase -->

## Rules
> **Keep every major section under an explicit H2 (`##`) heading so the agent can locate them unambiguously.**

## Items
| id | description | status |
|----|-------------|--------|
| 1 | {task_description} | pending |

## Log
<!-- AI appends detailed reasoning, tool output, and errors here -->

## ArchiveLog
<!-- RULE_LOG_ROTATE_01 stores condensed summaries here -->
"""
