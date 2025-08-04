# SwarmFlow

A distributed multi-agent orchestration framework for building scalable AI workflows with comprehensive observability.

## 🚀 Features

- **Dead-Simple API**: Minimal `@swarm_task` decorator and `run()` function
- **Auto-Dependency Inference**: Dependencies automatically inferred from function parameters
- **Agent Orchestration**: Create complex workflows with multiple AI agents
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
from swarmflow import swarm_task, run

@swarm_task
def fetch_data():
    return "Some data from API"

@swarm_task
def process_data(fetch_data):
    return f"Processed: {fetch_data}"

@swarm_task
def display_result(process_data):
    print(f"Final result: {process_data}")

# Run workflow - that's it!
run()
```

**That's it!** No complex setup, no manual dependency management. SwarmFlow automatically:
- ✅ Registers your tasks
- ✅ Infers dependencies from function parameters
- ✅ Executes in the correct order
- ✅ Handles retries and errors
- ✅ Sends traces to your dashboard

## 🔧 Advanced Usage

### Retry Logic
```python
@swarm_task(retries=3)
def unreliable_task():
    # This task will retry up to 3 times on failure
    pass
```

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
def final_step(step1, step2, step3):
    # Dependencies automatically inferred from parameter names
    return f"Combined: {step1}, {step2}, {step3}"

run()
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

### API Key Configuration
SwarmFlow automatically handles API keys with Martian-style simplicity:

```python
# Option 1: Set environment variable
export SWARMFLOW_API_KEY="sk_abc123..."
run()  # Automatically uses key from environment

# Option 2: Pass directly
run(api_key="sk_abc123...")

# Option 3: No key (logs warning but continues)
run()  # Shows warning but executes normally
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

SwarmFlow is designed for **production multi-agent systems** with dead-simple usage:

```
User's Agent Functions → @swarm_task decorator → run() → Observability Dashboard
```

- **Minimal**: Just decorator + run function
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
# Option 1: Environment variable (recommended)
export SWARMFLOW_API_KEY="sk_abc123..."
run()  # Automatically picks up from environment

# Option 2: Pass directly
run(api_key="sk_abc123...")

# Option 3: No authentication (logs warning but continues)
run()  # Shows warning but executes normally
```

### Backend Configuration
SwarmFlow automatically sends traces to `http://localhost:8000/api/trace`. For production deployment, update the backend URL in the SDK code to point to your centralized backend service.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](https://github.com/anirame128/swarmflow/blob/main/CONTRIBUTING.md).

## 📚 Documentation

For detailed documentation, visit: [https://github.com/anirame128/swarmflow](https://github.com/anirame128/swarmflow)

## 📄 License

### SDK License
The SwarmFlow SDK is licensed under the MIT License - see [LICENSE](https://github.com/anirame128/swarmflow/blob/main/LICENSE) file for details.

### Backend Services
SwarmFlow backend services, dashboard, and infrastructure require separate service agreements and API keys. The SDK is designed to work with official SwarmFlow backend services only.

**Why this model?**
- ✅ **Free SDK**: Developers can use the SDK without restrictions
- ✅ **Paid Services**: Backend services and dashboard require API keys
- ✅ **Industry Standard**: Follows the same model as Google Maps, Stripe, AWS SDKs
- ✅ **Developer Friendly**: Maximizes adoption while protecting your business model