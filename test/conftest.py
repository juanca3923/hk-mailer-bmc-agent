"""Valores mínimos de entorno para que `import config` (logger → Settings.load) no falle en pytest."""

from __future__ import annotations

import os

# Settings exige estas claves; load_dotenv(override=False) no las pisa si ya existen.
_MIN_ENV: dict[str, str] = {
    "HTTP_PORT": "8000",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "OLLAMA_MODEL": "qwen3.5:9b",
    "LLM_PROVIDER": "ollama",
    "OPENAI_API_KEY": "",
    "OPENAI_MODEL": "gpt-4o",
    "OPENAI_BASE_URL": "",
    "ANTHROPIC_API_KEY": "",
    "ANTHROPIC_MODEL": "claude-3-5-sonnet-20241022",
    "LANGFUSE_PUBLIC_KEY": "",
    "LANGFUSE_SECRET_KEY": "",
    "LANGFUSE_HOST": "",
    "LANGFUSE_PROMPT_NAME": "",
}

for _key, _val in _MIN_ENV.items():
    os.environ.setdefault(_key, _val)
