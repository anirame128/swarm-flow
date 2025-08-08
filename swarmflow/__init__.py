from .core.task import swarm_task
from .core.runner import run
from .core.flow import SwarmFlow
from .hooks import (
    write_output_to_memory,
    read_memory_into_arg,
    skip_if_flag_set,
    log_input_output,
    enforce_max_cost,
    set_flag_on_failure,
    append_output_to_memory_list,
    inject_retry_count_into_arg,
)

# Initialize LangChain instrumentation automatically
try:
    from .core.telemetry import instrument_langchain_llm
    instrument_langchain_llm()
except Exception as e:
    print(f"[SwarmFlow] ⚠️ Failed to initialize LangChain instrumentation: {e}")

__all__ = [
    "swarm_task", 
    "run", 
    "SwarmFlow",
    "write_output_to_memory",
    "read_memory_into_arg", 
    "skip_if_flag_set",
    "log_input_output",
    "enforce_max_cost",
    "set_flag_on_failure",
    "append_output_to_memory_list",
    "inject_retry_count_into_arg",
]
