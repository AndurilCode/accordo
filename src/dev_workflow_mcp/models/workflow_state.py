"""Workflow state models and enums."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class WorkflowPhase(str, Enum):
    """Workflow phases."""

    INIT = "INIT"
    ANALYZE = "ANALYZE"
    BLUEPRINT = "BLUEPRINT"
    CONSTRUCT = "CONSTRUCT"
    VALIDATE = "VALIDATE"


class WorkflowStatus(str, Enum):
    """Workflow status values."""

    READY = "READY"
    RUNNING = "RUNNING"
    NEEDS_PLAN_APPROVAL = "NEEDS_PLAN_APPROVAL"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class WorkflowItem(BaseModel):
    """Individual workflow item."""

    id: int
    description: str
    status: str = "pending"


class WorkflowState(BaseModel):
    """Complete workflow state."""

    last_updated: datetime = Field(default_factory=datetime.now)
    phase: WorkflowPhase
    status: WorkflowStatus
    current_item: str | None = None
    plan: str = ""
    items: list[WorkflowItem] = Field(default_factory=list)
    log: str = ""
    archive_log: str = ""

    def add_log_entry(self, entry: str) -> None:
        """Add entry to log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005
        self.log += f"\n[{timestamp}] {entry}"

        # Check if log rotation is needed (>5000 chars)
        if len(self.log) > 5000:
            self.rotate_log()

    def rotate_log(self) -> None:
        """Rotate log to archive when it gets too long."""
        # Move current log to archive
        if self.archive_log:
            self.archive_log += "\n\n--- LOG ROTATION ---\n\n"
        self.archive_log += self.log
        self.log = ""

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
