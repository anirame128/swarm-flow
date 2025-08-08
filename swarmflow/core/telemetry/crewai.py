"""
SwarmFlow CrewAI Integration

Instrumentation for CrewAI multi-agent systems to capture metadata and attach to SwarmFlow tasks.
"""

import json
import requests
import time
import uuid
from opentelemetry import trace
from .base import (
    determine_provider_and_cost, 
    attach_metadata_to_task, 
    extract_model_name_from_llm,
    TRACE_ENDPOINT,
    _clean_metadata
)

# Global registry for individual CrewAI task calls
INDIVIDUAL_CREW_TASK_CALLS = []

def capture_individual_crew_task_call(task_description: str, model: str, 
                                    prompt_tokens: int, completion_tokens: int, cost_usd: float):
    """Capture individual CrewAI task call data."""
    # Get current SwarmFlow context
    from ..task import TASK_REGISTRY
    
    current_task_name = "unknown_task"
    if TASK_REGISTRY:
        # Find the task that contains "execute" or "workflow" in its name
        for task in reversed(TASK_REGISTRY):
            if "execute" in task.name.lower() or "workflow" in task.name.lower():
                current_task_name = task.name
                break
        # If no specific task found, use the current task
        if current_task_name == "unknown_task":
            current_task_name = TASK_REGISTRY[-1].name
    
    call_data = {
        "task_description": task_description[:100] + "..." if len(task_description) > 100 else task_description,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cost_usd": cost_usd,
        "timestamp": time.time(),
        "call_type": "crewai_task_call",
        "parent_task_name": current_task_name  # Store the parent SwarmFlow task
    }
    INDIVIDUAL_CREW_TASK_CALLS.append(call_data)
    


def get_individual_crew_task_calls():
    """Get all captured individual CrewAI task calls."""
    return INDIVIDUAL_CREW_TASK_CALLS.copy()

def clear_individual_crew_task_calls():
    """Clear the individual CrewAI task calls registry."""
    global INDIVIDUAL_CREW_TASK_CALLS
    INDIVIDUAL_CREW_TASK_CALLS = []

def log_individual_crew_traces(run_id: str, api_key: str | None, task_name: str):
    """
    Log individual CrewAI agent traces to the SwarmFlow backend.
    
    Args:
        run_id: Unique identifier for this DAG run
        api_key: API key for authentication
        task_name: Name of the parent SwarmFlow task (for dependency tracking)
    """
    global INDIVIDUAL_CREW_TASK_CALLS
    
    # Filter calls for this specific task
    task_calls = [call for call in INDIVIDUAL_CREW_TASK_CALLS if call.get("parent_task_name") == task_name]
    
    if not task_calls:
        return
    
    for i, call_data in enumerate(task_calls):
        # Create a unique trace ID for this individual call
        trace_id = str(uuid.uuid4())
        
        # Create trace payload for individual CrewAI agent call
        crew_trace_payload = {
            "id": trace_id,
            "run_id": run_id,
            "name": f"crewai_{call_data['task_description'].replace(' ', '_').lower()}",
            "status": "success",
            "duration_ms": 0,  # Individual calls don't have separate timing
            "output": f"Completed {call_data['task_description']}",
            "metadata": _clean_metadata({
                "agent": "CrewAI_Agent", 
                "provider": determine_provider_and_cost(call_data['model'], 0, 0)[0],  # Just get provider name
                "model": call_data['model'],
                "tokens_used": call_data['total_tokens'],
                "prompt_tokens": call_data['prompt_tokens'],
                "completion_tokens": call_data['completion_tokens'],
                "cost_usd": call_data['cost_usd'],
                "call_type": call_data['call_type'],
                "individual_call": True
            }),
            "retry_count": 0,
            "dependencies": [task_name],  # Depend on the parent SwarmFlow task
            "flow_memory": {},
            "flow_policy": {}
        }
        
        try:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["x-api-key"] = api_key
                
                res = requests.post(
                    TRACE_ENDPOINT, 
                    headers=headers, 
                    data=json.dumps(crew_trace_payload)
                )
        except Exception as e:
            pass  # Silently handle trace upload failures

def check_and_send_individual_traces(run_id: str, api_key: str | None, task_name: str):
    """Check if this task has pending individual CrewAI traces and send them."""
    pending_crew_calls = [call for call in INDIVIDUAL_CREW_TASK_CALLS if call.get("parent_task_name") == task_name]
    if pending_crew_calls:
        log_individual_crew_traces(run_id, api_key, task_name)
        # Clear only the traces for this task
        INDIVIDUAL_CREW_TASK_CALLS[:] = [call for call in INDIVIDUAL_CREW_TASK_CALLS if call.get("parent_task_name") != task_name]

def instrument_crewai():
    """Instrument CrewAI to capture metadata and attach to SwarmFlow tasks."""
    try:
        from crewai import Crew, Agent, Task
        from crewai.llm import LLM as CrewAILLM
        
        # Check if already patched
        if getattr(Crew, "_swarmflow_patched", False):
            return
        
        # Store original methods
        original_kickoff = Crew.kickoff
        original_agent_execute_task = Agent.execute_task
        original_llm_call = CrewAILLM.call
        
        def traced_crew_kickoff(self, *args, **kwargs):
            """Trace CrewAI crew execution to capture metadata."""
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span("crew.kickoff") as span:
                # Execute the original crew kickoff
                result = original_kickoff(self, *args, **kwargs)
                
                # Extract metadata from CrewOutput
                if hasattr(result, 'token_usage') and result.token_usage:
                    
                    # Extract crew-level token usage
                    crew_token_usage = result.token_usage
                    
                    # Handle different token usage formats
                    if hasattr(crew_token_usage, 'get'):
                        # Dictionary format
                        prompt_tokens = crew_token_usage.get("prompt_tokens", 0)
                        completion_tokens = crew_token_usage.get("completion_tokens", 0)
                        total_tokens = crew_token_usage.get("total_tokens", 0)
                    else:
                        # UsageMetrics object format
                        prompt_tokens = getattr(crew_token_usage, "prompt_tokens", 0)
                        completion_tokens = getattr(crew_token_usage, "completion_tokens", 0)
                        total_tokens = getattr(crew_token_usage, "total_tokens", 0)
                    
                    # Get model name from crew's LLM
                    model_name = "groq/llama3-8b-8192"  # Default
                    if hasattr(self, "llm"):
                        model_name = extract_model_name_from_llm(self.llm)
                    
                    provider, cost_usd = determine_provider_and_cost(model_name, prompt_tokens, completion_tokens)
                    
                    # Attach metadata to the appropriate SwarmFlow task
                    from ..task import TASK_REGISTRY
                    
                    # Find the task that contains "execute" or "workflow" in its name, or use the current task
                    target_task = None
                    for task in reversed(TASK_REGISTRY):
                        if "execute" in task.name.lower() or "workflow" in task.name.lower():
                            target_task = task
                            break
                    
                    # If no specific task found, use the current task
                    if not target_task:
                        target_task = TASK_REGISTRY[-1] if TASK_REGISTRY else None
                    
                    if target_task:
                        attach_metadata_to_task(
                            model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd,
                            agent_type="CrewAIProcessor",
                            additional_metadata={"crew_level": True}
                        )
                    
                    # Set span attributes
                    span.set_attribute("crew.model_name", model_name)
                    span.set_attribute("crew.prompt_tokens", prompt_tokens)
                    span.set_attribute("crew.completion_tokens", completion_tokens)
                    span.set_attribute("crew.total_tokens", total_tokens)
                    span.set_attribute("crew.cost_usd", cost_usd)
                
                # Extract individual task token usage from tasks_output
                if hasattr(result, 'tasks_output') and result.tasks_output:
                    
                    for i, task_output in enumerate(result.tasks_output):
                        if hasattr(task_output, 'token_usage') and task_output.token_usage:
                            task_token_usage = task_output.token_usage
                            task_prompt_tokens = task_token_usage.get("prompt_tokens", 0)
                            task_completion_tokens = task_token_usage.get("completion_tokens", 0)
                            task_total_tokens = task_token_usage.get("total_tokens", 0)
                            
                            # Get task description
                            task_description = getattr(task_output, 'description', f'Task {i+1}')
                            
                            _, task_cost_usd = determine_provider_and_cost(model_name, task_prompt_tokens, task_completion_tokens)
                            
                            # Capture individual task call
                            capture_individual_crew_task_call(
                                task_description=task_description,
                                model=model_name,
                                prompt_tokens=task_prompt_tokens,
                                completion_tokens=task_completion_tokens,
                                cost_usd=task_cost_usd
                            )
                            

                            
                            # Set span attributes for individual task
                            span.set_attribute(f"task.{i+1}.description", task_description)
                            span.set_attribute(f"task.{i+1}.model_name", model_name)
                            span.set_attribute(f"task.{i+1}.prompt_tokens", task_prompt_tokens)
                            span.set_attribute(f"task.{i+1}.completion_tokens", task_completion_tokens)
                            span.set_attribute(f"task.{i+1}.total_tokens", task_total_tokens)
                            span.set_attribute(f"task.{i+1}.cost_usd", task_cost_usd)
                
                # Extract individual agent metrics BEFORE aggregation
                individual_agent_metrics = []
                for i, agent in enumerate(self.agents):
                    if hasattr(agent, '_token_process'):
                        agent_metrics = agent._token_process.get_summary()
                        agent_info = {
                            'agent_index': i,
                            'agent_role': getattr(agent, 'role', f'Agent_{i}'),
                            'total_tokens': agent_metrics.total_tokens,
                            'prompt_tokens': agent_metrics.prompt_tokens,
                            'completion_tokens': agent_metrics.completion_tokens,
                            'cached_prompt_tokens': agent_metrics.cached_prompt_tokens,
                            'successful_requests': agent_metrics.successful_requests
                        }
                        individual_agent_metrics.append(agent_info)
                
                # Store individual agent metrics in SwarmFlow tracking
                for agent_info in individual_agent_metrics:
                    _, agent_cost_usd = determine_provider_and_cost(model_name, agent_info['prompt_tokens'], agent_info['completion_tokens'])
                    
                    capture_individual_crew_task_call(
                        task_description=f"Agent: {agent_info['agent_role']}",
                        model=model_name,
                        prompt_tokens=agent_info['prompt_tokens'],
                        completion_tokens=agent_info['completion_tokens'],
                        cost_usd=agent_cost_usd
                    )

                
                # Extract aggregated usage_metrics from crew object (CrewAI's built-in metrics)
                if hasattr(self, 'usage_metrics') and self.usage_metrics:
                    usage_metrics = self.usage_metrics
                    
                    # Extract metrics from UsageMetrics object
                    if hasattr(usage_metrics, 'total_tokens'):
                        total_tokens = usage_metrics.total_tokens
                        prompt_tokens = getattr(usage_metrics, 'prompt_tokens', 0)
                        completion_tokens = getattr(usage_metrics, 'completion_tokens', 0)
                        _, cost_usd = determine_provider_and_cost(model_name, prompt_tokens, completion_tokens)
                        

                        
                        # Note: Aggregate metrics are already captured at crew level,
                        # no need to store as individual call
                        
                        # Set span attributes
                        span.set_attribute("crew.usage_metrics.total_tokens", total_tokens)
                        span.set_attribute("crew.usage_metrics.prompt_tokens", prompt_tokens)
                        span.set_attribute("crew.usage_metrics.completion_tokens", completion_tokens)
                        span.set_attribute("crew.usage_metrics.cost_usd", cost_usd)
                        
                        # Also extract individual task metrics if available
                        if hasattr(usage_metrics, 'tasks') and usage_metrics.tasks:
                            
                            for i, task_metric in enumerate(usage_metrics.tasks):
                                if hasattr(task_metric, 'total_tokens'):
                                    task_total = task_metric.total_tokens
                                    task_prompt = getattr(task_metric, 'prompt_tokens', 0)
                                    task_completion = getattr(task_metric, 'completion_tokens', 0)
                                    _, task_cost = determine_provider_and_cost(model_name, task_prompt, task_completion)
                                    task_name = getattr(task_metric, 'task_name', f'Task {i+1}')
                                    
                                    capture_individual_crew_task_call(
                                        task_description=f"Individual Task: {task_name}",
                                        model=model_name,
                                        prompt_tokens=task_prompt,
                                        completion_tokens=task_completion,
                                        cost_usd=task_cost
                                    )
                                    

                                    
                                    # Set span attributes for individual task metric
                                    span.set_attribute(f"task_metric.{i+1}.name", task_name)
                                    span.set_attribute(f"task_metric.{i+1}.total_tokens", task_total)
                                    span.set_attribute(f"task_metric.{i+1}.prompt_tokens", task_prompt)
                                    span.set_attribute(f"task_metric.{i+1}.completion_tokens", task_completion)
                                    span.set_attribute(f"task_metric.{i+1}.cost_usd", task_cost)

                
                return result
        
        def traced_agent_execute_task(self, task, *args, **kwargs):
            """Trace individual agent task execution."""
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(f"agent.execute_task.{self.role}") as span:
                # Set agent-specific attributes
                span.set_attribute("agent.role", self.role)
                span.set_attribute("agent.goal", self.goal)
                span.set_attribute("task.description", task.description)
                
                # Execute the original agent task execution
                result = original_agent_execute_task(self, task, *args, **kwargs)
                
                # Extract token usage from the result if available
                if hasattr(result, "token_usage") and result.token_usage:
                    token_usage = result.token_usage
                    prompt_tokens = token_usage.get("prompt_tokens", 0)
                    completion_tokens = token_usage.get("completion_tokens", 0)
                    total_tokens = token_usage.get("total_tokens", 0)
                    
                    # Get model name from agent's LLM
                    model_name = "gpt-4o-mini"  # Default
                    if hasattr(self, "llm"):
                        model_name = extract_model_name_from_llm(self.llm)
                    
                    provider, cost_usd = determine_provider_and_cost(model_name, prompt_tokens, completion_tokens)
                    
                    # Attach metadata to current SwarmFlow task for individual agent
                    attach_metadata_to_task(
                        model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd,
                        agent_type="CrewAIAgent",
                        additional_metadata={
                            "agent_role": self.role,
                            "task_description": task.description,
                        }
                    )
                    
                    # Set span attributes for individual agent call
                    span.set_attribute("llm.model_name", model_name)
                    span.set_attribute("llm.provider", provider)
                    span.set_attribute("llm.prompt_tokens", prompt_tokens)
                    span.set_attribute("llm.completion_tokens", completion_tokens)
                    span.set_attribute("llm.total_tokens", total_tokens)
                    span.set_attribute("llm.cost_usd", cost_usd)
                    

                
                return result
        
        def traced_llm_call(self, *args, **kwargs):
            """Trace individual LLM calls to capture token usage."""
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span("llm.individual_call") as span:
                # Execute the original LLM call
                result = original_llm_call(self, *args, **kwargs)
                
                # Extract token usage from the result
                if hasattr(result, "token_usage") and result.token_usage:
                    token_usage = result.token_usage
                    prompt_tokens = token_usage.get("prompt_tokens", 0)
                    completion_tokens = token_usage.get("completion_tokens", 0)
                    total_tokens = token_usage.get("total_tokens", 0)
                    
                    # Get model name
                    model_name = extract_model_name_from_llm(self)
                    
                    provider, cost_usd = determine_provider_and_cost(model_name, prompt_tokens, completion_tokens)
                    
                    # Attach metadata to current SwarmFlow task for individual LLM call
                    attach_metadata_to_task(model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd, agent_type="CrewAILLM")
                    
                    # Set span attributes
                    span.set_attribute("llm.model_name", model_name)
                    span.set_attribute("llm.provider", provider)
                    span.set_attribute("llm.prompt_tokens", prompt_tokens)
                    span.set_attribute("llm.completion_tokens", completion_tokens)
                    span.set_attribute("llm.total_tokens", total_tokens)
                    span.set_attribute("llm.cost_usd", cost_usd)
                    

                
                return result
        
        # Apply patches
        Crew.kickoff = traced_crew_kickoff
        Agent.execute_task = traced_agent_execute_task
        CrewAILLM.call = traced_llm_call
        
        # Mark as patched
        Crew._swarmflow_patched = True
        
    except ImportError:
        pass
    except Exception as e:
        pass
