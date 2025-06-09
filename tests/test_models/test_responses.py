"""Tests for response models."""

import pytest
from pydantic import ValidationError

from src.accordo_mcp.models.responses import (
    StateUpdateResponse,
    WorkflowResponse,
)


class TestWorkflowResponse:
    """Test WorkflowResponse model."""

    def test_valid_creation_minimal(self):
        """Test creating a valid WorkflowResponse with minimal fields."""
        response = WorkflowResponse(success=True, message="Operation successful")
        assert response.success is True
        assert response.message == "Operation successful"
        assert response.next_prompt is None
        assert response.next_params is None

    def test_valid_creation_with_all_fields(self):
        """Test creating WorkflowResponse with all fields."""
        response = WorkflowResponse(
            success=False,
            message="Operation failed",
            next_prompt="error_recovery_prompt",
            next_params={"error": "Test error"},
        )
        assert response.success is False
        assert response.message == "Operation failed"
        assert response.next_prompt == "error_recovery_prompt"
        assert response.next_params == {"error": "Test error"}

    def test_validation_error_missing_success(self):
        """Test that missing success field raises validation error."""
        with pytest.raises(ValidationError):
            WorkflowResponse(message="Test message")

    def test_validation_error_missing_message(self):
        """Test that missing message field raises validation error."""
        with pytest.raises(ValidationError):
            WorkflowResponse(success=True)

    def test_serialization(self):
        """Test that WorkflowResponse can be serialized."""
        response = WorkflowResponse(
            success=True,
            message="Test message",
            next_prompt="test_prompt",
            next_params={"param1": "value1"},
        )
        data = response.model_dump()
        assert data == {
            "success": True,
            "message": "Test message",
            "next_prompt": "test_prompt",
            "next_params": {"param1": "value1"},
        }

    def test_serialization_with_none_values(self):
        """Test serialization with None values."""
        response = WorkflowResponse(success=False, message="Error occurred")
        data = response.model_dump()
        assert data == {
            "success": False,
            "message": "Error occurred",
            "next_prompt": None,
            "next_params": None,
        }

    def test_deserialization(self):
        """Test that WorkflowResponse can be deserialized from dict."""
        data = {
            "success": True,
            "message": "Success",
            "next_prompt": "continue_prompt",
            "next_params": {"step": 1},
        }
        response = WorkflowResponse(**data)
        assert response.success is True
        assert response.message == "Success"
        assert response.next_prompt == "continue_prompt"
        assert response.next_params == {"step": 1}


class TestStateUpdateResponse:
    """Test StateUpdateResponse model."""

    def test_valid_creation(self):
        """Test creating a valid StateUpdateResponse."""
        response = StateUpdateResponse(
            success=True,
            message="State updated successfully",
            current_phase="CONSTRUCT",
            current_status="RUNNING",
        )
        assert response.success is True
        assert response.message == "State updated successfully"
        assert response.current_phase == "CONSTRUCT"
        assert response.current_status == "RUNNING"

    def test_validation_error_missing_success(self):
        """Test that missing success field raises validation error."""
        with pytest.raises(ValidationError):
            StateUpdateResponse(
                message="Test message", current_phase="INIT", current_status="READY"
            )

    def test_validation_error_missing_message(self):
        """Test that missing message field raises validation error."""
        with pytest.raises(ValidationError):
            StateUpdateResponse(
                success=True, current_phase="INIT", current_status="READY"
            )

    def test_validation_error_missing_current_phase(self):
        """Test that missing current_phase field raises validation error."""
        with pytest.raises(ValidationError):
            StateUpdateResponse(
                success=True, message="Test message", current_status="READY"
            )

    def test_validation_error_missing_current_status(self):
        """Test that missing current_status field raises validation error."""
        with pytest.raises(ValidationError):
            StateUpdateResponse(
                success=True, message="Test message", current_phase="INIT"
            )

    def test_serialization(self):
        """Test that StateUpdateResponse can be serialized."""
        response = StateUpdateResponse(
            success=False,
            message="Update failed",
            current_phase="VALIDATE",
            current_status="ERROR",
        )
        data = response.model_dump()
        assert data == {
            "success": False,
            "message": "Update failed",
            "current_phase": "VALIDATE",
            "current_status": "ERROR",
        }

    def test_deserialization(self):
        """Test that StateUpdateResponse can be deserialized from dict."""
        data = {
            "success": True,
            "message": "Phase transition complete",
            "current_phase": "BLUEPRINT",
            "current_status": "NEEDS_PLAN_APPROVAL",
        }
        response = StateUpdateResponse(**data)
        assert response.success is True
        assert response.message == "Phase transition complete"
        assert response.current_phase == "BLUEPRINT"
        assert response.current_status == "NEEDS_PLAN_APPROVAL"

    def test_different_phase_status_combinations(self):
        """Test various valid phase and status combinations."""
        test_cases = [
            ("INIT", "READY"),
            ("ANALYZE", "RUNNING"),
            ("BLUEPRINT", "NEEDS_PLAN_APPROVAL"),
            ("CONSTRUCT", "RUNNING"),
            ("VALIDATE", "COMPLETED"),
        ]

        for phase, status in test_cases:
            response = StateUpdateResponse(
                success=True,
                message=f"Phase: {phase}, Status: {status}",
                current_phase=phase,
                current_status=status,
            )
            assert response.current_phase == phase
            assert response.current_status == status
