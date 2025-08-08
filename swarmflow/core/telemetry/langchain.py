"""
SwarmFlow LangChain Integration

Instrumentation for LangChain LLM calls to capture metadata and attach to SwarmFlow tasks.
"""

from opentelemetry import trace
from .base import (
    extract_token_usage, 
    determine_provider_and_cost, 
    attach_metadata_to_task
)

def instrument_langchain_llm():
    """Instrument LangChain LLM calls to capture metadata and attach to SwarmFlow tasks."""
    try:
        from langchain_core.language_models.base import BaseLanguageModel
        
        # Check if already patched
        if getattr(BaseLanguageModel, "_swarmflow_patched", False):
            return
        
        # Store original methods
        original_invoke = BaseLanguageModel.invoke
        original_predict = getattr(BaseLanguageModel, "predict", None)
        original_predict_messages = getattr(BaseLanguageModel, "predict_messages", None)
        original_ainvoke = getattr(BaseLanguageModel, "ainvoke", None)
        original_apredict = getattr(BaseLanguageModel, "apredict", None)
        original_apredict_messages = getattr(BaseLanguageModel, "apredict_messages", None)
        
        def extract_and_attach_metadata(result):
            """Extract LLM metadata and attach to current SwarmFlow task."""
            token_data = extract_token_usage(result)
            if not token_data:
                return None, 0, 0, 0, 0
            
            model_name, prompt_tokens, completion_tokens, total_tokens = token_data
            provider, cost_usd = determine_provider_and_cost(model_name, prompt_tokens, completion_tokens)
            
            attach_metadata_to_task(model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd)
            
            return model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd
        
        def set_span_attributes(span, model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd):
            """Set standard LLM span attributes."""
            if model_name:
                span.set_attribute("llm.model_name", model_name)
                span.set_attribute("llm.prompt_tokens", prompt_tokens)
                span.set_attribute("llm.completion_tokens", completion_tokens)
                span.set_attribute("llm.total_tokens", total_tokens)
                span.set_attribute("llm.cost_usd", cost_usd)
        
        def traced_invoke(self, input, *args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span("llm.invoke") as span:
                # Execute the original LLM call
                result = original_invoke(self, input, *args, **kwargs)
                
                # Extract and attach metadata
                model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd = extract_and_attach_metadata(result)
                
                # Set span attributes
                set_span_attributes(span, model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd)
                
                return result
        
        def traced_predict(self, *args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span("llm.predict") as span:
                # Execute the original LLM call
                result = original_predict(self, *args, **kwargs)
                
                # Extract and attach metadata
                model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd = extract_and_attach_metadata(result)
                
                # Set span attributes
                set_span_attributes(span, model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd)
                
                return result
        
        def traced_predict_messages(self, *args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span("llm.predict_messages") as span:
                # Execute the original LLM call
                result = original_predict_messages(self, *args, **kwargs)
                
                # Extract and attach metadata
                model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd = extract_and_attach_metadata(result)
                
                # Set span attributes
                set_span_attributes(span, model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd)
                
                return result
        
        async def traced_ainvoke(self, input, *args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span("llm.ainvoke") as span:
                # Execute the original LLM call
                result = await original_ainvoke(self, input, *args, **kwargs)
                
                # Extract and attach metadata
                model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd = extract_and_attach_metadata(result)
                
                # Set span attributes
                set_span_attributes(span, model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd)
                
                return result
        
        async def traced_apredict(self, *args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span("llm.apredict") as span:
                # Execute the original LLM call
                result = await original_apredict(self, *args, **kwargs)
                
                # Extract and attach metadata
                model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd = extract_and_attach_metadata(result)
                
                # Set span attributes
                set_span_attributes(span, model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd)
                
                return result
        
        async def traced_apredict_messages(self, *args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span("llm.apredict_messages") as span:
                # Execute the original LLM call
                result = await original_apredict_messages(self, *args, **kwargs)
                
                # Extract and attach metadata
                model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd = extract_and_attach_metadata(result)
                
                # Set span attributes
                set_span_attributes(span, model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd)
                
                return result
        
        # Apply patches to BaseLanguageModel
        BaseLanguageModel.invoke = traced_invoke
        if original_predict:
            BaseLanguageModel.predict = traced_predict
        if original_predict_messages:
            BaseLanguageModel.predict_messages = traced_predict_messages
        if original_ainvoke:
            BaseLanguageModel.ainvoke = traced_ainvoke
        if original_apredict:
            BaseLanguageModel.apredict = traced_apredict
        if original_apredict_messages:
            BaseLanguageModel.apredict_messages = traced_apredict_messages
        
        # Mark as patched
        BaseLanguageModel._swarmflow_patched = True
        
    except ImportError:
        pass
    except Exception as e:
        pass
