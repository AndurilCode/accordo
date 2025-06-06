# Workflow Composition Guide

This guide explains how to use workflow composition to split complex workflows into multiple files for better organization and reusability.

## Overview

Workflow composition allows you to:
- **Split complex workflows** into smaller, focused files
- **Reuse workflows** across different contexts
- **Organize workflows** by functionality or team ownership
- **Maintain readability** in large workflow definitions

## Basic Concepts

### Workflow Nodes vs. Composition Nodes

**Traditional Workflow Node:**
```yaml
analyze_requirements:
  goal: "Analyze the requirements"
  acceptance_criteria:
    requirement_analysis: "MUST break down requirements"
  next_allowed_nodes: [design_architecture]
```

**Workflow Composition Node:**
```yaml
implement_feature:
  workflow: ./coding-workflow.yaml
  next_allowed_nodes: [comprehensive_testing]
```

### Key Differences

| Feature | Traditional Node | Composition Node |
|---------|------------------|------------------|
| **Goal** | Required | Not allowed (defined in referenced workflow) |
| **Acceptance Criteria** | Optional | Not allowed (defined in referenced workflow) |
| **Workflow Reference** | Not allowed | Required |
| **Execution** | Direct execution | Delegates to external workflow |

## Workflow Composition Syntax

### Basic Syntax

```yaml
node_name:
  workflow: ./path/to/external-workflow.yaml
  next_allowed_nodes: [next_node]
```

### Path Resolution

- **Relative paths**: Resolved relative to the current workflow file
- **Absolute paths**: Used as-is (discouraged for portability)
- **Security**: Path traversal (`../`) and system directories are blocked

### Examples

```yaml
# Relative path (recommended)
implement_feature:
  workflow: ./coding-workflow.yaml

# Subdirectory
run_tests:
  workflow: ./testing/comprehensive-testing.yaml

# Parallel workflow
create_docs:
  workflow: ./documentation-workflow.yaml
```

## Complete Example

### Main Workflow: `feature-development.yaml`

```yaml
name: Feature Development Workflow
description: Comprehensive feature development with composition

inputs:
  task_description:
    type: string
    description: Description of the feature to develop
    required: true

workflow:
  goal: Complete feature development
  root: analyze_requirements
  tree:
    analyze_requirements:
      goal: "Analyze requirements for {{ inputs.task_description }}"
      acceptance_criteria:
        requirement_analysis: "MUST break down feature requirements"
        scope_definition: "MUST clearly define scope boundaries"
      next_allowed_nodes: [design_architecture]

    design_architecture:
      goal: "Design architecture for {{ inputs.task_description }}"
      acceptance_criteria:
        technical_design: "MUST create detailed technical design"
        implementation_plan: "MUST break down implementation steps"
      next_allowed_nodes: [implement_feature]

    # Workflow composition - delegates to external workflow
    implement_feature:
      workflow: ./coding-workflow.yaml
      next_allowed_nodes: [comprehensive_testing]

    comprehensive_testing:
      goal: "Test {{ inputs.task_description }}"
      acceptance_criteria:
        unit_testing: "MUST implement unit tests with 90% coverage"
        integration_testing: "MUST create integration tests"
      next_allowed_nodes: []
```

### Supporting Workflow: `coding-workflow.yaml`

```yaml
name: Coding Workflow
description: Focused coding workflow for feature implementation

inputs:
  task_description:
    type: string
    description: Description of the coding task
    required: true

workflow:
  goal: Implement code changes following best practices
  root: setup_development
  tree:
    setup_development:
      goal: "Setup development environment"
      acceptance_criteria:
        environment_setup: "MUST verify development environment"
        project_understanding: "MUST understand project structure"
      next_allowed_nodes: [implement_core_logic]

    implement_core_logic:
      goal: "Implement core functionality"
      acceptance_criteria:
        core_implementation: "MUST implement all core functionality"
        coding_standards: "MUST follow project coding standards"
      next_allowed_nodes: [add_tests]

    add_tests:
      goal: "Add comprehensive tests"
      acceptance_criteria:
        unit_tests: "MUST create unit tests with good coverage"
        integration_tests: "MUST create integration tests"
      next_allowed_nodes: []
```

## Execution Flow

1. **Start Main Workflow**: Begin with `feature-development.yaml`
2. **Execute Normal Nodes**: Process `analyze_requirements` and `design_architecture`
3. **Encounter Composition Node**: When reaching `implement_feature`
4. **Automatic Transition**: System automatically loads and transitions to `coding-workflow.yaml`
5. **Execute Sub-Workflow**: Process all nodes in the coding workflow
6. **Return to Main**: When coding workflow completes, return to main workflow
7. **Continue Main Workflow**: Process `comprehensive_testing`

## State Management

### Workflow Stack

The system maintains a stack of workflow contexts:

```
[Main Workflow Context]
  ↓ transition to coding-workflow.yaml
[Main Workflow Context, Coding Workflow Context]
  ↓ coding workflow completes
[Main Workflow Context]
```

### Input Inheritance

Sub-workflows inherit inputs from parent workflows:

```yaml
# Parent workflow inputs
inputs:
  task_description: "Add user authentication"
  feature_complexity: "medium"

# Sub-workflow receives these inputs plus any additional inputs it defines
```

### Output Capture

Completed workflows store their outputs:

```yaml
workflow_outputs:
  "Coding Workflow":
    implementation_completed: true
    files_modified: ["auth.py", "user.py"]
    tests_added: 15
```

## Best Practices

### 1. Workflow Organization

```
.workflow-commander/workflows/
├── main-workflows/
│   ├── feature-development.yaml
│   └── bug-fix.yaml
├── sub-workflows/
│   ├── coding-workflow.yaml
│   ├── testing-workflow.yaml
│   └── documentation-workflow.yaml
└── specialized/
    ├── security-review.yaml
    └── performance-testing.yaml
```

### 2. Naming Conventions

- **Main workflows**: Descriptive names (`feature-development.yaml`)
- **Sub-workflows**: Action-focused (`coding-workflow.yaml`)
- **Specialized workflows**: Domain-specific (`security-review.yaml`)

### 3. Input Design

```yaml
# Good: Generic, reusable inputs
inputs:
  task_description:
    type: string
    required: true
  complexity_level:
    type: string
    default: "medium"

# Avoid: Overly specific inputs
inputs:
  specific_feature_name:
    type: string
    required: true
```

### 4. Error Handling

The system provides comprehensive error handling:

- **File Not Found**: Clear error when referenced workflow doesn't exist
- **Path Security**: Prevents access to system directories
- **Validation Errors**: Reports YAML validation issues
- **Circular Dependencies**: Prevents infinite workflow loops

## Advanced Features

### Conditional Composition

```yaml
# Use next_allowed_workflows for external workflow transitions
documentation_phase:
  goal: "Create documentation"
  acceptance_criteria:
    user_docs: "MUST create user documentation"
  next_allowed_workflows: [documentation]  # External workflow transition
  next_allowed_nodes: [feature_complete]   # Continue in current workflow
```

### Multiple Sub-Workflows

```yaml
quality_assurance:
  goal: "Ensure quality"
  acceptance_criteria:
    code_review: "MUST conduct code review"
  next_allowed_nodes: [security_review, performance_test]

security_review:
  workflow: ./security/security-review.yaml
  next_allowed_nodes: [finalize]

performance_test:
  workflow: ./testing/performance-testing.yaml
  next_allowed_nodes: [finalize]
```

### Dynamic Workflow Selection

While not currently implemented, future versions may support:

```yaml
# Future feature concept
implement_feature:
  workflow: "{{ inputs.implementation_type }}-workflow.yaml"
```

## Migration Guide

### Converting Existing Workflows

1. **Identify Large Workflows**: Look for workflows with >10 nodes
2. **Find Natural Boundaries**: Identify logical groupings of nodes
3. **Extract Sub-Workflows**: Move related nodes to separate files
4. **Replace with Composition**: Replace node groups with workflow references
5. **Test Thoroughly**: Verify all transitions work correctly

### Example Migration

**Before (Monolithic):**
```yaml
workflow:
  tree:
    analyze: { ... }
    design: { ... }
    setup_dev: { ... }
    code_core: { ... }
    add_tests: { ... }
    code_review: { ... }
    test_integration: { ... }
    test_performance: { ... }
    create_docs: { ... }
    deploy: { ... }
```

**After (Composed):**
```yaml
workflow:
  tree:
    analyze: { ... }
    design: { ... }
    implement:
      workflow: ./coding-workflow.yaml
    test:
      workflow: ./testing-workflow.yaml
    document:
      workflow: ./documentation-workflow.yaml
    deploy: { ... }
```

## Troubleshooting

### Common Issues

1. **Workflow Not Found**
   ```
   ❌ External workflow file not found: ./missing-workflow.yaml
   ```
   **Solution**: Check file path and ensure file exists

2. **Path Security Error**
   ```
   ❌ Unsafe path detected: '../../../etc/passwd' contains '..'
   ```
   **Solution**: Use relative paths within workflow directory

3. **Validation Error**
   ```
   ❌ Node cannot have both 'workflow' and 'goal' fields
   ```
   **Solution**: Remove goal and acceptance_criteria from composition nodes

4. **Circular Dependency**
   ```
   ❌ Circular workflow dependency detected
   ```
   **Solution**: Restructure workflows to avoid circular references

### Debugging

1. **Enable Verbose Logging**: Check workflow transition logs
2. **Validate Workflows**: Use workflow validation tools
3. **Test Individually**: Test sub-workflows independently
4. **Check File Permissions**: Ensure workflow files are readable

## Limitations

### Current Limitations

- **No Circular Dependency Detection**: Manual prevention required
- **Simple Input Passing**: No complex input transformation
- **No Conditional Composition**: Static workflow references only
- **No Parallel Composition**: Sequential execution only

### Future Enhancements

- Dynamic workflow selection based on inputs
- Parallel workflow execution
- Advanced input/output mapping
- Workflow dependency graphs
- Automatic circular dependency detection

## API Reference

### WorkflowNode Properties

```python
class WorkflowNode:
    workflow: Optional[str]  # Path to external workflow
    is_workflow_node: bool   # True if this node references external workflow
```

### WorkflowEngine Methods

```python
def execute_workflow_transition(
    state: DynamicWorkflowState,
    current_workflow_def: WorkflowDefinition,
    target_workflow_path: str,
    outputs: dict[str, Any] | None = None,
) -> tuple[bool, WorkflowDefinition | None, str]:
    """Execute transition to external workflow."""

def return_from_workflow(
    state: DynamicWorkflowState,
    completed_workflow_outputs: dict[str, Any] | None = None,
) -> tuple[bool, WorkflowDefinition | None, str]:
    """Return from completed external workflow."""
```

### WorkflowLoader Methods

```python
def load_external_workflow(
    workflow_path: str,
    base_workflow_path: str | None = None
) -> WorkflowDefinition | None:
    """Load external workflow with security validation."""
```

## Examples Repository

See the `.workflow-commander/workflows/` directory for complete examples:

- `feature-development.yaml`: Main workflow with composition
- `coding-workflow.yaml`: Focused coding sub-workflow
- `documentation.yaml`: Documentation workflow example

## Support

For issues or questions about workflow composition:

1. Check this guide for common patterns
2. Validate your YAML syntax
3. Test workflows individually before composing
4. Review error messages for specific guidance

Happy composing! 🚀 