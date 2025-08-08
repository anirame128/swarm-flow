"""
SwarmFlow Utilities

Utility functions for SwarmFlow operations.
"""

from typing import List, TYPE_CHECKING
from .task import Task

if TYPE_CHECKING:
    pass

# Core task orchestration utilities

def topological_sort(tasks: List[Task]) -> List[Task]:
    """
    Perform topological sort on tasks based on their dependencies.
    
    Args:
        tasks: List of Task objects to sort
        
    Returns:
        List of tasks in dependency order
        
    Raises:
        ValueError: If a cycle is detected in the dependency graph
    """
    visited, temp, ordering = set(), set(), []

    def dfs(task: Task):
        if task.name in temp:
            # Build cycle path for better error reporting
            cycle_path = list(temp) + [task.name]
            raise ValueError(f"Cycle detected in workflow: {' → '.join(cycle_path)}")
        if task.name in visited:
            return
        
        temp.add(task.name)
        for dep in task.dependencies:
            dfs(dep)
        temp.remove(task.name)
        visited.add(task.name)
        ordering.append(task)

    for task in tasks:
        if task.name not in visited:
            dfs(task)

    return ordering

def validate_dependencies(tasks: List[Task], name_to_task: dict) -> None:
    """
    Validate that all task dependencies exist in the registry.
    
    Args:
        tasks: List of all tasks
        name_to_task: Mapping of task names to Task objects
        
    Raises:
        ValueError: If a dependency is not found in the registry
    """
    for task in tasks:
        for param in task.fn.__code__.co_varnames[:task.fn.__code__.co_argcount]:
            if param in name_to_task:
                continue
            raise ValueError(
                f"Unknown dependency '{param}' used in task `{task.name}`. "
                "Make sure the argument matches the name of another @swarm_task."
            )

def enforce_single_mode(mode: str) -> None:
    """
    Enforce that only one orchestration mode is used per execution.
    
    Args:
        mode: The mode being used ("decorator" or "flow")
        
    Raises:
        RuntimeError: If multiple modes are detected
    """
    global USED_MODE
    if USED_MODE and USED_MODE != mode:
        raise RuntimeError(
            f"Cannot mix DAG modes: attempted '{mode}' but already using '{USED_MODE}'"
        )
    USED_MODE = mode

# Global state for mode enforcement
USED_MODE = None