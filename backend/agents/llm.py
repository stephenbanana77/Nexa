"""LLM client with OpenAI Compatible API."""
import os
from openai import OpenAI


def get_llm_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", "https://api.moonshot.cn/v1"),
    )


def chat(messages: list[dict], model: str = "moonshot-v1-8k") -> str:
    client = get_llm_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""
