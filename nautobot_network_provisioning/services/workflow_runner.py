"""
WorkflowRunner - Graph-based workflow execution engine

This module implements the backend execution engine for graph-based workflows.
It reads the Workflow.graph_definition JSON structure and executes nodes in the
correct order based on the graph topology.
"""

import logging
from typing import Dict, List, Any, Optional
from collections import deque, defaultdict
from django.utils import timezone
from nautobot.dcim.models import Device
from nautobot_network_provisioning.models import (
    TaskIntent, Workflow, Execution, ExecutionStep, TaskStrategy
)
from .context_resolver import ContextResolver
from .template_renderer import build_context, render_template_from_context
from .provider_runtime import select_provider_config, load_provider_driver

logger = logging.getLogger(__name__)


class WorkflowRunner:
    """
    Executes graph-based workflows by:
    1. Parsing the graph_definition JSON
    2. Performing topological sort to determine execution order
    3. Executing nodes in order (handling parallel execution for Fork/Join)
    4. Handling conditional branches (Decision nodes)
    """

    def __init__(self, workflow: Workflow, execution: Execution, device: Device):
        self.workflow = workflow
        self.execution = execution
        self.device = device
        self.graph = workflow.graph_definition or {}
        self.nodes = {node['id']: node for node in self.graph.get('nodes', [])}
        self.edges = self.graph.get('edges', [])
        
        # Build adjacency lists
        self.incoming_edges = defaultdict(list)
        self.outgoing_edges = defaultdict(list)
        for edge in self.edges:
            self.outgoing_edges[edge['source']].append(edge)
            self.incoming_edges[edge['target']].append(edge)

    def execute(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Main execution method. Returns execution results.
        """
        try:
            # 1. Validate graph structure
            if not self._validate_graph():
                raise ValueError("Invalid workflow graph structure")

            # 2. Find start node
            start_node = self._find_start_node()
            if not start_node:
                raise ValueError("No start node found in workflow")

            # 3. Setup context resolver
            resolver = ContextResolver(self.device, overrides=self.execution.input_data or {})

            # 4. Select provider
            provider_config = select_provider_config(device=self.device)
            if not provider_config:
                raise ValueError(f"No enabled AutomationProviderConfig found for {self.device}")
            driver = load_provider_driver(provider_config)

            # 5. Execute graph
            results = self._execute_graph(start_node, resolver, driver, dry_run)

            return {
                'status': 'completed',
                'results': results
            }

        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }

    def _validate_graph(self) -> bool:
        """Validate that the graph is well-formed."""
        if not self.nodes:
            return False

        # Check for start node
        if not self._find_start_node():
            return False

        # Check for end node
        end_nodes = [n for n in self.nodes.values() if n.get('type') == 'end']
        if not end_nodes:
            return False

        return True

    def _find_start_node(self) -> Optional[Dict]:
        """Find the start node (node with type='start')."""
        for node in self.nodes.values():
            if node.get('type') == 'start':
                return node
        return None

    def _execute_graph(
        self,
        start_node: Dict,
        resolver: ContextResolver,
        driver: Any,
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Execute the workflow graph starting from the start node.
        Uses BFS to traverse the graph, handling different node types.
        """
        results = {}
        visited = set()
        queue = deque([start_node['id']])
        execution_order = []

        # Topological sort (BFS-based)
        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue

            node = self.nodes[node_id]
            node_type = node.get('type', 'task')

            # Execute node based on type
            if node_type == 'task':
                result = self._execute_task_node(node, resolver, driver, dry_run)
                results[node_id] = result
                execution_order.append(node_id)

            elif node_type == 'decision':
                result = self._execute_decision_node(node, resolver)
                results[node_id] = result
                execution_order.append(node_id)
                # Follow the appropriate branch
                next_node_id = self._get_decision_branch(node_id, result['condition_result'])
                if next_node_id:
                    queue.append(next_node_id)
                continue

            elif node_type == 'fork':
                # Execute all parallel branches
                parallel_nodes = self._get_fork_branches(node_id)
                for branch_node_id in parallel_nodes:
                    queue.append(branch_node_id)
                execution_order.append(node_id)
                continue

            elif node_type == 'join':
                # Wait for all incoming branches (simplified - in real implementation would need async)
                execution_order.append(node_id)
                # Continue to next node
                pass

            elif node_type in ['start', 'end']:
                execution_order.append(node_id)
                # No execution needed for start/end nodes

            visited.add(node_id)

            # Add next nodes to queue
            for edge in self.outgoing_edges[node_id]:
                target_id = edge['target']
                if target_id not in visited:
                    queue.append(target_id)

        return {
            'execution_order': execution_order,
            'node_results': results
        }

    def _execute_task_node(
        self,
        node: Dict,
        resolver: ContextResolver,
        driver: Any,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Execute a task node."""
        node_data = node.get('data', {})
        task_id = node_data.get('taskId')

        if not task_id:
            raise ValueError(f"Task node {node['id']} has no taskId")

        try:
            task_intent = TaskIntent.objects.get(pk=task_id)
        except TaskIntent.DoesNotExist:
            raise ValueError(f"TaskIntent {task_id} not found")

        # Select strategy
        strategy = self._select_implementation(task_intent)
        if not strategy:
            raise ValueError(f"No strategy found for {task_intent.name} on {self.device.platform}")

        # Create execution step
        exec_step = ExecutionStep.objects.create(
            execution=self.execution,
            task_strategy=strategy,
            status="running"
        )

        try:
            # Resolve variables
            mappings = task_intent.variable_mappings or {}
            resolved = resolver.resolve(mappings)

            # Build rendering context
            render_ctx = build_context(
                device=resolved.get("device", {}),
                intended=resolved.get("intended", {}),
                extra={
                    "config_context": resolved.get("config_context", {}),
                    "execution_id": str(self.execution.pk),
                    "meta": {"step": task_intent.name, "node_id": node['id']}
                }
            )

            # Render template
            if strategy.logic_type == "jinja2":
                rendered = render_template_from_context(
                    strategy.template_content,
                    render_ctx
                )
                exec_step.rendered_content = rendered

                # Execute or diff
                if dry_run:
                    result = driver.diff(
                        target=self.device,
                        rendered_content=rendered,
                        context=render_ctx
                    )
                    exec_step.output = f"--- DIFF ---\n{result.diff}\n\n--- RENDERED ---\n{rendered}"
                else:
                    result = driver.apply(
                        target=self.device,
                        rendered_content=rendered,
                        context=render_ctx
                    )
                    exec_step.output = f"--- LOGS ---\n{result.logs}\n\n--- RENDERED ---\n{rendered}"

                if not result.ok:
                    exec_step.status = "failed"
                    exec_step.error_message = result.details.get("error", "Unknown error")
                    exec_step.save()
                    raise Exception(f"Task {task_intent.name} failed: {exec_step.error_message}")

            exec_step.status = "completed"
            exec_step.end_time = timezone.now()
            exec_step.save()

            return {
                'status': 'completed',
                'step_id': str(exec_step.pk),
                'rendered': rendered if implementation.logic_type == "jinja2" else None
            }

        except Exception as e:
            exec_step.status = "failed"
            exec_step.error_message = str(e)
            exec_step.end_time = timezone.now()
            exec_step.save()
            raise

    def _execute_decision_node(self, node: Dict, resolver: ContextResolver) -> Dict[str, Any]:
        """Execute a decision node and evaluate condition."""
        node_data = node.get('data', {})
        condition = node_data.get('condition', '')

        # Simple condition evaluation (in production, use a proper expression evaluator)
        # For now, just return True/False based on a simple check
        try:
            # This is a placeholder - in production, you'd use a proper expression evaluator
            # like `simpleeval` or `asteval` to safely evaluate Python expressions
            condition_result = self._evaluate_condition(condition, resolver)
        except Exception as e:
            logger.error(f"Failed to evaluate condition: {e}")
            condition_result = False

        return {
            'status': 'completed',
            'condition': condition,
            'condition_result': condition_result
        }

    def _evaluate_condition(self, condition: str, resolver: ContextResolver) -> bool:
        """
        Evaluate a condition expression.
        WARNING: This is a simplified implementation. In production, use a safe expression evaluator.
        """
        if not condition:
            return True

        # Placeholder: simple string matching
        # In production, use a library like `simpleeval` for safe expression evaluation
        try:
            # For now, just check if condition contains common patterns
            if '==' in condition:
                parts = condition.split('==')
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip().strip('"\'')
                    # This is a placeholder - real implementation would resolve variables
                    return False  # Placeholder
        except:
            pass

        return False

    def _get_decision_branch(self, node_id: str, condition_result: bool) -> Optional[str]:
        """Get the next node ID based on decision result."""
        edges = self.outgoing_edges[node_id]
        if not edges:
            return None

        # In a real implementation, edges would have labels like "true" or "false"
        # For now, just take the first edge if True, second if False
        if condition_result and len(edges) > 0:
            return edges[0]['target']
        elif not condition_result and len(edges) > 1:
            return edges[1]['target']
        elif len(edges) > 0:
            return edges[0]['target']

        return None

    def _get_fork_branches(self, node_id: str) -> List[str]:
        """Get all nodes that branch from a fork node."""
        return [edge['target'] for edge in self.outgoing_edges[node_id]]

    def _select_implementation(self, task_intent: TaskIntent) -> Optional[TaskStrategy]:
        """Select the appropriate strategy for a task intent."""
        platform = self.device.platform
        if not platform:
            return None

        strategy = TaskStrategy.objects.filter(
            task_intent=task_intent,
            platform=platform,
            enabled=True
        ).order_by("-priority").first()

        return strategy

