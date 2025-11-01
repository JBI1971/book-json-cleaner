"""
API Client Wrappers

Simple wrappers for OpenAI and Anthropic APIs.
"""

from .openai_client import get_client as get_openai_client, quick_chat as openai_chat
from .anthropic_client import get_client as get_anthropic_client, quick_chat as anthropic_chat

__all__ = [
    'get_openai_client',
    'openai_chat',
    'get_anthropic_client',
    'anthropic_chat',
]
