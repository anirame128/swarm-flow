# SwarmFlow

A distributed multi-agent orchestration framework for building scalable AI workflows with comprehensive observability.

## 🚀 Features

- **Agent Orchestration**: Create complex workflows with multiple AI agents
- **Dependency Management**: Define task dependencies with automatic execution ordering
- **Retry Logic**: Built-in retry mechanisms for resilient agent execution
- **Observability**: OpenTelemetry integration for tracing and monitoring
- **Error Handling**: Graceful failure propagation and recovery
- **Real-time Monitoring**: Send task traces to your monitoring dashboard
- **Cycle Detection**: Automatic detection of circular dependencies
- **Production Ready**: Comprehensive error handling and logging

## 📦 Installation

```bash
pip install swarmflow
```

## 🎯 Quick Start

```python
from swarmflow import SwarmFlow, swarm_task

@swarm_task
def fetch_data():
    return "Some data from API"

@swarm_task
def process_data(data):
    return f"Processed: {data}"

@swarm_task
def display_result(result):
    print(f"Final result: {result}")

# Create workflow
flow = SwarmFlow(api_key="sk_abc123...")  # ✅ Pass your API key
flow.add(fetch_data)
flow.add(process_data).depends_on("process_data", "fetch_data")
flow.add(display_result).depends_on("display_result", "process_data")

# You can also specify multiple dependencies at once:
# flow.add(step4).depends_on("step4", "step2", "step3")

# Run workflow
flow.run()
```

## 🔧 Advanced Usage

### Multiple Dependencies
```python
@swarm_task
def step1():
    return "Step 1 completed"

@swarm_task
def step2():
    return "Step 2 completed"

@swarm_task
def step3():
    return "Step 3 completed"

@swarm_task
def final_step(step1_result, step2_result, step3_result):
    return f"Combined: {step1_result}, {step2_result}, {step3_result}"

# Create workflow with multiple dependencies
flow = SwarmFlow(api_key="sk_abc123...")  # ✅ Pass your API key
flow.add(step1)
flow.add(step2)
flow.add(step3)
flow.add(final_step).depends_on("final_step", "step1", "step2", "step3")
```

### Auto-Extracted Groq Metadata
```python
from groq import Groq

@swarm_task
def llm_task():
    # This will automatically extract metadata from Groq responses
    client = Groq()
    response = client.chat.completions.create(
        model="llama-3-70b",
        messages=[{"role": "user", "content": "Hello"}]
    )
    return response

# SwarmFlow automatically detects and extracts:
# - Model name (llama-3-70b, llama-4-scout-17b, etc.)
# - Provider (Groq)
# - Token usage (prompt + completion tokens)
# - Precise cost calculation (USD)
# - Timing metrics (queue, prompt, completion, total time)
# - All added to task.metadata automatically

# Example output with metadata:
# [SwarmFlow] Task: llm_task
#   ↳ Status: success
#   ↳ Duration: 1234 ms
#   ↳ Output: <Groq ChatCompletion object>
#   ↳ Metadata: {'agent': 'LLMProcessor', 'provider': 'Groq', 'model': 'llama-3-70b', 'tokens_used': 150, 'cost_usd': 0.000089, 'queue_time_s': 0.1, 'prompt_time_s': 0.5, 'completion_time_s': 0.8, 'total_time_s': 1.4}
```

### Retry Logic
```python
@swarm_task(retries=3)
def unreliable_task():
    # This task will retry up to 3 times on failure
    pass
```

### Custom Metadata
```python
@swarm_task
def custom_task():
    # You can add custom metadata to tasks
    task = custom_task._task
    task.metadata["custom_field"] = "custom_value"
    return "Task completed"
```

### Real-time Monitoring
SwarmFlow automatically sends task traces to the SwarmFlow backend service at `http://localhost:8000/api/trace` for real-time monitoring and analytics.

**Trace Structure:**
```json
{
  "id": "task-uuid",
  "run_id": "dag-run-uuid",  // Consistent across all tasks in the same DAG run
  "name": "task_name",
  "status": "success|failure|retrying|skipped",
  "duration_ms": 1234,
  "output": "task output",
  "metadata": {
    "agent": "LLMProcessor",
    "provider": "Groq",
    "model": "llama-3-70b",
    "tokens_used": 150,
    "cost_usd": 0.000089
  },
  "dependencies": ["dep1", "dep2"]
}
```

### Observability
SwarmFlow automatically provides:
- **Task execution traces** with OpenTelemetry
- **Performance metrics** (execution time, success rates)
- **Dependency visualization** and cycle detection
- **Error tracking** and failure propagation
- **Auto-extracted Groq metadata** (model, provider, token usage, precise cost calculation, timing metrics)

## 🏗️ Architecture

SwarmFlow is designed for **production multi-agent systems**:

```
User's Agent Functions → @swarm_task decorator → SwarmFlow Engine → Observability Dashboard
```

- **Lightweight**: Minimal overhead on your agent functions
- **Scalable**: Handles complex dependency graphs
- **Observable**: Real-time monitoring and debugging
- **Resilient**: Built-in retry logic and error handling

## 📊 Monitoring Dashboard

Get comprehensive insights into your multi-agent workflows:
- **Real-time execution** monitoring
- **Performance analytics** and optimization
- **Error tracking** and debugging
- **Cost analysis** for LLM usage (auto-calculated)
- **Workflow visualization** and dependency graphs
- **Groq metadata extraction** (comprehensive model support with timing and cost analytics)
- **DAG run tracking** with unique run_id for grouping and analytics

## 🚀 Deployment Configuration

### API Key Authentication
SwarmFlow supports API key authentication for secure trace reporting:

```python
# Option 1: Pass API key directly
flow = SwarmFlow(api_key="sk_abc123...")

# Option 2: Use environment variable
export SWARMFLOW_API_KEY="sk_abc123..."
flow = SwarmFlow()  # Automatically picks up from environment
```

### Backend Configuration
SwarmFlow automatically sends traces to `http://localhost:8000/api/trace`. For production deployment, update the backend URL in the SDK code to point to your centralized backend service.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](https://github.com/anirame128/swarmflow/blob/main/CONTRIBUTING.md).

## 📚 Documentation

For detailed documentation, visit: [https://github.com/anirame128/swarmflow](https://github.com/anirame128/swarmflow)

## 📄 License

MIT License - see [LICENSE](https://github.com/anirame128/swarmflow/blob/main/LICENSE) file for details.