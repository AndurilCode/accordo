# Workflow Node Fields Reference

This document provides detailed information about the fields available in workflow nodes and how to use them effectively.

## User Approval (`needs_approval`)

### Overview

The `needs_approval` field enables workflow creators to implement approval gates at critical workflow nodes. When set to `true`, the workflow engine requires explicit user approval before allowing transitions to subsequent nodes.

**Key Benefits:**
- **Quality Control**: Ensure human oversight at critical decision points
- **Risk Management**: Prevent automated execution of high-risk operations
- **Compliance**: Meet requirements for manual review processes
- **Interactive Workflows**: Enable human-in-the-loop workflow patterns

**When to Use:**
- Deployment or production operations
- Code review checkpoints
- Financial or security-sensitive operations
- Manual validation steps
- Critical infrastructure changes

### Field Definition

```yaml
needs_approval: bool = Field(
    default=False,
    description="Whether this node requires explicit user approval before proceeding to next node execution. Ignored for terminal nodes."
)
```

**Properties:**
- **Type**: Boolean (`true` or `false`)
- **Default**: `false` 
- **Location**: WorkflowNode model in `src/accordo-mcp/models/yaml_workflow.py`
- **Scope**: Applies only to non-terminal nodes (nodes with `next_allowed_nodes`)

### Usage Guide

#### Basic Syntax

Add the `needs_approval` field to any workflow node:

```yaml
node_name:
  goal: "Description of what this node accomplishes"
  acceptance_criteria:
    criterion_name: "Completion requirements"
  needs_approval: true  # Requires user approval
  next_allowed_nodes: [next_node]
```

#### Workflow Transition with Approval

When transitioning FROM an approval-required node, include `user_approval: true`:

```bash
workflow_guidance(
  action="next", 
  context='{"choose": "next_node", "user_approval": true, "criteria_evidence": {"criterion_name": "detailed evidence"}}'
)
```

#### Error Handling

Attempting to transition without approval results in a clear error:

```
Error: Node 'node_name' requires explicit user approval before transition
```

### Examples

#### Example 1: Basic Approval Node

```yaml
plan_deployment:
  goal: |
    Create deployment plan for production environment.
    Review all changes and verify readiness for deployment.
  acceptance_criteria:
    plan_created: "Deployment plan documented with all steps"
    risks_assessed: "Risk assessment completed and mitigation planned"
  needs_approval: true  # Manual approval required
  next_allowed_nodes: [execute_deployment]
```

#### Example 2: Approval Transition

```bash
# Correct: Include user_approval: true
workflow_guidance(
  action="next", 
  context='{"choose": "execute_deployment", "user_approval": true, "criteria_evidence": {"plan_created": "Created 5-step deployment plan", "risks_assessed": "Identified 3 risks with mitigation strategies"}}'
)
```

#### Example 3: Error Case

```bash
# Incorrect: Missing user_approval will fail
workflow_guidance(
  action="next", 
  context='{"choose": "execute_deployment", "criteria_evidence": {"plan_created": "Plan ready"}}'
)
# Results in: Error: Node 'plan_deployment' requires explicit user approval before transition
```

#### Example 4: Terminal Node Behavior

```yaml
complete:
  goal: "Finalize and complete the workflow"
  acceptance_criteria:
    deliverables_ready: "All deliverables completed"
  needs_approval: true  # This will be IGNORED (terminal node)
  next_allowed_nodes: []  # Terminal node - no next nodes
```

**Note**: Terminal nodes (nodes with empty `next_allowed_nodes`) ignore the `needs_approval` setting since there are no transitions to control.

#### Example 5: Complete Approval Workflow

```yaml
name: Deployment Approval Workflow
description: Demonstrates approval gates at critical deployment phases

workflow:
  goal: Deploy application with approval checkpoints
  root: analyze

  tree:
    analyze:
      goal: "Analyze deployment requirements and current state"
      acceptance_criteria:
        requirements_analyzed: "Deployment requirements documented"
      next_allowed_nodes: [plan]

    plan:
      goal: |
        Create detailed deployment plan with risk assessment.
        This requires approval before proceeding to implementation.
      acceptance_criteria:
        plan_created: "Deployment plan created with all steps"
        risks_assessed: "Risk assessment completed"
      needs_approval: true  # First approval gate
      next_allowed_nodes: [implement]

    implement:
      goal: "Execute deployment plan in staging environment"
      acceptance_criteria:
        staging_deployed: "Application deployed to staging"
        tests_passed: "All staging tests completed successfully"
      next_allowed_nodes: [review]

    review:
      goal: |
        Review staging deployment and approve production release.
        Critical approval gate for production deployment.
      acceptance_criteria:
        staging_validated: "Staging deployment validated"
        production_ready: "Ready for production deployment"
      needs_approval: true  # Second approval gate
      next_allowed_nodes: [deploy]

    deploy:
      goal: "Deploy to production environment"
      acceptance_criteria:
        production_deployed: "Successfully deployed to production"
      next_allowed_nodes: []  # Terminal node
```

### Technical Details

#### Engine Validation Logic

The workflow engine validates approval requirements in `WorkflowEngine.validate_transition()`:

```python
needs_approval = getattr(current_node, 'needs_approval', False)
if needs_approval and current_node.next_allowed_nodes and not user_approval:
    raise ValueError(f"Node '{current_node_name}' requires explicit user approval before transition")
```

#### Validation Rules

1. **Approval Check**: Only performed if `needs_approval: true`
2. **Terminal Node Exception**: Approval ignored for nodes with empty `next_allowed_nodes`
3. **User Approval Required**: Must include `user_approval: true` in transition context
4. **Error Handling**: Clear error messages guide users to correct usage

#### Schema Analyzer Integration

The schema analyzer automatically detects approval-required nodes and formats appropriate user guidance:

```python
if needs_approval:
    # Adds approval guidance to node status display
    guidance_text += "⚠️ **APPROVAL REQUIRED** for this node transition"
```

### Integration Guide

#### Using Approval in Workflow Guidance

**Standard Transition (No Approval)**:
```bash
workflow_guidance(action="next", context='{"choose": "node_name", "criteria_evidence": {...}}')
```

**Approval Transition**:
```bash
workflow_guidance(action="next", context='{"choose": "node_name", "user_approval": true, "criteria_evidence": {...}}')
```

#### Schema Analyzer Formatting

Approval-required nodes display special formatting in workflow status:

- **Keywords**: "APPROVAL REQUIRED", "user_approval", "explicit approval"
- **Instructions**: Clear guidance on how to provide approval
- **Visual Indicators**: Warning symbols and highlighted text

#### User Interface Implications

When workflows encounter approval-required nodes:

1. **Status Display**: Shows approval requirement clearly
2. **Error Messages**: Guides users to include `user_approval: true`
3. **Context Format**: Maintains JSON structure for proper tracking
4. **Evidence Requirements**: Still requires criteria evidence alongside approval

### Troubleshooting

#### Common Issues and Solutions

**Issue**: "Node requires explicit user approval before transition"
- **Cause**: Attempting to transition from approval node without `user_approval: true`
- **Solution**: Add `"user_approval": true` to the transition context

**Issue**: Approval setting seems to be ignored
- **Cause**: Node is terminal (empty `next_allowed_nodes`)
- **Solution**: Approval settings only apply to non-terminal nodes

**Issue**: Workflow stuck at approval node
- **Cause**: Incorrect context format or missing approval flag
- **Solution**: Use JSON format: `'{"choose": "node", "user_approval": true, "criteria_evidence": {...}}'`

#### Error Messages and Meanings

| Error Message | Meaning | Solution |
|---------------|---------|----------|
| "Node 'X' requires explicit user approval" | Missing `user_approval: true` | Add approval flag to context |
| "Invalid JSON in context" | Malformed context string | Use proper JSON format |
| "Missing criteria_evidence" | No evidence provided | Include criteria evidence in context |

#### Debugging Approval Problems

1. **Check Node Definition**: Verify `needs_approval: true` is set correctly
2. **Verify Node Type**: Ensure node has `next_allowed_nodes` (not terminal)
3. **Validate Context**: Use proper JSON format with all required fields
4. **Test Transition**: Use exact format from examples above

---

**Related Documentation:**
- [Workflow Examples](../examples/workflows/basic/) - See `approval-example.yaml`
- [Workflow Engine](README.md) - Core workflow system documentation
- [Node Structure Guide](README.md#basic-workflow-structure) - Basic node configuration