"""
SwarmFlow Telemetry (Legacy Compatibility)

This file provides backward compatibility for existing imports.
All telemetry functionality has been moved to the telemetry/ module.
"""

# Import everything from the new modular telemetry system
from .telemetry import *

# Legacy imports for backward compatibility
from .telemetry.base import (
    setup_tracer,
    log_trace
)

from .telemetry.langchain import instrument_langchain_llm
from .telemetry.crewai import (
    instrument_crewai,
    capture_individual_crew_task_call,
    get_individual_crew_task_calls,
    clear_individual_crew_task_calls
)

# Expose legacy function names for backward compatibility
_determine_provider_and_cost = determine_provider_and_cost
_extract_token_usage = extract_token_usage
_attach_metadata_to_task = attach_metadata_to_task
_extract_model_name_from_llm = extract_model_name_from_llm

# Legacy compatibility for direct imports
def log_individual_crew_traces(*args, **kwargs):
    """Legacy function - delegates to new modular system."""
    from .telemetry.crewai import log_individual_crew_traces
    return log_individual_crew_traces(*args, **kwargs)
