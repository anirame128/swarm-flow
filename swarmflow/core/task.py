"""
SwarmFlow Task Definition

Core task definition and decorator functionality.
"""

import uuid
from functools import wraps
from typing import Callable

# GLOBAL TASK REGISTRY
TASK_REGISTRY = []

class Task:
    """Represents a single task in a SwarmFlow workflow."""
    
    def __init__(self, fn: Callable, retries: int = 0,
                 before: Callable = None, after: Callable = None,
                 on_error: Callable = None, on_final: Callable = None):
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

    def add_dependency(self, task: "Task"):
        """Add a dependency to this task."""
        self.dependencies.append(task)

def swarm_task(fn=None, *, retries=0, before=None, after=None, on_error=None, on_final=None):
    """
    Decorator to register a function as a SwarmFlow task.
    
    Args:
        fn: The function to decorate
        retries: Number of retry attempts on failure
        before: Hook to execute before task runs
        after: Hook to execute after task succeeds
        on_error: Hook to execute when task fails
        on_final: Hook to execute after task completes
    """
    def wrapper(f):
        task = Task(f, retries=retries, before=before, after=after, 
                   on_error=on_error, on_final=on_final)

        @wraps(f)
        def inner(*args, **kwargs):
            task.args = args
            task.kwargs = kwargs
            return task.fn(*args, **kwargs)

        inner._task = task
        TASK_REGISTRY.append(task)
        return inner

    return wrapper if fn is None else wrapper(fn)
