"""
SwarmFlow Telemetry

Modular telemetry system for multi-agent framework instrumentation.
"""

# Import core telemetry functions
from .base import (
    setup_tracer,
    log_trace,
    determine_provider_and_cost,
    extract_token_usage,
    attach_metadata_to_task,
    extract_model_name_from_llm
)

# Import integration modules
from .langchain import instrument_langchain_llm
from .crewai import (
    instrument_crewai,
    capture_individual_crew_task_call,
    get_individual_crew_task_calls,
    clear_individual_crew_task_calls
)

# Re-export for backward compatibility
__all__ = [
    # Core utilities
    "setup_tracer",
    "log_trace", 
    
    # Shared utility functions
    "determine_provider_and_cost",
    "extract_token_usage", 
    "attach_metadata_to_task",
    "extract_model_name_from_llm",
    
    # LangChain integration
    "instrument_langchain_llm",
    
    # CrewAI integration
    "instrument_crewai",
    "capture_individual_crew_task_call",
    "get_individual_crew_task_calls", 
    "clear_individual_crew_task_calls"
]

def initialize_telemetry():
    """Initialize all telemetry integrations."""
    # Set up base tracer
    setup_tracer()
    
    # Initialize integrations
    instrument_langchain_llm()
    instrument_crewai()
    
    # Initialize native SDK instrumentations
    from .groq import instrument_groq_native
    from .openai import instrument_openai_native
    from .anthropic import instrument_anthropic_native
    
    instrument_groq_native()
    instrument_openai_native()
    instrument_anthropic_native()

# Note: Telemetry is now initialized in runner.py to avoid double initialization
# This ensures telemetry is only initialized once per execution
