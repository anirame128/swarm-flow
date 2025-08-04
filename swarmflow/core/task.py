import inspect
import uuid
import os
import time
import json
import requests
from functools import wraps
from typing import Any, Callable
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

# GLOBAL TASK REGISTRY
TASK_REGISTRY = []

# Minimal Task object
class Task:
    def __init__(self, fn: Callable, retries: int = 0):
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

    def add_dependency(self, task: "Task"):
        self.dependencies.append(task)

# Decorator
def swarm_task(fn=None, *, retries=0):
    def wrapper(f):
        task = Task(f, retries=retries)

        @wraps(f)
        def inner(*args, **kwargs):
            task.args = args
            task.kwargs = kwargs
            return task.fn(*args, **kwargs)

        inner._task = task
        TASK_REGISTRY.append(task)
        return inner

    return wrapper if fn is None else wrapper(fn)

# Core runner
def run(api_key: str | None = None):
    api_key = api_key or os.getenv("SWARMFLOW_API_KEY")
    tracer = _setup_tracer()
    name_to_task = {task.name: task for task in TASK_REGISTRY}

    # 🔁 Infer dependencies from param names
    for task in TASK_REGISTRY:
        for param in inspect.signature(task.fn).parameters:
            if param in name_to_task:
                task.add_dependency(name_to_task[param])

    run_id = str(uuid.uuid4())

    # Topological sort
    def topological_sort(tasks):
        visited, temp, ordering = set(), set(), []

        def dfs(t):
            if t.name in temp:
                raise ValueError(f"Cycle detected involving: {t.name}")
            if t.name in visited:
                return
            temp.add(t.name)
            for d in t.dependencies:
                dfs(d)
            temp.remove(t.name)
            visited.add(t.name)
            ordering.append(t)

        for t in tasks:
            if t.name not in visited:
                dfs(t)

        return ordering

    # Run DAG
    for task in topological_sort(TASK_REGISTRY):
        with tracer.start_as_current_span(task.name) as span:
            start = time.time()

            if any(dep.status != "success" for dep in task.dependencies):
                task.status = "skipped"
                continue

            success = False
            for attempt in range(task.retries + 1):
                task.current_retry = attempt
                try:
                    inputs = [d.output for d in task.dependencies]
                    if task.fn.__code__.co_argcount > 0:
                        task.output = task.fn(*inputs, *task.args, **task.kwargs)
                    else:
                        task.output = task.fn()
                    task.status = "success"
                    success = True
                    break
                except Exception as e:
                    task.output = str(e)
                    task.status = "retrying" if attempt < task.retries else "failure"

            task.execution_time_ms = int((time.time() - start) * 1000)
            _extract_metadata(task)
            _log_trace(task, run_id, api_key)
            span.set_attribute("task.status", task.status)
            span.set_attribute("task.duration_ms", task.execution_time_ms)
            span.set_attribute("task.output", str(task.output))

    # Finalize run status
    _finalize_run_status(TASK_REGISTRY, run_id, api_key)

def _log_trace(task: Task, run_id: str, api_key: str | None):
    output = (
        task.output.choices[0].message.content 
        if hasattr(task.output, "choices") else str(task.output)
    )
    trace_payload = {
        "id": task.id,
        "run_id": run_id,
        "name": task.name,
        "status": task.status,
        "duration_ms": task.execution_time_ms,
        "output": output,
        "metadata": _clean(task.metadata),
        "retry_count": task.retries if task.status == "failure" else task.current_retry,
        "dependencies": [d.name for d in task.dependencies],
    }

    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key
            requests.post("http://localhost:8000/api/trace", headers=headers, data=json.dumps(trace_payload))
        else:
            print("[SwarmFlow] ⚠️ No API key provided. Skipping trace upload.")
    except Exception as e:
        print(f"[SwarmFlow] Failed to send trace: {e}")

def _extract_metadata(task: Task):
    output = task.output
    if not output or not hasattr(output, "model") or not hasattr(output, "usage"):
        return

    model = output.model
    usage = output.usage
    pt, ct = getattr(usage, "prompt_tokens", 0), getattr(usage, "completion_tokens", 0)
    total = getattr(usage, "total_tokens", 0)
    cost = _estimate_cost_groq(model, pt, ct)

    task.metadata.update({
        "agent": "LLMProcessor",
        "provider": "Groq",
        "model": model,
        "tokens_used": total,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "cost_usd": cost
    })

def _estimate_cost_groq(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = {
        "llama-4-scout-17b-16e-instruct": (0.11, 0.34),
        "qwen3-32b": (0.29, 0.59),
        "mistral-saba-24b": (0.79, 0.79),
        "llama-3.3-70b": (0.59, 0.79),
        "llama-3.1-8b": (0.05, 0.08),
    }
    model = model.split("/")[-1].lower()
    in_price, out_price = pricing.get(model, (0, 0))
    return round((input_tokens * in_price + output_tokens * out_price) / 1_000_000, 6)

def _setup_tracer():
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    return tracer

def _finalize_run_status(tasks, run_id: str, api_key: str | None):
    statuses = [task.status for task in tasks]
    if all(s == "success" for s in statuses):
        run_status = "completed"
    elif any(s == "failure" for s in statuses):
        run_status = "failed"
    else:
        run_status = "partial"

    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key
        res = requests.patch(
            "http://localhost:8000/api/runs/update-status",
            headers=headers,
            data=json.dumps({
                "run_id": run_id,
                "status": run_status,
            })
        )
        res.raise_for_status()
    except Exception as e:
        print(f"[SwarmFlow] ⚠️ Failed to update run status: {e}")

def _clean(d: dict[str, Any]):
    return {k: v for k, v in d.items() if v is not None}
