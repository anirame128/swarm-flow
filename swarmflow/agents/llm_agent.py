import os
from groq import Groq
from dotenv import load_dotenv
from swarmflow.core.decorator import swarm_task

load_dotenv()

@swarm_task
def summarize_text(text: str) -> str:
    try:
        client = Groq()
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text."},
                {"role": "user", "content": f"Summarize this text:\n{text}"}
            ],
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=False
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"Groq LLM error: {e}")
