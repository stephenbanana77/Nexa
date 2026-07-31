"""LLM client with OpenAI Compatible API."""
import os
from openai import OpenAI


def get_llm_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"),
    )


def chat(messages: list[dict], model: str = None) -> str:
    model = model or os.getenv("LLM_MODEL", "deepseek-chat")
    client = get_llm_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""
