# examples/basic_flow.py

from swarmflow.core.flow import SwarmFlow
from swarmflow.core.decorator import swarm_task
from swarmflow.agents.llm_agent import summarize_text

@swarm_task
def fetch_article():
    return """
    SwarmFlow is an open-source multi-agent orchestration engine for AI workflows. 
    It allows developers to build, visualize, and trace DAGs made of LLM tasks. 
    The project is modular, extensible, and aims to standardize agent orchestration.
    """

@swarm_task
def print_result(text):
    print("\n🧠 Final Output:")
    print(text)

if __name__ == "__main__":
    flow = SwarmFlow()
    flow.add(fetch_article)
    flow.add(summarize_text).depends_on("summarize_text", "fetch_article")
    flow.add(print_result).depends_on("print_result", "summarize_text")

    flow.run()
