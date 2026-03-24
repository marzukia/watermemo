import json
import urllib.request
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from openai import OpenAI

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a prompt from core/prompts/<name>.md"""
    return (PROMPTS_DIR / f"{name}.md").read_text()


def get_llm_config() -> dict:
    """Return LLM connection settings from Django settings."""
    return {
        "base_url": settings.LLM_BASE_URL,
        "api_key": settings.LLM_API_KEY,
        "model": settings.LLM_MODEL,
        "embedding_model": settings.LLM_EMBEDDING_MODEL,
    }


@lru_cache(maxsize=1)
def llm_client() -> OpenAI:
    """Return a cached OpenAI-compatible client."""
    config = get_llm_config()
    return OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
    )


def chat(question: str, system_prompt: str | None = None) -> str | None:
    """Send a question to the LLM and return the response as a string."""
    config = get_llm_config()
    client = llm_client()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=config["model"],
        messages=messages,
    )
    return response.choices[0].message.content


def stream_chat(question: str, system_prompt: str | None = None) -> Iterator[str]:
    """Stream tokens from the LLM, yielding each content delta as a string."""
    config = get_llm_config()
    client = llm_client()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": question})

    with client.chat.completions.create(
        model=config["model"],
        messages=messages,
        stream=True,
    ) as stream:
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


def embed(text: str, model: str | None = None) -> list[float]:
    """Generate an embedding vector using Ollama's native /api/embed endpoint.

    Uses LLM_EMBED_BASE_URL if set, otherwise falls back to LLM_BASE_URL.
    This allows chat and embeddings to use different providers — e.g. OpenRouter
    for chat and a local/remote Ollama instance for nomic-embed-text.

    The base_url /v1 suffix is stripped to reach the Ollama host-level API.
    """
    config = get_llm_config()
    embed_base_url = settings.LLM_EMBED_BASE_URL or config["base_url"]
    base = embed_base_url.removesuffix("/v1")
    model_name = model or config["embedding_model"]

    payload = json.dumps({"model": model_name, "input": text}).encode()
    req = urllib.request.Request(
        f"{base}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    return result["embeddings"][0]
