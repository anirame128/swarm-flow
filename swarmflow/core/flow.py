import time
import requests
import json
import os
import uuid
from collections import deque
from typing import Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from swarmflow.core.task import Task

class SwarmFlow:
    def __init__(self, api_key: str | None = None):
        self.run_id = str(uuid.uuid4())  # Unique per DAG run
        self.api_key = api_key or os.getenv("SWARMFLOW_API_KEY")  # ✅ API key for authentication
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
    
    def depends_on(self, task_name, *dependency_names):
        for dep_name in dependency_names:
            self.tasks[task_name].add_dependency(self.tasks[dep_name])
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
    
    def _finalize_run_status(self):
        statuses = [task.status for task in self.tasks.values()]
        if all(s == "success" for s in statuses):
            run_status = "completed"
        elif any(s == "failure" for s in statuses):
            run_status = "failed"
        else:
            run_status = "partial"

        try:
            res = requests.patch(
                "http://localhost:8000/api/runs/update-status",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key or ""
                },
                data=json.dumps({
                    "run_id": self.run_id,
                    "status": run_status,
                })
            )
            res.raise_for_status()
        except Exception as e:
            print(f"[SwarmFlow] ⚠️ Failed to update run status: {e}")

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
                    task.current_retry = attempt  # NEW LINE
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
                self._extract_metadata(task)
                span.set_attribute("task.status", task.status)
                span.set_attribute("task.output", str(task.output))
                span.set_attribute("task.duration_ms", task.execution_time_ms)
                self._log(task)

        self._finalize_run_status()

    def _log(self, task: Task):
        print(f"\n[SwarmFlow] Task: {task.name}")
        print(f"  ↳ Status: {task.status}")
        print(f"  ↳ Duration: {task.execution_time_ms} ms")
        print(f"  ↳ Output: {task.output}")
        if task.metadata:
            print(f"  ↳ Metadata: {task.metadata}")
            for key, value in task.metadata.items():
                print(f"    • {key}: {value}")

        # Send trace to frontend API
        output_serialized = (
            task.output.choices[0].message.content 
            if hasattr(task.output, "choices") else str(task.output)
        )

        # Clean metadata to remove None values for JSON serialization
        metadata_clean = self._clean_metadata(task.metadata)

        trace_payload = {
            "id": task.id,
            "run_id": self.run_id,  # ✅ Consistent across all tasks in this DAG run
            "name": task.name,
            "status": task.status,
            "duration_ms": task.execution_time_ms,
            "output": output_serialized,  # ✅ fixed - properly serialized
            "metadata": metadata_clean,  # ✅ cleaned - no None values
            "retry_count": task.retries if task.status == "failure" else getattr(task, "current_retry", 0),  # For failures: total retries used; for successes: attempts taken
            "dependencies": [dep.name for dep in task.dependencies],
        }

        try:
            # Send traces to SwarmFlow backend service
            api_url = "http://localhost:8000/api/trace"
            
            # Prepare headers with API key if available
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["x-api-key"] = self.api_key  # ✅ Pass API key for authentication
            
            res = requests.post(
                api_url,
                headers=headers,
                data=json.dumps(trace_payload)
            )
            res.raise_for_status()
        except Exception as e:
            print(f"[SwarmFlow] ⚠️ Failed to send trace: {e}")

    def _extract_metadata(self, task: Task):
        output = task.output

        if not output or not hasattr(output, "model") or not hasattr(output, "usage"):
            return

        model = output.model
        usage = output.usage
        prompt_tokens = getattr(usage, "prompt_tokens", 0)
        completion_tokens = getattr(usage, "completion_tokens", 0)
        total_tokens = getattr(usage, "total_tokens", 0)

        # Timing
        queue_time = getattr(usage, "queue_time", None)
        prompt_time = getattr(usage, "prompt_time", None)
        completion_time = getattr(usage, "completion_time", None)
        total_time = getattr(usage, "total_time", None)

        # Cost calculation based on Groq pricing
        cost_usd = self._estimate_cost_groq(model, prompt_tokens, completion_tokens)

        task.metadata.update({
            "agent": "LLMProcessor",
            "provider": "Groq",
            "model": model,
            "tokens_used": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
            "queue_time_s": queue_time,
            "prompt_time_s": prompt_time,
            "completion_time_s": completion_time,
            "total_time_s": total_time
        })

    def _estimate_cost_groq(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = {
            "llama-4-scout-17b-16e-instruct": (0.11, 0.34),
            "llama-4-maverick-17b-128e-instruct": (0.20, 0.60),
            "llama-guard-4-12b": (0.20, 0.20),
            "deepseek-r1-distill": (0.75, 0.99),
            "qwen3-32b": (0.29, 0.59),
            "mistral-saba-24b": (0.79, 0.79),
            "llama-3.3-70b": (0.59, 0.79),
            "llama-3.1-8b": (0.05, 0.08),
            "llama-3-70b": (0.59, 0.79),
            "llama-3-8b": (0.05, 0.08),
            "gemma-2-9b": (0.20, 0.20),
            "llama-guard-3-8b": (0.20, 0.20),
        }

        # Normalize model name (remove provider prefix if present)
        normalized_model = model.split("/")[-1].lower()
        input_price, output_price = pricing.get(normalized_model, (0.0, 0.0))
        return round((input_tokens * input_price + output_tokens * output_price) / 1_000_000, 6)

    def _clean_metadata(self, obj: dict[str, Any]) -> dict:
        """Remove None values from metadata for JSON serialization"""
        return {k: v for k, v in obj.items() if v is not None}