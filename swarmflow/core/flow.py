import time
import requests
import json
import os
import uuid
from typing import Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

class SwarmFlow:
    """SwarmFlow instance for shared memory and policy enforcement only.
    Task execution is handled by the global TASK_REGISTRY and run() function."""
    
    def __init__(self, api_key: str | None = None):
        self.run_id = str(uuid.uuid4())  # Unique per DAG run
        self.api_key = api_key or os.getenv("SWARMFLOW_API_KEY")
        self.memory = {}  # Shared memory for all tasks in this DAG run
        self.policy = {}  # User-defined DAG-level enforcement rules
    
    def set_memory(self, key, value):
        """Set a value in the shared memory"""
        self.memory[key] = value
        return self
    
    def get_memory(self, key, default=None):
        """Get a value from the shared memory"""
        return self.memory.get(key, default)
    
    def set_policy(self, key: str, value: Any):
        """Set a policy rule"""
        self.policy[key] = value
        return self
    
    def get_policy(self, key: str, default=None):
        """Get a policy rule"""
        return self.policy.get(key, default)