"""
Centralized LLM client factory for ERSim.

Supports two backends:
  - openrouter (default): uses OPENROUTER_API_KEY, routes through OpenRouter
  - ollama: uses local Ollama instance at localhost:11434

Configuration via environment variables:
  ERSIM_BACKEND=ollama|openrouter   (default: openrouter)
  ERSIM_MODEL=<model_id>            (override default model for gameplay)
  ERSIM_GEN_MODEL=<model_id>        (override default model for case generation)
  OPENROUTER_API_KEY=...            (required for openrouter backend)
  OLLAMA_HOST=...                   (optional, default: http://localhost:11434)

Or pass backend="ollama" to get_client() / get_model() programmatically.
"""

import os
from openai import OpenAI


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

_backend: str | None = None  # cached after first call


def _detect_backend(override: str | None = None) -> str:
    global _backend
    if override:
        _backend = override
        return _backend
    if _backend:
        return _backend
    _backend = os.environ.get("ERSIM_BACKEND", "openrouter").lower()
    return _backend


# ---------------------------------------------------------------------------
# Default model maps
# ---------------------------------------------------------------------------

# Models for each backend — gameplay (fast, cheap) and generation (smart)
_MODEL_DEFAULTS = {
    "openrouter": {
        "gameplay": "anthropic/claude-haiku-4-5",
        "generation": "anthropic/claude-opus-4-5",
    },
    "ollama": {
        "gameplay": "glm-4.7-flash",
        "generation": "qwen3.5:27b",
    },
}


def get_model(purpose: str = "gameplay", override: str | None = None, backend: str | None = None) -> str:
    """
    Get the model ID for a given purpose.

    Args:
        purpose: "gameplay" or "generation"
        override: explicit model override (from --model flag)
        backend: explicit backend override
    """
    if override:
        return override

    # Check env overrides
    if purpose == "generation":
        env_model = os.environ.get("ERSIM_GEN_MODEL")
    else:
        env_model = os.environ.get("ERSIM_MODEL")
    if env_model:
        return env_model

    be = _detect_backend(backend)
    return _MODEL_DEFAULTS.get(be, _MODEL_DEFAULTS["openrouter"])[purpose]


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

_client_cache: dict[str, OpenAI] = {}


def get_client(backend: str | None = None) -> OpenAI:
    """
    Get an OpenAI-compatible client for the active backend.

    Ollama exposes an OpenAI-compatible API at /v1, so we use the
    same OpenAI SDK for both backends.
    """
    be = _detect_backend(backend)

    if be in _client_cache:
        return _client_cache[be]

    if be == "ollama":
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        client = OpenAI(
            api_key="ollama",  # Ollama doesn't check this but SDK requires it
            base_url=f"{host}/v1",
        )
    else:
        # OpenRouter
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            env_path = os.path.expanduser("~/.hermes/.env")
            if os.path.exists(env_path):
                for line in open(env_path):
                    line = line.strip()
                    if line.startswith("OPENROUTER_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        break
        if not key:
            raise RuntimeError(
                "OPENROUTER_API_KEY not found. "
                "Set it in your environment or ~/.hermes/.env, "
                "or use --ollama for local inference."
            )
        client = OpenAI(
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
        )

    _client_cache[be] = client
    return client


# ---------------------------------------------------------------------------
# Convenience: reset (for testing)
# ---------------------------------------------------------------------------

def reset():
    """Clear cached client and backend. Used in tests."""
    global _backend
    _backend = None
    _client_cache.clear()
