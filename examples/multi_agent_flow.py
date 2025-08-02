from swarmflow.core.flow import SwarmFlow
from swarmflow.core.decorator import swarm_task

@swarm_task
def retrieve_context():
    result = "SwarmFlow is an orchestration engine for AI workflows."
    task = retrieve_context._task
    task.metadata = {
        "agent": "RetrieverAgent",
        "model_used": "none",
        "tokens_used": 0,
        "cost_usd": 0.0
    }
    return result

@swarm_task
def summarize_text(text):
    summary = f"Summary: {text[:30]}..."
    task = summarize_text._task
    task.metadata = {
        "agent": "SummarizerAgent",
        "model_used": "gpt-4o",
        "tokens_used": 120,
        "cost_usd": 0.0024
    }
    return summary

@swarm_task
def format_result(text):
    formatted = f"🧠 Final Output:\n{text.upper()}"
    task = format_result._task
    task.metadata = {
        "agent": "FormatterAgent",
        "model_used": "claude-3-haiku",
        "tokens_used": 80,
        "cost_usd": 0.0011
    }
    return formatted

if __name__ == "__main__":
    flow = SwarmFlow()
    flow.add(retrieve_context)
    flow.add(summarize_text).depends_on("summarize_text", "retrieve_context")
    flow.add(format_result).depends_on("format_result", "summarize_text")
    flow.run()