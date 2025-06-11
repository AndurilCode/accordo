"""Workflow state models and enums."""

import json
from datetime import UTC, datetime
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator, model_validator

from .yaml_workflow import WorkflowDefinition


class WorkflowItem(BaseModel):
    """Individual workflow item."""

    id: int
    description: str
    status: str = "pending"


class DynamicWorkflowState(BaseModel):
    """Dynamic workflow state that can work with any YAML-defined workflow."""

    # Session identification
    session_id: str = Field(description="Unique session identifier (UUID)")
    client_id: str = Field(default="default", description="Client session identifier")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Session creation time"
    )

    # Workflow definition reference
    workflow_name: str = Field(description="Name of the workflow being executed")
    workflow_file: str | None = Field(
        default=None, description="Path to workflow YAML file"
    )

    # Session file management
    session_filename: str | None = Field(
        default=None,
        description="Unique filename for this session's persistent storage",
    )

    # Dynamic workflow state
    last_updated: datetime = Field(default_factory=datetime.now)
    current_node: str = Field(description="Current node in the workflow")
    status: str = Field(description="Current status (node-specific or global)")
    execution_context: dict[str, Any] = Field(
        default_factory=dict, description="Runtime context and variables"
    )

    # Workflow inputs and outputs
    inputs: dict[str, Any] = Field(
        default_factory=dict, description="Workflow input values"
    )
    node_outputs: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Outputs from completed nodes"
    )

    # Execution tracking
    current_item: str | None = None
    plan: str = Field(
        default="",
        description="DEPRECATED: Plan field is unused in YAML workflows. "
        "Workflow structure is defined by YAML definition instead.",
    )
    items: list[WorkflowItem] = Field(default_factory=list)
    log: list[str] = Field(default_factory=list)
    archive_log: list[str] = Field(default_factory=list)

    # Node execution history
    node_history: list[str] = Field(
        default_factory=list, description="History of visited nodes"
    )

    @model_validator(mode="before")
    @classmethod
    def ensure_session_id(cls, data: Any) -> Any:
        """Ensure session_id is present, auto-generating if needed."""
        if isinstance(data, dict) and (
            "session_id" not in data or not data["session_id"]
        ):
            # Lazy import to avoid circular dependency
            from ..utils.session_id_utils import generate_session_id

            data["session_id"] = generate_session_id()
        return data

    @field_validator("node_outputs")
    @classmethod
    def validate_node_outputs(cls, v):
        """Validate node_outputs structure and provide guidance."""
        if not isinstance(v, dict):
            return {}

        # Validate each node's outputs
        validated_outputs = {}
        for node_name, outputs in v.items():
            if not isinstance(outputs, dict):
                continue

            # If outputs exist, ensure they have the expected structure
            if outputs and "completed_criteria" not in outputs:
                # Could add logging here, but keeping validation pure
                pass

            validated_outputs[node_name] = outputs

        return validated_outputs

    def add_log_entry(self, entry: str) -> None:
        """Add entry to log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005
        formatted_entry = f"[{timestamp}] {entry}"
        self.log.append(formatted_entry)

        # Check if log rotation is needed (>5000 chars total)
        total_chars = sum(len(log_entry) for log_entry in self.log)
        if total_chars > 5000:
            self.rotate_log()

    def rotate_log(self) -> None:
        """Rotate log to archive when it gets too long."""
        # Move current log to archive
        if self.archive_log:
            self.archive_log.append("--- LOG ROTATION ---")
        self.archive_log.extend(self.log)
        self.log.clear()

    def get_next_pending_item(self) -> WorkflowItem | None:
        """Get the next pending item."""
        for item in self.items:
            if item.status == "pending":
                return item
        return None

    def mark_item_completed(self, item_id: int) -> bool:
        """Mark an item as completed."""
        for item in self.items:
            if item.id == item_id:
                item.status = "completed"
                return True
        return False

    def transition_to_node(
        self, node_name: str, workflow_def: WorkflowDefinition
    ) -> bool:
        """Transition to a new node in the workflow.

        Args:
            node_name: The name of the node to transition to
            workflow_def: The workflow definition to validate the transition

        Returns:
            bool: True if transition is valid and successful
        """
        # Validate that the transition is allowed
        if not workflow_def.workflow.validate_transition(self.current_node, node_name):
            return False

        # Record the transition
        self.node_history.append(self.current_node)
        self.current_node = node_name
        self.last_updated = datetime.now(UTC)

        # Log the transition
        self.add_log_entry(
            f"🔄 Transitioned from {self.node_history[-1]} to {node_name}"
        )

        return True

    def complete_current_node(self, outputs: dict[str, Any] | None = None) -> None:
        """Mark the current node as completed with optional outputs.

        Args:
            outputs: Optional outputs from the completed node. Should include
                    'completed_criteria' dict with evidence for acceptance criteria
                    and 'goal_achieved' boolean indicating goal completion.
        """
        if not self.current_node:
            # Edge case: No current node to complete
            self.add_log_entry(
                "⚠️ Warning: Attempted to complete node but no current_node set"
            )
            return

        if outputs:
            # Validate outputs structure for better debugging
            if not isinstance(outputs, dict):
                self.add_log_entry(
                    f"⚠️ Warning: Node outputs for {self.current_node} are not a dict, converting"
                )
                outputs = {"raw_output": str(outputs)}

            self.node_outputs[self.current_node] = outputs

            # Log detailed completion if criteria evidence provided
            criteria_evidence = outputs.get("completed_criteria", {})
            if criteria_evidence:
                self.add_log_entry(
                    f"✅ Completed node: {self.current_node} with {len(criteria_evidence)} criteria satisfied"
                )
                # Show detailed evidence for each criterion satisfied
                for criterion, evidence in criteria_evidence.items():
                    # Always show full evidence without truncation per user requirement
                    self.add_log_entry(f"   📋 Criterion satisfied: {criterion}")
                    self.add_log_entry(f"      Evidence: {evidence}")
            else:
                self.add_log_entry(
                    f"✅ Completed node: {self.current_node} (no detailed criteria recorded)"
                )
        else:
            # Store empty outputs to track completion - this was the bug!
            # Before the fix, this case would result in empty node_outputs
            self.node_outputs[self.current_node] = {
                "completion_status": "completed_without_outputs",
                "completion_timestamp": datetime.now(UTC).isoformat(),
            }
            self.add_log_entry(
                f"✅ Completed node: {self.current_node} (no outputs provided, basic tracking added)"
            )

        # Update last_updated timestamp
        self.last_updated = datetime.now(UTC)

    def get_available_next_nodes(self, workflow_def: WorkflowDefinition) -> list[str]:
        """Get the list of nodes that can be transitioned to from current node.

        Args:
            workflow_def: The workflow definition

        Returns:
            list[str]: List of available next node names
        """
        current_node = workflow_def.workflow.get_node(self.current_node)
        if not current_node:
            return []
        return current_node.next_allowed_nodes

    def has_node_completion_evidence(self, node_name: str) -> bool:
        """Check if a node has proper completion evidence.

        Args:
            node_name: Name of the node to check

        Returns:
            bool: True if node has completion evidence
        """
        if node_name not in self.node_outputs:
            return False

        outputs = self.node_outputs[node_name]
        return isinstance(outputs, dict) and bool(outputs)

    def get_node_completion_summary(self, node_name: str) -> str:
        """Get a summary of node completion status.

        Args:
            node_name: Name of the node to summarize

        Returns:
            str: Human-readable completion summary
        """
        if not self.has_node_completion_evidence(node_name):
            return f"Node '{node_name}' completed without detailed evidence"

        outputs = self.node_outputs[node_name]
        criteria_count = len(outputs.get("completed_criteria", {}))

        if criteria_count > 0:
            return (
                f"Node '{node_name}' completed with {criteria_count} criteria satisfied"
            )
        else:
            return f"Node '{node_name}' completed with basic outputs recorded"

    def to_markdown(self, workflow_def: WorkflowDefinition | None = None) -> str:
        """Generate markdown representation of dynamic workflow state."""
        # Format timestamp
        timestamp = self.last_updated.strftime("%Y-%m-%d")

        # Format current item
        current_item = self.current_item or "null"

        # Format items table
        if self.items:
            items_lines = [
                "| id | description | status |",
                "|----|-------------|--------|",
            ]
            for item in self.items:
                items_lines.append(
                    f"| {item.id} | {item.description} | {item.status} |"
                )
            items_table = "\n".join(items_lines)
        else:
            items_table = "| id | description | status |\n|----|-------------|--------|\n<!-- No items yet -->"

        # Format plan (deprecated for YAML workflows)
        plan_section = "*DEPRECATED: Plan section unused in YAML workflows. See 'Current Workflow' section above for goal and structure.*"

        # Format log
        log_content = "\n".join(self.log) if self.log else "<!-- No log entries yet -->"

        # Format archive log
        archive_log_content = (
            "\n".join(self.archive_log)
            if self.archive_log
            else "<!-- RULE_LOG_ROTATE_01 stores condensed summaries here -->"
        )

        # Get workflow-specific information
        workflow_info = ""
        available_nodes = []
        completed_nodes_progress = ""

        if workflow_def:
            current_node_def = workflow_def.workflow.get_node(self.current_node)
            if current_node_def:
                workflow_info = f"""
## Current Workflow: {workflow_def.name}
**Description:** {workflow_def.description}
**Current Node:** {self.current_node}
**Goal:** {current_node_def.goal}

### Acceptance Criteria:
{chr(10).join(f"- **{key}:** {value}" for key, value in current_node_def.acceptance_criteria.items())}

### Available Next Nodes:
{chr(10).join(f"- {node}" for node in current_node_def.next_allowed_nodes) if current_node_def.next_allowed_nodes else "- End of workflow"}

### Node History:
{chr(10).join(f"{i + 1}. {node}" for i, node in enumerate(self.node_history))}
"""
            available_nodes = self.get_available_next_nodes(workflow_def)

            # Generate completed nodes progress section
            if self.node_outputs:
                progress_lines = ["## Completed Nodes Progress", ""]

                for node_name in self.node_history:
                    if node_name in self.node_outputs:
                        node_def = workflow_def.workflow.get_node(node_name)
                        outputs = self.node_outputs[node_name]

                        progress_lines.append(f"### 🎯 {node_name}")

                        if node_def and node_def.goal:
                            # Display full goal without truncation
                            progress_lines.append(f"**Goal:** {node_def.goal}")

                        # Show acceptance criteria satisfaction with comprehensive evidence
                        if node_def and node_def.acceptance_criteria:
                            progress_lines.append("**Acceptance Criteria Satisfied:**")

                            # Check if outputs contain acceptance criteria evidence
                            criteria_evidence = outputs.get("completed_criteria", {})
                            if isinstance(criteria_evidence, dict):
                                for (
                                    criterion,
                                    description,
                                ) in node_def.acceptance_criteria.items():
                                    if criterion in criteria_evidence:
                                        evidence = criteria_evidence[criterion]
                                        # Always show full evidence without truncation
                                        progress_lines.append(
                                            f"   ✅ **{criterion}**: {evidence}"
                                        )
                                        # Also show the original criterion description for context
                                        progress_lines.append(
                                            f"      📋 Criterion satisfied: {description}"
                                        )
                                    else:
                                        progress_lines.append(
                                            f"   ❓ **{criterion}**: {description} (no evidence recorded)"
                                        )
                            else:
                                # Fallback: just list the criteria as completed
                                for (
                                    criterion,
                                    description,
                                ) in node_def.acceptance_criteria.items():
                                    progress_lines.append(
                                        f"   ✅ **{criterion}**: {description}"
                                    )

                        # Show additional outputs if any
                        if outputs:
                            filtered_outputs = {
                                k: v
                                for k, v in outputs.items()
                                if k not in ["completed_criteria", "goal_achieved"]
                            }
                            if filtered_outputs:
                                progress_lines.append("**Additional Outputs:**")
                                for key, value in filtered_outputs.items():
                                    # Always provide full text without truncation per user requirement
                                    progress_lines.append(f"   📄 **{key}**: {value}")

                        progress_lines.append("")  # Add spacing between nodes

                completed_nodes_progress = chr(10).join(progress_lines) + chr(10)
            elif self.node_history:
                completed_nodes_progress = f"""## Completed Nodes Progress

{chr(10).join(f"- ✅ **{node}**: Completed (no detailed output recorded)" for node in self.node_history)}

"""

        # Create summary section for key navigation info
        current_node_def = workflow_def.workflow.get_node(self.current_node) if workflow_def else None
        current_goal = current_node_def.goal if current_node_def else "Loading..."
        
        # Calculate progress
        if workflow_def and hasattr(workflow_def.workflow, 'nodes'):
            total_nodes = len(workflow_def.workflow.nodes)
            current_position = len(self.node_history) + 1
            progress_display = f"({current_position}/{total_nodes})"
        else:
            progress_display = ""
        
        # Format next steps prominently
        next_steps_display = ""
        if available_nodes:
            next_steps_display = f"**→ Next:** {', '.join(available_nodes)}"
        else:
            next_steps_display = "**→ Next:** End of workflow"

        # Create dynamic template with summary-first approach
        template = f"""📊 **DYNAMIC WORKFLOW STATE**

**Workflow:** {self.workflow_name}
**Current Node:** {self.current_node} {progress_display}
**Status:** {self.status}
{next_steps_display}

**Current Goal:** {current_goal}

**Progress:** {" → ".join(self.node_history + [self.current_node])}

---

## Detailed Session State
_Last updated: {timestamp}_

### Workflow Information
**Task:** {current_item}
{workflow_info}
{completed_nodes_progress}### Plan
{plan_section}

### Rules
> **Dynamic workflow execution based on YAML definition**

#### Current Node Processing
1. Execute the goal: {current_goal}
2. Meet acceptance criteria before proceeding
3. Choose next node from available options: {", ".join(available_nodes) if available_nodes else "End workflow"}

#### Workflow Navigation
- **Available Next Nodes:** {", ".join(available_nodes) if available_nodes else "None (end of workflow)"}
- **Node History:** {" → ".join(self.node_history + [self.current_node])}

---

### Items
{items_table}

### Log
{log_content}

### ArchiveLog
{archive_log_content}
"""

        return template

    def to_json(self) -> str:
        """Convert state to JSON string for persistence."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "DynamicWorkflowState":
        """Create state from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


class WorkflowState(BaseModel):
    """Complete workflow state with client-session support."""

    # Session identification
    client_id: str = Field(default="default", description="Client session identifier")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Session creation time"
    )

    # Workflow state
    last_updated: datetime = Field(default_factory=datetime.now)
    phase: str
    status: str
    current_item: str | None = None
    plan: str = ""
    items: list[WorkflowItem] = Field(default_factory=list)
    log: list[str] = Field(default_factory=list)
    archive_log: list[str] = Field(default_factory=list)

    # Template for markdown generation
    MARKDOWN_TEMPLATE: ClassVar[str] = """# Workflow State
_Last updated: {timestamp}_

## State
Phase: {phase}  
Status: {status}  
CurrentItem: {current_item}  

## Plan
{plan}

## Rules
> **Keep every major section under an explicit H2 (`##`) heading so the agent can locate them unambiguously.**

### [PHASE: ANALYZE]
1. Read **project_config.md**, relevant code & docs.  
2. Summarize requirements. *No code or planning.*

### [PHASE: BLUEPRINT]
1. Decompose task into ordered steps.  
2. Write pseudocode or file-level diff outline under **## Plan**.  
3. Set `Status = NEEDS_PLAN_APPROVAL` and await user confirmation.

### [PHASE: CONSTRUCT]
1. Follow the approved **## Plan** exactly.  
2. After each atomic change:  
   - run test / linter commands specified in `project_config.md`  
   - capture tool output in **## Log**  
3. On success of all steps, set `Phase = VALIDATE`.

### [PHASE: VALIDATE]
1. Rerun full test suite & any E2E checks.  
2. If clean, set `Status = COMPLETED`.  
3. Trigger **RULE_ITERATE_01** when applicable.

---

### RULE_INIT_01
Trigger ▶ `Phase == INIT`  
Action ▶ Ask user for first high-level task → `Phase = ANALYZE, Status = RUNNING`.

### RULE_ITERATE_01
Trigger ▶ `Status == COMPLETED && Items contains unprocessed rows`  
Action ▶  
1. Set `CurrentItem` to next unprocessed row in **## Items**.  
2. Clear **## Log**, reset `Phase = ANALYZE, Status = READY`.

### RULE_LOG_ROTATE_01
Trigger ▶ `length(## Log) > 5 000 chars`  
Action ▶ Summarise the top 5 findings from **## Log** into **## ArchiveLog**, then clear **## Log**.

### RULE_SUMMARY_01
Trigger ▶ `Phase == VALIDATE && Status == COMPLETED`  
Action ▶ 
1. Read `project_config.md`.
2. Construct the new changelog line: `- <One-sentence summary of completed work>`.
3. Find the `## Changelog` heading in `project_config.md`.
4. Insert the new changelog line immediately after the `## Changelog` heading and its following newline (making it the new first item in the list).

---

## Items
{items_table}

## Log
{log}

## ArchiveLog
{archive_log}
"""

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, v):
        """Validate client_id format."""
        if not v or not isinstance(v, str):
            return "default"
        # Basic validation - alphanumeric plus hyphens and underscores
        if not all(c.isalnum() or c in "-_" for c in v):
            return "default"
        return v

    def add_log_entry(self, entry: str) -> None:
        """Add entry to log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005
        formatted_entry = f"[{timestamp}] {entry}"
        self.log.append(formatted_entry)

        # Check if log rotation is needed (>5000 chars total)
        total_chars = sum(len(log_entry) for log_entry in self.log)
        if total_chars > 5000:
            self.rotate_log()

    def rotate_log(self) -> None:
        """Rotate log to archive when it gets too long."""
        # Move current log to archive
        if self.archive_log:
            self.archive_log.append("--- LOG ROTATION ---")
        self.archive_log.extend(self.log)
        self.log.clear()

    def get_next_pending_item(self) -> WorkflowItem | None:
        """Get the next pending item."""
        for item in self.items:
            if item.status == "pending":
                return item
        return None

    def mark_item_completed(self, item_id: int) -> bool:
        """Mark an item as completed."""
        for item in self.items:
            if item.id == item_id:
                item.status = "completed"
                return True
        return False

    def to_markdown(self) -> str:
        """Generate markdown representation of workflow state."""
        # Format timestamp
        timestamp = self.last_updated.strftime("%Y-%m-%d")

        # Format current item
        current_item = self.current_item or "null"

        # Format items table
        if self.items:
            items_lines = [
                "| id | description | status |",
                "|----|-------------|--------|",
            ]
            for item in self.items:
                items_lines.append(
                    f"| {item.id} | {item.description} | {item.status} |"
                )
            items_table = "\n".join(items_lines)
        else:
            items_table = "| id | description | status |\n|----|-------------|--------|\n<!-- No items yet -->"

        # Format plan
        plan = (
            self.plan
            if self.plan.strip()
            else "*No plan yet. Use `workflow_guidance` with action `plan` to create one.*"
        )

        # Format log
        log_content = "\n".join(self.log) if self.log else "<!-- No log entries yet -->"

        # Format archive log
        archive_log_content = (
            "\n".join(self.archive_log)
            if self.archive_log
            else "<!-- RULE_LOG_ROTATE_01 stores condensed summaries here -->"
        )

        # Fill in template
        return self.MARKDOWN_TEMPLATE.format(
            timestamp=timestamp,
            phase=self.phase,
            status=self.status,
            current_item=current_item,
            plan=plan,
            items_table=items_table,
            log=log_content,
            archive_log=archive_log_content,
        )

    def to_json(self) -> str:
        """Convert to JSON for persistence."""
        # Convert to dict and handle datetime serialization
        raw_data = self.model_dump()

        # Convert datetime objects to ISO format
        for field in ["created_at", "last_updated"]:
            if field in raw_data and raw_data[field]:
                raw_data[field] = raw_data[field].isoformat()

        # Helper function to convert empty values to None (except items which should stay as array)
        def empty_to_none(value):
            if value == "" or value == []:
                return None
            return value

        # Structure data according to expected format
        data = {
            "metadata": {
                "client_id": raw_data["client_id"],
                "created_at": raw_data["created_at"],
                "last_updated": raw_data["last_updated"],
            },
            "state": {
                "phase": raw_data["phase"],
                "status": raw_data["status"],
                "current_item": empty_to_none(raw_data["current_item"]),
            },
            "plan": empty_to_none(raw_data["plan"]),
            "items": raw_data["items"],  # Keep items as array even when empty
            "log": empty_to_none(raw_data["log"]),
            "archive_log": empty_to_none(raw_data["archive_log"]),
        }

        return json.dumps(data, indent=2)

    @classmethod
    def from_markdown(cls, content: str, client_id: str) -> "WorkflowState":
        """Parse workflow state from markdown content."""
        lines = content.split("\n")

        # Initialize with defaults
        phase = "INIT"
        status = "READY"
        current_item = None
        plan = ""
        items = []
        log = []
        archive_log = []

        # Parse sections
        current_section = None
        current_content = []

        for line in lines:
            if line.startswith("## "):
                # Process previous section
                if current_section:
                    cls._process_section(current_section, current_content, locals())

                # Start new section
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)

        # Process final section
        if current_section:
            cls._process_section(current_section, current_content, locals())

        return cls(
            client_id=client_id,
            phase=phase,
            status=status,
            current_item=current_item,
            plan=plan,
            items=items,
            log=log,
            archive_log=archive_log,
        )

    @classmethod
    def _process_section(
        cls, section_name: str, content: list[str], context: dict
    ) -> None:
        """Process a section of markdown content."""
        content_text = "\n".join(content).strip()

        if section_name == "State":
            # Parse state fields
            for line in content:
                if line.startswith("Phase:"):
                    phase_str = line.split(":", 1)[1].strip()
                    context["phase"] = phase_str
                elif line.startswith("Status:"):
                    status_str = line.split(":", 1)[1].strip()
                    context["status"] = status_str
                elif line.startswith("CurrentItem:"):
                    current_item_str = line.split(":", 1)[1].strip()
                    context["current_item"] = (
                        current_item_str if current_item_str != "null" else None
                    )

        elif section_name == "Plan":
            context["plan"] = content_text

        elif section_name == "Items":
            context["items"] = cls._parse_items_table(content)

        elif section_name == "Log":
            context["log"] = [line.strip() for line in content if line.strip()]

        elif section_name == "ArchiveLog":
            context["archive_log"] = [line.strip() for line in content if line.strip()]

    @classmethod
    def _parse_items_table(cls, lines: list[str]) -> list[WorkflowItem]:
        """Parse items table from markdown lines."""
        items = []
        for line in lines:
            if "|" in line and "----" not in line and "id" not in line:
                parts = [part.strip() for part in line.split("|")]
                if len(parts) >= 4:  # | id | description | status |
                    try:
                        item_id = int(parts[1])
                        description = parts[2]
                        status = parts[3]
                        items.append(
                            WorkflowItem(
                                id=item_id, description=description, status=status
                            )
                        )
                    except (ValueError, IndexError):
                        continue
        return items
