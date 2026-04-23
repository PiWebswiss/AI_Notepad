######
# This file was developed with the assistance of OpenAI Codex (ChatGPT).
######

"""Ollama client helpers."""

import ollama

# Reuse the same client instance for each (host, timeout) pair to avoid
# creating a new HTTP connection on every request.
_CLIENT_CACHE = {}


def get_ollama_client(host: str, timeout: float):
    """Create and cache one Ollama client per host/timeout tuple."""
    key = (host, float(timeout))
    client = _CLIENT_CACHE.get(key)
    if client is not None:
        return client
    client = ollama.Client(host=host, timeout=timeout)
    _CLIENT_CACHE[key] = client
    return client


def extract_chat_content(resp) -> str:
    """Extract text content from an Ollama chat response (Pydantic model)."""
    if resp is None:
        return ""
    return resp.message.content or ""
