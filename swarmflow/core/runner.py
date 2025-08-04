"""
SwarmFlow Runner

Handles the main execution logic for task workflows.
"""

import inspect
import time
import os
from typing import Callable, TYPE_CHECKING
from opentelemetry import trace
from .task import TASK_REGISTRY
from .flow import SwarmFlow
from .utils import topological_sort, validate_dependencies, enforce_single_mode
from .telemetry import setup_tracer, log_trace
from .policy import finalize_run_status

if TYPE_CHECKING:
    from .task import Task

def run(api_key: str | None = None):
    """
    Execute all registered tasks in dependency order.
    
    Args:
        api_key: API key for authentication (optional)
    """
    api_key = api_key or os.getenv("SWARMFLOW_API_KEY")
    
    # Enforce single mode usage
    enforce_single_mode("decorator")
    
    # Set up tracing
    tracer = setup_tracer()
    
    # Create SwarmFlow instance for memory and policy
    flow = SwarmFlow(api_key)
    
    # Build task mapping and inject flow context
    name_to_task = {task.name: task for task in TASK_REGISTRY}
    for task in TASK_REGISTRY:
        task.flow = flow
    
    # Validate dependencies
    validate_dependencies(TASK_REGISTRY, name_to_task)
    
    # Infer dependencies from parameter names
    for task in TASK_REGISTRY:
        for param in inspect.signature(task.fn).parameters:
            if param in name_to_task:
                task.add_dependency(name_to_task[param])
    
    run_id = flow.run_id
    
    # Execute tasks in topological order
    for task in topological_sort(TASK_REGISTRY):
        with tracer.start_as_current_span(task.name) as span:
            start = time.time()
            
            # Skip if any dependency failed
            if any(dep.status != "success" for dep in task.dependencies):
                task.status = "skipped"
                continue
            
            # Execute task with retry logic
            success = False
            for attempt in range(task.retries + 1):
                task.current_retry = attempt
                try:
                    # Execute before hooks
                    if task.before:
                        if isinstance(task.before, list):
                            for hook in task.before:
                                hook(task)
                        else:
                            task.before(task)
                    
                    # Execute task function
                    inputs = [d.output for d in task.dependencies]
                    if task.fn.__code__.co_argcount > 0:
                        task.output = task.fn(*inputs, *task.args, **task.kwargs)
                    else:
                        task.output = task.fn()
                    
                    # Execute after hooks
                    if task.after:
                        if isinstance(task.after, list):
                            for hook in task.after:
                                hook(task)
                        else:
                            task.after(task)
                    
                    task.status = "success"
                    success = True
                    break
                except Exception as e:
                    task.output = str(e)
                    task.status = "retrying" if attempt < task.retries else "failure"
                    
                    # Execute on_error hooks
                    if task.on_error:
                        if isinstance(task.on_error, list):
                            for hook in task.on_error:
                                hook(task, e)
                        else:
                            task.on_error(task, e)
            
            # Calculate execution time
            task.execution_time_ms = int((time.time() - start) * 1000)
            
            # Execute on_final hooks
            if task.on_final:
                if isinstance(task.on_final, list):
                    for hook in task.on_final:
                        hook(task)
                else:
                    task.on_final(task)
            
            # Extract metadata and log trace
            _extract_metadata(task)
            log_trace(task, run_id, api_key, flow.memory, flow.policy)
            
            # Set span attributes
            span.set_attribute("task.status", task.status)
            span.set_attribute("task.duration_ms", task.execution_time_ms)
            span.set_attribute("task.output", str(task.output))
    
    # Finalize run status with policy enforcement
    finalize_run_status(TASK_REGISTRY, run_id, api_key, flow.memory, flow.policy)

def _extract_metadata(task: "Task"):
    """Extract metadata from task output (e.g., LLM responses)."""
    output = task.output
    
    if not output or not hasattr(output, "model") or not hasattr(output, "usage"):
        return
    
    model = output.model
    usage = output.usage
    prompt_tokens = getattr(usage, "prompt_tokens", 0)
    completion_tokens = getattr(usage, "completion_tokens", 0)
    total_tokens = getattr(usage, "total_tokens", 0)
    
    # Cost calculation based on Groq pricing
    cost_usd = _estimate_cost_groq(model, prompt_tokens, completion_tokens)
    
    task.metadata.update({
        "agent": "LLMProcessor",
        "provider": "Groq",
        "model": model,
        "tokens_used": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": cost_usd,
    })

def _estimate_cost_groq(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for Groq model usage."""
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