"""Pure schema-driven workflow template generator.

This module generates workflow templates by analyzing existing workflows or
providing basic template structures. No hardcoded patterns.
"""

from pathlib import Path
from typing import Any

import yaml

from ..utils.yaml_loader import WorkflowLoader


class WorkflowTemplateGenerator:
    """Schema-driven workflow template generator."""

    def __init__(self, templates_dir: str = "src/accordo-mcp/templates"):
        """Initialize the template generator.

        Args:
            templates_dir: Directory containing template files
        """
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def generate_template_from_existing(
        self, source_workflow_path: str, output_path: str
    ) -> bool:
        """Generate template by analyzing an existing workflow.

        Args:
            source_workflow_path: Path to existing workflow file
            output_path: Path for generated template

        Returns:
            Success status
        """
        try:
            loader = WorkflowLoader()
            source_workflow = loader.load_workflow(source_workflow_path)

            if not source_workflow:
                return False

            # Create template by generalizing the source workflow
            template_data = {
                "name": "Custom Workflow (Based on " + source_workflow.name + ")",
                "description": f"Template based on {source_workflow.name} - customize as needed",
                "inputs": source_workflow.inputs
                or {
                    "task_description": {
                        "type": "string",
                        "description": "Task description",
                        "required": True,
                    }
                },
                "workflow": {
                    "goal": "Define your workflow goal here (customized from: "
                    + source_workflow.workflow.goal
                    + ")",
                    "root": source_workflow.workflow.root,
                    "tree": self._generalize_nodes(source_workflow.workflow.tree),
                },
            }

            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(template_data, f, default_flow_style=False, indent=2)

            return True

        except Exception:
            return False

    def _generalize_nodes(self, nodes: dict) -> dict:
        """Generalize workflow nodes for template use."""
        generalized = {}

        for node_name, node in nodes.items():
            generalized[node_name] = {
                "goal": f"Customize this goal (was: {node.goal})",
                "acceptance_criteria": node.acceptance_criteria
                or {
                    "criteria_1": "Define specific acceptance criteria",
                    "criteria_2": "Add more criteria as needed",
                },
                "next_allowed_nodes": node.next_allowed_nodes or [],
                "next_allowed_workflows": node.next_allowed_workflows or [],
            }

        return generalized

    def create_basic_template(
        self, template_name: str, output_path: str, node_count: int = 3
    ) -> bool:
        """Create a basic workflow template.

        Args:
            template_name: Name for the template
            output_path: Path for the template file
            node_count: Number of nodes to include

        Returns:
            Success status
        """
        try:
            # Generate basic node sequence
            nodes = {}
            node_names = [f"step_{i + 1}" for i in range(node_count)]

            for i, node_name in enumerate(node_names):
                next_nodes = [node_names[i + 1]] if i < len(node_names) - 1 else []

                nodes[node_name] = {
                    "goal": f"Define goal for {node_name}",
                    "acceptance_criteria": {
                        "criteria_1": f"Define acceptance criteria for {node_name}",
                        "criteria_2": "Add more criteria as needed",
                    },
                    "next_allowed_nodes": next_nodes,
                    "next_allowed_workflows": [],
                }

            template_data = {
                "name": template_name,
                "description": f"Basic {node_count}-step workflow template - customize as needed",
                "inputs": {
                    "task_description": {
                        "type": "string",
                        "description": "Task description",
                        "required": True,
                    }
                },
                "workflow": {
                    "goal": f"Define the overall goal for {template_name}",
                    "root": node_names[0] if node_names else "start",
                    "tree": nodes,
                },
            }

            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(template_data, f, default_flow_style=False, indent=2)

            return True

        except Exception:
            return False

    def analyze_workflow_patterns(
        self, workflows_dir: str = ".accordo/workflows"
    ) -> dict[str, Any]:
        """Analyze existing workflows to identify common patterns.

        Args:
            workflows_dir: Directory containing workflow files

        Returns:
            Analysis results showing patterns
        """
        loader = WorkflowLoader(workflows_dir)
        workflows = loader.discover_workflows()

        if not workflows:
            return {"patterns": {}, "analysis": "No workflows found"}

        # Analyze patterns
        patterns = {
            "common_node_names": {},
            "common_goals": {},
            "workflow_lengths": [],
            "common_inputs": {},
            "execution_patterns": {},
            "input_patterns": {},
            "node_patterns": {},
            "length_distribution": {},
        }

        for workflow in workflows.values():
            # Analyze node names
            for node_name in workflow.workflow.tree:
                patterns["common_node_names"][node_name] = (
                    patterns["common_node_names"].get(node_name, 0) + 1
                )

            # Analyze workflow length
            patterns["workflow_lengths"].append(len(workflow.workflow.tree))

            # Analyze inputs
            if workflow.inputs:
                for input_name in workflow.inputs:
                    patterns["common_inputs"][input_name] = (
                        patterns["common_inputs"].get(input_name, 0) + 1
                    )

            # Track input patterns
            for input_name in workflow.inputs:
                patterns["input_patterns"][input_name] = (
                    patterns["input_patterns"].get(input_name, 0) + 1
                )

            # Track node patterns
            for node_name in workflow.workflow.tree:
                patterns["node_patterns"][node_name] = (
                    patterns["node_patterns"].get(node_name, 0) + 1
                )

            # Track workflow length
            workflow_length = len(workflow.workflow.tree)
            patterns["length_distribution"][workflow_length] = (
                patterns["length_distribution"].get(workflow_length, 0) + 1
            )

        # Calculate averages and summarize
        avg_length = (
            sum(patterns["workflow_lengths"]) / len(patterns["workflow_lengths"])
            if patterns["workflow_lengths"]
            else 0
        )

        # Get most common patterns
        most_common_nodes = sorted(
            patterns["common_node_names"].items(), key=lambda x: x[1], reverse=True
        )[:5]
        most_common_inputs = sorted(
            patterns["common_inputs"].items(), key=lambda x: x[1], reverse=True
        )[:3]

        return {
            "total_workflows": len(workflows),
            "average_workflow_length": round(avg_length, 1),
            "most_common_nodes": most_common_nodes,
            "most_common_inputs": most_common_inputs,
            "length_range": f"{min(patterns['workflow_lengths'])}-{max(patterns['workflow_lengths'])}"
            if patterns["workflow_lengths"]
            else "0",
            "patterns": patterns,
        }

    def suggest_template_from_patterns(
        self, analysis: dict[str, Any], template_name: str, output_path: str
    ) -> bool:
        """Create template based on discovered patterns.

        Args:
            analysis: Result from analyze_workflow_patterns
            template_name: Name for the new template
            output_path: Path for template file

        Returns:
            Success status
        """
        try:
            # Use patterns to suggest template structure
            suggested_length = int(analysis.get("average_workflow_length", 3))
            common_nodes = analysis.get("most_common_nodes", [])
            common_inputs = analysis.get("most_common_inputs", [])

            # Build nodes based on common patterns
            nodes = {}
            if common_nodes:
                # Use most common node names
                for i, (node_name, count) in enumerate(common_nodes):
                    if i >= suggested_length:
                        break

                    # Determine next nodes
                    if i < len(common_nodes) - 1 and i < suggested_length - 1:
                        next_node = common_nodes[i + 1][0]
                        next_nodes = [next_node]
                    else:
                        next_nodes = []

                    nodes[node_name] = {
                        "goal": f"Define goal for {node_name} (commonly used in {count} workflows)",
                        "acceptance_criteria": {
                            "criteria_1": f"Define acceptance criteria for {node_name}",
                            "criteria_2": "Based on common patterns in existing workflows",
                        },
                        "next_allowed_nodes": next_nodes,
                        "next_allowed_workflows": [],
                    }
            else:
                # Fallback to basic pattern
                return self.create_basic_template(
                    template_name, output_path, suggested_length
                )

            # Build inputs based on common patterns
            inputs = {}
            if common_inputs:
                for input_name, count in common_inputs:
                    inputs[input_name] = {
                        "type": "string",
                        "description": f"{input_name} (used in {count} workflows)",
                        "required": input_name == "task_description",
                    }
            else:
                inputs = {
                    "task_description": {
                        "type": "string",
                        "description": "Task description",
                        "required": True,
                    }
                }

            root_node = list(nodes.keys())[0] if nodes else "start"

            template_data = {
                "name": template_name,
                "description": f"Template based on patterns from {analysis['total_workflows']} existing workflows",
                "inputs": inputs,
                "workflow": {
                    "goal": f"Define the overall goal for {template_name} (based on common patterns)",
                    "root": root_node,
                    "tree": nodes,
                },
            }

            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(template_data, f, default_flow_style=False, indent=2)

            return True

        except Exception:
            return False

    def list_available_templates(self) -> list[str]:
        """List available template files.

        Returns:
            List of template file names
        """
        if not self.templates_dir.exists():
            return []

        templates = []
        for template_file in self.templates_dir.glob("*.yaml"):
            templates.append(template_file.name)

        return sorted(templates)

    def get_template_info(self, template_name: str) -> dict[str, Any] | None:
        """Get information about a template.

        Args:
            template_name: Name of template file

        Returns:
            Template information or None if not found
        """
        template_path = self.templates_dir / template_name

        if not template_path.exists():
            return None

        try:
            with open(template_path, encoding="utf-8") as f:
                template_data = yaml.safe_load(f)

            return {
                "name": template_data.get("name", "Unknown"),
                "description": template_data.get("description", "No description"),
                "node_count": len(template_data.get("workflow", {}).get("tree", {})),
                "inputs": list(template_data.get("inputs", {}).keys()),
                "root_node": template_data.get("workflow", {}).get("root", "Unknown"),
            }

        except Exception:
            return None


# Convenience functions


def create_workflow_template(
    name: str, description: str, output_path: str, template_type: str = "basic"
) -> bool:
    """Create a workflow template using the generator.

    Args:
        name: Template name
        description: Template description
        output_path: Path for template file
        template_type: Type of template to create

    Returns:
        Success status
    """
    generator = WorkflowTemplateGenerator()

    if template_type == "basic":
        return generator.create_basic_template(name, output_path)
    elif template_type == "pattern-based":
        analysis = generator.analyze_workflow_patterns()
        return generator.suggest_template_from_patterns(analysis, name, output_path)
    else:
        return generator.create_basic_template(name, output_path)


def analyze_existing_workflows(
    workflows_dir: str = ".accordo/workflows",
) -> dict[str, Any]:
    """Analyze existing workflows for patterns.

    Args:
        workflows_dir: Directory containing workflows

    Returns:
        Pattern analysis results
    """
    generator = WorkflowTemplateGenerator()
    return generator.analyze_workflow_patterns(workflows_dir)
