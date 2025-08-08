"""
SwarmFlow Task Definition

Core task definition and decorator functionality.
"""

import uuid
from functools import wraps
from typing import Callable, Optional, Union, List

# GLOBAL TASK REGISTRY
TASK_REGISTRY = []

# GLOBAL CURRENTLY EXECUTING TASK
CURRENT_EXECUTING_TASK = None

def _validate_hook(hook: Optional[Callable], name: str) -> None:
    """Validate that a hook is callable if provided."""
    if hook is not None and not callable(hook):
        raise ValueError(f"{name} must be callable, got {type(hook)}")

class Task:
    """Represents a single task in a SwarmFlow workflow."""
    
    def __init__(self, fn: Callable, retries: int = 0,
                 before: Optional[Union[Callable, List[Callable]]] = None, 
                 after: Optional[Union[Callable, List[Callable]]] = None,
                 on_error: Optional[Union[Callable, List[Callable]]] = None, 
                 on_final: Optional[Union[Callable, List[Callable]]] = None):
        
        # Validate function
        if not callable(fn):
            raise ValueError("fn must be callable")
        
        # Validate hooks
        _validate_hook(before, "before")
        _validate_hook(after, "after") 
        _validate_hook(on_error, "on_error")
        _validate_hook(on_final, "on_final")
        
        # Validate retries
        if not isinstance(retries, int) or retries < 0:
            raise ValueError("retries must be a non-negative integer")
        
        self.fn = fn
        self.name = fn.__name__
        self.id = str(uuid.uuid4())
        self.dependencies = []
        self.args = []
        self.kwargs = {}
        self.output = None
        self.status = "pending"
        self.execution_time_ms = 0
        self.retries = retries
        self.current_retry = 0
        self.metadata = {}

        # Hook functions
        self.before = before
        self.after = after
        self.on_error = on_error
        self.on_final = on_final
        
        # Flow reference for shared memory access
        self.flow = None  # Will be assigned when added to a SwarmFlow

    def add_dependency(self, task: "Task") -> None:
        """Add a dependency to this task."""
        if not isinstance(task, Task):
            raise ValueError("Dependency must be a Task object")
        if task == self:
            raise ValueError("Task cannot depend on itself")
        if task not in self.dependencies:
            self.dependencies.append(task)

    def __repr__(self) -> str:
        return f"Task(name='{self.name}', status='{self.status}', dependencies={len(self.dependencies)})"

def swarm_task(fn=None, *, retries=0, before=None, after=None, on_error=None, on_final=None):
    """
    Decorator to register a function as a SwarmFlow task.
    
    Args:
        fn: The function to decorate
        retries: Number of retry attempts on failure (must be >= 0)
        before: Hook to execute before task runs (callable or list of callables)
        after: Hook to execute after task succeeds (callable or list of callables)
        on_error: Hook to execute when task fails (callable or list of callables)
        on_final: Hook to execute after task completes (callable or list of callables)
        
    Returns:
        Decorated function that registers the task
        
    Raises:
        ValueError: If any hook is not callable or retries is invalid
    """
    def wrapper(f):
        # Create Task object with validation
        task = Task(f, retries=retries, before=before, after=after, 
                   on_error=on_error, on_final=on_final)

        @wraps(f)
        def inner(*args, **kwargs):
            # Store args/kwargs for execution context (used by runner and hooks)
            task.args = args
            task.kwargs = kwargs
            return task.fn(*args, **kwargs)

        inner._task = task
        TASK_REGISTRY.append(task)
        return inner

    return wrapper if fn is None else wrapper(fn)
