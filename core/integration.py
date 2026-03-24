from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

import httpx
from django.conf import settings
from openai import OpenAI

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text()


def get_llm_config() -> dict:
    return {
        "base_url": settings.LLM_BASE_URL,
        "api_key": settings.LLM_API_KEY,
        "model": settings.LLM_MODEL,
        "embedding_model": settings.LLM_EMBEDDING_MODEL,
    }


def _ollama_base_url() -> str:
    """Strip /v1 suffix to get the native Ollama API base."""
    url = settings.LLM_BASE_URL.rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3]
    return url


@lru_cache(maxsize=1)
def llm_client() -> OpenAI:
    config = get_llm_config()
    return OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
    )


def chat(question: str, system_prompt: str | None = None) -> str | None:
    """Send a chat request via the native Ollama /api/chat endpoint.

    Uses the native endpoint rather than /v1/chat/completions because
    Ollama 0.18.x ignores the `think` parameter on the compat API.
    """
    config = get_llm_config()

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": question})

    resp = httpx.post(
        f"{_ollama_base_url()}/api/chat",
        json={
            "model": config["model"],
            "messages": messages,
            "think": False,
            "stream": False,
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def stream_chat(question: str, system_prompt: str | None = None) -> Iterator[str]:
    """Streaming variant of chat(). Yields tokens."""
    config = get_llm_config()

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": question})

    with httpx.stream(
        "POST",
        f"{_ollama_base_url()}/api/chat",
        json={
            "model": config["model"],
            "messages": messages,
            "think": False,
            "stream": True,
        },
        timeout=120.0,
    ) as resp:
        resp.raise_for_status()
        import json
        for line in resp.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            content = data.get("message", {}).get("content", "")
            if content:
                yield content


@lru_cache(maxsize=1)
def embed_client() -> OpenAI:
    """Cached OpenAI client for embeddings. Falls back to main LLM config."""
    config = get_llm_config()
    base_url = settings.LLM_EMBED_BASE_URL or config["base_url"]
    api_key = settings.LLM_EMBED_API_KEY or config["api_key"]
    return OpenAI(api_key=api_key, base_url=base_url)


def embed(text: str, model: str | None = None) -> list[float]:
    """Generate an embedding vector via the OpenAI-compatible embeddings endpoint."""
    config = get_llm_config()
    model_name = model or config["embedding_model"]

    response = embed_client().embeddings.create(model=model_name, input=text)
    return list(response.data[0].embedding)
