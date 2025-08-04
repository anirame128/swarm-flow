# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.4] - 2025-01-04

### Fixed
- **Run status update bug**: Added missing `_finalize_run_status()` functionality to the new refactored API
  - Run status now properly updates from "running" to "completed"/"failed"/"partial" in database
  - Added PATCH request to `/api/runs/update-status` endpoint
  - Includes proper API key authentication and error handling
  - Same logic as old API: "completed" if all tasks succeed, "failed" if any fail, "partial" otherwise

## [0.3.3] - 2025-01-04

### Changed
- **Major API Refactoring**: Completely redesigned SwarmFlow for Martian-style simplicity
- **Minimal API**: Replaced complex `SwarmFlow` class with dead-simple `@swarm_task` and `run()` functions
- **Auto-dependency inference**: Dependencies are now automatically inferred from function parameter names
- **Global task registry**: Tasks are automatically registered when decorated with `@swarm_task`
- **Smart API key handling**: Automatically uses `SWARMFLOW_API_KEY` from environment, with graceful fallback

### Added
- **New minimal API**: `from swarmflow import swarm_task, run`
- **Parameter-based dependencies**: Function parameters automatically become dependencies
- **Martian-style simplicity**: No manual dependency management required
- **Environment variable support**: `SWARMFLOW_API_KEY` automatically detected from `.env`

### Removed
- **SwarmFlow class**: Replaced with functional `run()` approach
- **Manual dependency management**: No more `.depends_on()` calls needed
- **Complex setup**: Simplified to just decorator + run

### Example of new API:
```python
from swarmflow import swarm_task, run

@swarm_task
def seed():
    return "Summarize this: SwarmFlow is awesome"

@swarm_task(retries=1)
def summarize(seed):
    return ask_llm(seed)

@swarm_task
def extract_summary(summarize):
    return summarize.choices[0].message.content

run()  # That's it!
```

## [0.3.2] - 2025-01-02

### Fixed
- **Task initialization bug**: Fixed crash when accessing `task.current_retry` for skipped tasks or tasks with no retries
  - Added safe fallback: `getattr(task, "current_retry", 0)` in `_log()` method
  - Added `self.current_retry = 0` initialization in `Task.__init__()` constructor
  - Ensures all tasks have consistent retry tracking regardless of execution path

## [0.3.1] - 2025-01-02

### Fixed
- **Retry count tracking**: Fixed retry count logic to accurately report attempts taken vs retries used
  - For successful tasks: reports attempts taken to succeed
  - For failed tasks: reports total retries used
  - Previously always showed 0 due to logging only after retry loop completion

## [0.3.0] - 2025-01-02

### Added
- **Run status persistence**: Added `_finalize_run_status()` method to compute and persist overall DAG run status
- **Retry count tracking**: Each task trace now includes `retry_count` for better debugging and monitoring
- **Enhanced run-level status**: Automatic computation of run status:
  - `"completed"` if all tasks are successful
  - `"failed"` if any task fails
  - `"partial"` if some succeed and some fail/skipped
- **Run status API integration**: PATCH requests to `/api/runs/update-status` to persist run-level status
- **Resumption preparation**: Foundation for future workflow resumption capabilities

### Changed
- **Enhanced task execution**: Added `current_retry` tracking during retry loops
- **Improved trace payload**: Trace payloads now include retry count for each task execution

## [0.2.0] - 2025-01-02

### Added
- **API key authentication**: Added support for API key authentication in trace reporting
- **Environment variable support**: Can use `SWARMFLOW_API_KEY` environment variable as fallback
- **Secure trace reporting**: All POST requests to backend now include `x-api-key` header when API key is provided

## [0.1.9] - 2025-01-02

### Added
- **DAG run tracking**: Added unique `run_id` that's consistent across all tasks in a single DAG run
- **Enhanced trace structure**: Trace payloads now include `run_id` for better grouping and analytics

## [0.1.8] - 2025-01-02

### Fixed
- **Metadata serialization**: Added `_clean_metadata()` method to remove None values from metadata before JSON serialization
- **Trace payload**: Fixed metadata preservation in trace payloads sent to backend

## [0.1.7] - 2025-01-02

### Fixed
- **JSON serialization**: Fixed trace payload serialization to handle Groq ChatCompletion objects properly
- **Output extraction**: Added proper extraction of message content from LLM response objects

## [0.1.6] - 2025-01-02

### Fixed
- **Groq attribute access**: Fixed usage object attribute access to use `getattr()` instead of dict-style access
- **Model name normalization**: Added proper model name normalization to handle provider prefixes (e.g., "meta-llama/llama-3-70b" → "llama-3-70b")

## [0.1.5] - 2025-01-02

### Changed
- **Groq-focused metadata extraction**: Replaced OpenAI/Anthropic support with comprehensive Groq metadata extraction including timing metrics and precise cost calculation
- **Enhanced cost calculation**: Added support for all Groq models with accurate pricing per million tokens

## [0.1.4] - 2025-01-02

### Added
- **Auto-extracted Groq metadata**: Automatically detects and extracts model, provider, token usage, precise cost calculation, and timing metrics from Groq responses
- **Enhanced observability**: Groq metadata is automatically added to task traces and monitoring dashboard

## [0.1.3] - 2025-01-02

### Changed
- **Cleaner imports**: Users can now import directly with `from swarmflow import SwarmFlow, swarm_task`

## [0.1.2] - 2025-01-02

### Changed
- **Simplified backend configuration**: Hardcoded to localhost:8000 for development

## [0.1.1] - 2025-01-02

### Added
- **Multiple dependency support**: `depends_on()` now accepts multiple dependencies in a single call
- **Backend integration**: Traces are sent to SwarmFlow backend service at localhost:8000

## [0.1.0] - 2024-12-19

### Added
- Initial release of SwarmFlow
- Agent orchestration framework with dependency management
- Built-in retry logic for resilient agent execution
- OpenTelemetry integration for observability
- Real-time monitoring capabilities
- Cycle detection for dependency graphs
- Comprehensive error handling and logging
- `@swarm_task` decorator for easy agent function definition
- `SwarmFlow` class for workflow orchestration

### Features
- Multi-agent workflow orchestration
- Automatic task dependency resolution
- Performance monitoring and tracing
- Production-ready error handling
- Scalable architecture for complex workflows 