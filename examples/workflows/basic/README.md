# Basic Workflow Examples

This directory contains simple, easy-to-understand workflow examples that demonstrate fundamental concepts of the Workflow Commander system.

## Available Examples

### 1. Simple Linear Workflow (`simple-linear.yaml`)

**Purpose**: Demonstrates a basic linear workflow with automatic progression through sequential phases.

**Structure**:
```
start → analyze → plan → execute → review → complete
```

**Key Features**:
- **Linear Progression**: Each phase has exactly one next step
- **Auto-Progression**: Workflow automatically advances through phases
- **Input Variables**: Uses dynamic input variables in goals
- **Clear Acceptance Criteria**: Each phase has specific completion criteria

**Use Cases**:
- Basic task completion workflows
- Simple project management
- Learning workflow fundamentals
- Template for custom linear workflows

**How to Use**:
```bash
# 1. Discover and start the workflow
workflow_discovery(task_description="Complete: documentation update")

# 2. Start the workflow
workflow_guidance(action="start", context="workflow: Simple Linear Workflow")

# 3. The workflow will auto-progress through all phases
workflow_guidance(action="next")  # Moves through: start → analyze → plan → execute → review → complete
```

### 2. Simple Decision Workflow (`simple-decision.yaml`)

**Purpose**: Demonstrates decision points and branching logic based on task complexity.

**Structure**:
```
assess → choose_approach → [simple_approach | standard_approach | complex_approach] → finalize
                          ↓                ↓                     ↓
                       finalize    validate_standard    validate_complex → review_complex → finalize
```

**Key Features**:
- **Decision Points**: Manual choice between different approaches
- **Branching Logic**: Different paths based on complexity assessment
- **Path Convergence**: All paths converge at the finalization phase
- **Backtracking**: Allows returning to previous phases if needed

**Use Cases**:
- Adaptive workflows based on task complexity
- Quality assurance with different validation levels
- Resource allocation based on requirements
- Learning decision-making in workflows

**How to Use**:
```bash
# 1. Start the workflow
workflow_guidance(action="start", context="workflow: Simple Decision Workflow")

# 2. Progress through assessment
workflow_guidance(action="next")  # Moves to: choose_approach

# 3. Make a decision based on complexity
workflow_guidance(action="next", context="choose: simple_approach")      # For simple tasks
# OR
workflow_guidance(action="next", context="choose: standard_approach")    # For moderate tasks  
# OR
workflow_guidance(action="next", context="choose: complex_approach")     # For complex tasks

# 4. Continue based on chosen path
workflow_guidance(action="next")  # Continues through selected approach
```

## Workflow Concepts Demonstrated

### Input Variables
Both examples show how to use input variables in workflow definitions:

```yaml
inputs:
  task_description:
    type: string
    description: Task provided by the user
    required: true
```

Usage in goals:
```yaml
goal: |
  **PHASE NAME:** ${{ inputs.task_description }}
  
  Description of what this phase accomplishes...
```

### Acceptance Criteria
Each phase defines clear acceptance criteria for completion:

```yaml
acceptance_criteria:
  requirements_clear: "Basic task requirements are understood and documented"
  scope_defined: "Clear scope and boundaries identified for the task"
  next_steps_identified: "Next steps in the workflow are clear"
```

### Linear vs. Decision Workflows

**Linear Workflow Pattern**:
```yaml
phase_name:
  goal: "Description of phase objective"
  acceptance_criteria: { ... }
  next_allowed_nodes: [next_phase]  # Single next step = auto-progression
```

**Decision Workflow Pattern**:
```yaml
decision_phase:
  goal: "Choose between options based on criteria"
  acceptance_criteria: { ... }
  next_allowed_nodes: [option_a, option_b, option_c]  # Multiple options = manual choice
```

## Customization Tips

### Modifying Examples for Your Use Case

1. **Change Input Variables**:
   ```yaml
   inputs:
     your_custom_input:
       type: string
       description: "Description of your input"
       required: true
   ```

2. **Update Phase Names and Goals**:
   ```yaml
   your_phase_name:
     goal: |
       **YOUR PHASE:** ${{ inputs.your_custom_input }}
       
       Description of what this phase should accomplish...
   ```

3. **Modify Acceptance Criteria**:
   ```yaml
   acceptance_criteria:
     your_criteria: "Description of what constitutes completion"
     another_criteria: "Additional completion requirement"
   ```

4. **Adjust Workflow Structure**:
   - Add new phases by creating new nodes
   - Change progression by modifying `next_allowed_nodes`
   - Create decision points by adding multiple next nodes

### Best Practices

1. **Clear Phase Names**: Use descriptive names that indicate purpose
2. **Specific Goals**: Write clear, actionable goals for each phase
3. **Measurable Criteria**: Define acceptance criteria that can be objectively verified
4. **Logical Flow**: Ensure workflow progression makes sense for your use case
5. **Input Variables**: Use variables to make workflows reusable
6. **Documentation**: Include comments explaining complex logic

## Testing Your Modifications

Before using modified workflows in production:

1. **Validate YAML Syntax**: Ensure your YAML is properly formatted
2. **Test Workflow Discovery**: Verify the workflow can be discovered
3. **Test Progression**: Walk through each phase to ensure proper flow
4. **Test Decision Points**: Verify all decision paths work correctly
5. **Test Edge Cases**: Try unexpected inputs or scenarios

## Getting Help

If you have questions about these examples:

1. **Documentation**: Check the [Workflow Guide](../../docs/workflows/) for detailed information
2. **Tutorials**: Try the [step-by-step tutorials](../tutorials/) for hands-on learning
3. **Community**: Join the community discussions for help and tips
4. **Issues**: Report problems or suggestions via GitHub issues 