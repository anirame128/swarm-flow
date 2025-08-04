"""
SwarmFlow Telemetry

Handles tracing, logging, and observability for task execution.
"""

import json
import requests
from typing import Any, Dict, TYPE_CHECKING
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

if TYPE_CHECKING:
    from .task import Task

def setup_tracer():
    """Set up OpenTelemetry tracer for task execution."""
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    trace.get_tracer_provider().add_span_processor(
        SimpleSpanProcessor(ConsoleSpanExporter())
    )
    return tracer

def log_trace(
    task: "Task", 
    run_id: str, 
    api_key: str | None, 
    memory: Dict[str, Any] = None, 
    policy: Dict[str, Any] = None
):
    """
    Log task trace to the SwarmFlow backend.
    
    Args:
        task: The task that was executed
        run_id: Unique identifier for this DAG run
        api_key: API key for authentication
        memory: Shared memory state
        policy: Active policy rules
    """
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
        "metadata": _clean_metadata(task.metadata),
        "retry_count": task.retries if task.status == "failure" else task.current_retry,
        "dependencies": [d.name for d in task.dependencies],
    }

    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key
            requests.post(
                "http://localhost:8000/api/trace", 
                headers=headers, 
                data=json.dumps({
                    "run_id": run_id,
                    "trace": trace_payload,
                    "flow_memory": memory or {},
                    "flow_policy": policy or {}
                })
            )
        else:
            print("[SwarmFlow] ⚠️ No API key provided. Skipping trace upload.")
    except Exception as e:
        print(f"[SwarmFlow] Failed to send trace: {e}")

def _clean_metadata(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values from metadata for JSON serialization."""
    return {k: v for k, v in obj.items() if v is not None} 