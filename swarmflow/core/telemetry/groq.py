"""
SwarmFlow Native Groq SDK Integration

Instrumentation for native Groq SDK calls to capture metadata and attach to SwarmFlow tasks.
"""

from opentelemetry import trace
from .base import (
    determine_provider_and_cost, 
    attach_metadata_to_task
)

def instrument_groq_native():
    """Instrument native Groq SDK calls to capture metadata."""
    try:
        import groq
        
        # Check if already patched
        if getattr(groq, "_swarmflow_patched", False):
            return
        
        # Find the ChatCompletion class
        try:
            from groq.resources.chat import Completions
            original_create = Completions.create
        except ImportError:
            return
        
        def traced_groq_create(self, *args, **kwargs):
            """Trace Groq chat.completions.create calls."""
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span("groq.chat.completions.create") as span:
                # Execute the original API call
                result = original_create(self, *args, **kwargs)
                
                # Extract metadata from response
                if hasattr(result, 'usage') and result.usage:
                    usage = result.usage
                    prompt_tokens = getattr(usage, 'prompt_tokens', 0)
                    completion_tokens = getattr(usage, 'completion_tokens', 0)
                    total_tokens = getattr(usage, 'total_tokens', 0)
                    
                    # Get model name from the request
                    model_name = "unknown"
                    if 'model' in kwargs:
                        model_name = kwargs['model']
                    
                    # Add groq/ prefix if not present
                    if not model_name.startswith('groq/') and model_name != 'unknown':
                        model_name = f"groq/{model_name}"
                    
                    provider, cost_usd = determine_provider_and_cost(model_name, prompt_tokens, completion_tokens)
                    
                    # Attach metadata to current SwarmFlow task
                    attach_metadata_to_task(
                        model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd,
                        agent_type="GroqNative"
                    )
                    
                    # Set span attributes
                    span.set_attribute("groq.model_name", model_name)
                    span.set_attribute("groq.prompt_tokens", prompt_tokens)
                    span.set_attribute("groq.completion_tokens", completion_tokens)
                    span.set_attribute("groq.total_tokens", total_tokens)
                    span.set_attribute("groq.cost_usd", cost_usd)
                
                return result
        
        # Patch the method on the class
        Completions.create = traced_groq_create
        
        # Mark as patched
        groq._swarmflow_patched = True
        
    except ImportError:
        pass
    except Exception as e:
        pass
