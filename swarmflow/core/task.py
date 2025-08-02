import uuid
from functools import wraps

class Task:
    def __init__(self, fn, retries=0):
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
        self.failed_due_to_dependency = False
        self.metadata = {}
    
    def add_dependency(self, task):
        self.dependencies.append(task)
    
def swarm_task(fn=None, *, retries=0):
    def wrapper(fn):
        task = Task(fn, retries=retries)

        @wraps(fn)
        def inner(*args, **kwargs):
            task.args = args
            task.kwargs = kwargs
            return task.fn(*args, **kwargs)

        inner._task = task
        return inner
    
    if fn is None:
        return wrapper
    return wrapper(fn)
