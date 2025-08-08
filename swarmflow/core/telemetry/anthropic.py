"""
SwarmFlow Native Anthropic SDK Integration

Instrumentation for native Anthropic SDK calls to capture metadata and attach to SwarmFlow tasks.
"""

from opentelemetry import trace
from .base import (
    determine_provider_and_cost, 
    attach_metadata_to_task
)

def instrument_anthropic_native():
    """Instrument native Anthropic SDK calls to capture metadata."""
    try:
        import anthropic
        
        # Check if already patched
        if getattr(anthropic, "_swarmflow_patched", False):
            return
        
        # Find the Messages class
        try:
            from anthropic.resources.messages import Messages
            original_create = Messages.create
        except ImportError:
            return
        
        def traced_anthropic_create(self, *args, **kwargs):
            """Trace Anthropic messages.create calls."""
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span("anthropic.messages.create") as span:
                # Execute the original API call
                result = original_create(self, *args, **kwargs)
                
                # Extract metadata from response
                if hasattr(result, 'usage') and result.usage:
                    usage = result.usage
                    prompt_tokens = getattr(usage, 'input_tokens', 0)
                    completion_tokens = getattr(usage, 'output_tokens', 0)
                    total_tokens = prompt_tokens + completion_tokens
                    
                    # Get model name from the request
                    model_name = "unknown"
                    if 'model' in kwargs:
                        model_name = kwargs['model']
                    
                    # Add anthropic/ prefix if not present
                    if not model_name.startswith('anthropic/') and model_name != 'unknown':
                        model_name = f"anthropic/{model_name}"
                    
                    provider, cost_usd = determine_provider_and_cost(model_name, prompt_tokens, completion_tokens)
                    
                    # Attach metadata to current SwarmFlow task
                    attach_metadata_to_task(
                        model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd,
                        agent_type="AnthropicNative"
                    )
                    
                    # Set span attributes
                    span.set_attribute("anthropic.model_name", model_name)
                    span.set_attribute("anthropic.prompt_tokens", prompt_tokens)
                    span.set_attribute("anthropic.completion_tokens", completion_tokens)
                    span.set_attribute("anthropic.total_tokens", total_tokens)
                    span.set_attribute("anthropic.cost_usd", cost_usd)
                
                return result
        
        # Patch the method on the class
        Messages.create = traced_anthropic_create
        
        # Mark as patched
        anthropic._swarmflow_patched = True
        
    except ImportError:
        pass
    except Exception as e:
        pass
