"""LLM client with OpenAI Compatible API."""
import os
from openai import OpenAI
from utils.config import settings


def get_llm_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"),
    )


def chat(messages: list[dict], model: str = None) -> str:
    model = model or os.getenv("LLM_MODEL", "deepseek-chat")
    client = get_llm_client()

    # Prepend system message to enforce Chinese responses
    if not any(m.get("role") == "system" for m in messages):
        messages = [{"role": "system", "content": "你是一个数据分析助手。请始终用中文回答用户的问题，包括分析结果、SQL注释、图表标题等全部使用中文。"}] + list(messages)

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        timeout=settings.LLM_TIMEOUT,
    )
    return response.choices[0].message.content or ""
