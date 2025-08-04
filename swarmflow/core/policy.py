"""
SwarmFlow Policy Enforcement

Handles run status finalization and policy enforcement rules.
"""

import json
import requests
from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .task import Task

def finalize_run_status(
    tasks: List["Task"], 
    run_id: str, 
    api_key: str | None, 
    memory: Dict[str, Any] = None, 
    policy: Dict[str, Any] = None
):
    """
    Finalize run status and enforce policy rules.
    
    Args:
        tasks: List of all tasks in the workflow
        run_id: Unique identifier for this DAG run
        api_key: API key for authentication
        memory: Shared memory state
        policy: Active policy rules
    """
    statuses = [task.status for task in tasks]
    run_status = "completed" if all(s == "success" for s in statuses) else \
                 "failed" if any(s == "failure" for s in statuses) else "partial"

    # Enforce policy: abort if memory flag is True
    if policy and memory:
        flag = policy.get("abort_on_flag")
        if flag and memory.get(flag):
            run_status = "aborted"
            print(f"[SwarmFlow] 🚨 Policy violation: memory flag '{flag}' is True → aborting run")

        # Enforce policy: abort if cost exceeds max
        max_cost = policy.get("max_cost")
        if max_cost:
            total_cost = sum(t.metadata.get("cost_usd", 0) for t in tasks)
            if total_cost > max_cost:
                run_status = "aborted"
                print(f"[SwarmFlow] 🚨 Policy violation: total cost ${total_cost:.4f} exceeded max ${max_cost} → aborting run")

        # Enforce policy: abort if required memory keys are missing
        required_keys = policy.get("require_outputs", [])
        missing_keys = [k for k in required_keys if memory.get(k) is None]
        if missing_keys:
            run_status = "aborted"
            print(f"[SwarmFlow] 🚨 Policy violation: missing required outputs {missing_keys} → aborting run")

    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key
        res = requests.patch(
            "http://localhost:8000/api/runs/update-status",
            headers=headers,
            data=json.dumps({
                "run_id": run_id,
                "status": run_status,
            })
        )
        res.raise_for_status()
        
        # Finalize memory/policy snapshot
        if api_key and memory is not None and policy is not None:
            try:
                res = requests.post(
                    "http://localhost:8000/api/runs/finalize",
                    headers=headers,
                    data=json.dumps({
                        "run_id": run_id,
                        "memory": _safe_dict(memory),
                        "policy": _safe_dict(policy)
                    })
                )
                res.raise_for_status()
            except Exception as e:
                print(f"[SwarmFlow] ⚠️ Failed to finalize memory/policy: {e}")
    except Exception as e:
        print(f"[SwarmFlow] ⚠️ Failed to update run status: {e}")

def _safe_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Make dictionary JSON serializable by converting non-serializable values to strings."""
    def make_jsonable(v):
        try:
            json.dumps(v)
            return v
        except:
            return str(v)
    return {k: make_jsonable(v) for k, v in d.items()} 