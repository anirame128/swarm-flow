# SwarmFlow

A distributed multi-agent orchestration framework for building scalable AI workflows.

## Features

- **Agent Orchestration**: Create complex workflows with multiple AI agents
- **Dependency Management**: Define task dependencies with automatic execution ordering
- **Retry Logic**: Built-in retry mechanisms for resilient agent execution
- **Observability**: OpenTelemetry integration for tracing and monitoring
- **Error Handling**: Graceful failure propagation and recovery
- **Real-time Monitoring**: Send task traces to your monitoring dashboard

## Installation

```bash
pip install swarmflow
```

## Quick Start

```python
from swarmflow.core.flow import SwarmFlow
from swarmflow.core.decorator import swarm_task

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

# Run workflow
flow.run()
```

## Advanced Usage

### Retry Logic
```python
@swarm_task(retries=3)
def unreliable_task():
    # This task will retry up to 3 times on failure
    pass
```

### Real-time Monitoring
```bash
export API_URL="https://your-dashboard.com"
python your_workflow.py
```

## Documentation

For detailed documentation, visit: [https://github.com/anirame128/swarmflow](https://github.com/anirame128/swarmflow)

## License

MIT License - see LICENSE file for details.