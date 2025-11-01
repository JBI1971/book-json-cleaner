from __future__ import annotations
import os
from anthropic import Anthropic

def get_client() -> Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return Anthropic(api_key=key)

def quick_chat(prompt: str) -> str:
    client = get_client()
    resp = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.content[0].text
