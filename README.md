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
flow = SwarmFlow()
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
flow = SwarmFlow()
flow.add(step1)
flow.add(step2)
flow.add(step3)
flow.add(final_step).depends_on("final_step", "step1", "step2", "step3")
```

### Retry Logic
```python
@swarm_task(retries=3)
def unreliable_task():
    # This task will retry up to 3 times on failure
    pass
```

### Real-time Monitoring
SwarmFlow automatically sends task traces to the SwarmFlow backend service at `http://localhost:8000/api/trace` for real-time monitoring and analytics.

### Observability
SwarmFlow automatically provides:
- **Task execution traces** with OpenTelemetry
- **Performance metrics** (execution time, success rates)
- **Dependency visualization** and cycle detection
- **Error tracking** and failure propagation

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
- **Cost analysis** for LLM usage
- **Workflow visualization** and dependency graphs

## 🚀 Deployment Configuration

SwarmFlow automatically sends traces to `http://localhost:8000/api/trace`. For production deployment, update the backend URL in the SDK code to point to your centralized backend service.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](https://github.com/anirame128/swarmflow/blob/main/CONTRIBUTING.md).

## 📚 Documentation

For detailed documentation, visit: [https://github.com/anirame128/swarmflow](https://github.com/anirame128/swarmflow)

## 📄 License

MIT License - see [LICENSE](https://github.com/anirame128/swarmflow/blob/main/LICENSE) file for details.