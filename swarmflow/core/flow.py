import time
from collections import deque
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from swarmflow.core.task import Task

class SwarmFlow:
    def __init__(self):
        trace.set_tracer_provider(TracerProvider())
        tracer = trace.get_tracer(__name__)
        span_processor = SimpleSpanProcessor(ConsoleSpanExporter())
        trace.get_tracer_provider().add_span_processor(span_processor)
        self.tracer = tracer
        self.tasks = {}
    
    def add(self, fn):
        task = fn._task
        self.tasks[task.name] = task
        return self
    
    def depends_on(self, task_name, dependency_name):
        self.tasks[task_name].add_dependency(self.tasks[dependency_name])
        return self

    def _topological_sort(self):
        visited = set()
        temp_stack = set()
        ordering = []

        def dfs(task):
            if task.name in temp_stack:
                # Build cycle path for better error reporting
                cycle_path = list(temp_stack) + [task.name]
                raise ValueError(f"Cycle detected in workflow: {' → '.join(cycle_path)}")
            if task.name in visited:
                return

            temp_stack.add(task.name)
            for dep in task.dependencies:
                dfs(dep)
            temp_stack.remove(task.name)
            visited.add(task.name)
            ordering.append(task)

        for task in self.tasks.values():
            if task.name not in visited:
                dfs(task)

        return ordering
    
    def run(self):
        ordered_tasks = self._topological_sort()

        for task in ordered_tasks:
            with self.tracer.start_as_current_span(task.name) as span:
                start = time.time()

                # Skip if any dependency failed
                if any(dep.status != "success" for dep in task.dependencies):
                    task.status = "skipped"
                    task.failed_due_to_dependency = True
                    task.execution_time_ms = 0
                    span.set_attribute("task.status", task.status)
                    span.set_attribute("task.output", str(task.output))
                    span.set_attribute("task.duration_ms", task.execution_time_ms)
                    self._log(task)
                    continue

                success = False
                for attempt in range(task.retries + 1):
                    try:
                        inputs = [dep.output for dep in task.dependencies]
                        # Only pass dependency inputs if the task function expects arguments
                        if task.fn.__code__.co_argcount > 0:
                            task.output = task.fn(*inputs, *task.args, **task.kwargs)
                        else:
                            task.output = task.fn(*task.args, **task.kwargs)
                        task.status = "success"
                        success = True
                        break
                    except Exception as e:
                        task.output = str(e)
                        task.status = "retrying" if attempt < task.retries else "failure"

                task.execution_time_ms = int((time.time() - start) * 1000)
                span.set_attribute("task.status", task.status)
                span.set_attribute("task.output", str(task.output))
                span.set_attribute("task.duration_ms", task.execution_time_ms)
                self._log(task)

    def _log(self, task: Task):
        print(f"\n[SwarmFlow] Task: {task.name}")
        print(f"  ↳ Status: {task.status}")
        print(f"  ↳ Duration: {task.execution_time_ms} ms")
        print(f"  ↳ Output: {task.output}")