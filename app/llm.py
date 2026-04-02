"""Ollama client helpers and response compatibility adapters."""

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
    try:
        # Pass timeout if the installed ollama version supports it.
        client = ollama.Client(host=host, timeout=timeout)
    except TypeError:
        # Older versions of the ollama package do not accept a timeout parameter.
        client = ollama.Client(host=host)
    _CLIENT_CACHE[key] = client
    return client


def extract_chat_content(resp) -> str:
    """Extract text content from both legacy dict and pydantic response formats."""
    if resp is None:
        return ""
    # Legacy format: response is a plain dict (older ollama versions).
    if isinstance(resp, dict):
        return (resp.get("message") or {}).get("content") or ""
    # Pydantic format: response is an object with a .message.content attribute.
    try:
        return resp.message.content or ""
    except AttributeError:
        return ""
