"""
SwarmFlow Runner

Handles the main execution logic for task workflows.
"""

import inspect
import time
import os
from typing import TYPE_CHECKING

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, continue without it
    pass

from .task import TASK_REGISTRY
from . import task
from .flow import SwarmFlow
from .utils import topological_sort, validate_dependencies, enforce_single_mode
from .telemetry import (
    setup_tracer, 
    log_trace, 
    instrument_langchain_llm, 
    instrument_crewai,
    determine_provider_and_cost
)
from .telemetry.base import set_current_executing_task
from .policy import finalize_run_status

if TYPE_CHECKING:
    from .task import Task

def run(api_key: str | None = None, policy: dict | None = None):
    """
    Execute all registered tasks in dependency order.
    
    Args:
        api_key: API key for authentication (ignored; sourced from environment)
        policy: Policy rules to enforce during execution (optional)
    """
    # Enforce environment-only API key usage
    api_key = os.getenv("SWARMFLOW_API_KEY")
    
    # Enforce single mode usage
    enforce_single_mode("decorator")
    
    # Instrument all LLM providers for comprehensive metadata capture
    instrument_langchain_llm()  # Supports OpenAI, Groq, Anthropic, etc.
    instrument_crewai()         # Supports CrewAI multi-agent systems
    
    # Set up tracing
    tracer = setup_tracer()
    
    # Create SwarmFlow instance for memory and policy
    flow = SwarmFlow(api_key)
    
    # Inject policy if provided
    if policy:
        flow.policy.update(policy)
    
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
    for current_task in topological_sort(TASK_REGISTRY):
        with tracer.start_as_current_span(current_task.name) as span:
            start = time.time()
            
            # Skip if any dependency failed
            if any(dep.status != "success" for dep in current_task.dependencies):
                current_task.status = "skipped"
                continue
            
            # Execute task with retry logic
            success = False
            for attempt in range(current_task.retries + 1):
                current_task.current_retry = attempt
                try:
                    # Execute before hooks
                    if current_task.before:
                        if isinstance(current_task.before, list):
                            for hook in current_task.before:
                                hook(current_task)
                        else:
                            current_task.before(current_task)
                    
                    # Execute task function
                    inputs = [d.output for d in current_task.dependencies]
                    
                    # Set current executing task for telemetry (using shared function)
                    set_current_executing_task(current_task)
                    
                    try:
                        if current_task.fn.__code__.co_argcount > 0:
                            current_task.output = current_task.fn(*inputs, *current_task.args, **current_task.kwargs)
                        else:
                            current_task.output = current_task.fn()
                    finally:
                        # Clear current executing task
                        set_current_executing_task(None)
                    
                    # Execute after hooks
                    if current_task.after:
                        if isinstance(current_task.after, list):
                            for hook in current_task.after:
                                hook(current_task)
                        else:
                            current_task.after(current_task)
                    
                    current_task.status = "success"
                    success = True
                    break
                except Exception as e:
                    current_task.output = str(e)
                    current_task.status = "retrying" if attempt < current_task.retries else "failure"
                    
                    # Execute on_error hooks
                    is_final = (attempt == current_task.retries)
                    
                    if current_task.on_error:
                        if isinstance(current_task.on_error, list):
                            for hook in current_task.on_error:
                                # check if hook expects 3 args (supports final_retry)
                                if hook.__code__.co_argcount == 3:
                                    hook(current_task, e, final_retry=is_final)
                                else:
                                    hook(current_task, e)
                        else:
                            if current_task.on_error.__code__.co_argcount == 3:
                                current_task.on_error(current_task, e, final_retry=is_final)
                            else:
                                current_task.on_error(current_task, e)
            
            # Calculate execution time
            current_task.execution_time_ms = int((time.time() - start) * 1000)
            
            # Execute on_final hooks
            if current_task.on_final:
                if isinstance(current_task.on_final, list):
                    for hook in current_task.on_final:
                        hook(current_task)
                else:
                    current_task.on_final(current_task)
            
            # Extract metadata and log trace
            _extract_metadata(current_task)
            log_trace(current_task, run_id, api_key, flow.memory, flow.policy)
            
            # Set span attributes
            span.set_attribute("task.status", current_task.status)
            span.set_attribute("task.duration_ms", current_task.execution_time_ms)
            span.set_attribute("task.output", str(current_task.output))
    
    # Finalize run status with policy enforcement
    finalize_run_status(TASK_REGISTRY, run_id, api_key, flow.memory, flow.policy)
    
    # Return the output of the last task
    if TASK_REGISTRY:
        return TASK_REGISTRY[-1].output
    return None


def _extract_metadata(task: "Task"):
    """Extract metadata from task output or captured LLM result."""
    # Check if task has metadata from instrumentation
    if hasattr(task, "metadata") and task.metadata:
        # Metadata should already be populated by instrumentation
        if "agent" in task.metadata:
            # Check if we have better model information from captured calls
            _enhance_metadata_from_captured_calls(task)

            return
        # If it has CrewAI metadata, don't overwrite it but enhance it
        if "crew_level" in task.metadata:
            _enhance_metadata_from_captured_calls(task)

            return
    
    # Fallback: try to extract from task output if it's a known LLM result format
    output = task.output

    
    # Try to get model information from captured CrewAI calls first
    model_info_from_calls = _get_model_info_from_captured_calls(task)
    
    # Only extract if it's actually an LLM result object, not a string or other type
    if hasattr(output, 'token_usage') and output.token_usage and not isinstance(output, str):

        
        token_usage = output.token_usage
        
        # Handle different token usage formats
        if hasattr(token_usage, 'get'):
            # Dictionary format
            prompt_tokens = token_usage.get("prompt_tokens", 0)
            completion_tokens = token_usage.get("completion_tokens", 0)
            total_tokens = token_usage.get("total_tokens", 0)
        else:
            # UsageMetrics object format
            prompt_tokens = getattr(token_usage, "prompt_tokens", 0)
            completion_tokens = getattr(token_usage, "completion_tokens", 0)
            total_tokens = getattr(token_usage, "total_tokens", 0)
        
        # Determine provider and model - prefer captured call info over task output
        if model_info_from_calls:
            model_name = model_info_from_calls["model"]
            provider = model_info_from_calls["provider"] 
        elif hasattr(output, "model"):
            model_name = output.model
            provider, _ = determine_provider_and_cost(model_name, prompt_tokens, completion_tokens)
        else:
            model_name = "unknown"
            provider = "Unknown"
        
        _, cost_usd = determine_provider_and_cost(model_name, prompt_tokens, completion_tokens)
        
        # Only update metadata if it doesn't already have proper instrumentation metadata
        if not task.metadata or "agent" not in task.metadata or task.metadata.get("agent") == "LLMProcessor":
            task.metadata.update({
                "agent": "LLMProcessor",
                "provider": provider,
                "model": model_name,
                "tokens_used": total_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": cost_usd,
            })

def _get_model_info_from_captured_calls(task: "Task") -> dict:
    """Get model information from captured CrewAI calls for this task."""
    from .telemetry import get_individual_crew_task_calls
    
    # Get recent captured calls that might be related to this task
    recent_calls = get_individual_crew_task_calls()
    
    # Look for calls that happened around the same time as this task
    if recent_calls:
        # Get the most recent call with model information
        latest_call = recent_calls[-1]
        if latest_call.get("model") and latest_call.get("model") != "unknown":
            provider, _ = determine_provider_and_cost(
                latest_call["model"], 
                latest_call.get("prompt_tokens", 0), 
                latest_call.get("completion_tokens", 0)
            )
            return {
                "model": latest_call["model"],
                "provider": provider
            }
    
    return None

def _enhance_metadata_from_captured_calls(task: "Task"):
    """Enhance existing task metadata with information from captured calls."""
    # If model is unknown or missing, try to get from captured calls
    if (not task.metadata.get("model") or 
        task.metadata.get("model") == "unknown" or
        task.metadata.get("provider") == "Unknown"):
        
        model_info = _get_model_info_from_captured_calls(task)
        if model_info:
            # Update with better model information
            task.metadata.update({
                "model": model_info["model"],
                "provider": model_info["provider"]
            })
            
            # Recalculate cost with correct model
            _, corrected_cost = determine_provider_and_cost(
                model_info["model"],
                task.metadata.get("prompt_tokens", 0),
                task.metadata.get("completion_tokens", 0)
            )
            task.metadata["cost_usd"] = corrected_cost
            
 