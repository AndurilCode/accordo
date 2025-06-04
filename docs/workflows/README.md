# Workflow System Documentation

This section will contain comprehensive workflow system documentation. For now, please refer to:

## 🚀 Dynamic Workflow Creation by Agents

**Revolutionary Feature:** AI agents can generate custom YAML workflows on-the-fly for any task!

### How Dynamic Creation Works

1. **Task Analysis**: Agent analyzes the specific requirements and complexity
2. **Creation Guidance**: Use `workflow_creation_guidance()` to get comprehensive templates and best practices
3. **YAML Generation**: Agent creates custom workflow YAML tailored to exact needs
4. **Execution**: Start the custom workflow with full state management and progression control

### Workflow Creation Tool

```bash
workflow_creation_guidance(
    task_description="Your specific task description",
    workflow_type="coding|documentation|debugging|testing|analysis|etc",
    complexity_level="simple|medium|complex"
)
```

**Returns comprehensive guidance including:**
- **Task analysis framework** - How to break down requirements into logical phases
- **YAML structure specification** - Complete schema with required and optional fields
- **Complete example workflows** - Ready-to-adapt templates
- **Best practices** - Design principles for effective workflows
- **Technical requirements** - Validation criteria and formatting rules

### Starting Custom Workflows

```bash
workflow_guidance(
    action="start", 
    context="workflow: Your Custom Workflow Name\nyaml: <complete_yaml_content>"
)
```

This enables workflows for **any domain** - web development, data science, DevOps, research, documentation, testing, and beyond!

### Example Workflows

See the [examples/workflows/basic/](../../examples/workflows/basic/) directory for:

- **[simple-linear.yaml](../../examples/workflows/basic/simple-linear.yaml)** - Basic 5-phase linear workflow
- **[simple-decision.yaml](../../examples/workflows/basic/simple-decision.yaml)** - Decision workflow with branching
- **[Usage Guide](../../examples/workflows/basic/README.md)** - Detailed explanations and instructions

## Ready Workflows Reference
- **[debugging.yaml](./workflows/debugging.yaml)** - For debug specific tasks
- **[default-coding.yaml](./workflows/default-coding.yaml)** - For any coding related task
- **[documentation.yaml](./workflows/documentation.yaml)** - For documentation tasks


### Basic Workflow Structure

```yaml
name: My Workflow
description: Brief description

inputs:
  task_description:
    type: string
    required: true

workflow:
  goal: Overall objective
  root: start_node
  
  tree:
    start_node:
      goal: "What this node accomplishes"
      acceptance_criteria:
        criteria_name: "What constitutes completion"
      next_allowed_nodes: [next_node]
```