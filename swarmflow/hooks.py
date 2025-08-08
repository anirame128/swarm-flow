# swarmflow/hooks.py
"""
SwarmFlow Hook Utilities

Plug-and-play orchestration logic using flow.memory.
These are parameterized factories that return valid hooks.
"""

def write_output_to_memory(key: str):
    """Writes task.output to flow.memory[key], auto-extracting content if present"""
    def hook(task):
        output = task.output

        # Try to auto-extract .choices[0].message.content if possible
        try:
            if hasattr(output, "choices") and len(output.choices) > 0:
                content = output.choices[0].message.content
                task.flow.memory[key] = content
            else:
                task.flow.memory[key] = output
        except Exception as e:
            task.flow.memory[key] = output  # Fallback to raw output

        return task
    return hook

def read_memory_into_arg(mem_key: str, arg_name: str):
    """Injects flow.memory[mem_key] into task.kwargs[arg_name]"""
    def hook(task):
        if mem_key in task.flow.memory:
            task.kwargs[arg_name] = task.flow.memory[mem_key]
        return task
    return hook

def skip_if_flag_set(flag_key: str):
    """Skips task if flow.memory[flag_key] is True"""
    def hook(task):
        if task.flow.memory.get(flag_key):
            raise RuntimeError(f"Task skipped due to memory flag '{flag_key}'")
        return task
    return hook

def log_input_output():
    """Logs task args/kwargs and output to console"""
    def before(task):
        return task

    def after(task):
        return task

    return before, after

def enforce_max_cost(max_usd: float):
    """Fails task if current task's cost exceeds max_usd"""
    def hook(task):
        current_cost = task.metadata.get("cost_usd", 0)
        if current_cost > max_usd:
            raise RuntimeError(f"Task cost ${current_cost:.4f} exceeded max ${max_usd}")
        return task
    return hook



def set_flag_on_failure(flag_key: str):
    def hook(task, error, final_retry=False):
        if final_retry:
            task.flow.memory[flag_key] = True
        return "FAIL"
    return hook

def append_output_to_memory_list(key: str):
    """Appends task.output to a list at flow.memory[key]"""
    def hook(task):
        if key not in task.flow.memory:
            task.flow.memory[key] = []
        task.flow.memory[key].append(task.output)
        return task
    return hook

def inject_retry_count_into_arg(arg_name: str):
    """Injects current retry count into task.kwargs[arg_name]"""
    def hook(task):
        task.kwargs[arg_name] = task.current_retry
        return task
    return hook 