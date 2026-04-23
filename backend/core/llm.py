"""
LLM setup for Gemma 4 via Ollama + LangChain.

Provides ChatOllama initialization with Gemma 4's recommended sampling
parameters (temperature=1.0, top_p=0.95, top_k=64) and an Ollama
health check function.
"""

import os
import httpx
from langchain_ollama import ChatOllama


def get_llm() -> ChatOllama:
    """
    Create a ChatOllama instance configured for Gemma 4.

    Uses sampling parameters from the official Gemma 4 model card:
      - temperature=1.0
      - top_p=0.95
      - top_k=64
    """
    model = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    llm = ChatOllama(
        model=model,
        base_url=base_url,
        temperature=1.0,
        top_p=0.95,
        top_k=64,
    )
    print(f"ChatOllama initialized — model={model}, base_url={base_url}")
    return llm


def get_llm_with_tools(llm: ChatOllama, tools: list) -> ChatOllama:
    """
    Bind a list of tool functions to a ChatOllama instance.

    Args:
        llm: The base ChatOllama instance.
        tools: List of @tool decorated functions from make_tools().

    Returns:
        A new ChatOllama instance with tools bound.
    """
    if not tools:
        print("[LLM] No tools to bind")
        return llm

    tool_names = [t.name for t in tools]
    print(f"[LLM] Binding {len(tools)} tools: {tool_names}")

    bound = llm.bind_tools(tools)
    print(f"[LLM] Tools bound successfully")
    return bound


async def check_ollama_status() -> dict:
    """
    Check if Ollama is running and the target model is available.

    Returns:
        Dict with {status, model, models_available} on success.

    Raises:
        ConnectionError: If Ollama is not reachable.
        ValueError: If the target model is not pulled.
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    target_model = os.getenv("OLLAMA_MODEL", "gemma4:e2b")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        raise ConnectionError(
            f"Ollama is not running at {base_url}. "
            f"Start it with: ollama serve\n"
            f"Error: {e}"
        )

    data = response.json()
    models = [m.get("name", "") for m in data.get("models", [])]

    # Check if target model (or a variant of it) is available
    model_found = any(target_model in m for m in models)

    if not model_found:
        raise ValueError(
            f"Model '{target_model}' not found in Ollama. "
            f"Available models: {models}\n"
            f"Pull it with: ollama pull {target_model}"
        )

    return {
        "status": "ok",
        "model": target_model,
        "models_available": models,
    }
