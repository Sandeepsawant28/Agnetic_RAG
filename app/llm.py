from openai import OpenAI
from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def chat(messages, temperature=0.1) -> str:
    r = client.chat.completions.create(
        model=LLM_MODEL, messages=messages, temperature=temperature
    )
    return r.choices[0].message.content