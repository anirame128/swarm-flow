"""
SwarmFlow Base Telemetry

Core telemetry utilities, trace logging, and shared functions.
"""

import json
import requests
import os
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from ..pricing import estimate_cost_openai, estimate_cost_groq, estimate_cost_anthropic

if TYPE_CHECKING:
    from ..task import Task

# Configurable backend URL (defaults preserved)
BACKEND_BASE_URL = os.getenv("SWARMFLOW_BACKEND_URL", "http://localhost:8000")
TRACE_ENDPOINT = f"{BACKEND_BASE_URL}/api/trace"

_TRACER_INITIALIZED = False



def setup_tracer():
    """Set up OpenTelemetry tracer for task execution (idempotent)."""
    global _TRACER_INITIALIZED
    if _TRACER_INITIALIZED:
        return trace.get_tracer(__name__)
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    _TRACER_INITIALIZED = True
    return tracer

# Centralized utility functions for all integrations

def determine_provider_and_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> Tuple[str, float]:
    """Centralized function to determine provider and calculate cost."""
    if "gpt" in model_name.lower():
        provider = "OpenAI"
        cost_usd = estimate_cost_openai(model_name, prompt_tokens, completion_tokens)
    elif "claude" in model_name.lower():
        provider = "Anthropic"
        cost_usd = estimate_cost_anthropic(model_name, prompt_tokens, completion_tokens)
    elif "llama" in model_name.lower() or "groq" in model_name.lower():
        provider = "Groq"
        cost_usd = estimate_cost_groq(model_name, prompt_tokens, completion_tokens)
    else:
        provider = "Unknown"
        cost_usd = 0.0
    
    return provider, cost_usd

def extract_token_usage(result) -> Optional[Tuple[str, int, int, int]]:
    """Extract token usage from various LLM result formats."""
    model_name = "unknown"
    prompt_tokens = completion_tokens = total_tokens = 0
    
    # Check for metadata in response_metadata (Groq format)
    if hasattr(result, "response_metadata") and result.response_metadata:
        metadata = result.response_metadata
        model_name = metadata.get("model_name", "unknown")
        token_usage = metadata.get("token_usage", {})
        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)
        total_tokens = token_usage.get("total_tokens", 0)
        return model_name, prompt_tokens, completion_tokens, total_tokens
    
    # Check for OpenAI format (usage attribute)
    elif hasattr(result, "usage") and result.usage:
        model_name = getattr(result, "model", "unknown")
        usage = result.usage
        prompt_tokens = getattr(usage, "prompt_tokens", 0)
        completion_tokens = getattr(usage, "completion_tokens", 0)
        total_tokens = getattr(usage, "total_tokens", 0)
        return model_name, prompt_tokens, completion_tokens, total_tokens
    
    # Check for Anthropic format
    elif hasattr(result, "usage") and hasattr(result.usage, "input_tokens"):
        model_name = getattr(result, "model", "unknown")
        usage = result.usage
        prompt_tokens = getattr(usage, "input_tokens", 0)
        completion_tokens = getattr(usage, "output_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens
        return model_name, prompt_tokens, completion_tokens, total_tokens
    
    return None

# Global variable to track currently executing task (avoid import issues)
_CURRENT_EXECUTING_TASK = None

def set_current_executing_task(task):
    """Set the currently executing task (called by runner)."""
    global _CURRENT_EXECUTING_TASK
    _CURRENT_EXECUTING_TASK = task

def get_current_executing_task():
    """Get the currently executing task."""
    global _CURRENT_EXECUTING_TASK
    return _CURRENT_EXECUTING_TASK

def attach_metadata_to_task(model_name: str, prompt_tokens: int, completion_tokens: int, 
                           total_tokens: int, cost_usd: float, agent_type: str = "LLMProcessor",
                           additional_metadata: Dict[str, Any] = None):
    """Centralized function to attach metadata to current SwarmFlow task."""
    from ..task import TASK_REGISTRY
    
    # Use the currently executing task if available (from our own tracking)
    active_task = get_current_executing_task()
    
    # Fallback to last registered task if no current executing task
    if not active_task and TASK_REGISTRY:
        active_task = TASK_REGISTRY[-1]
    
    if not active_task:
        return
    
    provider, _ = determine_provider_and_cost(model_name, prompt_tokens, completion_tokens)
    
    metadata = {
        "agent": agent_type,
        "provider": provider,
        "model": model_name,
        "tokens_used": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": cost_usd,
    }
    
    if additional_metadata:
        metadata.update(additional_metadata)
    
    active_task.metadata.update(metadata)

def extract_model_name_from_llm(llm_obj) -> str:
    """Extract model name from various LLM object types."""
    if hasattr(llm_obj, "model_name"):
        return llm_obj.model_name
    elif hasattr(llm_obj, "model"):
        return llm_obj.model
    elif hasattr(llm_obj, "_model_name"):
        return llm_obj._model_name
    elif hasattr(llm_obj, "name"):
        return llm_obj.name
    else:
        return "unknown"

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
    def _safe_output(obj):
        """Safely extract content from ChatCompletion objects or convert to string."""
        try:
            if hasattr(obj, "choices") and isinstance(obj.choices, list) and len(obj.choices) > 0:
                return obj.choices[0].message.content
            return str(obj)
        except Exception as e:
            return f"[SwarmFlow] Output serialization failed: {e}"
    
    output = _safe_output(task.output)
    
    # Create the base trace payload with fields at root level
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
        "flow_memory": _safe_dict(memory or {}),
        "flow_policy": _safe_dict(policy or {})
    }

    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key
            
            res = requests.post(
                TRACE_ENDPOINT, 
                headers=headers, 
                data=json.dumps(trace_payload)
            )
            
            # Check for individual traces that need to be sent
            from .crewai import check_and_send_individual_traces
            check_and_send_individual_traces(run_id, api_key, task.name)
                
        else:
            pass
    except Exception as e:
        pass

def _safe_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Make dictionary JSON serializable by converting non-serializable values to strings."""
    def make_jsonable(v):
        try:
            json.dumps(v)
            return v
        except:
            return str(v)
    return {k: make_jsonable(v) for k, v in d.items()}

def _clean_metadata(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values from metadata for JSON serialization."""
    return {k: v for k, v in obj.items() if v is not None}
