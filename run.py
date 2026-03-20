#!/usr/bin/env python3
"""
ERSim launcher.

Usage:
  python run.py                    # OpenRouter backend (default)
  python run.py --ollama           # Local Ollama backend
  python run.py --ollama --model qwen3:30b  # Local with specific model
  python run.py --port 8080        # Custom port

Environment variables (alternative to flags):
  ERSIM_BACKEND=ollama|openrouter
  ERSIM_MODEL=<model_id>
  ERSIM_GEN_MODEL=<model_id>
"""

import argparse
import os
import sys


def check_ollama():
    """Verify Ollama is running and has at least one model."""
    try:
        import urllib.request
        import json
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        req = urllib.request.Request(f"{host}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            if not models:
                print("WARNING: Ollama is running but has no models.")
                print("  Run: ollama pull glm-4.7-flash")
                sys.exit(1)
            return models
    except Exception as e:
        print(f"ERROR: Cannot reach Ollama at {os.environ.get('OLLAMA_HOST', 'http://localhost:11434')}")
        print(f"  {e}")
        print("  Make sure Ollama is running: ollama serve")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="ERSim — Emergency Room Simulator")
    parser.add_argument("--ollama", action="store_true",
                        help="Use local Ollama for inference (default: OpenRouter)")
    parser.add_argument("--model", type=str, default=None,
                        help="Override gameplay model ID")
    parser.add_argument("--gen-model", type=str, default=None,
                        help="Override case generation model ID")
    parser.add_argument("--port", type=int, default=8000,
                        help="API server port (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="API server host (default: 0.0.0.0)")
    args = parser.parse_args()

    # Set backend
    if args.ollama:
        os.environ["ERSIM_BACKEND"] = "ollama"
    elif "ERSIM_BACKEND" not in os.environ:
        os.environ["ERSIM_BACKEND"] = "openrouter"

    # Set model overrides
    if args.model:
        os.environ["ERSIM_MODEL"] = args.model
    if args.gen_model:
        os.environ["ERSIM_GEN_MODEL"] = args.gen_model

    # Import after env is set
    from llm import _detect_backend, get_model

    backend = _detect_backend()
    gameplay_model = get_model("gameplay")
    gen_model = get_model("generation")

    print(f"ERSim starting...")
    print(f"  Backend:    {backend}")
    print(f"  Gameplay:   {gameplay_model}")
    print(f"  Generation: {gen_model}")

    # Backend-specific checks
    if backend == "ollama":
        models = check_ollama()
        print(f"  Ollama models: {', '.join(models[:5])}")
        if gameplay_model not in models:
            # Try partial match (ollama uses name:tag format)
            base = gameplay_model.split(":")[0]
            matches = [m for m in models if m.startswith(base)]
            if not matches:
                print(f"  WARNING: '{gameplay_model}' not found in Ollama.")
                print(f"    Run: ollama pull {gameplay_model}")
    else:
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            env_path = os.path.expanduser("~/.hermes/.env")
            if os.path.exists(env_path):
                for line in open(env_path):
                    if line.strip().startswith("OPENROUTER_API_KEY="):
                        key = "found"
                        break
        if not key:
            print("  WARNING: OPENROUTER_API_KEY not found")

    print(f"  Server:     http://{args.host}:{args.port}")
    print(flush=True)

    # Launch uvicorn
    # ws_ping_interval/timeout bumped for slow local LLM inference
    import uvicorn
    uvicorn.run("api.main:app", host=args.host, port=args.port, reload=False,
                log_level="info",
                ws_ping_interval=30,
                ws_ping_timeout=120)


if __name__ == "__main__":
    main()
