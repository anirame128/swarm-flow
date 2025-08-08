"""
SwarmFlow Pricing

Cost estimation functions for various LLM providers.
"""

def estimate_cost_openai(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost for OpenAI models based on current pricing."""
    # OpenAI pricing per 1M tokens (as of 2025)
    pricing = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4.1": {"input": 2.00, "output": 8.00},
        "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
        "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
        "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
        "gpt-4o-2024-08-06": {"input": 2.50, "output": 10.00},
        "o3-mini": {"input": 1.10, "output": 4.40},
        "o3": {"input": 2.00, "output": 8.00},
        "o4-mini": {"input": 1.10, "output": 4.40},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "gpt-3.5-turbo-0125": {"input": 0.50, "output": 1.50},
    }
    
    # Find the model pricing (try exact match first, then partial)
    model_pricing = None
    for model, prices in pricing.items():
        if model_name == model or model_name.startswith(model):
            model_pricing = prices
            break
    
    if not model_pricing:
        # Default to gpt-4o-mini pricing if model not found
        model_pricing = pricing["gpt-4o-mini"]
    
    # Calculate cost in USD
    input_cost = (prompt_tokens / 1_000_000) * model_pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * model_pricing["output"]
    total_cost = input_cost + output_cost
    
    return total_cost

def estimate_cost_groq(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost for Groq models based on current pricing."""
    # Groq pricing per 1M tokens
    pricing = {
        "llama3-8b-8192": {"input": 0.05, "output": 0.10},
        "llama3-70b-8192": {"input": 0.59, "output": 0.87},
        "llama3.1-8b": {"input": 0.05, "output": 0.10},
        "llama3.1-70b": {"input": 0.59, "output": 0.87},
        "llama3.1-405b": {"input": 2.87, "output": 4.25},
        "mixtral-8x7b-32768": {"input": 0.14, "output": 0.42},
        "gemma2-9b": {"input": 0.10, "output": 0.10},
        "gemma2-27b": {"input": 0.20, "output": 0.20},
    }
    
    # Find the model pricing
    model_pricing = pricing.get(model_name, pricing["llama3-8b-8192"])
    
    # Calculate cost in USD
    input_cost = (prompt_tokens / 1_000_000) * model_pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * model_pricing["output"]
    total_cost = input_cost + output_cost
    
    return total_cost

def estimate_cost_anthropic(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost for Anthropic models based on current pricing."""
    # Anthropic pricing per 1M tokens
    pricing = {
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
        "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    }
    
    # Find the model pricing
    model_pricing = pricing.get(model_name, pricing["claude-3-5-sonnet-20241022"])
    
    # Calculate cost in USD
    input_cost = (prompt_tokens / 1_000_000) * model_pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * model_pricing["output"]
    total_cost = input_cost + output_cost
    
    return total_cost
